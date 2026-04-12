"""
Claude Code Agent implementation using the Claude Code CLI as a subprocess.
This agent wraps the `claude` CLI tool from the claudecode submodule.

Requirements:
- Claude Code CLI must be installed: curl -fsSL https://claude.ai/install.sh | bash
- Authenticate with: claude auth login (uses Claude.ai Pro subscription - no extra API cost)
  OR set ANTHROPIC_API_KEY environment variable

Free usage: If you have a Claude.ai Pro/Max subscription, authenticate once via browser
and use Claude Code without additional API costs.
"""

import asyncio
import os
import shutil
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentMessage, AgentStatus, AgentType, AgentCapability
from src.core.config import settings
from src.core.logging_config import get_logger

# Directory where prompt .md files are stored
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


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


def _find_claude_cli() -> str:
    """Find the claude CLI executable path."""
    # Check common installation paths
    candidates = [
        shutil.which("claude"),
        os.path.expanduser("~/.claude/local/claude"),
        "/usr/local/bin/claude",
        "/usr/bin/claude",
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


class ClaudeCodeAgent(BaseAgent):
    """
    Agent powered by Claude Code CLI (subprocess-based).
    
    Uses the official Claude Code CLI tool to process requests.
    Free with Claude.ai Pro subscription (no extra API cost).
    Falls back to ANTHROPIC_API_KEY if CLI auth is not set up.
    """

    def __init__(
        self,
        agent_id: str = None,
        name: str = "ClaudeCodeAgent",
        agent_type: AgentType = AgentType.MAIN,
        specialization: str = "technical",
        capabilities: List[AgentCapability] = None,
        api_key: str = None
    ):
        default_capabilities = [
            AgentCapability(
                name="code_generation",
                description="Generate, review, and refactor code using Claude Code CLI",
                parameters={"max_tokens": 8192, "timeout": 120}
            ),
            AgentCapability(
                name="codebase_analysis",
                description="Analyze and understand entire codebases",
                parameters={"context_window": 200000}
            ),
            AgentCapability(
                name="git_workflows",
                description="Handle git operations, commits, and PR workflows",
                parameters={"timeout": 60}
            ),
            AgentCapability(
                name="text_generation",
                description="Generate high-quality text and documentation",
                parameters={"max_tokens": 4096}
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
        self._claude_cli_path = _find_claude_cli()
        self._cli_available = self._claude_cli_path is not None

        if self._cli_available:
            self.logger.info(f"ClaudeCodeAgent {self.name} initialized. CLI found at: {self._claude_cli_path}")
        else:
            self.logger.warning(
                f"ClaudeCodeAgent {self.name} initialized but Claude Code CLI not found. "
                "Install with: curl -fsSL https://claude.ai/install.sh | bash"
            )

    def _get_api_key(self) -> str:
        """Get the effective API key (user override > server default)"""
        return self._api_key_override or settings.ANTHROPIC_API_KEY or ""

    def is_available(self) -> bool:
        """Check if Claude Code CLI is available"""
        return self._cli_available

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message using Claude Code CLI"""
        try:
            self.update_status(AgentStatus.BUSY)

            system_prompt = self._get_system_prompt()
            full_prompt = f"{system_prompt}\n\nUser Request: {message.content}"

            response = await self._call_claude_code_cli(full_prompt)
            formatted_response = self._format_code_blocks(response)

            response_message = AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content=formatted_response,
                message_type="text",
                metadata={
                    "original_message_id": message.id,
                    "agent_specialization": self.specialization,
                    "provider": "claude_code_cli",
                    "cli_path": self._claude_cli_path,
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
        """Execute a specific task using Claude Code CLI"""
        try:
            self.update_status(AgentStatus.BUSY)
            task_type = task.get("type", "general")
            task_description = task.get("description", "")

            system_prompt = self._get_task_prompt(task_type)
            full_prompt = f"{system_prompt}\n\nTask: {task_description}"

            response = await self._call_claude_code_cli(full_prompt)

            result = {
                "task_id": task.get("id", "unknown"),
                "status": "completed",
                "result": response,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "execution_time": datetime.utcnow().isoformat(),
                "specialization": self.specialization,
                "provider": "claude_code_cli"
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

    async def _call_claude_code_cli(self, prompt: str, timeout: int = 120) -> str:
        """
        Call the Claude Code CLI as a subprocess.
        
        Uses `claude -p <prompt>` for non-interactive (print) mode.
        This mode processes a single prompt and returns the response.
        """
        if not self._cli_available:
            # Fallback: try to use Claude API directly if CLI not available
            return await self._fallback_to_api(prompt)

        env = os.environ.copy()
        api_key = self._get_api_key()
        if api_key:
            env["ANTHROPIC_API_KEY"] = api_key

        try:
            # Use claude -p for non-interactive print mode
            cmd = [self._claude_cli_path, "-p", prompt, "--output-format", "text"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return f"Claude Code CLI timed out after {timeout} seconds. Please try a simpler request."

            if process.returncode == 0:
                output = stdout.decode("utf-8", errors="replace").strip()
                if output:
                    return output
                else:
                    return "Claude Code CLI returned an empty response."
            else:
                error_output = stderr.decode("utf-8", errors="replace").strip()
                self.logger.error(f"Claude Code CLI error (exit {process.returncode}): {error_output}")

                # Check for common errors
                if "not logged in" in error_output.lower() or "authentication" in error_output.lower():
                    return (
                        "Claude Code CLI is not authenticated. Please run `claude auth login` in your terminal "
                        "to authenticate with your Claude.ai account, or add your ANTHROPIC_API_KEY in profile settings."
                    )
                elif "api key" in error_output.lower():
                    return (
                        "Claude Code CLI requires an API key. Please add your ANTHROPIC_API_KEY in profile settings "
                        "or authenticate with `claude auth login`."
                    )

                return f"Claude Code CLI error: {error_output or 'Unknown error'}"

        except FileNotFoundError:
            self._cli_available = False
            return await self._fallback_to_api(prompt)
        except Exception as e:
            self.logger.error(f"Error running Claude Code CLI: {e}")
            return f"Error running Claude Code CLI: {str(e)}"

    async def _fallback_to_api(self, prompt: str) -> str:
        """Fallback to direct Anthropic API call when CLI is not available"""
        import httpx

        api_key = self._get_api_key()
        if not api_key:
            return (
                "Claude Code CLI is not installed and no ANTHROPIC_API_KEY is configured. "
                "Install Claude Code: curl -fsSL https://claude.ai/install.sh | bash\n"
                "Or add your Anthropic API key in Profile → API Keys."
            )

        payload = {
            "model": "claude-sonnet-4-5",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}]
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
                    return data["content"][0].get("text", "")
                return "No response from Claude API."
        except Exception as e:
            return f"Claude API fallback error: {str(e)}"

    def _get_system_prompt(self) -> str:
        """Get system prompt based on agent specialization."""
        prompt_file_map = {
            "general": "general.md",
            "analyst": "analyst.md",
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
            "general": "You are a helpful AI assistant powered by Claude Code. Provide accurate, helpful responses.",
            "technical": "You are an expert technical AI powered by Claude Code. Focus on code quality, architecture, and technical accuracy.",
            "coordinator": "You are Custodian AI — an intelligent orchestrator powered by Claude Code. Answer the user's question directly and expertly.",
        }
        return fallbacks.get(self.specialization, fallbacks.get("general", "You are a helpful AI assistant."))

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
            "coding": "You are an expert programmer. Provide clean, efficient, and well-documented code solutions.",
            "analysis": "You are an expert analyst. Provide thorough analysis with clear insights.",
            "research": "You are an expert researcher. Provide comprehensive, accurate information.",
        }
        return fallbacks.get(task_type, self._get_system_prompt())

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
        return text

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status including CLI availability"""
        status = super().get_status()
        status["cli_available"] = self._cli_available
        status["cli_path"] = self._claude_cli_path
        status["provider"] = "claude_code_cli"
        return status
