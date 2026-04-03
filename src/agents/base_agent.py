"""
Base Agent class for Custodian AI Army
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
import uuid
from datetime import datetime
from pydantic import BaseModel

from src.core.logging_config import get_logger


class AgentStatus(Enum):
    """Agent status enumeration"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class AgentType(Enum):
    """Agent type enumeration"""
    MAIN = "main"
    SUB = "sub"


class AgentCapability(BaseModel):
    """Agent capability model"""
    name: str
    description: str
    parameters: Dict[str, Any] = {}


class AgentMessage(BaseModel):
    """Message model for agent communication"""
    id: str = None
    sender_id: str
    receiver_id: str
    content: str
    message_type: str = "text"
    timestamp: datetime = None
    metadata: Dict[str, Any] = {}
    
    def __init__(self, **data):
        if data.get('id') is None:
            data['id'] = str(uuid.uuid4())
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class BaseAgent(ABC):
    """Base class for all agents in the Custodian AI Army"""
    
    def __init__(
        self,
        agent_id: str = None,
        name: str = "BaseAgent",
        agent_type: AgentType = AgentType.MAIN,
        capabilities: List[AgentCapability] = None
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name
        self.agent_type = agent_type
        self.status = AgentStatus.IDLE
        self.capabilities = capabilities or []
        self.sub_agents: List['BaseAgent'] = []
        self.parent_agent: Optional['BaseAgent'] = None
        self.logger = get_logger(f"agent.{self.name}")
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
        self.logger.info(f"Agent {self.name} ({self.agent_id}) initialized")
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and return a response"""
        pass
    
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task"""
        pass
    
    def add_sub_agent(self, sub_agent: 'BaseAgent') -> None:
        """Add a sub-agent to this agent"""
        if sub_agent not in self.sub_agents:
            self.sub_agents.append(sub_agent)
            sub_agent.parent_agent = self
            self.logger.info(f"Sub-agent {sub_agent.name} added to {self.name}")
    
    def remove_sub_agent(self, sub_agent: 'BaseAgent') -> None:
        """Remove a sub-agent from this agent"""
        if sub_agent in self.sub_agents:
            self.sub_agents.remove(sub_agent)
            sub_agent.parent_agent = None
            self.logger.info(f"Sub-agent {sub_agent.name} removed from {self.name}")
    
    async def delegate_to_sub_agent(
        self, 
        task: Dict[str, Any], 
        sub_agent_name: str = None
    ) -> Dict[str, Any]:
        """Delegate a task to a sub-agent"""
        if not self.sub_agents:
            raise ValueError("No sub-agents available for delegation")
        
        # Find the appropriate sub-agent
        target_agent = None
        if sub_agent_name:
            target_agent = next(
                (agent for agent in self.sub_agents if agent.name == sub_agent_name),
                None
            )
        else:
            # Find the first available sub-agent
            target_agent = next(
                (agent for agent in self.sub_agents if agent.status == AgentStatus.IDLE),
                None
            )
        
        if not target_agent:
            raise ValueError("No suitable sub-agent found for delegation")
        
        self.logger.info(f"Delegating task to sub-agent {target_agent.name}")
        return await target_agent.execute_task(task)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "type": self.agent_type.value,
            "status": self.status.value,
            "capabilities": [cap.dict() for cap in self.capabilities],
            "sub_agents": [agent.agent_id for agent in self.sub_agents],
            "parent_agent": self.parent_agent.agent_id if self.parent_agent else None,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }
    
    def update_status(self, status: AgentStatus) -> None:
        """Update agent status"""
        old_status = self.status
        self.status = status
        self.last_activity = datetime.utcnow()
        self.logger.info(f"Agent {self.name} status changed from {old_status.value} to {status.value}")
    
    def add_capability(self, capability: AgentCapability) -> None:
        """Add a new capability to the agent"""
        self.capabilities.append(capability)
        self.logger.info(f"Capability '{capability.name}' added to agent {self.name}")
    
    def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a specific capability"""
        return any(cap.name == capability_name for cap in self.capabilities)