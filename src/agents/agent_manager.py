"""
Agent Manager for orchestrating the Custodian AI Army
"""

from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
import uuid

from src.agents.base_agent import BaseAgent, AgentMessage, AgentStatus, AgentType
from src.agents.gemini_agent import GeminiAgent
from src.agents.nim_agent import NIMAgent
from src.agents.claude_agent import ClaudeAgent
from src.agents.groq_agent import GroqAgent
from src.core.config import get_model_for_agent
from src.core.logging_config import get_logger

# ─────────────────────────────────────────────────────────────────────────────
# Provider registry
# Maps provider key → agent class
# Priority fallback order: groq → gemini → anthropic → nim
# ─────────────────────────────────────────────────────────────────────────────
PROVIDER_CLASSES = {
    "groq":      GroqAgent,
    "gemini":    GeminiAgent,
    "anthropic": ClaudeAgent,
    "nim":       NIMAgent,
}

# Default provider used when no user preference is set
# Groq is the primary: completely free, ultra-fast, no credit card required
DEFAULT_PROVIDER = "groq"

# Role definitions: each role has a canonical name and specialization.
# These are the only agents exposed to the user.
AGENT_ROLES = [
    {"name": "CustodianAI",    "specialization": "coordinator",   "type": AgentType.MAIN},
    {"name": "AnalystAI",      "specialization": "analyst",       "type": AgentType.MAIN},
    {"name": "DataAnalystAI",  "specialization": "data_analyst",  "type": AgentType.SUB},
    {"name": "MarketAnalystAI","specialization": "market_analyst","type": AgentType.SUB},
    {"name": "CreativeAI",     "specialization": "creative",      "type": AgentType.MAIN},
    {"name": "WriterAI",       "specialization": "writer",        "type": AgentType.SUB},
    {"name": "DesignerAI",     "specialization": "designer",      "type": AgentType.SUB},
    {"name": "TechnicalAI",    "specialization": "technical",     "type": AgentType.MAIN},
    {"name": "CoderAI",        "specialization": "coder",         "type": AgentType.SUB},
    {"name": "ArchitectAI",    "specialization": "architect",     "type": AgentType.SUB},
    {"name": "ResearchAI",     "specialization": "researcher",    "type": AgentType.MAIN},
    {"name": "FactCheckerAI",  "specialization": "fact_checker",  "type": AgentType.SUB},
    {"name": "TrendAnalystAI", "specialization": "trend_analyst", "type": AgentType.SUB},
]

# Sub-agent parent relationships
SUB_AGENT_PARENTS = {
    "DataAnalystAI":  "AnalystAI",
    "MarketAnalystAI":"AnalystAI",
    "WriterAI":       "CreativeAI",
    "DesignerAI":     "CreativeAI",
    "CoderAI":        "TechnicalAI",
    "ArchitectAI":    "TechnicalAI",
    "FactCheckerAI":  "ResearchAI",
    "TrendAnalystAI": "ResearchAI",
}


class AgentManager:
    """Manages all agents in the Custodian AI Army"""

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.main_agents: Dict[str, BaseAgent] = {}
        self.sub_agents: Dict[str, BaseAgent] = {}
        self.logger = get_logger("agent_manager")
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running = False

        # Active provider — shared across all agents
        self._active_provider: str = DEFAULT_PROVIDER

        # Initialize default agent army
        self._initialize_default_agents()

    # ─────────────────────────────────────────────────────────────────────────
    # Initialization
    # ─────────────────────────────────────────────────────────────────────────

    def _initialize_default_agents(self):
        """Initialize role-based agents using the default provider."""
        self._build_agents_for_provider(DEFAULT_PROVIDER)
        self.logger.info(f"Initialized {len(self.agents)} agents using provider '{DEFAULT_PROVIDER}'")

    def _build_agents_for_provider(self, provider: str):
        """(Re)build all role agents using the given provider class."""
        AgentClass = PROVIDER_CLASSES.get(provider, GeminiAgent)

        # Clear existing agents
        self.agents.clear()
        self.main_agents.clear()
        self.sub_agents.clear()

        # Instantiate each role with its assigned model
        agent_by_name: Dict[str, BaseAgent] = {}
        for role in AGENT_ROLES:
            agent_name = role["name"]

            # Look up the per-agent model for this provider
            assigned_model = get_model_for_agent(provider, agent_name)

            # Build kwargs — GeminiAgent has a slightly different constructor
            # (it didn't originally support api_key/model params, now it does)
            kwargs = {
                "name": agent_name,
                "specialization": role["specialization"],
                "agent_type": role["type"],
            }
            if assigned_model:
                kwargs["model"] = assigned_model

            agent = AgentClass(**kwargs)
            self.register_agent(agent)
            agent_by_name[agent_name] = agent

            self.logger.info(
                f"  [{provider}] {agent_name} → model: {assigned_model or 'provider default'}"
            )

        # Wire up sub-agent relationships
        for child_name, parent_name in SUB_AGENT_PARENTS.items():
            child = agent_by_name.get(child_name)
            parent = agent_by_name.get(parent_name)
            if child and parent:
                parent.add_sub_agent(child)

        self._active_provider = provider
        self.logger.info(f"Built {len(self.agents)} agents for provider '{provider}'")

    # ─────────────────────────────────────────────────────────────────────────
    # Provider switching
    # ─────────────────────────────────────────────────────────────────────────

    def switch_provider(self, provider: str, user_api_keys: Optional[Dict[str, str]] = None) -> bool:
        """
        Switch all agents to a different provider.
        Optionally inject user-supplied API keys into the new agents.
        Returns True on success, False if provider is unknown.
        """
        if provider not in PROVIDER_CLASSES:
            self.logger.warning(f"Unknown provider: {provider}")
            return False

        self._build_agents_for_provider(provider)

        # Inject user API keys if provided
        if user_api_keys:
            self._inject_api_keys(user_api_keys)

        self.logger.info(f"Switched all agents to provider '{provider}'")
        return True

    def _inject_api_keys(self, keys: Dict[str, str]):
        """Inject user-supplied API keys into all current agents."""
        for agent in self.agents.values():
            if hasattr(agent, '_api_key_override'):
                provider = self._active_provider
                key_map = {
                    "groq":      keys.get("groq_api_key"),
                    "gemini":    keys.get("gemini_api_key"),
                    "anthropic": keys.get("anthropic_api_key"),
                    "nim":       keys.get("nim_api_key"),
                }
                agent._api_key_override = key_map.get(provider)

    @property
    def active_provider(self) -> str:
        return self._active_provider

    # ─────────────────────────────────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────────────────────────────────

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the manager"""
        self.agents[agent.agent_id] = agent

        if agent.agent_type == AgentType.MAIN:
            self.main_agents[agent.agent_id] = agent
        else:
            self.sub_agents[agent.agent_id] = agent

        self.logger.info(f"Registered agent: {agent.name} ({agent.agent_id})")

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the manager"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]

            if agent_id in self.main_agents:
                del self.main_agents[agent_id]
            if agent_id in self.sub_agents:
                del self.sub_agents[agent_id]

            del self.agents[agent_id]

            self.logger.info(f"Unregistered agent: {agent.name} ({agent_id})")
            return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Lookups
    # ─────────────────────────────────────────────────────────────────────────

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self.agents.get(agent_id)

    def get_agent_by_name(self, name: str) -> Optional[BaseAgent]:
        for agent in self.agents.values():
            if agent.name == name:
                return agent
        return None

    def get_agents_by_specialization(self, specialization: str) -> List[BaseAgent]:
        result = []
        for agent in self.agents.values():
            if hasattr(agent, 'specialization') and agent.specialization == specialization:
                result.append(agent)
        return result

    def get_available_agents(self) -> List[BaseAgent]:
        return [agent for agent in self.agents.values() if agent.status == AgentStatus.IDLE]

    def get_main_agents(self) -> List[BaseAgent]:
        return list(self.main_agents.values())

    def get_army_status(self) -> Dict[str, Any]:
        status_counts = {}
        for status in AgentStatus:
            status_counts[status.value] = sum(
                1 for agent in self.agents.values() if agent.status == status
            )

        return {
            "total_agents": len(self.agents),
            "main_agents": len(self.main_agents),
            "sub_agents": len(self.sub_agents),
            "status_distribution": status_counts,
            "agents": [agent.get_status() for agent in self.agents.values()],
            "active_provider": self._active_provider,
            "last_updated": datetime.utcnow().isoformat()
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Messaging
    # ─────────────────────────────────────────────────────────────────────────

    async def send_message(self, message: AgentMessage) -> AgentMessage:
        target_agent = self.get_agent(message.receiver_id)

        if not target_agent:
            raise ValueError(f"Agent {message.receiver_id} not found")

        self.logger.info(f"Sending message from {message.sender_id} to {message.receiver_id}")

        try:
            response = await target_agent.process_message(message)
            return response
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            raise

    async def execute_task(self, task: Dict[str, Any], preferred_agent: str = None) -> Dict[str, Any]:
        target_agent = None

        if preferred_agent:
            target_agent = self.get_agent(preferred_agent) or self.get_agent_by_name(preferred_agent)

        if not target_agent:
            target_agent = self._find_best_agent_for_task(task)

        if not target_agent:
            raise ValueError("No suitable agent found for the task")

        self.logger.info(f"Executing task with agent: {target_agent.name}")

        try:
            result = await target_agent.execute_task(task)
            return result
        except Exception as e:
            self.logger.error(f"Error executing task: {str(e)}")
            raise

    def _find_best_agent_for_task(self, task: Dict[str, Any]) -> Optional[BaseAgent]:
        task_type = task.get("type", "general")
        task_description = task.get("description", "").lower()

        specialization_mapping = {
            "analysis": "analyst",
            "data": "analyst",
            "research": "researcher",
            "creative": "creative",
            "writing": "creative",
            "design": "creative",
            "technical": "technical",
            "coding": "technical",
            "programming": "technical",
            "coordination": "coordinator",
            "management": "coordinator"
        }

        if task_type in specialization_mapping:
            agents = self.get_agents_by_specialization(specialization_mapping[task_type])
            available_agents = [a for a in agents if a.status == AgentStatus.IDLE and a.agent_type == AgentType.MAIN]
            if available_agents:
                return available_agents[0]

        for keyword, specialization in specialization_mapping.items():
            if keyword in task_description:
                agents = self.get_agents_by_specialization(specialization)
                available_agents = [a for a in agents if a.status == AgentStatus.IDLE and a.agent_type == AgentType.MAIN]
                if available_agents:
                    return available_agents[0]

        available_main_agents = [a for a in self.main_agents.values() if a.status == AgentStatus.IDLE]
        if available_main_agents:
            return available_main_agents[0]

        return None

    async def broadcast_message(self, message: str, sender_id: str = "system") -> List[AgentMessage]:
        responses = []

        for agent in self.agents.values():
            if agent.agent_id != sender_id:
                msg = AgentMessage(
                    sender_id=sender_id,
                    receiver_id=agent.agent_id,
                    content=message,
                    message_type="broadcast"
                )

                try:
                    response = await agent.process_message(msg)
                    responses.append(response)
                except Exception as e:
                    self.logger.error(f"Error broadcasting to {agent.name}: {str(e)}")

        return responses

    async def start_message_processing(self):
        self.running = True
        self.logger.info("Started message processing")

        while self.running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self.send_message(message)
                self.message_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in message processing loop: {str(e)}")

    async def stop_message_processing(self):
        self.running = False
        self.logger.info("Stopped message processing")

    async def shutdown(self):
        self.logger.info("Shutting down Agent Manager")

        await self.stop_message_processing()

        for agent in self.agents.values():
            if hasattr(agent, 'close'):
                try:
                    await agent.close()
                except Exception as e:
                    self.logger.error(f"Error closing agent {agent.name}: {str(e)}")

        self.agents.clear()
        self.main_agents.clear()
        self.sub_agents.clear()

        self.logger.info("Agent Manager shutdown complete")
