"""
Configuration settings for Custodian AI Army
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional, Dict


class Settings(BaseSettings):
    """Application settings"""

    # Application Configuration
    APP_HOST: str = "localhost"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # ─────────────────────────────────────────────────────────────────────────
    # Google Gemini API Configuration
    # ─────────────────────────────────────────────────────────────────────────
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MODEL: str = "gemini-2.5-flash"  # Default / fallback model

    # ─────────────────────────────────────────────────────────────────────────
    # Anthropic Claude API Configuration
    # ─────────────────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-5"  # Default / fallback model

    # ─────────────────────────────────────────────────────────────────────────
    # Groq API Configuration (OpenAI-compatible, completely free tier)
    # Get your FREE key at: https://console.groq.com (no credit card required)
    # ─────────────────────────────────────────────────────────────────────────
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  # Default / fallback model

    # ─────────────────────────────────────────────────────────────────────────
    # NVIDIA NIM API Configuration (OpenAI-compatible, free tier available)
    # Get your free key at: https://build.nvidia.com
    # ─────────────────────────────────────────────────────────────────────────
    NIM_API_KEY: Optional[str] = None
    NIM_MODEL: str = "meta/llama-3.3-70b-instruct"  # Default / fallback model

    # ─────────────────────────────────────────────────────────────────────────
    # MCP (Model Context Protocol) Configuration
    # ─────────────────────────────────────────────────────────────────────────
    MCP_ENABLED: bool = True  # Enable/disable MCP tool calling globally

    # ─────────────────────────────────────────────────────────────────────────
    # Database Configuration
    # ─────────────────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./custodian_ai.db"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_SECRET: str = "your-jwt-secret-change-in-production"

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # GitHub OAuth Configuration
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/github/callback"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# ─────────────────────────────────────────────────────────────────────────────
# Per-Agent Model Assignments
# Maps: provider → agent_name → model_id
# These override the global GROQ_MODEL / CLAUDE_MODEL / GEMINI_MODEL / NIM_MODEL
# ─────────────────────────────────────────────────────────────────────────────

AGENT_MODELS: Dict[str, Dict[str, str]] = {

    # ── Groq ──────────────────────────────────────────────────────────────────
    # Groq hosts multiple free models. We assign based on capability needs:
    # - llama-4-scout: massive 10M context, best for orchestration & architecture
    # - llama-3.3-70b-versatile: best reasoning + tool use
    # - kimi-k2-instruct: 60 RPM, excellent for agentic/coding tasks
    # - qwen3-32b: 60 RPM, 500K TPD, good for creative/data tasks
    # - llama-3.1-8b-instant: ultra-fast for simple tasks
    "groq": {
        "CustodianAI":    "meta-llama/llama-4-scout-17b-16e-instruct",
        "ResearchAI":     "llama-3.3-70b-versatile",
        "FactCheckerAI":  "llama-3.3-70b-versatile",
        "TrendAnalystAI": "moonshotai/kimi-k2-instruct",
        "AnalystAI":      "llama-3.3-70b-versatile",
        "DataAnalystAI":  "qwen/qwen3-32b",
        "MarketAnalystAI":"moonshotai/kimi-k2-instruct",
        "TechnicalAI":    "llama-3.3-70b-versatile",
        "CoderAI":        "moonshotai/kimi-k2-instruct",
        "ArchitectAI":    "meta-llama/llama-4-scout-17b-16e-instruct",
        "CreativeAI":     "qwen/qwen3-32b",
        "WriterAI":       "qwen/qwen3-32b",
        "DesignerAI":     "llama-3.1-8b-instant",
    },

    # ── Anthropic Claude ──────────────────────────────────────────────────────
    # Claude models by capability tier:
    # - claude-opus-4-5: most capable, for complex orchestration & research
    # - claude-sonnet-4-5: balanced performance, for most agents
    # - claude-haiku-3-5: fastest/cheapest, for simple tasks
    "anthropic": {
        "CustodianAI":    "claude-opus-4-5",
        "ResearchAI":     "claude-opus-4-5",
        "FactCheckerAI":  "claude-sonnet-4-5",
        "TrendAnalystAI": "claude-sonnet-4-5",
        "AnalystAI":      "claude-sonnet-4-5",
        "DataAnalystAI":  "claude-sonnet-4-5",
        "MarketAnalystAI":"claude-sonnet-4-5",
        "TechnicalAI":    "claude-opus-4-5",
        "CoderAI":        "claude-sonnet-4-5",
        "ArchitectAI":    "claude-opus-4-5",
        "CreativeAI":     "claude-sonnet-4-5",
        "WriterAI":       "claude-sonnet-4-5",
        "DesignerAI":     "claude-haiku-3-5",
    },

    # ── Google Gemini ─────────────────────────────────────────────────────────
    # Gemini models by capability tier:
    # - gemini-2.5-pro: most capable, for complex reasoning & orchestration
    # - gemini-2.5-flash: fast + capable, for most agents
    # - gemini-2.0-flash: fastest, for creative/simple tasks
    "gemini": {
        "CustodianAI":    "gemini-2.5-pro",
        "ResearchAI":     "gemini-2.5-pro",
        "FactCheckerAI":  "gemini-2.5-flash",
        "TrendAnalystAI": "gemini-2.5-flash",
        "AnalystAI":      "gemini-2.5-flash",
        "DataAnalystAI":  "gemini-2.5-flash",
        "MarketAnalystAI":"gemini-2.5-flash",
        "TechnicalAI":    "gemini-2.5-pro",
        "CoderAI":        "gemini-2.5-flash",
        "ArchitectAI":    "gemini-2.5-pro",
        "CreativeAI":     "gemini-2.0-flash",
        "WriterAI":       "gemini-2.0-flash",
        "DesignerAI":     "gemini-2.0-flash",
    },

    # ── NVIDIA NIM ────────────────────────────────────────────────────────────
    # NIM models by specialization:
    # - meta/llama-3.3-70b-instruct: general purpose, strong reasoning
    # - qwen/qwen2.5-coder-32b-instruct: specialized for coding tasks
    # - mistralai/mistral-large-2-instruct: strong for creative/writing
    # - meta/llama-3.1-8b-instruct: fast, for simple tasks
    "nim": {
        "CustodianAI":    "meta/llama-3.3-70b-instruct",
        "ResearchAI":     "meta/llama-3.3-70b-instruct",
        "FactCheckerAI":  "meta/llama-3.3-70b-instruct",
        "TrendAnalystAI": "meta/llama-3.3-70b-instruct",
        "AnalystAI":      "meta/llama-3.3-70b-instruct",
        "DataAnalystAI":  "meta/llama-3.3-70b-instruct",
        "MarketAnalystAI":"meta/llama-3.3-70b-instruct",
        "TechnicalAI":    "meta/llama-3.3-70b-instruct",
        "CoderAI":        "qwen/qwen2.5-coder-32b-instruct",
        "ArchitectAI":    "meta/llama-3.3-70b-instruct",
        "CreativeAI":     "mistralai/mistral-large-2-instruct",
        "WriterAI":       "mistralai/mistral-large-2-instruct",
        "DesignerAI":     "meta/llama-3.1-8b-instruct",
    },
}


def get_model_for_agent(provider: str, agent_name: str) -> Optional[str]:
    """
    Get the recommended model for a specific agent and provider.

    Falls back to the global provider model if no specific assignment exists.

    Args:
        provider: One of 'groq', 'anthropic', 'gemini', 'nim'
        agent_name: The agent's name (e.g., 'CustodianAI', 'CoderAI')

    Returns:
        Model identifier string, or None to use the provider default
    """
    provider_models = AGENT_MODELS.get(provider, {})
    return provider_models.get(agent_name)
