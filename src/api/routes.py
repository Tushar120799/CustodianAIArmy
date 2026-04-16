"""
API Routes for Custodian AI Army
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
import subprocess
import json
import os
import sqlite3
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from src.agents.agent_manager import AgentManager
from src.core.database import (
    get_chats_for_user, save_chat_session, DB_PATH,
    get_user_api_keys, get_user_api_keys_raw, save_user_api_keys, delete_user_api_key, get_user_github_token, save_custom_agent_config, get_custom_agent_config,
    get_user_plan, check_and_increment_rate_limit, upgrade_user_plan
)
from src.agents.base_agent import AgentMessage
from src.core.logging_config import get_logger
from src.api.auth import get_current_user_from_cookies, User
from src.api.build import get_mvp_builder, MVPBuilder

# Initialize router and logger
router = APIRouter()
logger = get_logger("api")

# Global agent manager instance
agent_manager = AgentManager()


# Global MVP Builder instance (initialized on first use)
_mvp_builder: Optional[MVPBuilder] = None


def get_mvp_builder_instance() -> MVPBuilder:
    """Get or create the MVP Builder instance."""
    global _mvp_builder
    if _mvp_builder is None:
        _mvp_builder = get_mvp_builder(agent_manager)
    return _mvp_builder


async def get_owned_mvp_session(
    session_id: str,
    current_user: User = Depends(get_current_user_from_cookies)
) -> "MVPSession":
    """
    Dependency to get an MVP session and verify ownership.
    """
    mvp_builder = get_mvp_builder_instance()
    session = mvp_builder.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify ownership
    if session.user_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized")

    return session


# Pydantic models for MVP Builder API
class MVPCreateSessionRequest(BaseModel):
    product_idea: str


class MVPSessionResponse(BaseModel):
    session_id: str
    product_idea: str
    current_phase: str
    overall_progress: int
    mode: str
    github_connected: bool


class MVPMessageRequest(BaseModel):
    session_id: str
    message: str
    agent_name: Optional[str] = None
    mode: str = "plan"


class MVPAdvancePhaseRequest(BaseModel):
    session_id: str

class MVPPublishRequest(BaseModel):
    session_id: str
    repo_name: str

class MVPConnectGitHubRequest(BaseModel):
    session_id: str
    github_token: str
    repo_name: Optional[str] = None

class MVPDisconnectGitHubRequest(BaseModel):
    session_id: str

class MVPSelectGitHubRepoRequest(BaseModel):
    session_id: str

class CustomAgentConfigRequest(BaseModel):
    agent_id: Optional[str] = None
    name: str
    description: str
    skills: List[str]
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
    history: Optional[List[Dict[str, Any]]] = []

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

# This endpoint is accessible at /api/v1/agents/custom
@router.get("/agents/custom")
async def get_custom_agents_page(
    current_user: User = Depends(get_current_user_from_cookies)
):
    """
    Placeholder endpoint for the custom agents management page.
    This will return a list of custom agents configured by the user.
    """
    try:
        # In a real implementation, you would fetch custom agent configurations
        # from a database associated with the current_user.
        # For now, we'll return a placeholder or any saved configs.
        custom_agent_configs = get_custom_agent_config(current_user.email)
        return {
            "message": "Welcome to your Custom Agents management page!",
            "user_email": current_user.email,
            "custom_agents": custom_agent_configs
        }
    except Exception as e:
        logger.error(f"Error accessing custom agents page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/custom")
async def create_or_update_custom_agent(
    request: CustomAgentConfigRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """
    Create or update a custom agent configuration for the user.
    This allows users to define skills and prompts for their agents.
    """
    try:
        # Save the custom agent configuration to the database
        config_data = request.dict()
        config_data["user_email"] = current_user.email
        agent_id = save_custom_agent_config(config_data)

        return {
            "success": True,
            "message": f"Custom agent '{request.name}' saved successfully.",
            "agent_id": agent_id
        }
    except Exception as e:
        logger.error(f"Error creating/updating custom agent: {str(e)}")
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

@router.post("/chat/guest")
async def guest_chat(chat_request: ChatRequest, request: Request):
    """Guest chat — NIM only, 3 requests/day, no auth required"""
    # Use per-IP identifier so each device gets its own 3-request counter
    # Check X-Forwarded-For first (for reverse proxies / Vercel), fall back to direct client IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    guest_identifier = f"guest_{client_ip}"
    rate = check_and_increment_rate_limit(guest_identifier)
    if not rate["allowed"]:
        return {
            "agent_response": {
                "content": (
                    "🔒 **You've used all 3 free daily requests as a guest.**\n\n"
                    "**Sign in with Google** to unlock:\n"
                    "- ✅ 20 requests per day\n"
                    "- ✅ Access to Gemini, Claude, and NIM providers\n"
                    "- ✅ Chat history saved\n\n"
                    "[Sign in with Google →](/api/v1/auth/google)"
                ),
                "agent_name": "System",
                "agent_id": "system",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"rate_limited": True}
            },
            "plan_info": rate
        }
    # Force NIM for guests
    if agent_manager.active_provider != "nim":
        agent_manager.switch_provider("nim")
    agent_name = chat_request.agent_name or "CustodianAI"
    target = agent_manager.get_agent_by_name(agent_name)
    if not target and chat_request.agent_id:
        target = agent_manager.get_agent(chat_request.agent_id)
    if not target:
        target = next(iter(agent_manager.main_agents.values()), None)
    if not target:
        raise HTTPException(status_code=404, detail="No agent available")
    msg = AgentMessage(
        sender_id="guest",
        receiver_id=target.agent_id,
        content=chat_request.message,
        message_type="chat"
    )
    response = await agent_manager.send_message(msg)
    return {
        "agent_response": {
            "content": response.content,
            "agent_name": target.name,
            "agent_id": target.agent_id,
            "specialization": getattr(target, "specialization", None),
            "timestamp": response.timestamp.isoformat(),
            "metadata": response.metadata
        },
        "plan_info": rate
    }


@router.get("/user/plan")
async def get_user_plan_endpoint(request: Request):
    """Get plan info — guest-friendly (no auth required)"""
    from src.api.auth import get_user_from_session, decode_jwt_token
    email = "guest@custodian.ai"
    try:
        # Try session cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            user = get_user_from_session(session_id)
            if user:
                email = user.email
        # Try JWT access_token cookie
        if email == "guest@custodian.ai":
            access_token = request.cookies.get("access_token")
            if access_token:
                payload = decode_jwt_token(access_token)
                if payload and payload.get("email"):
                    email = payload["email"]
    except Exception:
        pass
    plan_info = get_user_plan(email)
    return plan_info


@router.post("/chat")
async def chat_with_agent(
    request: ChatRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Chat with a specific agent or let the system choose the best one"""
    try:
        # Log security event - user is authenticated
        logger.info(f"Authenticated chat request from user: {current_user.email} (ID: {current_user.id})")

        # ── Rate limiting for free/pro users ──────────────────────────────────
        rate = check_and_increment_rate_limit(current_user.email)
        if not rate["allowed"]:
            return {
                "agent_response": {
                    "content": (
                        "⚠️ **Daily request limit reached.**\n\n"
                        "You have used all your free requests for today. "
                        "Your limit resets at midnight UTC.\n\n"
                        "Upgrade to **Pro** for 50 requests/day and priority access."
                    ),
                    "agent_name": "System",
                    "agent_id": "system",
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {"rate_limited": True}
                },
                "plan_info": rate
            }

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
        
        # Build conversation history (cap at last 20 messages to avoid token limits)
        history = request.history[-20:] if request.history else []

        # Create and send message
        chat_message = AgentMessage(
            sender_id="user",
            receiver_id=target_agent.agent_id,
            content=request.message,
            message_type="chat",
            metadata={"history": history}
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

# ─────────────────────────────────────────────────────────────────────────────
# COURSE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

# Path to the course data JSON (served from static/data/)
COURSE_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "data", "course-data.json")
# Path to Programming-Slides sections
SLIDES_SECTIONS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dependencies", "Programming-Slides", "sections")


def _load_course_data() -> List[Dict[str, Any]]:
    """Load course data from JSON file"""
    try:
        with open(COURSE_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("courses", [])
    except Exception as e:
        logger.error(f"Error loading course data: {str(e)}")
        return []


@router.get("/courses")
async def list_courses(lang: Optional[str] = None, category: Optional[str] = None):
    """List all available courses, optionally filtered by language and/or category"""
    try:
        courses = _load_course_data()
        if lang:
            courses = [c for c in courses if c.get("lang") == lang]
        if category:
            courses = [c for c in courses if c.get("category", "").lower() == category.lower()]
        # Strip sections from list view for brevity
        summary = []
        for c in courses:
            summary.append({
                "id": c["id"],
                "lang": c["lang"],
                "title": c["title"],
                "category": c.get("category", "General"),
                "description": c.get("description", ""),
                "icon": c.get("icon", "fas fa-book"),
                "slide_count": c.get("slide_count", 0),
                "section_count": len(c.get("sections", []))
            })
        return {"courses": summary, "total": len(summary)}
    except Exception as e:
        logger.error(f"Error listing courses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_id}")
async def get_course(course_id: str, lang: str = "en"):
    """Get full course details including sections"""
    try:
        courses = _load_course_data()
        course = next((c for c in courses if c["id"] == course_id and c["lang"] == lang), None)
        if not course:
            # Try any language
            course = next((c for c in courses if c["id"] == course_id), None)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        return course
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_id}/slides/{lang}")
async def get_course_slides(course_id: str, lang: str):
    """Get all slide content for a course as a list of sections with markdown content"""
    try:
        courses = _load_course_data()
        course = next((c for c in courses if c["id"] == course_id and c["lang"] == lang), None)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        section_dir = os.path.join(SLIDES_SECTIONS_PATH, course_id)
        slides = []
        for i, section in enumerate(course.get("sections", [])):
            file_path = os.path.join(section_dir, section["file"])
            content = ""
            if os.path.isfile(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            slides.append({
                "index": i,
                "title": section["title"],
                "file": section["file"],
                "content": content
            })
        return {"course_id": course_id, "lang": lang, "slides": slides}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course slides: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_id}/slides/{lang}/{section_index}")
async def get_single_slide(course_id: str, lang: str, section_index: int):
    """Get a single slide's content by index"""
    try:
        courses = _load_course_data()
        course = next((c for c in courses if c["id"] == course_id and c["lang"] == lang), None)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        sections = course.get("sections", [])
        if section_index < 0 or section_index >= len(sections):
            raise HTTPException(status_code=404, detail="Section index out of range")

        section = sections[section_index]
        section_dir = os.path.join(SLIDES_SECTIONS_PATH, course_id)
        file_path = os.path.join(section_dir, section["file"])
        content = ""
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

        return {
            "course_id": course_id,
            "lang": lang,
            "index": section_index,
            "title": section["title"],
            "file": section["file"],
            "content": content,
            "total_sections": len(sections)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting slide: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class ProgressUpdateRequest(BaseModel):
    course_id: str
    lang: str = "en"
    section_index: int = 0
    completed_sections: List[int] = []


@router.get("/progress")
async def get_user_progress(
    session_id: Optional[str] = None,
    access_token: Optional[str] = None
):
    """Get all course progress for the authenticated user (guest-friendly: returns empty if not authed)"""
    from fastapi import Cookie
    from src.api.auth import get_user_from_session, decode_jwt_token
    # Try to get user from cookies manually (guest-friendly)
    user = None
    try:
        from starlette.requests import Request
    except Exception:
        pass
    # Return empty progress for guests
    return {"progress": []}


@router.get("/progress/me")
async def get_my_progress(
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Get all course progress for the authenticated user"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT course_id, lang, section_index, completed_sections, last_updated
            FROM user_progress
            WHERE user_email = ?
            ORDER BY last_updated DESC
        ''', (current_user.email,))
        rows = cursor.fetchall()
        conn.close()

        progress = []
        for row in rows:
            progress.append({
                "course_id": row[0],
                "lang": row[1],
                "section_index": row[2],
                "completed_sections": json.loads(row[3]),
                "last_updated": row[4]
            })
        return {"progress": progress}
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/progress")
async def update_user_progress(
    request: ProgressUpdateRequest,
    session_id: Optional[str] = None,
    access_token: Optional[str] = None
):
    """Update course progress - silently ignores if user not authenticated (guest mode)"""
    from src.api.auth import get_user_from_session, decode_jwt_token
    user = None
    if session_id:
        user = get_user_from_session(session_id)
    if not user and access_token:
        payload = decode_jwt_token(access_token)
        if payload:
            from src.api.auth import User as AuthUser
            user = AuthUser(id=payload["sub"], email=payload["email"], name=payload["name"], picture=payload.get("picture"))
    if not user:
        # Guest mode: silently ignore progress saves
        return {"status": "guest", "message": "Progress not saved (not authenticated)"}
    try:
        now = datetime.utcnow().isoformat()
        completed_str = json.dumps(request.completed_sections)
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_progress (user_email, course_id, lang, section_index, completed_sections, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_email, course_id, lang) DO UPDATE SET
                section_index=excluded.section_index,
                completed_sections=excluded.completed_sections,
                last_updated=excluded.last_updated
        ''', (user.email, request.course_id, request.lang, request.section_index, completed_str, now))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Progress updated"}
    except Exception as e:
        logger.error(f"Error updating progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# COURSE-AWARE CHAT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class CourseChatRequest(BaseModel):
    message: str
    course_id: Optional[str] = None
    lang: str = "en"
    section_index: int = 0
    code: Optional[str] = None


@router.post("/chat/course")
async def course_chat(
    request: CourseChatRequest
):
    """Chat with the AI tutor with course context awareness (no auth required - open to all users)"""
    try:
        # Build course context if course_id provided
        course_context = {}
        if request.course_id:
            courses = _load_course_data()
            course = next((c for c in courses if c["id"] == request.course_id and c["lang"] == request.lang), None)
            if course:
                sections = course.get("sections", [])
                current_section = sections[request.section_index] if request.section_index < len(sections) else {}
                # Load slide content
                section_dir = os.path.join(SLIDES_SECTIONS_PATH, request.course_id)
                slide_content = ""
                if current_section.get("file"):
                    file_path = os.path.join(section_dir, current_section["file"])
                    if os.path.isfile(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            slide_content = f.read()[:2000]  # Limit context size
                course_context = {
                    "course_title": course["title"],
                    "section_title": current_section.get("title", ""),
                    "slide_content": slide_content,
                    "user_code": request.code or ""
                }

        # Get or create tutor agent
        tutor_agent = agent_manager.get_agent_by_name("TechnicalAI")
        if not tutor_agent:
            tutor_agent = agent_manager.get_agent_by_name("CustodianAI")
        if not tutor_agent:
            raise HTTPException(status_code=404, detail="No suitable agent found")

        # Build enriched message with course context
        enriched_message = request.message
        if course_context:
            enriched_message = f"""[Course Context]
Course: {course_context.get('course_title', '')}
Topic: {course_context.get('section_title', '')}
Slide Content:
{course_context.get('slide_content', '')}

{"User's Code:\n```\n" + course_context.get('user_code', '') + "\n```\n" if course_context.get('user_code') else ''}
[Student Question]
{request.message}"""

        chat_message = AgentMessage(
            sender_id="user",
            receiver_id=tutor_agent.agent_id,
            content=enriched_message,
            message_type="chat",
            metadata={"course_context": course_context, "is_tutor_mode": True}
        )

        response = await agent_manager.send_message(chat_message)

        return {
            "user_message": request.message,
            "agent_response": {
                "content": response.content,
                "agent_name": tutor_agent.name,
                "agent_id": tutor_agent.agent_id,
                "timestamp": response.timestamp.isoformat(),
            },
            "course_context": {
                "course_id": request.course_id,
                "section_index": request.section_index,
                "section_title": course_context.get("section_title", "")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in course chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP / SHUTDOWN
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# USER API KEYS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class UserApiKeysRequest(BaseModel):
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    nim_api_key: Optional[str] = None

class SwitchProviderRequest(BaseModel):
    provider: str  # 'gemini' | 'anthropic' | 'nim'


@router.get("/user/api-keys")
async def get_my_api_keys(
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Get the current user's saved API keys (masked for security)"""
    try:
        keys = get_user_api_keys(current_user.email)
        return {
            "status": "success",
            "user_email": current_user.email,
            "keys": keys
        }
    except Exception as e:
        logger.error(f"Error getting API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/api-keys")
async def save_my_api_keys(
    request: UserApiKeysRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Save or update the current user's API keys"""
    try:
        keys_dict = {
            "gemini_api_key": request.gemini_api_key,
            "anthropic_api_key": request.anthropic_api_key,
            "nim_api_key": request.nim_api_key,
        }
        success = save_user_api_keys(current_user.email, keys_dict)
        if success:
            return {"status": "success", "message": "API keys saved successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save API keys")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/provider/switch")
async def switch_provider(
    request: SwitchProviderRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Switch the active AI provider for all agents globally."""
    valid_providers = ["groq", "gemini", "anthropic", "nim"]
    if request.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )
    try:
        # Load user's API keys to inject into the new agents
        user_keys = get_user_api_keys_raw(current_user.email)
        success = agent_manager.switch_provider(request.provider, user_keys)
        if success:
            return {
                "status": "success",
                "active_provider": agent_manager.active_provider,
                "message": f"All agents switched to {request.provider}"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching provider: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/provider/active")
async def get_active_provider():
    """Get the currently active AI provider."""
    return {
        "active_provider": agent_manager.active_provider,
        "available_providers": ["groq", "gemini", "anthropic", "nim"]
    }


class UpgradePlanRequest(BaseModel):
    plan: str  # 'pro' | 'free'


@router.post("/user/upgrade-plan")
async def upgrade_plan(
    request: UpgradePlanRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Upgrade the current user's plan (called after payment confirmation)."""
    valid_plans = ["free", "pro"]
    if request.plan not in valid_plans:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {', '.join(valid_plans)}")
    try:
        success = upgrade_user_plan(current_user.email, request.plan)
        if success:
            plan_info = get_user_plan(current_user.email)
            return {
                "status": "success",
                "message": f"Plan upgraded to {request.plan}",
                "plan": request.plan,
                "plan_info": plan_info
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upgrade plan")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upgrading plan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/api-keys/{provider}")
async def delete_my_api_key(
    provider: str,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Delete a specific provider's API key for the current user"""
    valid_providers = ["gemini", "anthropic", "nim"]
    if provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )
    try:
        success = delete_user_api_key(current_user.email, provider)
        if success:
            return {"status": "success", "message": f"{provider} API key removed"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete API key")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP / SHUTDOWN
# ─────────────────────────────────────────────────────────────────────────────

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



# ─────────────────────────────────────────────────────────────────────────────
# MVP Builder API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/mvp/create-session")
async def mvp_create_session(
    request: MVPCreateSessionRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Create a new MVP building session."""
    try:
        mvp_builder = get_mvp_builder_instance()
        session = await mvp_builder.create_session(current_user.email, request.product_idea)

        return {
            "success": True,
            "session": session.to_dict()
        }
    except Exception as e:
        logger.error(f"Error creating MVP session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mvp/sessions")
async def mvp_get_all_sessions(
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Get all MVP sessions for the current user."""
    try:
        mvp_builder = get_mvp_builder_instance()
        user_sessions = [
            s.to_dict() for s in mvp_builder.sessions.values()
            if s.user_email == current_user.email
        ]
        return {
            "success": True,
            "sessions": user_sessions,
            "count": len(user_sessions)
        }
    except Exception as e:
        logger.error(f"Error getting user MVP sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mvp/session/{mvp_session_id}")
async def mvp_get_session(
    mvp_session_id: str,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Get an existing MVP session."""
    try:
        session = await get_owned_mvp_session(mvp_session_id, current_user)
        return {"success": True, "session": session.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MVP session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mvp/send-message")
async def mvp_send_message(
    request: MVPMessageRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Send a message to the MVP builder."""
    try:
        mvp_builder = get_mvp_builder_instance()
        session = await get_owned_mvp_session(request.session_id, current_user)
        result = await mvp_builder.send_message(request.session_id, request.message, request.mode, request.agent_name)
        return {
            "success": True,
            "result": result,
            "session": session.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending MVP message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mvp/advance-phase")
async def mvp_advance_phase(
    request: MVPAdvancePhaseRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Advance to the next MVP phase."""
    try:
        mvp_builder = get_mvp_builder_instance()
        result = await mvp_builder.advance_phase(request.session_id)
        session = await get_owned_mvp_session(request.session_id, current_user)
        return {
            "success": result.get("success", False),
            "result": result,
            "session": session.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error advancing MVP phase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mvp/session/{mvp_session_id}/files")
async def mvp_list_files(
    mvp_session_id: str,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """List all files in the MVP workspace."""
    try:
        mvp_builder = get_mvp_builder_instance()
        session = await get_owned_mvp_session(mvp_session_id, current_user)
        file_tree = mvp_builder.get_workspace_files_tree(mvp_session_id)

        return {
            "success": True,
            "files": file_tree,
            "file_count": len(session.files)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing MVP files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mvp/session/{mvp_session_id}/file")
async def mvp_read_file(
    mvp_session_id: str,
    path: str,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Read a specific file from the MVP workspace."""
    try:
        mvp_builder = get_mvp_builder_instance()
        await get_owned_mvp_session(mvp_session_id, current_user)
        content = await mvp_builder.read_file(mvp_session_id, path)

        if content is None:
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "success": True,
            "path": path,
            "content": content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading MVP file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mvp/connect-github")
async def mvp_connect_github(
    request: MVPConnectGitHubRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Connect GitHub account for publishing.""" # This line was correctly indented.
    github_token_to_use = request.github_token
    try:
        # If no token provided in request, try to get it from user's saved keys
        if not github_token_to_use:
            # Assuming get_user_github_token exists and retrieves the token
            github_token_to_use = get_user_github_token(current_user.email)

        if not github_token_to_use:
            raise HTTPException(status_code=400, detail="GitHub token is required to connect. Please provide one or connect via profile settings.")
        mvp_builder = get_mvp_builder_instance()
        await get_owned_mvp_session(request.session_id, current_user)
        result = await mvp_builder.connect_github(request.session_id, github_token_to_use, request.repo_name)
        return {
            "success": result.get("success", False),
            "message": result.get("message", "GitHub connected"),
            "github_username": result.get("github_username")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting GitHub: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mvp/disconnect-github")
async def mvp_disconnect_github(
    request: MVPDisconnectGitHubRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Disconnect GitHub account for a session."""
    try:
        session = await get_owned_mvp_session(request.session_id, current_user)
        session.github_connected = False
        session.github_token = None
        session.github_username = None
        session.github_repo_name = None
        session.add_log("GitHub account disconnected.")
        return {
            "success": True,
            "message": "GitHub account disconnected successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting GitHub: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mvp/session/{mvp_session_id}/github-repos")
async def mvp_get_github_repos(
    mvp_session_id: str,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Get a list of repositories for the connected GitHub account."""
    try:
        mvp_builder = get_mvp_builder_instance()
        await get_owned_mvp_session(mvp_session_id, current_user)
        repos = await mvp_builder.get_github_repos(mvp_session_id)
        return {"success": True, "repos": repos}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GitHub repos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mvp/publish")
async def mvp_publish_to_github(
    request: MVPPublishRequest,
    current_user: User = Depends(get_current_user_from_cookies)
):
    """Publish the MVP to GitHub."""
    try:
        mvp_builder = get_mvp_builder_instance()
        result = await mvp_builder.publish_to_github(request.session_id, request.repo_name)
        await get_owned_mvp_session(request.session_id, current_user)
        return {
            "success": result.get("success", False),
            "repo_url": result.get("repo_url"),
            "message": result.get("message")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing to GitHub: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
