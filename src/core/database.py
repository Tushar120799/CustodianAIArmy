import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Iterator
import os

# Use /tmp for serverless environments (Vercel, AWS Lambda, etc.)
# Vercel only allows writing to /tmp directory
DB_PATH = os.getenv('DATABASE_PATH', '/tmp/chat_history.db')

def init_db():
    try:
        # Ensure the directory exists
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        
        # Use WAL mode for better concurrency (optional for serverless)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            # WAL mode may not be supported in all environments
            pass
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                title TEXT NOT NULL,
                start_time TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                messages TEXT NOT NULL
            )
        ''')

        # User progress tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                course_id TEXT NOT NULL,
                lang TEXT NOT NULL DEFAULT 'en',
                section_index INTEGER NOT NULL DEFAULT 0,
                completed_sections TEXT NOT NULL DEFAULT '[]',
                last_updated TEXT NOT NULL,
                UNIQUE(user_email, course_id, lang)
            )
        ''')

        # User profile/preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                user_email TEXT PRIMARY KEY,
                current_course TEXT,
                current_lang TEXT DEFAULT 'en',
                preferences TEXT NOT NULL DEFAULT '{}',
                last_updated TEXT NOT NULL
            )
        ''')

        # User API keys table (per-user custom API keys)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_api_keys (
                user_email TEXT PRIMARY KEY,
                gemini_api_key TEXT,
                anthropic_api_key TEXT,
                nim_api_key TEXT,
                last_updated TEXT NOT NULL
            )
        ''')

        # User plans and rate limiting table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_plans (
                user_email TEXT PRIMARY KEY,
                plan TEXT NOT NULL DEFAULT 'guest',
                requests_today INTEGER NOT NULL DEFAULT 0,
                last_reset_date TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()
        print(f"Database initialized at {DB_PATH}")
        return True
    except sqlite3.OperationalError as e:
        print(f"Database initialization error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected database initialization error: {e}")
        return False

def get_db() -> sqlite3.Connection:
    """
    Get a database connection.
    For FastAPI dependency injection.
    """
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def get_chats_for_user(email: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_email, title, start_time, last_updated, messages
        FROM chat_sessions
        WHERE user_email = ?
        ORDER BY last_updated DESC
    ''', (email,))
    rows = cursor.fetchall()
    conn.close()
    
    chats = []
    for row in rows:
        chats.append({
            "id": row[0],
            "user_email": row[1],
            "title": row[2],
            "start_time": row[3],
            "last_updated": row[4],
            "messages": json.loads(row[5])
        })
    return chats

def save_chat_session(chat_data: Dict[str, Any]) -> str:
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    
    chat_id = chat_data.get("id")
    if not chat_id:
        chat_id = str(uuid.uuid4())
        
    messages_str = json.dumps(chat_data.get("messages", []))
    now = datetime.utcnow().isoformat()
    start_time = chat_data.get("start_time")
    if not start_time:
        start_time = now
    
    cursor.execute('''
        INSERT INTO chat_sessions (id, user_email, title, start_time, last_updated, messages)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            last_updated=excluded.last_updated,
            messages=excluded.messages
    ''', (
        chat_id, 
        chat_data.get("user_email", "guest"), 
        chat_data.get("title", "New Chat"), 
        start_time, 
        now, 
        messages_str
    ))
    
    conn.commit()
    conn.close()
    return chat_id

def get_user_api_keys(user_email: str) -> Dict[str, Any]:
    """Get user's custom API keys (returns masked values for display)"""
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT gemini_api_key, anthropic_api_key, nim_api_key, last_updated
        FROM user_api_keys
        WHERE user_email = ?
    ''', (user_email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "gemini_api_key": None,
            "anthropic_api_key": None,
            "nim_api_key": None,
            "has_gemini": False,
            "has_anthropic": False,
            "has_nim": False,
            "last_updated": None
        }

    def mask_key(key: Optional[str]) -> Optional[str]:
        if not key:
            return None
        if len(key) <= 8:
            return "****"
        return key[:4] + "****" + key[-4:]

    return {
        "gemini_api_key": mask_key(row[0]),
        "anthropic_api_key": mask_key(row[1]),
        "nim_api_key": mask_key(row[2]),
        "has_gemini": bool(row[0]),
        "has_anthropic": bool(row[1]),
        "has_nim": bool(row[2]),
        "last_updated": row[3]
    }


def get_user_api_keys_raw(user_email: str) -> Dict[str, Optional[str]]:
    """Get user's actual (unmasked) API keys for internal use only"""
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT gemini_api_key, anthropic_api_key, nim_api_key
        FROM user_api_keys
        WHERE user_email = ?
    ''', (user_email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"gemini_api_key": None, "anthropic_api_key": None, "nim_api_key": None}

    return {
        "gemini_api_key": row[0],
        "anthropic_api_key": row[1],
        "nim_api_key": row[2]
    }


def save_user_api_keys(user_email: str, keys: Dict[str, Optional[str]]) -> bool:
    """Save or update user's API keys. Pass None to keep existing value, empty string to clear."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        # Get existing keys first
        cursor.execute('''
            SELECT gemini_api_key, anthropic_api_key, nim_api_key
            FROM user_api_keys WHERE user_email = ?
        ''', (user_email,))
        existing = cursor.fetchone()

        if existing:
            # Update only provided keys (None means "don't change")
            new_gemini = keys.get("gemini_api_key", None)
            new_anthropic = keys.get("anthropic_api_key", None)
            new_nim = keys.get("nim_api_key", None)

            final_gemini = new_gemini if new_gemini is not None else existing[0]
            final_anthropic = new_anthropic if new_anthropic is not None else existing[1]
            final_nim = new_nim if new_nim is not None else existing[2]

            # Empty string means "clear the key"
            final_gemini = None if final_gemini == "" else final_gemini
            final_anthropic = None if final_anthropic == "" else final_anthropic
            final_nim = None if final_nim == "" else final_nim

            cursor.execute('''
                UPDATE user_api_keys
                SET gemini_api_key = ?, anthropic_api_key = ?, nim_api_key = ?, last_updated = ?
                WHERE user_email = ?
            ''', (final_gemini, final_anthropic, final_nim, now, user_email))
        else:
            gemini = keys.get("gemini_api_key") or None
            anthropic = keys.get("anthropic_api_key") or None
            nim = keys.get("nim_api_key") or None
            cursor.execute('''
                INSERT INTO user_api_keys (user_email, gemini_api_key, anthropic_api_key, nim_api_key, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_email, gemini, anthropic, nim, now))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving API keys: {e}")
        return False


def delete_user_api_key(user_email: str, provider: str) -> bool:
    """Delete a specific provider's API key for a user"""
    valid_providers = {"gemini": "gemini_api_key", "anthropic": "anthropic_api_key", "nim": "nim_api_key"}
    if provider not in valid_providers:
        return False

    column = valid_providers[provider]
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute(f'''
            UPDATE user_api_keys
            SET {column} = NULL, last_updated = ?
            WHERE user_email = ?
        ''', (now, user_email))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting API key: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PLAN / RATE LIMITING FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

PLAN_LIMITS = {
    "guest": {"daily_limit": 3,  "providers": ["nim"]},
    "free":  {"daily_limit": 20, "providers": ["gemini", "anthropic", "nim"]},
    "pro":   {"daily_limit": 50, "providers": ["gemini", "anthropic", "nim"]},
}


def get_user_plan(user_email: str) -> Dict[str, Any]:
    """Get plan info for a user. Creates a guest record if none exists."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT plan, requests_today, last_reset_date FROM user_plans WHERE user_email = ?",
        (user_email,)
    )
    row = cursor.fetchone()

    if not row:
        # New user — insert as guest
        cursor.execute(
            "INSERT INTO user_plans (user_email, plan, requests_today, last_reset_date) VALUES (?, 'guest', 0, ?)",
            (user_email, today)
        )
        conn.commit()
        plan, requests_today, last_reset_date = "guest", 0, today
    else:
        plan, requests_today, last_reset_date = row[0], row[1], row[2]
        # Reset counter if it's a new day
        if last_reset_date != today:
            cursor.execute(
                "UPDATE user_plans SET requests_today = 0, last_reset_date = ? WHERE user_email = ?",
                (today, user_email)
            )
            conn.commit()
            requests_today = 0

    conn.close()

    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["guest"])
    return {
        "plan": plan,
        "requests_today": requests_today,
        "daily_limit": limits["daily_limit"],
        "remaining": max(0, limits["daily_limit"] - requests_today),
        "allowed_providers": limits["providers"],
    }


def check_and_increment_rate_limit(user_email: str) -> Dict[str, Any]:
    """
    Check if the user is within their daily limit and increment the counter.
    Returns dict with: allowed (bool), plan, requests_today, daily_limit, remaining.
    """
    info = get_user_plan(user_email)
    if info["requests_today"] >= info["daily_limit"]:
        info["allowed"] = False
        return info

    # Increment
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE user_plans SET requests_today = requests_today + 1, last_reset_date = ? WHERE user_email = ?",
        (today, user_email)
    )
    conn.commit()
    conn.close()

    info["requests_today"] += 1
    info["remaining"] = max(0, info["daily_limit"] - info["requests_today"])
    info["allowed"] = True
    return info


def upgrade_user_plan(user_email: str, new_plan: str) -> bool:
    """Upgrade or change a user's plan."""
    if new_plan not in PLAN_LIMITS:
        return False
    today = datetime.utcnow().strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO user_plans (user_email, plan, requests_today, last_reset_date)
               VALUES (?, ?, 0, ?)
               ON CONFLICT(user_email) DO UPDATE SET plan = excluded.plan""",
            (user_email, new_plan, today)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error upgrading plan: {e}")
        return False


# Initialize the database when this module is loaded
try:
    init_db()
except Exception as e:
    print(f"Failed to initialize database: {e}")
