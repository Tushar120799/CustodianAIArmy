"""
NVIDIA NIM Agent implementation
Uses NVIDIA's NIM API (OpenAI-compatible) for free/open-source model inference.
Supports Llama 3.3 70B, Qwen 2.5 Coder, Mistral Large, and other NIM-hosted models.
Get your free API key at: https://build.nvidia.com

MCP Tool Calling:
  Each agent specialization has a set of MCP tools available (web search,
  filesystem, memory, etc.). When the model requests a tool call, this agent
  executes it via the MCPToolExecutor and feeds the result back to the model.
"""

import httpx
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentMessage, AgentStatus, AgentType, AgentCapability
from src.core.config import settings
from src.core.logging_config import get_logger

# Directory where prompt .md files are stored
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

NIM_API_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"

# Maximum tool-calling iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 5


def _load_prompt(filename: str) -> str:
    """Load a prompt from a .md file in the prompts directory."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        lines = content.splitlines()
        if lines and lines[0].startswith("#"):
            content = "\n".join(lines[1:]).strip()
        return content
    except FileNotFoundError:
        return ""


class NIMAgent(BaseAgent):
    """Agent powered by NVIDIA NIM API (OpenAI-compatible, free tier available)"""

    def __init__(
        self,
        agent_id: str = None,
        name: str = "NIMAgent",
        agent_type: AgentType = AgentType.MAIN,
        specialization: str = "general",
        capabilities: List[AgentCapability] = None,
        api_key: str = None,
        model: str = None
    ):
        default_capabilities = [
            AgentCapability(
                name="text_generation",
                description="Generate human-like text responses using NVIDIA NIM models",
                parameters={"max_tokens": 2048, "temperature": 0.7}
            ),
            AgentCapability(
                name="conversation",
                description="Engage in natural conversations with open-source LLMs",
                parameters={"context_window": 8192}
            ),
            AgentCapability(
                name="code_generation",
                description="Generate and explain code using powerful open-source models",
                parameters={"timeout": 60}
            ),
            AgentCapability(
                name="tool_use",
                description="Use MCP tools (web search, filesystem, memory) to augment responses",
                parameters={"max_iterations": MAX_TOOL_ITERATIONS}
            ),
        ]
        if capabilities:
            default_capabilities.extend(capabilities)
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=agent_type,
            capabilities=default_capabilities
        )
        self.specialization = specialization
        # Allow runtime override of API key (for per-user keys)
        self._api_key_override = api_key
        self._model_override = model

        # Lazy-initialized MCP tool executor
        self._mcp_executor = None

        self.logger.info(f"NIMAgent {self.name} initialized with specialization: {specialization}")

    def _get_api_key(self) -> str:
        """Get the effective API key (user override > server default)"""
        return self._api_key_override or settings.NIM_API_KEY or ""

    def _get_model(self) -> str:
        """Get the effective model name"""
        return self._model_override or settings.NIM_MODEL or NIM_DEFAULT_MODEL

    def _get_mcp_executor(self):
        """Get or create the MCP tool executor for this agent's specialization."""
        if not settings.MCP_ENABLED:
            return None
        if self._mcp_executor is None:
            try:
                from src.mcp.mcp_client import MCPToolExecutor
                self._mcp_executor = MCPToolExecutor(self.specialization)
            except Exception as e:
                self.logger.warning(f"Could not initialize MCP executor: {e}")
                return None
        return self._mcp_executor

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message using NVIDIA NIM"""
        try:
            self.update_status(AgentStatus.BUSY)

            if self.specialization == "coordinator":
                task = {
                    "id": f"task_{message.id}",
                    "type": "delegated_task",
                    "description": message.content,
                    "parameters": message.metadata
                }
                task_result = await self.execute_task(task)
                response_content = task_result.get("result", "Task completed, but no result was returned.")
                if task_result.get("status") == "failed":
                    response_content = f"Sorry, the task failed. Error: {task_result.get('error')}"

                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    content=response_content,
                    message_type="text",
                    metadata={"original_message_id": message.id, "delegated_task": True, "provider": "nvidia_nim"}
                )

            system_prompt = self._get_system_prompt()
            response = await self._call_nim_api(
                system_prompt=system_prompt,
                user_message=message.content,
                context=message.metadata.get("context", {}),
                history=message.metadata.get("history", [])
            )
            formatted_response = self._format_code_blocks(response)
            response_message = AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content=formatted_response,
                message_type="text",
                metadata={
                    "original_message_id": message.id,
                    "agent_specialization": self.specialization,
                    "provider": "nvidia_nim",
                    "model": self._get_model(),
                    "processing_time": (datetime.utcnow() - message.timestamp).total_seconds()
                }
            )
            self.update_status(AgentStatus.IDLE)
            return response_message
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            self.update_status(AgentStatus.ERROR)
            return AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content=f"Error processing your request: {str(e)}",
                message_type="error",
                metadata={"error": str(e), "original_message_id": message.id}
            )

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task using NVIDIA NIM"""
        try:
            self.update_status(AgentStatus.BUSY)
            task_type = task.get("type", "general")
            task_description = task.get("description", "")
            task_parameters = task.get("parameters", {})

            system_prompt = self._get_task_prompt(task_type)
            response = await self._call_nim_api(
                system_prompt=system_prompt,
                user_message=task_description,
                context=task_parameters,
            )
            result = {
                "task_id": task.get("id", "unknown"),
                "status": "completed",
                "result": response,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "execution_time": datetime.utcnow().isoformat(),
                "specialization": self.specialization,
                "provider": "nvidia_nim",
                "model": self._get_model()
            }
            self.update_status(AgentStatus.IDLE)
            return result
        except Exception as e:
            self.logger.error(f"Error executing task: {str(e)}")
            self.update_status(AgentStatus.ERROR)
            return {
                "task_id": task.get("id", "unknown"),
                "status": "failed",
                "error": str(e),
                "agent_id": self.agent_id,
                "agent_name": self.name
            }

    def _get_system_prompt(self) -> str:
        """Get system prompt based on agent specialization."""
        prompt_file_map = {
            "general": "general.md",
            "analyst": "analyst.md",
            "data_analyst": "data_analyst.md",
            "market_analyst": "market_analyst.md",
            "creative": "creative.md",
            "writer": "writer.md",
            "designer": "designer.md",
            "technical": "technical.md",
            "coder": "coder.md",
            "architect": "architect.md",
            "researcher": "researcher.md",
            "fact_checker": "fact_checker.md",
            "trend_analyst": "trend_analyst.md",
            "tutor": "tutor.md",
            "coordinator": "coordinator.md",
        }
        filename = prompt_file_map.get(self.specialization)
        if filename:
            loaded = _load_prompt(filename)
            if loaded:
                return loaded
        fallbacks = {
            "general": "You are a helpful AI assistant powered by NVIDIA NIM. Provide accurate, helpful, and engaging responses.",
            "analyst": "You are a data analyst AI powered by NVIDIA NIM. Focus on analytical thinking, data interpretation, and insights.",
            "creative": "You are a creative AI assistant powered by NVIDIA NIM. Focus on creative writing, brainstorming, and innovative solutions.",
            "technical": "You are a technical AI assistant powered by NVIDIA NIM. Focus on technical accuracy, problem-solving, and detailed explanations.",
            "researcher": "You are a research AI assistant powered by NVIDIA NIM. Focus on thorough research, fact-checking, and comprehensive analysis.",
            "tutor": "You are an expert, encouraging programming tutor powered by NVIDIA NIM. Help students learn programming concepts clearly and effectively.",
            "coordinator": "You are Custodian AI — an intelligent orchestrator powered by NVIDIA NIM. Adopt the persona of the best expert and answer the user's question directly.",
        }
        return fallbacks.get(self.specialization, fallbacks["general"])

    def _get_task_prompt(self, task_type: str) -> str:
        """Get task-specific system prompt."""
        task_file_map = {
            "analysis": "task_analysis.md",
            "writing": "task_writing.md",
            "coding": "task_coding.md",
            "research": "task_research.md",
            "planning": "task_planning.md",
        }
        filename = task_file_map.get(task_type)
        if filename:
            loaded = _load_prompt(filename)
            if loaded:
                return loaded
        fallbacks = {
            "analysis": "You are an expert analyst. Provide thorough analysis with clear insights and recommendations.",
            "writing": "You are an expert writer. Create well-structured, engaging, and high-quality content.",
            "coding": "You are an expert programmer. Provide clean, efficient, and well-documented code solutions.",
            "research": "You are an expert researcher. Provide comprehensive, accurate, and well-sourced information.",
            "planning": "You are an expert planner. Create detailed, actionable, and realistic plans.",
        }
        return fallbacks.get(task_type, self._get_system_prompt())

    async def _call_nim_api(
        self,
        system_prompt: str,
        user_message: str,
        context: Dict[str, Any] = None,
        history: list = None
    ) -> str:
        """
        Call the NVIDIA NIM API (OpenAI-compatible) with MCP tool calling support.

        Implements an agentic loop:
        1. Send message to NIM with available tool definitions
        2. If model requests tool calls → execute via MCP → feed results back
        3. Repeat until model returns a final text response (or max iterations)
        """
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError(
                "NIM_API_KEY not configured. Get your free key at https://build.nvidia.com"
            )

        model = self._get_model()

        # Build multi-turn conversation from history
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history:
                sender = msg.get("sender", "")
                content = msg.get("content", "")
                if not content:
                    continue
                role = "user" if sender == "You" else "assistant"
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Get MCP tool definitions for this agent (OpenAI-compatible format)
        mcp_executor = self._get_mcp_executor()
        tool_definitions = []
        if mcp_executor:
            tool_definitions = mcp_executor.get_tool_definitions_openai()

        # Determine if this message is simple/conversational (skip tools for those)
        _simple_msg = user_message.strip()
        _is_simple = (
            len(_simple_msg) < 20 and
            not any(kw in _simple_msg.lower() for kw in [
                "search", "find", "look up", "fetch", "get", "what is", "who is",
                "news", "latest", "current", "today", "weather", "price", "stock",
                "read", "write", "file", "code", "calculate", "analyze", "research"
            ])
        )

        # Agentic tool-calling loop
        for iteration in range(MAX_TOOL_ITERATIONS):
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "top_p": 1.0,
                "max_tokens": 2048,
                "stream": False
            }

            # Add tools to payload only for non-trivial messages
            if tool_definitions and not _is_simple:
                payload["tools"] = tool_definitions
                payload["tool_choice"] = "auto"

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{NIM_API_BASE_URL}/chat/completions",
                        json=payload,
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()

                if "choices" not in data or len(data["choices"]) == 0:
                    return f"Unexpected API response format: {data}"

                choice = data["choices"][0]
                message_obj = choice.get("message", {})
                finish_reason = choice.get("finish_reason", "")

                # ── Tool calls requested by the model ──────────────────────
                if finish_reason == "tool_calls" and "tool_calls" in message_obj:
                    tool_calls = message_obj["tool_calls"]

                    # Append the assistant's tool-call message to history
                    messages.append({
                        "role": "assistant",
                        "content": message_obj.get("content"),
                        "tool_calls": tool_calls
                    })

                    # Execute each tool call via MCP
                    for tool_call in tool_calls:
                        tool_name = tool_call["function"]["name"]
                        try:
                            tool_args = json.loads(tool_call["function"].get("arguments", "{}"))
                        except json.JSONDecodeError:
                            tool_args = {}

                        self.logger.info(f"[MCP] {self.name} calling tool: {tool_name}({tool_args})")

                        if mcp_executor:
                            tool_result = await mcp_executor.execute_tool(tool_name, tool_args)
                            tool_content = tool_result.content
                        else:
                            tool_content = f"MCP tools are disabled. Cannot execute '{tool_name}'."

                        # Append tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_content
                        })

                    # Continue the loop to get the model's next response
                    continue

                # ── Final text response ────────────────────────────────────
                if "content" in message_obj and message_obj["content"]:
                    return message_obj["content"]
                elif finish_reason:
                    return f"API didn't return text. Finish reason: {finish_reason}"

                return f"Unexpected API response format: {data}"

            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP error calling NIM API: Status {e.response.status_code}, Response: {e.response.text}")
                if e.response.status_code == 401:
                    return "NIM API Error: Invalid API key. Please check your NVIDIA NIM API key in your profile settings."
                elif e.response.status_code == 429:
                    return "NIM API Error: Rate limit exceeded. Please wait a moment and try again."
                return f"NIM API Error (Status: {e.response.status_code}): {e.response.text}"
            except Exception as e:
                self.logger.error(f"Error calling NIM API: {e}")
                return f"I encountered an unexpected error when communicating with NVIDIA NIM: {str(e)}"

        # Exceeded max iterations
        self.logger.warning(f"[MCP] {self.name} exceeded max tool iterations ({MAX_TOOL_ITERATIONS})")
        return "I reached the maximum number of tool-calling steps. Please try rephrasing your request."

    def _format_code_blocks(self, text: str) -> str:
        """Ensure all code blocks are properly formatted."""
        import re
        if '```' in text:
            code_blocks = [m for m in re.finditer(r'```[a-zA-Z]*\n[\s\S]*?```', text)]
            if not code_blocks:
                return text + "\n\n⚠️ Warning: The code block above appears incomplete."
            return text
        if re.search(r"def |class |import |print\(", text):
            return f"```python\n{text}\n```"
        if text.strip().startswith('{') and text.strip().endswith('}'):
            return f"```json\n{text}\n```"
        if re.search(r"<\w+>|SELECT |INSERT |UPDATE |DELETE ", text):
            return f"```\n{text}\n```"
        return text
