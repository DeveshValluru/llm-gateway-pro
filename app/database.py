import sqlite3
import json
from config import DB_PATH

SCHEMA_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    rate_limit INTEGER DEFAULT 10,
    allowed_models TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

SCHEMA_LOGS = """
CREATE TABLE IF NOT EXISTS request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    latency_ms REAL,
    status_code INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    curr = conn.cursor()
    curr.execute(SCHEMA_USERS)
    curr.execute(SCHEMA_LOGS)
    conn.commit()
    conn.close()


def get_user_by_api_key(api_key):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"], 
        "rate_limit": row["rate_limit"], 
        "allowed_models": json.loads(row["allowed_models"])
    }

def log_request(user_id, model, prompt_tokens, completion_tokens, latency_ms,status_code):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO request_logs (user_id, model, prompt_tokens, completion_tokens, latency_ms, status_code) VALUES (?, ?, ?, ?, ?, ?)",
    (user_id, model, prompt_tokens, completion_tokens, latency_ms, status_code)
    )
    conn.commit()
    conn.close()

def count_recent_requests(user_id,seconds):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as cnt FROM request_logs WHERE user_id = ? AND created_at >= datetime('now', ?)",
        (user_id, f"-{seconds} seconds")
    )
    row = cur.fetchone()
    conn.close()
    return row['cnt']


def seed_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM users"
    )
    count = cur.fetchone()[0]
    if count > 0:
        conn.close()
        return
    cur.execute(
        "INSERT INTO users (username, api_key, rate_limit, allowed_models) VALUES (?, ?, ?, ?)",
        ("alice", "sk-alice-dev-key", 20, json.dumps(["pirate", "genz", "formal"]))
    )
    cur.execute(
        "INSERT INTO users (username, api_key, rate_limit, allowed_models) VALUES (?, ?, ?, ?)",
        ("bob", "sk-bob-dev-key", 5, json.dumps(["pirate"]))
    )
    # Dedicated benchmark user with a very high rate limit so scripts/bench.py
    # measures the serving stack, not the rate limiter.
    cur.execute(
        "INSERT INTO users (username, api_key, rate_limit, allowed_models) VALUES (?, ?, ?, ?)",
        ("bench", "sk-bench-key", 100000, json.dumps(["pirate", "genz", "formal"]))
    )
    conn.commit()
    conn.close()
    print("seeded 3 users")



if __name__ == "__main__":
    init_db()
    seed_users()