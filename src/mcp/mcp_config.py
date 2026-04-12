"""
MCP Server Configuration and Agent-to-Tools Mapping.

Defines which MCP servers are available and which tools each agent specialization
has access to. Uses DuckDuckGo (free, no API key) for web search.
"""

from typing import Dict, List, Any

# ─────────────────────────────────────────────────────────────────────────────
# MCP Server Definitions
# Each server has: name, command, args, and optional env vars
# ─────────────────────────────────────────────────────────────────────────────

MCP_SERVERS: Dict[str, Dict[str, Any]] = {
    "fetch": {
        "name": "fetch",
        "description": "Fetch web content from any URL",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
        "tools": ["fetch"],
    },
    "duckduckgo": {
        "name": "duckduckgo",
        "description": "Free web search via DuckDuckGo (no API key required)",
        "command": "uvx",
        "args": ["duckduckgo-mcp-server"],
        "env": {},
        "tools": ["duckduckgo_web_search", "duckduckgo_news_search"],
    },
    "filesystem": {
        "name": "filesystem",
        "description": "Read and write files on the local filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        "env": {},
        "tools": ["read_file", "write_file", "list_directory", "search_files", "create_directory"],
    },
    "memory": {
        "name": "memory",
        "description": "Persistent knowledge graph memory for agents",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {},
        "tools": ["create_entities", "create_relations", "add_observations",
                  "delete_entities", "delete_observations", "delete_relations",
                  "read_graph", "search_nodes", "open_nodes"],
    },
    "sequential_thinking": {
        "name": "sequential_thinking",
        "description": "Structured multi-step reasoning tool",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "env": {},
        "tools": ["sequentialthinking"],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Agent Specialization → Available MCP Tools Mapping
# ─────────────────────────────────────────────────────────────────────────────

# Tools available to ALL agents by default
DEFAULT_TOOLS = ["fetch"]

# Additional tools per specialization
AGENT_TOOLS: Dict[str, List[str]] = {
    # Coordinator — orchestrates everything, needs memory + reasoning
    "coordinator": [
        "fetch",
        "duckduckgo_web_search",
        "duckduckgo_news_search",
        "create_entities",
        "add_observations",
        "search_nodes",
        "read_graph",
        "sequentialthinking",
    ],

    # Research cluster — web search is their primary capability
    "researcher": [
        "fetch",
        "duckduckgo_web_search",
        "duckduckgo_news_search",
        "create_entities",
        "add_observations",
        "search_nodes",
        "read_graph",
        "sequentialthinking",
    ],
    "fact_checker": [
        "fetch",
        "duckduckgo_web_search",
        "duckduckgo_news_search",
    ],
    "trend_analyst": [
        "fetch",
        "duckduckgo_web_search",
        "duckduckgo_news_search",
    ],

    # Analyst cluster — search + reasoning
    "analyst": [
        "fetch",
        "duckduckgo_web_search",
        "sequentialthinking",
    ],
    "data_analyst": [
        "fetch",
        "duckduckgo_web_search",
        "sequentialthinking",
    ],
    "market_analyst": [
        "fetch",
        "duckduckgo_web_search",
        "duckduckgo_news_search",
        "sequentialthinking",
    ],

    # Technical cluster — filesystem + reasoning
    "technical": [
        "fetch",
        "read_file",
        "write_file",
        "list_directory",
        "search_files",
        "sequentialthinking",
    ],
    "coder": [
        "fetch",
        "read_file",
        "write_file",
        "list_directory",
        "search_files",
        "create_directory",
    ],
    "architect": [
        "fetch",
        "read_file",
        "write_file",
        "list_directory",
        "search_files",
        "sequentialthinking",
    ],

    # Creative cluster — fetch for inspiration/references
    "creative": [
        "fetch",
        "duckduckgo_web_search",
    ],
    "writer": [
        "fetch",
        "duckduckgo_web_search",
    ],
    "designer": [
        "fetch",
    ],

    # General
    "general": [
        "fetch",
    ],

    # Tutor
    "tutor": [
        "fetch",
        "duckduckgo_web_search",
        "read_file",
    ],
}


def get_tools_for_specialization(specialization: str) -> List[str]:
    """Return the list of tool names available for a given agent specialization."""
    return AGENT_TOOLS.get(specialization, DEFAULT_TOOLS)


def get_servers_for_tools(tool_names: List[str]) -> List[str]:
    """Return the list of MCP server names needed to provide the given tools."""
    needed_servers = set()
    for server_name, server_config in MCP_SERVERS.items():
        for tool in tool_names:
            if tool in server_config["tools"]:
                needed_servers.add(server_name)
                break
    return list(needed_servers)
