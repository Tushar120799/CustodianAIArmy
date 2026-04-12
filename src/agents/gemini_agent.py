"""
Gemini Agent implementation
Uses Google's Gemini API for inference.
Supports Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.0 Flash, and other Gemini models.

MCP Tool Calling:
  Each agent specialization has a set of MCP tools available (web search,
  filesystem, memory, etc.). When the model requests a function call, this agent
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

GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"

# Maximum tool-calling iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 5


def _load_prompt(filename: str) -> str:
    """Load a prompt from a .md file in the prompts directory.
    Returns the file content stripped of leading/trailing whitespace.
    Falls back to an empty string if the file is not found."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        # Strip the first markdown heading line if present (e.g. "# Title\n\n")
        lines = content.splitlines()
        if lines and lines[0].startswith("#"):
            content = "\n".join(lines[1:]).strip()
        return content
    except FileNotFoundError:
        return ""


class GeminiAgent(BaseAgent):
    """Agent powered by Google Gemini models"""

    def __init__(
        self,
        agent_id: str = None,
        name: str = "GeminiAgent",
        agent_type: AgentType = AgentType.MAIN,
        specialization: str = "general",
        capabilities: List[AgentCapability] = None,
        api_key: str = None,
        model: str = None
    ):
        default_capabilities = [
            AgentCapability(
                name="text_generation",
                description="Generate human-like text responses",
                parameters={"max_tokens": 8192, "temperature": 0.7}
            ),
            AgentCapability(
                name="conversation",
                description="Engage in natural conversations",
                parameters={"context_window": 1000000}
            ),
            AgentCapability(
                name="task_execution",
                description="Execute various AI tasks",
                parameters={"timeout": 30}
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
        self._api_key_override = api_key
        self._model_override = model

        # Lazy-initialized MCP tool executor
        self._mcp_executor = None

        self.api_client = httpx.AsyncClient(
            base_url=settings.GEMINI_API_URL,
            headers={"Content-Type": "application/json"},
            timeout=60.0
        )
        self.logger.info(f"GeminiAgent {self.name} initialized with specialization: {specialization}")

    def _get_api_key(self) -> str:
        """Get the effective API key (user override > server default)"""
        return self._api_key_override or settings.GEMINI_API_KEY or ""

    def _get_model(self) -> str:
        """Get the effective model name"""
        return self._model_override or settings.GEMINI_MODEL or GEMINI_DEFAULT_MODEL

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
        """Process an incoming message using a Gemini model"""
        try:
            self.update_status(AgentStatus.BUSY)

            # If this is the coordinator, it should delegate and return the expert's response.
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
                    metadata={"original_message_id": message.id, "delegated_task": True, "provider": "gemini"}
                )

            # For all other agents, process normally
            system_prompt = self._get_system_prompt()
            response = await self._call_gemini_api(
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
                    "provider": "gemini",
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

    def _format_code_blocks(self, text: str) -> str:
        """Ensure all code, JSON, or similar blocks are wrapped in triple backticks and not truncated."""
        import re
        if '```' in text:
            code_blocks = [m for m in re.finditer(r'```[a-zA-Z]*\n[\s\S]*?```', text)]
            if not code_blocks:
                return text + "\n\n⚠️ Warning: The code block above appears incomplete. Please regenerate or check for missing lines."
            if '"""' in text:
                triple_quotes = text.count('"""')
                if triple_quotes % 2 != 0:
                    return text + "\n\n⚠️ Warning: The code block above contains an unterminated triple-quoted string."
            return text
        if re.search(r"def |class |import |print\(", text):
            if text.count('"""') % 2 != 0:
                return f"```python\n{text}\n```\n\n⚠️ Warning: The code block above contains an unterminated triple-quoted string."
            return f"```python\n{text}\n```"
        if text.strip().startswith('{') and text.strip().endswith('}'):
            return f"```json\n{text}\n```"
        if re.search(r"<\w+>|SELECT |INSERT |UPDATE |DELETE ", text):
            return f"```\n{text}\n```"
        return text

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task using a Gemini model"""
        try:
            self.update_status(AgentStatus.BUSY)
            task_type = task.get("type", "general")
            task_description = task.get("description", "")
            task_parameters = task.get("parameters", {})

            if task_type in ["complex_analysis", "multi_step"] and self.sub_agents:
                return await self._handle_complex_task(task)

            if task_type == "delegated_task":
                system_prompt = self._get_delegated_task_prompt(task_description)
            else:
                system_prompt = self._get_task_prompt(task_type)

            response = await self._call_gemini_api(
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
                "provider": "gemini",
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
            "general": "You are a helpful AI assistant. Provide accurate, helpful, and engaging responses.",
            "analyst": "You are a data analyst AI. Focus on analytical thinking, data interpretation, and insights.",
            "creative": "You are a creative AI assistant. Focus on creative writing, brainstorming, and innovative solutions.",
            "technical": "You are a technical AI assistant. Focus on technical accuracy, problem-solving, and detailed explanations.",
            "researcher": "You are a research AI assistant. Focus on thorough research, fact-checking, and comprehensive analysis.",
            "tutor": "You are an expert, encouraging programming tutor. Help students learn programming concepts clearly and effectively.",
            "coordinator": "You are Custodian AI — an intelligent orchestrator and the central command of the Custodian AI Army. Adopt the persona of the best expert and answer the user's question directly.",
        }
        return fallbacks.get(self.specialization, fallbacks["general"])

    def _get_delegated_task_prompt(self, user_message: str) -> str:
        """Route delegated tasks to the appropriate prompt."""
        if any(keyword in user_message.lower() for keyword in ['code', 'python', 'program', 'factorial', 'javascript']):
            return self._get_task_prompt("coding")
        return self._get_task_prompt("general")

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

    async def _call_gemini_api(
        self,
        system_prompt: str,
        user_message: str,
        context: Dict[str, Any] = None,
        history: list = None
    ) -> str:
        """
        Call the Google Gemini API with MCP tool calling support.

        Implements an agentic loop:
        1. Send message to Gemini with available function declarations
        2. If model returns functionCall parts → execute via MCP → feed results back
        3. Repeat until model returns a final text response (or max iterations)
        """
        api_key = self._get_api_key()
        if not api_key:
            self.logger.error("GEMINI_API_KEY not configured.")
            raise ValueError("GEMINI_API_KEY must be set to use the agent.")

        model = self._get_model()

        # Build multi-turn conversation from history
        contents = []
        if history:
            for msg in history:
                sender = msg.get("sender", "")
                content = msg.get("content", "")
                if not content:
                    continue
                role = "user" if sender == "You" else "model"
                contents.append({"role": role, "parts": [{"text": content}]})

        # Append the current user message (with system prompt prepended on first turn)
        if contents:
            contents.append({"role": "user", "parts": [{"text": user_message}]})
        else:
            full_prompt = f"{system_prompt}\n\nUser Request: {user_message}"
            contents.append({"role": "user", "parts": [{"text": full_prompt}]})

        # Get MCP tool definitions for this agent (Gemini format)
        mcp_executor = self._get_mcp_executor()
        tool_declarations = []
        if mcp_executor:
            tool_declarations = mcp_executor.get_tool_definitions_gemini()

        api_url = f"/models/{model}:generateContent?key={api_key}"

        # Agentic tool-calling loop
        for iteration in range(MAX_TOOL_ITERATIONS):
            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.7,
                    "topP": 1.0,
                    "maxOutputTokens": 8192,
                }
            }

            # Add function declarations if available
            if tool_declarations:
                payload["tools"] = [{"functionDeclarations": tool_declarations}]

            try:
                response = await self.api_client.post(api_url, json=payload)
                response.raise_for_status()
                data = response.json()

                if 'candidates' not in data or len(data['candidates']) == 0:
                    return f"Unexpected API response format: {data}"

                candidate = data['candidates'][0]
                finish_reason = candidate.get('finishReason', '')
                parts = candidate.get('content', {}).get('parts', [])

                # ── Function calls requested by the model ──────────────────
                function_call_parts = [p for p in parts if 'functionCall' in p]
                if function_call_parts:
                    # Append model's response to contents
                    contents.append({
                        "role": "model",
                        "parts": parts
                    })

                    # Execute each function call via MCP
                    function_responses = []
                    for part in function_call_parts:
                        fc = part["functionCall"]
                        tool_name = fc["name"]
                        tool_args = fc.get("args", {})

                        self.logger.info(f"[MCP] {self.name} calling tool: {tool_name}({tool_args})")

                        if mcp_executor:
                            tool_result = await mcp_executor.execute_tool(tool_name, tool_args)
                            result_content = tool_result.content
                        else:
                            result_content = f"MCP tools are disabled. Cannot execute '{tool_name}'."

                        function_responses.append({
                            "functionResponse": {
                                "name": tool_name,
                                "response": {"result": result_content}
                            }
                        })

                    # Append function responses as user turn
                    contents.append({
                        "role": "user",
                        "parts": function_responses
                    })

                    # Continue the loop to get the model's next response
                    continue

                # ── Final text response ────────────────────────────────────
                text_parts = [p.get('text', '') for p in parts if 'text' in p]
                if text_parts:
                    text = "\n".join(text_parts)
                    if '```' not in text and ("def " in text or "class " in text or "import " in text):
                        return f"```python\n{text}\n```"
                    return text

                if finish_reason:
                    return f"API didn't return text. Finish reason: {finish_reason}"

                return f"Unexpected API response format: {data}"

            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP error calling Gemini API: Status {e.response.status_code}, Response: {e.response.text}")
                return f"API Error (Status: {e.response.status_code}): {e.response.text}"
            except Exception as e:
                self.logger.error(f"Error calling Gemini API: {e}")
                return f"I encountered an unexpected error when trying to communicate with the API for your request: '{user_message}'. Details: {str(e)}."

        # Exceeded max iterations
        self.logger.warning(f"[MCP] {self.name} exceeded max tool iterations ({MAX_TOOL_ITERATIONS})")
        return "I reached the maximum number of tool-calling steps. Please try rephrasing your request."

    async def _handle_complex_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"Handling complex task with {len(self.sub_agents)} sub-agents")
        subtasks = self._decompose_task(task)
        results = []
        for i, subtask in enumerate(subtasks):
            if i < len(self.sub_agents):
                result = await self.sub_agents[i].execute_task(subtask)
                results.append(result)
            else:
                result = await self.execute_task(subtask)
                results.append(result)
        final_result = await self._synthesize_results(task, results)
        return final_result
