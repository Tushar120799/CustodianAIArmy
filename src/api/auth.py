"""
Authentication module for Google OAuth and JWT token management.
Provides backend-only authentication without Vercel dependencies.
"""

import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import httpx
import jwt

from ..core.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# In-memory session store (use Redis in production)
sessions: Dict[str, Dict[str, Any]] = {}

class User(BaseModel):
    """User model for authenticated users."""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = None

class TokenResponse(BaseModel):
    """Response model for token generation."""
    access_token: str
    token_type: str = "bearer"
    user: User

def generate_jwt_token(user: User, expires_minutes: int = 20) -> str:
    """
    Generate a JWT token for the user.
    
    Args:
        user: User object containing user data
        expires_minutes: Token expiration time in minutes
        
    Returns:
        Encoded JWT token
    """
    payload = {
        "sub": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def create_user_session(user: User) -> str:
    """
    Create a new user session and return session ID.
    
    Args:
        user: User object
        
    Returns:
        Session ID
    """
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "user": user.dict(),
        "created_at": datetime.utcnow(),
        "last_activity": datetime.utcnow()
    }
    return session_id

def get_user_from_session(session_id: str) -> Optional[User]:
    """
    Retrieve user from session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        User object or None if session invalid/expired
    """
    if session_id not in sessions:
        return None
    
    session = sessions[session_id]
    session["last_activity"] = datetime.utcnow()
    
    # Check session expiration (20 minutes)
    if datetime.utcnow() - session["created_at"] > timedelta(minutes=20):
        del sessions[session_id]
        return None
    
    return User(**session["user"])

@router.get("/google")
async def google_login():
    """
    Initiate Google OAuth flow.
    Redirects user to Google's OAuth consent screen.
    """
    # Build Google OAuth URL
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    # Construct URL with query parameters
    from urllib.parse import urlencode
    auth_url = f"{google_auth_url}?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)

@router.get("/google/callback")
async def google_callback(request: Request, code: str = None, error: str = None):
    """
    Handle Google OAuth callback.
    
    Args:
        code: Authorization code from Google
        error: OAuth error if any
    """
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    try:
        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            # Get user info from Google
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch user info")
            
            userinfo = userinfo_response.json()
            
            # Create user object
            user = User(
                id=userinfo.get("sub"),
                email=userinfo.get("email"),
                name=userinfo.get("name"),
                picture=userinfo.get("picture"),
                created_at=datetime.utcnow()
            )
            
            # Create session
            session_id = create_user_session(user)
            
            # Generate JWT token
            jwt_token = generate_jwt_token(user)
            
            # Set session cookie
            response = RedirectResponse(url="/")
            response.set_cookie(
                key="session_id",
                value=session_id,
                max_age=20 * 60,  # 20 minutes
                httponly=True,
                samesite="lax",
                secure=False  # Set to True in production with HTTPS
            )
            
            # Also return JWT in response body for API clients
            response.set_cookie(
                key="access_token",
                value=jwt_token,
                max_age=20 * 60,
                httponly=True,
                samesite="lax",
                secure=False
            )
            
            return response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.get("/status")
async def auth_status(
    session_id: Optional[str] = Cookie(None),
    access_token: Optional[str] = Cookie(None)
) -> JSONResponse:
    """
    Check current authentication status.
    
    Args:
        session_id: Session cookie
        access_token: JWT token cookie
        
    Returns:
        JSON response with authentication status and user info if authenticated
    """
    user = None
    
    # Try to get user from session first
    if session_id:
        user = get_user_from_session(session_id)
    
    # If no session, try JWT token
    if not user and access_token:
        payload = decode_jwt_token(access_token)
        if payload:
            user = User(
                id=payload["sub"],
                email=payload["email"],
                name=payload["name"],
                picture=payload.get("picture"),
                created_at=datetime.utcnow()
            )
    
    if user:
        return JSONResponse(
            status_code=200,
            content={
                "authenticated": True,
                "user": user.dict()
            }
        )
    
    return JSONResponse(
        status_code=200,
        content={
            "authenticated": False,
            "user": None
        }
    )

@router.post("/logout")
async def logout(
    session_id: Optional[str] = Cookie(None),
    access_token: Optional[str] = Cookie(None)
) -> JSONResponse:
    """
    Logout user and clear session.
    
    Args:
        session_id: Session cookie
        access_token: JWT token cookie
    """
    # Clear session from memory
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response = JSONResponse(
        status_code=200,
        content={"message": "Logged out successfully"}
    )
    
    # Clear cookies
    response.delete_cookie(key="session_id")
    response.delete_cookie(key="access_token")
    
    return response

@router.get("/me")
async def get_current_user(
    session_id: Optional[str] = Cookie(None),
    access_token: Optional[str] = Cookie(None)
) -> JSONResponse:
    """
    Get current authenticated user.
    
    Args:
        session_id: Session cookie
        access_token: JWT token cookie
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user = None
    
    # Try to get user from session first
    if session_id:
        user = get_user_from_session(session_id)
    
    # If no session, try JWT token
    if not user and access_token:
        payload = decode_jwt_token(access_token)
        if payload:
            user = User(
                id=payload["sub"],
                email=payload["email"],
                name=payload["name"],
                picture=payload.get("picture"),
                created_at=datetime.utcnow()
            )
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return JSONResponse(
        status_code=200,
        content={"user": user.dict()}
    )