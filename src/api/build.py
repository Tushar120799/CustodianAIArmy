"""
MVP Builder — Reinforced MVP Developer Pipeline Integration

This module implements the 5-phase MVP development pipeline:
1. Ideation — Refine product concept
2. Planning — Architecture & tech stack
3. Review — Validate approach
4. Polish — UX improvements
5. Build — Generate production code

Uses existing CustodianAI agent infrastructure and MCP tools.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

import httpx
from src.agents.agent_manager import AgentManager
from src.mcp.mcp_client import MCPToolExecutor
from src.core.logging_config import get_logger

logger = get_logger("mvp_builder")


class MVPPhase:
    """Represents a single phase in the MVP development pipeline."""

    def __init__(self, name: str, description: str, agent_specialization: str):
        self.name = name
        self.description = description
        self.agent_specialization = agent_specialization
        self.tasks: List[Dict[str, Any]] = []
        self.progress: int = 0
        self.status: str = "pending"  # pending, active, completed
        self.output: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "agent_specialization": self.agent_specialization,
            "tasks": self.tasks,
            "progress": self.progress,
            "status": self.status,
            "output": self.output
        }


class MVPSession:
    """Represents an active MVP building session."""

    def __init__(self, session_id: str, user_email: str, product_idea: str):
        self.session_id = session_id
        self.user_email = user_email
        self.product_idea = product_idea
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.current_phase_index: int = 0
        self.mode: str = "plan"  # plan or act
        self.github_connected: bool = False
        self.github_repo_name: Optional[str] = None
        self.github_token: Optional[str] = None  # Store token for operations
        self.github_username: Optional[str] = None
        self.workspace_path: Optional[Path] = None
        self.files: Dict[str, str] = {}
        self.chat_history: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []

        # Initialize 5 phases
        self.phases: List[MVPPhase] = [
            MVPPhase("Ideation", "Refine your product concept", "coordinator"),
            MVPPhase("Planning", "Architecture & tech stack", "architect"),
            MVPPhase("Review", "Validate the approach", "technical"),
            MVPPhase("Polish", "UX improvements", "designer"),
            MVPPhase("Build", "Generate production code", "coder"),
        ]

    @property
    def current_phase(self) -> MVPPhase:
        if 0 <= self.current_phase_index < len(self.phases):
            return self.phases[self.current_phase_index]
        return None

    @property
    def overall_progress(self) -> int:
        if not self.phases:
            return 0
        total = sum(p.progress for p in self.phases)
        return min(100, total // len(self.phases))

    def add_log(self, message: str, level: str = "info"):
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "level": level
        })
        logger.info(f"[MVPSession {self.session_id}] {message}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_email": self.user_email,
            "product_idea": self.product_idea,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_phase_index": self.current_phase_index,
            "current_phase": self.current_phase.name if self.current_phase else None,
            "mode": self.mode,
            "github_connected": self.github_connected,
            "github_repo_name": self.github_repo_name,
            "github_username": self.github_username,
            "overall_progress": self.overall_progress,
            "phases": [p.to_dict() for p in self.phases],
            "files": list(self.files.keys()),
            "chat_history": self.chat_history[-20:],  # Last 20 messages
            "logs": self.logs[-50:]  # Last 50 logs
        }


class MVPBuilder:
    """
    Main MVP Builder class that orchestrates the 5-phase pipeline.

    Integrates with:
    - Existing AgentManager for AI agent orchestration
    - MCP tools for file operations, web search, etc.
    - Container-based isolated workspaces (optional)
    """

    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.sessions: Dict[str, MVPSession] = {}
        self.workspace_base = Path("/tmp/mvp-workspaces")
        self.workspace_base.mkdir(parents=True, exist_ok=True)
        logger.info("MVP Builder initialized")

    async def create_session(self, user_email: str, product_idea: str) -> MVPSession:
        """Create a new MVP building session."""
        session_id = str(uuid.uuid4())
        session = MVPSession(session_id, user_email, product_idea)

        # Create isolated workspace
        workspace_path = self.workspace_base / session_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        session.workspace_path = workspace_path

        session.add_log(f"Session created for product: {product_idea[:50]}...", "info")
        self.sessions[session_id] = session

        return session

    def get_session(self, session_id: str) -> Optional[MVPSession]:
        """Get an existing session by ID."""
        return self.sessions.get(session_id)

    async def send_message(self, session_id: str, message: str, mode: str = "plan", agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to the MVP builder for a session.

        In 'plan' mode: Discuss and refine ideas
        In 'act' mode: Execute tasks and generate code
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.mode = mode
        session.chat_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.utcnow().isoformat(),
            "mode": mode
        })

        # Get appropriate agent for current phase
        current_phase = session.current_phase
        if not current_phase:
            return {"error": "No active phase"}

        # Find agent
        if agent_name:
            agent = self.agent_manager.get_agent_by_name(agent_name)
        else:
            # Find agent with matching specialization
            agent = self._get_agent_for_specialization(current_phase.agent_specialization)
            if not agent:
                agent = self.agent_manager.get_agent_by_name("CustodianAI")

        # Build context-aware prompt
        prompt = self._build_phase_prompt(session, message, mode)

        # Execute agent call
        try:
            from src.agents.base_agent import AgentMessage
            msg = AgentMessage(
                sender_id="mvp_builder",
                receiver_id=agent.agent_id,
                content=prompt,
                message_type="chat",
                metadata={"phase": current_phase.name, "mode": mode}
            )

            response = await self.agent_manager.send_message(msg)

            # Process response
            session.chat_history.append({
                "role": "assistant",
                "content": response.content,
                "timestamp": datetime.utcnow().isoformat(),
                "agent_name": agent.name,
                "phase": current_phase.name
            })

            session.add_log(f"Agent {agent.name} responded in {current_phase.name} phase")

            # Update phase progress
            if mode == "act":
                current_phase.progress = min(100, current_phase.progress + 20)

            session.updated_at = datetime.utcnow()

            return {
                "response": response.content,
                "agent_name": agent.name,
                "phase": current_phase.name,
                "progress": session.overall_progress
            }

        except Exception as e:
            logger.error(f"Error in MVP message processing: {e}")
            session.add_log(f"Error: {str(e)}", "error")
            return {"error": str(e)}

    def _get_agent_for_specialization(self, specialization: str):
        """Get an agent with the specified specialization."""
        agents = self.agent_manager.get_agents_by_specialization(specialization)
        if agents:
            return agents[0]

        # Fallback mappings
        fallback_map = {
            "coordinator": "CustodianAI",
            "architect": "ArchitectAI",
            "technical": "TechnicalAI",
            "designer": "DesignerAI",
            "coder": "CoderAI"
        }

        agent_name = fallback_map.get(specialization, "CustodianAI")
        return self.agent_manager.get_agent_by_name(agent_name)

    def _build_phase_prompt(self, session: MVPSession, user_message: str, mode: str) -> str:
        """Build a context-aware prompt for the current phase."""
        current_phase = session.current_phase

        phase_prompts = {
            "Ideation": (
                f"You are helping refine a product idea in the Ideation phase.\n"
                f"Product concept: {session.product_idea}\n"
                f"User message: {user_message}\n"
                f"Mode: {mode.upper()}\n\n"
                f"Help the user clarify their product vision, target users, and core features."
            ),
            "Planning": (
                f"You are an architect planning the technical implementation.\n"
                f"Product: {session.product_idea}\n"
                f"User message: {user_message}\n"
                f"Mode: {mode.upper()}\n\n"
                f"Design the architecture, suggest tech stack, and outline the implementation plan."
            ),
            "Review": (
                f"You are reviewing the planned approach.\n"
                f"Product: {session.product_idea}\n"
                f"User message: {user_message}\n"
                f"Mode: {mode.upper()}\n\n"
                f"Validate the architecture, identify potential issues, and suggest improvements."
            ),
            "Polish": (
                f"You are improving the UX and design.\n"
                f"Product: {session.product_idea}\n"
                f"User message: {user_message}\n"
                f"Mode: {mode.upper()}\n\n"
                f"Suggest UX improvements, accessibility enhancements, and polish details."
            ),
            "Build": (
                f"You are generating production-ready code.\n"
                f"Product: {session.product_idea}\n"
                f"User message: {user_message}\n"
                f"Mode: {mode.upper()}\n\n"
                f"Write clean, well-documented code. Use MCP filesystem tools to create files."
            )
        }

        base_prompt = phase_prompts.get(current_phase.name, user_message)

        # Add conversation history context (last 6 messages), excluding the most recent user message which is already in the prompt
        recent_history = session.chat_history[-7:-1] # Get up to 6 previous messages
        if recent_history:
            history_context = "\n\nHere is the recent conversation history for context:\n"
            for msg in recent_history:
                role = msg.get("role", "unknown")
                # Use a clear role mapping
                display_role = "User" if role == "user" else "Assistant"
                content = msg.get("content", "")
                history_context += f"--- {display_role} ---\n{content}\n\n"
            
            # Insert history before the user's latest message for better context flow
            if "User message:" in base_prompt:
                base_prompt = base_prompt.replace("User message:", f"{history_context}\nUser message:")
            else:
                base_prompt += history_context

        if mode == "act":
            base_prompt += "\n\nACTION MODE: Proceed with implementation. Use available tools to create files and execute tasks."
        else:
            base_prompt += "\n\nPLAN MODE: Discuss and plan without executing changes."

        return base_prompt

    async def advance_phase(self, session_id: str) -> Dict[str, Any]:
        """Advance to the next phase."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.current_phase:
            session.current_phase.status = "completed"
            session.current_phase.progress = 100

        if session.current_phase_index < len(session.phases) - 1:
            session.current_phase_index += 1
            next_phase = session.current_phase
            next_phase.status = "active"
            session.add_log(f"Advanced to {next_phase.name} phase")

            return {
                "success": True,
                "new_phase": next_phase.name,
                "progress": session.overall_progress
            }

        return {"success": False, "message": "Already at final phase"}

    async def connect_github(self, session_id: str, github_token: str, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """Connect GitHub account, get user info, and optionally clone a repo."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not github_token:
            raise ValueError("GitHub token is required to connect.")

        session.github_token = github_token

        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"token {github_token}"}
                user_response = await client.get("https://api.github.com/user", headers=headers)
                user_response.raise_for_status()
                user_data = user_response.json()
                login = user_data.get("login")
                if not login:
                    raise ValueError("Could not retrieve GitHub username.")
                
                session.github_username = login
                session.github_connected = True

                # 2. If repo_name is provided, clone it
                if repo_name:
                    # Ensure the repo_name is in the format 'owner/repo'
                    if '/' not in repo_name:
                        full_repo_name = f"{login}/{repo_name}"
                    else:
                        full_repo_name = repo_name

                    if not session.workspace_path:
                        raise ValueError("Workspace path is not set for this session.")

                    session.github_repo_name = full_repo_name
                    clone_url = f"https://{login}:{github_token}@github.com/{full_repo_name}.git"
                    session.add_log(f"Cloning repository {full_repo_name} into workspace...")

                    # Clone into a temporary directory and move contents to avoid "directory not empty" error
                    temp_clone_dir = session.workspace_path.parent / f"{session.session_id}_temp_clone"
                    if temp_clone_dir.exists():
                        import shutil
                        shutil.rmtree(temp_clone_dir)
                    temp_clone_dir.mkdir()

                    process = await asyncio.create_subprocess_exec(
                        'git', 'clone', clone_url, '.', # Clone into current dir
                        cwd=str(temp_clone_dir),
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    if process.returncode != 0:
                        raise Exception(f"Git clone failed: {stderr.decode().strip()}")

                    # Move cloned files to the actual workspace
                    for item in temp_clone_dir.iterdir():
                        if item.name != '.git': # Exclude the .git directory itself from direct move
                            import shutil
                            shutil.move(str(item), str(session.workspace_path / item.name))
                    
                    # Move .git directory separately
                    git_dir = temp_clone_dir / ".git"
                    if git_dir.exists():
                        import shutil
                        shutil.move(str(git_dir), str(session.workspace_path / ".git"))

                    import shutil
                    shutil.rmtree(temp_clone_dir)

                    session.add_log(f"Successfully cloned repository {full_repo_name}.")

                session.add_log(f"GitHub account connected for user: {session.github_username}")

            return {"success": True, "message": f"GitHub connected as {session.github_username}", "github_username": session.github_username}
        except Exception as e:
            logger.error(f"Error connecting to GitHub: {e}")
            session.add_log(f"Failed to connect GitHub: {str(e)}", "error")
            session.github_connected = False # Ensure it's marked as not connected on failure
            return {"success": False, "message": str(e)}

    async def get_github_repos(self, session_id: str) -> List[Dict[str, Any]]:
        """Fetch list of repositories for the connected GitHub user."""
        session = self.get_session(session_id)
        if not session or not session.github_token:
            raise ValueError("GitHub not connected for this session.")

        repos = []
        page = 1
        try:
            async with httpx.AsyncClient() as client:
                while True:
                    headers = {"Authorization": f"token {session.github_token}"}
                    # Fetch repos user has explicit access to (includes private)
                    repos_url = f"https://api.github.com/user/repos?type=all&per_page=100&page={page}"
                    response = await client.get(repos_url, headers=headers)
                    response.raise_for_status()
                    current_page_repos = response.json()

                    if not current_page_repos:
                        break

                    repos.extend(current_page_repos)
                    page += 1
            
            session.add_log(f"Fetched {len(repos)} repositories from GitHub.")
            return repos
        except Exception as e:
            logger.error(f"Error fetching GitHub repos: {e}")
            session.add_log(f"Error fetching GitHub repos: {str(e)}", "error")
            return []

    async def write_file(self, session_id: str, path: str, content: str) -> bool:
        """Write a file to the session workspace."""
        session = self.get_session(session_id)
        if not session:
            return False

        if session.workspace_path:
            full_path = session.workspace_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            session.files[path] = content
            session.add_log(f"Created file: {path}")
            return True

        return False

    async def read_file(self, session_id: str, path: str) -> Optional[str]:
        """Read a file from the session workspace."""
        session = self.get_session(session_id)
        if not session or not session.workspace_path:
            return None

        full_path = session.workspace_path / path
        if full_path.exists():
            return full_path.read_text()
        return None

    def list_files(self, session_id: str) -> List[str]:
        """List all files in the session workspace."""
        session = self.get_session(session_id)
        if not session:
            return []
        return list(session.files.keys())

    def get_workspace_files_tree(self, session_id: str) -> List[Dict[str, Any]]:
        """Get file tree structure for the workspace."""
        session = self.get_session(session_id)
        if not session:
            return []

        tree = []
        for file_path in sorted(session.files.keys()):
            parts = file_path.split("/")
            current_level = tree

            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # File
                    current_level.append({
                        "type": "file",
                        "name": part,
                        "path": file_path
                    })
                else:
                    # Directory
                    existing = next((x for x in current_level if x.get("name") == part), None)
                    if not existing:
                        dir_node = {"type": "directory", "name": part, "children": []}
                        current_level.append(dir_node)
                        current_level = dir_node["children"]
                    else:
                        current_level = existing.get("children", [])

        return tree


# Global MVP Builder instance
_mvp_builder: Optional[MVPBuilder] = None


def get_mvp_builder(agent_manager: AgentManager) -> MVPBuilder:
    """Get or create the global MVP Builder instance."""
    global _mvp_builder
    if _mvp_builder is None:
        _mvp_builder = MVPBuilder(agent_manager)
    return _mvp_builder

    async def _run_git_command(self, cwd: Path, command: List[str]):
        """Helper to run a git command in the workspace."""
        logger.info(f"Running git command: {' '.join(command)} in {cwd}")
        process = await asyncio.create_subprocess_exec(
            'git', *command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error_message = stderr.decode().strip()
            logger.error(f"Git command failed: {error_message}")
            raise Exception(f"Git command failed: {error_message}")
        return stdout.decode().strip()

    async def publish_to_github(self, session_id: str, repo_name: Optional[str] = None, commit_message: str = "feat: Initial MVP build") -> Dict[str, Any]:
        """Publish the MVP to GitHub by creating a new repo or a pull request."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if not all([session.github_connected, session.github_username, session.github_token, session.workspace_path]):
            return {"success": False, "message": "GitHub not connected"}

        try:
            if session.github_repo_name: # Existing repo
                session.add_log("Starting publication to existing repository...")
                # 1. Create and switch to a new feature branch
                feature_branch = f"feature/mvp-build-{uuid.uuid4().hex[:6]}"
                await self._run_git_command(session.workspace_path, ['checkout', '-b', feature_branch])
                session.add_log(f"Created feature branch: {feature_branch}")

                # 2. Add all changes and commit
                await self._run_git_command(session.workspace_path, ['add', '.'])
                await self._run_git_command(session.workspace_path, ['commit', '-m', commit_message])
                session.add_log("Committed changes to feature branch.")

                # 3. Push the feature branch to origin
                await self._run_git_command(session.workspace_path, ['push', '-u', 'origin', feature_branch])
                session.add_log(f"Pushed feature branch '{feature_branch}' to remote.")

                # 4. Create a pull request using the GitHub API
                session.add_log("Creating pull request...")
                headers = {
                    "Authorization": f"token {session.github_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                pr_data = {
                    "title": commit_message,
                    "head": feature_branch,
                    "base": "main", # Or determine default branch
                    "body": "This pull request was automatically generated by the CustodianAI MVP Builder."
                }
                api_url = f"https://api.github.com/repos/{session.github_repo_name}/pulls"
                
                async with httpx.AsyncClient() as client:
                    pr_response = await client.post(api_url, headers=headers, json=pr_data)
                    
                    if pr_response.status_code not in [201, 422]: # 422 means PR already exists
                        pr_response.raise_for_status()

                    pr_json = pr_response.json()
                    if "html_url" in pr_json:
                        pr_url = pr_json["html_url"]
                        session.add_log(f"Successfully created pull request: {pr_url}")
                        return {"success": True, "message": "Pull request created successfully.", "repo_url": pr_url}
                    elif pr_response.status_code == 422:
                         # Handle case where PR already exists
                        session.add_log("Pull request may already exist for this branch.")
                        pr_url = f"https://github.com/{session.github_repo_name}/pulls"
                        return {"success": True, "message": "Pull request may already exist.", "repo_url": pr_url}
                    else:
                        raise Exception(f"Failed to get PR URL from response: {pr_json}")

            else: # New repo
                if not repo_name:
                    return {"success": False, "message": "New repository name is required."}
                
                # Implementation for creating a new repo would go here.
                # This requires 'repo' scope on the PAT.
                # 1. Call GitHub API to create repo.
                # 2. git init, add, commit
                # 3. git remote add origin ...
                # 4. git push -u origin main
                session.add_log("New repository creation is not yet fully implemented.")
                repo_url = f"https://github.com/{session.github_repo_name}"
                return {"success": False, "message": "New repository creation not implemented.", "repo_url": repo_url}

        except Exception as e:
            logger.error(f"Error publishing to GitHub: {e}")
            session.add_log(f"Error publishing to GitHub: {str(e)}", "error")
            return {"success": False, "message": str(e)}