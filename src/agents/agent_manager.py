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
from src.agents.claude_code_agent import ClaudeCodeAgent
from src.core.logging_config import get_logger


class AgentManager:
    """Manages all agents in the Custodian AI Army"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.main_agents: Dict[str, BaseAgent] = {}
        self.sub_agents: Dict[str, BaseAgent] = {}
        self.logger = get_logger("agent_manager")
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        
        # Initialize default agent army
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        """Initialize the default set of agents"""
        
        # Main Coordinator Agent
        coordinator = GeminiAgent(
            name="CustodianAI",
            specialization="coordinator",
            agent_type=AgentType.MAIN
        )
        self.register_agent(coordinator)
        
        # Analyst Agent with sub-agents
        analyst_main = GeminiAgent(
            name="AnalystAI",
            specialization="analyst",
            agent_type=AgentType.MAIN
        )
        
        # Analyst sub-agents
        data_analyst = GeminiAgent(
            name="DataAnalystAI",
            specialization="analyst",
            agent_type=AgentType.SUB
        )
        
        market_analyst = GeminiAgent(
            name="MarketAnalystAI",
            specialization="analyst",
            agent_type=AgentType.SUB
        )
        
        analyst_main.add_sub_agent(data_analyst)
        analyst_main.add_sub_agent(market_analyst)
        
        self.register_agent(analyst_main)
        self.register_agent(data_analyst)
        self.register_agent(market_analyst)
        
        # Creative Agent with sub-agents
        creative_main = GeminiAgent(
            name="CreativeAI",
            specialization="creative",
            agent_type=AgentType.MAIN
        )
        
        writer_agent = GeminiAgent(
            name="WriterAI",
            specialization="creative",
            agent_type=AgentType.SUB
        )
        
        designer_agent = GeminiAgent(
            name="DesignerAI",
            specialization="creative",
            agent_type=AgentType.SUB
        )
        
        creative_main.add_sub_agent(writer_agent)
        creative_main.add_sub_agent(designer_agent)
        
        self.register_agent(creative_main)
        self.register_agent(writer_agent)
        self.register_agent(designer_agent)
        
        # Technical Agent with sub-agents
        technical_main = GeminiAgent(
            name="TechnicalAI",
            specialization="technical",
            agent_type=AgentType.MAIN
        )
        
        coder_agent = GeminiAgent(
            name="CoderAI",
            specialization="technical",
            agent_type=AgentType.SUB
        )
        
        architect_agent = GeminiAgent(
            name="ArchitectAI",
            specialization="technical",
            agent_type=AgentType.SUB
        )
        
        technical_main.add_sub_agent(coder_agent)
        technical_main.add_sub_agent(architect_agent)
        
        self.register_agent(technical_main)
        self.register_agent(coder_agent)
        self.register_agent(architect_agent)
        
        # Research Agent with sub-agents
        research_main = GeminiAgent(
            name="ResearchAI",
            specialization="researcher",
            agent_type=AgentType.MAIN
        )
        
        fact_checker = GeminiAgent(
            name="FactCheckerAI",
            specialization="researcher",
            agent_type=AgentType.SUB
        )
        
        trend_analyst = GeminiAgent(
            name="TrendAnalystAI",
            specialization="researcher",
            agent_type=AgentType.SUB
        )
        
        research_main.add_sub_agent(fact_checker)
        research_main.add_sub_agent(trend_analyst)
        
        self.register_agent(research_main)
        self.register_agent(fact_checker)
        self.register_agent(trend_analyst)

        # ── NVIDIA NIM Agents ──────────────────────────────────────────────────
        nim_coordinator = NIMAgent(
            name="NIM-CustodianAI",
            specialization="coordinator",
            agent_type=AgentType.MAIN
        )
        self.register_agent(nim_coordinator)

        nim_technical = NIMAgent(
            name="NIM-TechnicalAI",
            specialization="technical",
            agent_type=AgentType.MAIN
        )
        self.register_agent(nim_technical)

        nim_researcher = NIMAgent(
            name="NIM-ResearchAI",
            specialization="researcher",
            agent_type=AgentType.MAIN
        )
        self.register_agent(nim_researcher)

        nim_creative = NIMAgent(
            name="NIM-CreativeAI",
            specialization="creative",
            agent_type=AgentType.MAIN
        )
        self.register_agent(nim_creative)

        # ── Anthropic Claude Agents ────────────────────────────────────────────
        claude_coordinator = ClaudeAgent(
            name="Claude-CustodianAI",
            specialization="coordinator",
            agent_type=AgentType.MAIN
        )
        self.register_agent(claude_coordinator)

        claude_technical = ClaudeAgent(
            name="Claude-TechnicalAI",
            specialization="technical",
            agent_type=AgentType.MAIN
        )
        self.register_agent(claude_technical)

        claude_analyst = ClaudeAgent(
            name="Claude-AnalystAI",
            specialization="analyst",
            agent_type=AgentType.MAIN
        )
        self.register_agent(claude_analyst)

        claude_researcher = ClaudeAgent(
            name="Claude-ResearchAI",
            specialization="researcher",
            agent_type=AgentType.MAIN
        )
        self.register_agent(claude_researcher)

        # ── Claude Code Agent (CLI-based) ──────────────────────────────────────
        claude_code = ClaudeCodeAgent(
            name="ClaudeCode-AI",
            specialization="technical",
            agent_type=AgentType.MAIN
        )
        self.register_agent(claude_code)

        self.logger.info(f"Initialized {len(self.agents)} agents in the Custodian AI Army")
    
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
            
            # Remove from type-specific dictionaries
            if agent_id in self.main_agents:
                del self.main_agents[agent_id]
            if agent_id in self.sub_agents:
                del self.sub_agents[agent_id]
            
            # Remove from main dictionary
            del self.agents[agent_id]
            
            self.logger.info(f"Unregistered agent: {agent.name} ({agent_id})")
            return True
        
        return False
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID"""
        return self.agents.get(agent_id)
    
    def get_agent_by_name(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name"""
        for agent in self.agents.values():
            if agent.name == name:
                return agent
        return None
    
    def get_agents_by_specialization(self, specialization: str) -> List[BaseAgent]:
        """Get all agents with a specific specialization"""
        result = []
        for agent in self.agents.values():
            if hasattr(agent, 'specialization') and agent.specialization == specialization:
                result.append(agent)
        return result
    
    def get_available_agents(self) -> List[BaseAgent]:
        """Get all agents that are currently available (idle)"""
        return [agent for agent in self.agents.values() if agent.status == AgentStatus.IDLE]
    
    def get_main_agents(self) -> List[BaseAgent]:
        """Get all main agents"""
        return list(self.main_agents.values())
    
    def get_army_status(self) -> Dict[str, Any]:
        """Get the status of the entire agent army"""
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
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def send_message(self, message: AgentMessage) -> AgentMessage:
        """Send a message to a specific agent"""
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
        """Execute a task using the most appropriate agent"""
        
        # Find the best agent for the task
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
        """Find the best agent for a given task"""
        task_type = task.get("type", "general")
        task_description = task.get("description", "").lower()
        
        # Mapping of task types/keywords to specializations
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
        
        # Try to match by task type first
        if task_type in specialization_mapping:
            agents = self.get_agents_by_specialization(specialization_mapping[task_type])
            available_agents = [a for a in agents if a.status == AgentStatus.IDLE and a.agent_type == AgentType.MAIN]
            if available_agents:
                return available_agents[0]
        
        # Try to match by keywords in description
        for keyword, specialization in specialization_mapping.items():
            if keyword in task_description:
                agents = self.get_agents_by_specialization(specialization)
                available_agents = [a for a in agents if a.status == AgentStatus.IDLE and a.agent_type == AgentType.MAIN]
                if available_agents:
                    return available_agents[0]
        
        # Fallback to any available main agent
        available_main_agents = [a for a in self.main_agents.values() if a.status == AgentStatus.IDLE]
        if available_main_agents:
            return available_main_agents[0]
        
        return None
    
    async def broadcast_message(self, message: str, sender_id: str = "system") -> List[AgentMessage]:
        """Broadcast a message to all agents"""
        responses = []
        
        for agent in self.agents.values():
            if agent.agent_id != sender_id:  # Don't send to sender
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
        """Start the message processing loop"""
        self.running = True
        self.logger.info("Started message processing")
        
        while self.running:
            try:
                # Process messages from the queue
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self.send_message(message)
                self.message_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in message processing loop: {str(e)}")
    
    async def stop_message_processing(self):
        """Stop the message processing loop"""
        self.running = False
        self.logger.info("Stopped message processing")
    
    async def shutdown(self):
        """Shutdown all agents and cleanup resources"""
        self.logger.info("Shutting down Agent Manager")
        
        await self.stop_message_processing()
        
        # Close all agents
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