"""
API Routes for Custodian AI Army
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import subprocess
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

from src.agents.agent_manager import AgentManager
from src.core.database import get_chats_for_user, save_chat_session
from src.agents.base_agent import AgentMessage
from src.core.logging_config import get_logger
from src.api.auth import get_current_user_from_cookies, User

# Initialize router and logger
router = APIRouter()
logger = get_logger("api")

# Global agent manager instance
agent_manager = AgentManager()

# Pydantic models for API requests/responses
class TaskRequest(BaseModel):
    description: str
    task_type: str = "general"
    parameters: Dict[str, Any] = {}
    preferred_agent: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    agent_name: Optional[str] = None
    agent_id: Optional[str] = None

class ChatSessionSaveRequest(BaseModel):
    id: Optional[str] = None
    user_email: str
    title: str
    start_time: Optional[str] = None
    messages: List[Dict[str, Any]]

class CodeExecutionRequest(BaseModel):
    code: str
    language: str

class MessageRequest(BaseModel):
    content: str
    receiver_id: str
    message_type: str = "text"
    metadata: Dict[str, Any] = {}

class AgentStatusResponse(BaseModel):
    agent_id: str
    name: str
    type: str
    status: str
    specialization: Optional[str] = None
    capabilities: List[Dict[str, Any]]
    sub_agents: List[str]
    parent_agent: Optional[str]
    created_at: str
    last_activity: str

class ArmyStatusResponse(BaseModel):
    total_agents: int
    main_agents: int
    sub_agents: int
    status_distribution: Dict[str, int]
    agents: List[AgentStatusResponse]
    last_updated: str

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@router.get("/army/status", response_model=ArmyStatusResponse)
async def get_army_status():
    """Get the status of the entire agent army"""
    try:
        status = agent_manager.get_army_status()
        return status
    except Exception as e:
        logger.error(f"Error getting army status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents")
async def list_agents():
    """List all agents"""
    try:
        agents = []
        for agent in agent_manager.agents.values():
            agent_info = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "type": agent.agent_type.value,
                "status": agent.status.value,
                "specialization": getattr(agent, 'specialization', None),
                "capabilities": [cap.dict() for cap in agent.capabilities],
                "sub_agents_count": len(agent.sub_agents),
                "parent_agent": agent.parent_agent.agent_id if agent.parent_agent else None
            }
            agents.append(agent_info)
        
        return {"agents": agents, "total": len(agents)}
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}")
async def get_agent_details(agent_id: str):
    """Get detailed information about a specific agent"""
    try:
        agent = agent_manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return agent.get_status()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/by-name/{agent_name}")
async def get_agent_by_name(agent_name: str):
    """Get agent information by name"""
    try:
        agent = agent_manager.get_agent_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return agent.get_status()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent by name: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/specialization/{specialization}")
async def get_agents_by_specialization(specialization: str):
    """Get all agents with a specific specialization"""
    try:
        agents = agent_manager.get_agents_by_specialization(specialization)
        agent_list = [agent.get_status() for agent in agents]
        
        return {
            "specialization": specialization,
            "agents": agent_list,
            "count": len(agent_list)
        }
    except Exception as e:
        logger.error(f"Error getting agents by specialization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/execute")
async def execute_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """Execute a task using the most appropriate agent"""
    try:
        task = {
            "id": str(uuid.uuid4()),
            "type": task_request.task_type,
            "description": task_request.description,
            "parameters": task_request.parameters,
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Executing task: {task['id']}")
        
        result = await agent_manager.execute_task(task, task_request.preferred_agent)
        
        return {
            "task_id": task["id"],
            "status": "completed",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error executing task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/messages/send")
async def send_message(message_request: MessageRequest):
    """Send a message to a specific agent"""
    try:
        message = AgentMessage(
            sender_id="user",
            receiver_id=message_request.receiver_id,
            content=message_request.content,
            message_type=message_request.message_type,
            metadata=message_request.metadata
        )
        
        response = await agent_manager.send_message(message)
        
        return {
            "message_id": message.id,
            "response": {
                "id": response.id,
                "content": response.content,
                "sender_id": response.sender_id,
                "message_type": response.message_type,
                "timestamp": response.timestamp.isoformat(),
                "metadata": response.metadata
            }
        }
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/messages/broadcast")
async def broadcast_message(content: str):
    """Broadcast a message to all agents"""
    try:
        responses = await agent_manager.broadcast_message(content)
        
        response_data = []
        for response in responses:
            response_data.append({
                "id": response.id,
                "content": response.content,
                "sender_id": response.sender_id,
                "message_type": response.message_type,
                "timestamp": response.timestamp.isoformat(),
                "metadata": response.metadata
            })
        
        return {
            "broadcast_message": content,
            "responses": response_data,
            "response_count": len(response_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error broadcasting message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/available")
async def get_available_agents():
    """Get all currently available (idle) agents"""
    try:
        available_agents = agent_manager.get_available_agents()
        agent_list = [agent.get_status() for agent in available_agents]
        
        return {
            "available_agents": agent_list,
            "count": len(agent_list),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting available agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/main")
async def get_main_agents():
    """Get all main agents"""
    # Use the same logic as /agents but filter for main agents
    agents = []
    for agent in agent_manager.agents.values():
        if agent.agent_type.value == "main":
            agent_info = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "type": agent.agent_type.value,
                "status": agent.status.value,
                "specialization": getattr(agent, 'specialization', 'general'),
                "capabilities": [cap.dict() for cap in agent.capabilities],
                "sub_agents_count": len(agent.sub_agents),
                "parent_agent": agent.parent_agent.agent_id if agent.parent_agent else None
            }
            agents.append(agent_info)
    
    return {
        "main_agents": agents,
        "count": len(agents),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/chat")
async def chat_with_agent(
    request: ChatRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Chat with a specific agent or let the system choose the best one"""
    try:
        # Log security event - user is authenticated
        logger.info(f"Authenticated chat request from user: {current_user.email} (ID: {current_user.id})")

        # Find the target agent
        target_agent = None
        
        if request.agent_id:
            target_agent = agent_manager.get_agent(request.agent_id)
        elif request.agent_name:
            target_agent = agent_manager.get_agent_by_name(request.agent_name)
        else:
            # Use the coordinator agent as default
            target_agent = agent_manager.get_agent_by_name("CommanderAI")
        
        if not target_agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Create and send message
        chat_message = AgentMessage(
            sender_id="user",
            receiver_id=target_agent.agent_id,
            content=request.message,
            message_type="chat"
        )
        
        response = await agent_manager.send_message(chat_message)
        
        return {
            "user_message": request.message,
            "agent_response": {
                "content": response.content,
                "agent_name": target_agent.name,
                "agent_id": target_agent.agent_id,
                "specialization": getattr(target_agent, 'specialization', None),
                "timestamp": response.timestamp.isoformat(),
                "metadata": response.metadata
            },
            "user_info": {
                "user_id": current_user.id,
                "user_email": current_user.email,
                "user_name": current_user.name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/specializations")
async def get_available_specializations():
    """Get all available agent specializations"""
    try:
        specializations = set()
        for agent in agent_manager.agents.values():
            if hasattr(agent, 'specialization'):
                specializations.add(agent.specialization)
        
        return {
            "specializations": list(specializations),
            "count": len(specializations)
        }
        
    except Exception as e:
        logger.error(f"Error getting specializations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute-code")
async def execute_code(request: CodeExecutionRequest):
    """Execute code and return output"""
    try:
        if request.language.lower() in ["python", "py", "python3"]:
            # Basic python execution
            process = subprocess.Popen(
                ["python3", "-c", request.code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=10)
            
            return {
                "output": stdout if stdout else "",
                "error": stderr if stderr else "",
                "exit_code": process.returncode
            }
        else:
            return {"error": f"Language '{request.language}' execution is not supported yet. Only Python is supported.", "output": "", "exit_code": 1}
    except subprocess.TimeoutExpired:
        process.kill()
        return {"error": "Execution timed out", "output": "", "exit_code": -1}
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        return {"error": str(e), "output": "", "exit_code": -1}

@router.get("/chats")
async def get_chats(email: str):
    """Get all chat sessions for a user"""
    try:
        chats = get_chats_for_user(email)
        return {"chats": chats}
    except Exception as e:
        logger.error(f"Error getting chats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chats")
async def save_chat(request: ChatSessionSaveRequest):
    """Save or update a chat session"""
    try:
        chat_id = save_chat_session(request.dict())
        return {"status": "success", "id": chat_id}
    except Exception as e:
        logger.error(f"Error saving chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Debug endpoint to check agent manager state
@router.get("/debug/agents")
async def debug_agents():
    """Debug endpoint to check agent manager state"""
    return {
        "agent_manager_exists": agent_manager is not None,
        "agents_dict_exists": hasattr(agent_manager, 'agents'),
        "agents_count": len(agent_manager.agents) if hasattr(agent_manager, 'agents') else 0,
        "main_agents_dict_exists": hasattr(agent_manager, 'main_agents'),
        "main_agents_count": len(agent_manager.main_agents) if hasattr(agent_manager, 'main_agents') else 0,
        "agent_names": [agent.name for agent in agent_manager.agents.values()] if hasattr(agent_manager, 'agents') else []
    }

# Startup and shutdown events
@router.on_event("startup")
async def startup_event():
    """Initialize the agent manager on startup"""
    logger.info("API startup - Agent Manager initialized")

@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("API shutdown - Cleaning up Agent Manager")
    await agent_manager.shutdown()
