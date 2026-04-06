import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

def get_chats_for_user(email: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    chat_id = chat_data.get("id")
    if not chat_id:
        chat_id = str(uuid.uuid4())
        
    messages_str = json.dumps(chat_data.get("messages", []))
    now = datetime.utcnow().isoformat()
    start_time = chat_data.get("start_time", now)
    
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

# Initialize the database when this module is loaded
init_db()
