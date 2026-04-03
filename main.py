"""
Custodian AI Army - Main Application Entry Point
A futuristic AI agent orchestration system inspired by Abacus.ai
"""

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from src.api.routes import router as api_router
from src.core.config import settings
from src.core.logging_config import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Custodian AI Army",
    description="A futuristic AI agent orchestration system with multiple specialized agents",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the main UI
@app.get("/")
async def read_root():
    """Serve the main dashboard"""
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )