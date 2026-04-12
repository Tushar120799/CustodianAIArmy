"""
Gemini Agent implementation (renamed from Nemotron)
"""

import httpx
import os
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentMessage, AgentStatus, AgentType, AgentCapability
from src.core.config import settings
from src.core.logging_config import get_logger

# Directory where prompt .md files are stored
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


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
		capabilities: List[AgentCapability] = None
	):
		default_capabilities = [
			AgentCapability(
				name="text_generation",
				description="Generate human-like text responses",
				parameters={"max_tokens": 2048, "temperature": 0.7}
			),
			AgentCapability(
				name="conversation",
				description="Engage in natural conversations",
				parameters={"context_window": 4096}
			),
			AgentCapability(
				name="task_execution",
				description="Execute various AI tasks",
				parameters={"timeout": 30}
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
		self.api_client = httpx.AsyncClient(
			base_url=settings.GEMINI_API_URL,
			headers={"Content-Type": "application/json"},
			timeout=30.0
		)
		self.logger.info(f"GeminiAgent {self.name} initialized with specialization: {specialization}")

	async def process_message(self, message: AgentMessage) -> AgentMessage:
		"""Process an incoming message using a Gemini model"""
		try:
			self.update_status(AgentStatus.BUSY)

			# If this is the coordinator, it should delegate and return the expert's response.
			if self.specialization == "coordinator":
				# This is a task, so delegate it.
				task = {
					"id": f"task_{message.id}",
					"type": "delegated_task", # A generic type for the coordinator to handle
					"description": message.content,
					"parameters": message.metadata
				}
				task_result = await self.execute_task(task)

				# Format the task result as a chat message
				response_content = task_result.get("result", "Task completed, but no result was returned.")
				if task_result.get("status") == "failed":
					response_content = f"Sorry, the task failed. Error: {task_result.get('error')}"

				return AgentMessage(
					sender_id=self.agent_id,
					receiver_id=message.sender_id,
					content=response_content,
					message_type="text",
					metadata={"original_message_id": message.id, "delegated_task": True}
				)

			# For all other agents, process normally
			system_prompt = self._get_system_prompt()
			response = await self._call_gemini_api(
				system_prompt=system_prompt,
				user_message=message.content,
				context=message.metadata.get("context", {}),
				history=message.metadata.get("history", [])
			)
			# Ensure code blocks, JSON, and similar are always wrapped in triple backticks
			formatted_response = self._format_code_blocks(response)
			response_message = AgentMessage(
				sender_id=self.agent_id,
				receiver_id=message.sender_id,
				content=formatted_response,
				message_type="text",
				metadata={
					"original_message_id": message.id,
					"agent_specialization": self.specialization,
					"processing_time": (datetime.utcnow() - message.timestamp).total_seconds()
				}
			)
			self.update_status(AgentStatus.IDLE)
			return response_message
		except Exception as e:
			self.logger.error(f"Error processing message: {str(e)}")
			self.update_status(AgentStatus.ERROR)
			error_message = AgentMessage(
				sender_id=self.agent_id,
				receiver_id=message.sender_id,
				content=f"Error processing your request: {str(e)}",
				message_type="error",
				metadata={"error": str(e), "original_message_id": message.id}
			)
			return error_message

	async def process_message_old(self, message: AgentMessage) -> AgentMessage:
		"""Process an incoming message using a Gemini model"""
		try:
			self.update_status(AgentStatus.BUSY)
			system_prompt = self._get_system_prompt()
			response = await self._call_gemini_api(
				system_prompt=system_prompt,
				user_message=message.content,
				context=message.metadata.get("context", {})
			)
			# Ensure code blocks, JSON, and similar are always wrapped in triple backticks
			formatted_response = self._format_code_blocks(response)
			response_message = AgentMessage(
				sender_id=self.agent_id,
				receiver_id=message.sender_id,
				content=formatted_response,
				message_type="text",
				metadata={
					"original_message_id": message.id,
					"agent_specialization": self.specialization,
					"processing_time": (datetime.utcnow() - message.timestamp).total_seconds()
				}
			)
			self.update_status(AgentStatus.IDLE)
			return response_message
		except Exception as e:
			self.logger.error(f"Error processing message: {str(e)}")
			self.update_status(AgentStatus.ERROR)
			error_message = AgentMessage(
				sender_id=self.agent_id,
				receiver_id=message.sender_id,
				content=f"Error processing your request: {str(e)}",
				message_type="error",
				metadata={"error": str(e), "original_message_id": message.id}
			)
			return error_message

	def _format_code_blocks(self, text: str) -> str:
		"""Ensure all code, JSON, or similar blocks are wrapped in triple backticks and not truncated."""
		import re
		# If already contains code blocks, check for completeness
		if '```' in text:
			# Check for unclosed code block
			code_blocks = [m for m in re.finditer(r'```[a-zA-Z]*\n[\s\S]*?```', text)]
			if not code_blocks:
				# Unclosed code block detected
				return text + "\n\n⚠️ Warning: The code block above appears incomplete. Please regenerate or check for missing lines."
			# Optionally, check for unterminated triple quotes in Python code
			if '"""' in text:
				triple_quotes = text.count('"""')
				if triple_quotes % 2 != 0:
					return text + "\n\n⚠️ Warning: The code block above contains an unterminated triple-quoted string."
			return text
		# Detect Python code (simple heuristic)
		if re.search(r"def |class |import |print\(", text):
			# Check for unterminated triple quotes
			if text.count('"""') % 2 != 0:
				return f"```python\n{text}\n```\n\n⚠️ Warning: The code block above contains an unterminated triple-quoted string."
			return f"```python\n{text}\n```"
		# Detect JSON
		if text.strip().startswith('{') and text.strip().endswith('}'):
			return f"```json\n{text}\n```"
		# Detect other code-like content (e.g., XML, HTML, SQL)
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

			# If the task was delegated by the coordinator, get the correct prompt
			if task_type == "delegated_task":
				system_prompt = self._get_delegated_task_prompt(task_description)
			else:
				system_prompt = self._get_task_prompt(task_type)

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
				"specialization": self.specialization
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
		"""Get system prompt based on agent specialization.
		Loads from a .md file in src/agents/prompts/ if available,
		otherwise falls back to the hardcoded default."""
		# Map specialization names to prompt filenames
		# Includes both main agents and sub-agents with dedicated prompt files
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
		# Hardcoded fallbacks (used if .md file is missing or empty)
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
		"""
		This is a simplified version of a router. In a real-world scenario, this would
		use a more sophisticated model or logic to classify the user's request and
		return the appropriate expert prompt.
		"""
		if any(keyword in user_message.lower() for keyword in ['code', 'python', 'program', 'factorial', 'javascript']):
			return self._get_task_prompt("coding")
		# Add other routing rules here...
		return self._get_task_prompt("general") # Fallback

	def _get_task_prompt(self, task_type: str) -> str:
		"""Get task-specific system prompt.
		Loads from a .md file in src/agents/prompts/ if available,
		otherwise falls back to the hardcoded default."""
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
		# Hardcoded fallbacks
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
		"""Call the Google Gemini API"""
		if not settings.GEMINI_API_KEY:
			self.logger.error("GEMINI_API_KEY not configured.")
			raise ValueError("GEMINI_API_KEY must be set to use the agent.")

		# Build multi-turn conversation from history
		# Gemini uses "contents" array with role: "user" / "model"
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
			# System prompt already established; just send the user message
			contents.append({"role": "user", "parts": [{"text": user_message}]})
		else:
			# No history — prepend system prompt to the first user message
			full_prompt = f"{system_prompt}\n\nUser Request: {user_message}"
			contents.append({"role": "user", "parts": [{"text": full_prompt}]})

		payload = {
			"contents": contents,
			"generationConfig": {
				"temperature": 0.7,
				"topP": 1.0,
				"maxOutputTokens": 8192,
			}
		}
		model = settings.GEMINI_MODEL or "gemini-2.5-flash"
		api_url = f"/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
		try:
			response = await self.api_client.post(api_url, json=payload)
			response.raise_for_status()
			data = response.json()
			if 'candidates' in data and len(data['candidates']) > 0:
				candidate = data['candidates'][0]
				if 'content' in candidate and 'parts' in candidate['content'] and len(candidate['content']['parts']) > 0:
					text = candidate['content']['parts'][0].get('text', '')
					if '```' not in text and ("def " in text or "class " in text or "import " in text):
						return f"```python\n{text}\n```"
					return text
				elif 'finishReason' in candidate:
					return f"API didn't return text. Finish reason: {candidate.get('finishReason')}"
			return f"Unexpected API response format: {data}"
		except httpx.HTTPStatusError as e:
			self.logger.error(f"HTTP error calling Gemini API: Status {e.response.status_code}, Response: {e.response.text}")
			return f"API Error (Status: {e.response.status_code}): {e.response.text}"
		except Exception as e:
			self.logger.error(f"Error calling Gemini API: {e}")
			return f"I encountered an unexpected error when trying to communicate with the API for your request: '{user_message}'. Details: {str(e)}."

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
