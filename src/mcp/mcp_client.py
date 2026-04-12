"""
MCP Client — Executes MCP tool calls by spawning MCP server subprocesses.

This client implements a lightweight MCP protocol handler that:
1. Spawns MCP server processes (npx/uvx based)
2. Sends JSON-RPC tool call requests
3. Returns tool results to the calling agent

The client is used by agents during their tool-calling loop to execute
real MCP tools (web search, file operations, memory, etc.)
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional
from src.core.logging_config import get_logger

logger = get_logger("mcp_client")


class MCPToolResult:
    """Result from an MCP tool call."""

    def __init__(self, tool_name: str, content: str, is_error: bool = False):
        self.tool_name = tool_name
        self.content = content
        self.is_error = is_error

    def __repr__(self):
        status = "ERROR" if self.is_error else "OK"
        return f"MCPToolResult({self.tool_name}, {status}, {self.content[:100]}...)"


class MCPServerProcess:
    """
    Manages a single MCP server subprocess.
    Communicates via stdin/stdout using JSON-RPC 2.0.
    """

    def __init__(self, server_name: str, command: str, args: List[str], env: Dict[str, str] = None):
        self.server_name = server_name
        self.command = command
        self.args = args
        self.env = env or {}
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._initialized = False

    async def start(self) -> bool:
        """Start the MCP server subprocess."""
        try:
            full_env = {**os.environ, **self.env}
            cmd = [self.command] + self.args

            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env
            )

            # Initialize the MCP session
            await self._initialize()
            self._initialized = True
            logger.info(f"MCP server '{self.server_name}' started (PID: {self.process.pid})")
            return True

        except FileNotFoundError:
            logger.warning(f"MCP server '{self.server_name}' command not found: {self.command}")
            return False
        except Exception as e:
            logger.error(f"Failed to start MCP server '{self.server_name}': {e}")
            return False

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request and read the response."""
        if not self.process or self.process.returncode is not None:
            raise RuntimeError(f"MCP server '{self.server_name}' is not running")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {}
        }

        request_bytes = (json.dumps(request) + "\n").encode("utf-8")
        self.process.stdin.write(request_bytes)
        await self.process.stdin.drain()

        # Read response line
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=30.0
            )
            if not response_line:
                raise RuntimeError("MCP server closed connection")
            return json.loads(response_line.decode("utf-8").strip())
        except asyncio.TimeoutError:
            raise RuntimeError(f"MCP server '{self.server_name}' timed out")

    async def _initialize(self):
        """Send MCP initialize handshake."""
        response = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": False},
                "sampling": {}
            },
            "clientInfo": {
                "name": "CustodianAIArmy",
                "version": "1.0.0"
            }
        })

        if "error" in response:
            raise RuntimeError(f"MCP init error: {response['error']}")

        # Send initialized notification
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        self.process.stdin.write((json.dumps(notif) + "\n").encode("utf-8"))
        await self.process.stdin.drain()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call a tool on this MCP server."""
        try:
            response = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })

            if "error" in response:
                return MCPToolResult(
                    tool_name=tool_name,
                    content=f"Tool error: {response['error'].get('message', str(response['error']))}",
                    is_error=True
                )

            result = response.get("result", {})
            content_blocks = result.get("content", [])

            # Extract text content from content blocks
            text_parts = []
            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

            content = "\n".join(text_parts) if text_parts else str(result)
            is_error = result.get("isError", False)

            return MCPToolResult(tool_name=tool_name, content=content, is_error=is_error)

        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}' on '{self.server_name}': {e}")
            return MCPToolResult(
                tool_name=tool_name,
                content=f"Failed to execute tool '{tool_name}': {str(e)}",
                is_error=True
            )

    async def stop(self):
        """Stop the MCP server subprocess."""
        if self.process and self.process.returncode is None:
            try:
                self.process.stdin.close()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except Exception:
                self.process.kill()
            logger.info(f"MCP server '{self.server_name}' stopped")


class MCPToolExecutor:
    """
    High-level MCP tool executor used by agents.

    Manages a pool of MCP server processes and routes tool calls
    to the appropriate server. Servers are started lazily on first use.
    """

    def __init__(self, specialization: str):
        from src.mcp.mcp_config import get_tools_for_specialization, get_servers_for_tools, MCP_SERVERS
        self.specialization = specialization
        self.available_tools = get_tools_for_specialization(specialization)
        self.needed_servers = get_servers_for_tools(self.available_tools)
        self.mcp_servers_config = MCP_SERVERS
        self._servers: Dict[str, MCPServerProcess] = {}
        self._started = False
        self.logger = get_logger(f"mcp_executor.{specialization}")

    async def start(self):
        """Start all needed MCP server processes."""
        if self._started:
            return

        for server_name in self.needed_servers:
            config = self.mcp_servers_config.get(server_name)
            if not config:
                continue

            server = MCPServerProcess(
                server_name=server_name,
                command=config["command"],
                args=config["args"],
                env=config.get("env", {})
            )
            success = await server.start()
            if success:
                self._servers[server_name] = server
            else:
                self.logger.warning(f"Could not start MCP server '{server_name}' — tool will be unavailable")

        self._started = True

    async def stop(self):
        """Stop all MCP server processes."""
        for server in self._servers.values():
            await server.stop()
        self._servers.clear()
        self._started = False

    def _find_server_for_tool(self, tool_name: str) -> Optional[MCPServerProcess]:
        """Find which running server provides the given tool."""
        from src.mcp.mcp_config import MCP_SERVERS
        for server_name, config in MCP_SERVERS.items():
            if tool_name in config["tools"]:
                return self._servers.get(server_name)
        return None

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute a tool call, routing to the correct MCP server."""
        if not self._started:
            await self.start()

        if tool_name not in self.available_tools:
            return MCPToolResult(
                tool_name=tool_name,
                content=f"Tool '{tool_name}' is not available for {self.specialization} agents.",
                is_error=True
            )

        server = self._find_server_for_tool(tool_name)
        if not server:
            return MCPToolResult(
                tool_name=tool_name,
                content=f"MCP server for tool '{tool_name}' is not running. Please ensure the required MCP server is installed.",
                is_error=True
            )

        return await server.call_tool(tool_name, arguments)

    def get_tool_definitions_openai(self) -> List[Dict[str, Any]]:
        """
        Return tool definitions in OpenAI function calling format.
        Used by Groq, NIM, and other OpenAI-compatible providers.
        """
        return _OPENAI_TOOL_DEFINITIONS.get_for_tools(self.available_tools)

    def get_tool_definitions_anthropic(self) -> List[Dict[str, Any]]:
        """
        Return tool definitions in Anthropic Claude format.
        """
        return _ANTHROPIC_TOOL_DEFINITIONS.get_for_tools(self.available_tools)

    def get_tool_definitions_gemini(self) -> List[Dict[str, Any]]:
        """
        Return tool definitions in Google Gemini function declarations format.
        """
        return _GEMINI_TOOL_DEFINITIONS.get_for_tools(self.available_tools)


# ─────────────────────────────────────────────────────────────────────────────
# Tool Definition Registries (per provider format)
# ─────────────────────────────────────────────────────────────────────────────

class _ToolDefinitionRegistry:
    """Base registry for tool definitions."""

    def __init__(self, definitions: List[Dict[str, Any]]):
        self._all = {d["name"] if "name" in d else d.get("function", {}).get("name"): d
                     for d in definitions}

    def get_for_tools(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        return [self._all[name] for name in tool_names if name in self._all]


# ── OpenAI / Groq / NIM format ────────────────────────────────────────────────
_OPENAI_TOOL_DEFINITIONS = _ToolDefinitionRegistry([
    {
        "type": "function",
        "name": "fetch",
        "function": {
            "name": "fetch",
            "description": "Fetch the content of a web page or URL. Returns the page content as text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch content from"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "Maximum number of characters to return (default: 5000)",
                        "default": 5000
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "name": "duckduckgo_web_search",
        "function": {
            "name": "duckduckgo_web_search",
            "description": "Search the web using DuckDuckGo. Returns a list of search results with titles, URLs, and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "name": "duckduckgo_news_search",
        "function": {
            "name": "duckduckgo_news_search",
            "description": "Search for recent news articles using DuckDuckGo News.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The news search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of news articles to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "name": "read_file",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to read"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "name": "write_file",
        "function": {
            "name": "write_file",
            "description": "Write content to a file on the filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to write to"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "name": "list_directory",
        "function": {
            "name": "list_directory",
            "description": "List the contents of a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to list"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "name": "search_files",
        "function": {
            "name": "search_files",
            "description": "Search for files matching a pattern in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory to search in"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "The search pattern (glob or regex)"
                    }
                },
                "required": ["path", "pattern"]
            }
        }
    },
    {
        "type": "function",
        "name": "create_directory",
        "function": {
            "name": "create_directory",
            "description": "Create a new directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to create"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "name": "create_entities",
        "function": {
            "name": "create_entities",
            "description": "Create new entities in the knowledge graph memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "description": "List of entities to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "entityType": {"type": "string"},
                                "observations": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    }
                },
                "required": ["entities"]
            }
        }
    },
    {
        "type": "function",
        "name": "add_observations",
        "function": {
            "name": "add_observations",
            "description": "Add new observations to existing entities in the knowledge graph.",
            "parameters": {
                "type": "object",
                "properties": {
                    "observations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entityName": {"type": "string"},
                                "contents": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    }
                },
                "required": ["observations"]
            }
        }
    },
    {
        "type": "function",
        "name": "search_nodes",
        "function": {
            "name": "search_nodes",
            "description": "Search for nodes in the knowledge graph by query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant nodes"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "name": "read_graph",
        "function": {
            "name": "read_graph",
            "description": "Read the entire knowledge graph.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "name": "sequentialthinking",
        "function": {
            "name": "sequentialthinking",
            "description": "Use structured sequential thinking to reason through complex problems step by step.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "The current thinking step"
                    },
                    "nextThoughtNeeded": {
                        "type": "boolean",
                        "description": "Whether another thinking step is needed"
                    },
                    "thoughtNumber": {
                        "type": "integer",
                        "description": "Current thought number"
                    },
                    "totalThoughts": {
                        "type": "integer",
                        "description": "Estimated total thoughts needed"
                    }
                },
                "required": ["thought", "nextThoughtNeeded", "thoughtNumber", "totalThoughts"]
            }
        }
    },
])


# ── Anthropic Claude format ────────────────────────────────────────────────────
def _openai_to_anthropic(openai_def: Dict[str, Any]) -> Dict[str, Any]:
    """Convert OpenAI tool definition to Anthropic format."""
    fn = openai_def.get("function", openai_def)
    return {
        "name": fn["name"],
        "description": fn.get("description", ""),
        "input_schema": fn.get("parameters", {"type": "object", "properties": {}})
    }


_ANTHROPIC_TOOL_DEFINITIONS = _ToolDefinitionRegistry([
    _openai_to_anthropic(d) for d in _OPENAI_TOOL_DEFINITIONS._all.values()
])


# ── Google Gemini format ───────────────────────────────────────────────────────
def _openai_to_gemini(openai_def: Dict[str, Any]) -> Dict[str, Any]:
    """Convert OpenAI tool definition to Gemini function declaration format."""
    fn = openai_def.get("function", openai_def)
    return {
        "name": fn["name"],
        "description": fn.get("description", ""),
        "parameters": fn.get("parameters", {"type": "object", "properties": {}})
    }


_GEMINI_TOOL_DEFINITIONS = _ToolDefinitionRegistry([
    _openai_to_gemini(d) for d in _OPENAI_TOOL_DEFINITIONS._all.values()
])
