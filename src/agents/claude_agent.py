"""
Claude Agent implementation using Anthropic's official Python SDK.
Supports Claude Opus 4, Claude Sonnet 4.5, Claude Haiku, and other Anthropic models.
Get your API key at: https://console.anthropic.com
"""

import os
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentMessage, AgentStatus, AgentType, AgentCapability
from src.core.config import settings
from src.core.logging_config import get_logger

# Directory where prompt .md files are stored
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

CLAUDE_DEFAULT_MODEL = "claude-sonnet-4-5"


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


class ClaudeAgent(BaseAgent):
    """Agent powered by Anthropic's Claude models"""

    def __init__(
        self,
        agent_id: str = None,
        name: str = "ClaudeAgent",
        agent_type: AgentType = AgentType.MAIN,
        specialization: str = "general",
        capabilities: List[AgentCapability] = None,
        api_key: str = None,
        model: str = None
    ):
        default_capabilities = [
            AgentCapability(
                name="text_generation",
                description="Generate high-quality text responses using Claude models",
                parameters={"max_tokens": 4096, "temperature": 0.7}
            ),
            AgentCapability(
                name="conversation",
                description="Engage in nuanced, context-aware conversations",
                parameters={"context_window": 200000}
            ),
            AgentCapability(
                name="code_generation",
                description="Generate, review, and explain code with high accuracy",
                parameters={"timeout": 60}
            ),
            AgentCapability(
                name="reasoning",
                description="Advanced reasoning and analysis capabilities",
                parameters={"extended_thinking": True}
            )
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
        self.logger.info(f"ClaudeAgent {self.name} initialized with specialization: {specialization}")

    def _get_api_key(self) -> str:
        """Get the effective API key (user override > server default)"""
        return self._api_key_override or settings.ANTHROPIC_API_KEY or ""

    def _get_model(self) -> str:
        """Get the effective model name"""
        return self._model_override or settings.CLAUDE_MODEL or CLAUDE_DEFAULT_MODEL

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message using Claude"""
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
                    metadata={"original_message_id": message.id, "delegated_task": True, "provider": "anthropic_claude"}
                )

            system_prompt = self._get_system_prompt()
            response = await self._call_claude_api(
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
                    "provider": "anthropic_claude",
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
        """Execute a specific task using Claude"""
        try:
            self.update_status(AgentStatus.BUSY)
            task_type = task.get("type", "general")
            task_description = task.get("description", "")
            task_parameters = task.get("parameters", {})

            system_prompt = self._get_task_prompt(task_type)
            response = await self._call_claude_api(
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
                "provider": "anthropic_claude",
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
            "creative": "creative.md",
            "technical": "technical.md",
            "researcher": "researcher.md",
            "tutor": "tutor.md",
            "coordinator": "coordinator.md",
        }
        filename = prompt_file_map.get(self.specialization)
        if filename:
            loaded = _load_prompt(filename)
            if loaded:
                return loaded
        fallbacks = {
            "general": "You are a helpful AI assistant powered by Anthropic Claude. Provide accurate, thoughtful, and engaging responses.",
            "analyst": "You are a data analyst AI powered by Claude. Focus on analytical thinking, data interpretation, and actionable insights.",
            "creative": "You are a creative AI assistant powered by Claude. Focus on creative writing, brainstorming, and innovative solutions.",
            "technical": "You are a technical AI assistant powered by Claude. Focus on technical accuracy, problem-solving, and detailed explanations.",
            "researcher": "You are a research AI assistant powered by Claude. Focus on thorough research, fact-checking, and comprehensive analysis.",
            "tutor": "You are an expert, encouraging programming tutor powered by Claude. Help students learn programming concepts clearly and effectively.",
            "coordinator": "You are Custodian AI — an intelligent orchestrator powered by Anthropic Claude. Adopt the persona of the best expert and answer the user's question directly.",
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

    async def _call_claude_api(
        self,
        system_prompt: str,
        user_message: str,
        context: Dict[str, Any] = None,
        history: list = None
    ) -> str:
        """Call the Anthropic Claude API using httpx (avoids requiring anthropic package)"""
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not configured. Get your key at https://console.anthropic.com"
            )

        model = self._get_model()
        import httpx

        # Build multi-turn conversation from history
        messages = []
        if history:
            for msg in history:
                sender = msg.get("sender", "")
                content = msg.get("content", "")
                if not content:
                    continue
                role = "user" if sender == "You" else "assistant"
                messages.append({"role": role, "content": content})
        # Always append the current user message last
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": model,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": messages
        }

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                if "content" in data and len(data["content"]) > 0:
                    content_block = data["content"][0]
                    if content_block.get("type") == "text":
                        return content_block.get("text", "")

                if "stop_reason" in data:
                    return f"Claude didn't return text. Stop reason: {data.get('stop_reason')}"

                return f"Unexpected API response format: {data}"

        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error calling Claude API: Status {e.response.status_code}, Response: {e.response.text}")
            if e.response.status_code == 401:
                return "Claude API Error: Invalid API key. Please check your Anthropic API key in your profile settings."
            elif e.response.status_code == 429:
                return "Claude API Error: Rate limit exceeded. Please wait a moment and try again."
            elif e.response.status_code == 529:
                return "Claude API Error: Anthropic API is currently overloaded. Please try again later."
            return f"Claude API Error (Status: {e.response.status_code}): {e.response.text}"
        except Exception as e:
            self.logger.error(f"Error calling Claude API: {e}")
            return f"I encountered an unexpected error when communicating with Claude: {str(e)}"

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
