import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "bot.db")

def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
        CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        note_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0,1))
    
    );
    
    CREATE UNIQUE INDEX IF NOT EXISTS ux_models_single_active ON models(active) WHERE active=1;
    
    INSERT OR IGNORE INTO models(id, key, label, active) VALUES
        (1, 'deepseek/deepseek-chat-v3.1:free', 'DeepSeek V3.1 (free)', 1),
        (2, 'deepseek/deepseek-r1:free', 'DeepSeek R1 (free)', 0),
        (3, 'mistralai/mistral-small-24b-instruct-2501:free', 'Mistral Small 24b (free)', 0),
        (4, 'meta-llama/llama-3.1-8b-instruct:free', 'Llama 3.1 8B (free)', 0),
        (5, 'google/gemini-2.0-flash-exp:free', 'Gemini 2.0 Flash (free)', 0),
        (6, 'qwen/qwen3-coder:free', 'Qwen3 Coder (free)', 0),
        (7, 'minimax/minimax-m2:free', 'Minimax M2 (free)', 0),
        (8, 'microsoft/mai-ds-r1:free', 'MAI DS R1 (free)', 0),
        (9, 'alibaba/tongyi-deepresearch-30b-a3b:free', 'Tongyi DeepResearch 30B (free)', 0),
        (10, 'openai/gpt-oss-20b:free', 'GPT-OSS 20B (free)', 0),
        (11, 'z-ai/glm-4.5-air:free', 'GLM 4.5 Air (free)', 0),
        (12, 'nvidia/nemotron-nano-12b-v2-vl:free', 'Nemotron Nano 12B (free)', 0),
        (13, 'agentica-org/deepcoder-14b-preview:free', 'DeepCoder 14B (free)', 0),
        (14, 'moonshotai/kimi-k2:free', 'Kimi K2 (free)', 0);
    
    
    """
    with _connect() as conn:
        conn.executescript(schema)


def list_models() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT id,key,label,active FROM models ORDER BY id").fetchall()
        return [{"id":r["id"], "key":r["key"], "label":r["label"], "active":bool(r["active"])} for r in rows]


def get_active_model() -> dict:
    with _connect() as conn:
        row = conn.execute("SELECT id,key,label FROM models WHERE active=1").fetchone()
        if row:
            return {"id":row["id"], "key":row["key"], "label":row["label"], "active":True}
        row = conn.execute("SELECT id,key,label FROM models ORDER BY id LIMIT 1").fetchone()
        if not row:
            raise RuntimeError("В реестре моделей нет записей")
        conn.execute("UPDATE models SET active=CASE WHEN id=? THEN 1 ELSE 0 END", (row["id"],))
        return {"id":row["id"], "key":row["key"], "label":row["label"], "active":True}


def set_active_model(model_id: int) -> dict:
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute("SELECT 1 FROM models WHERE id=?", (model_id,)).fetchone()
        if not exists:
            conn.rollback()
            raise ValueError("Неизвестный ID модели")
        conn.execute("UPDATE models SET active=CASE WHEN id=? THEN 1 ELSE 0 END", (model_id,))
        conn.commit()
        return get_active_model()




def add_note(user_id: int, text: str) -> int:
    with _connect() as conn:
        cur_count = conn.execute(
            "SELECT COUNT(id) FROM notes WHERE user_id = ?",
            (user_id,)
        )
        count = cur_count.fetchone()[0]

        if count >= 50:
            return 0

        cur = conn.execute(
            "INSERT INTO notes(user_id, text) VALUES (?, ?)",
            (user_id, text)
        )
        note_id = cur.lastrowid

        conn.execute(
            "INSERT INTO stats(user_id, action, note_id) VALUES (?, 'create', ?)",
            (user_id, note_id)
        )

    return note_id


def list_notes(user_id: int, limit: int = 10):
    with _connect() as conn:
        cur = conn.execute(
            """SELECT id, text, created_at
            FROM notes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?""",
            (user_id, limit)
        )
    return cur.fetchall()


def update_note(user_id: int, note_id: int, text: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            """UPDATE notes
            SET text = ?
            WHERE user_id = ? AND id = ?""",
            (text, user_id, note_id)
        )
        if cur.rowcount > 0:
            conn.execute(
                "INSERT INTO stats(user_id, action, note_id) VALUES (?, 'edit', ?)",
                (user_id, note_id)
            )
            return True
    return False


def delete_note(user_id: int, note_id: int) -> bool:
    with _connect() as conn:
        cur_check = conn.execute("SELECT id FROM notes WHERE user_id = ? AND id = ?", (user_id, note_id))
        if cur_check.fetchone():
            conn.execute(
                "INSERT INTO stats(user_id, action, note_id) VALUES (?, 'delete', ?)",
                (user_id, note_id)
            )
            cur_del = conn.execute(
                "DELETE FROM notes WHERE user_id = ? AND id = ?",
                (user_id, note_id)
            )
            return cur_del.rowcount > 0
    return False


def find_notes(user_id: int, query_text: str, limit: int = 10):
    with _connect() as conn:
        cur = conn.execute(
            """SELECT id, text
            FROM notes
            WHERE user_id = ?
            AND text LIKE '%' || ? || '%'
            ORDER BY id DESC
            LIMIT ?""",
            (user_id, query_text, limit)
        )
    return cur.fetchall()


def list_all_notes(user_id: int):

    with _connect() as conn:
        cur = conn.execute(
            """SELECT id, text, created_at
            FROM notes
            WHERE user_id = ?
            ORDER BY id ASC""",
            (user_id,)
        )
    return cur.fetchall()


def get_combined_stats(user_id: int):

    stats = {
        'total_notes': 0,
        'total_chars': 0,
        'total_created': 0,
        'total_edited': 0,
        'total_deleted': 0,
        'weekly_created': 0,
        'weekly_edited': 0,
        'weekly_deleted': 0,
    }
    with _connect() as conn:
        cur_notes = conn.execute(
            "SELECT COUNT(id) as count, SUM(LENGTH(text)) as chars FROM notes WHERE user_id = ?",
            (user_id,)
        )
        notes_row = cur_notes.fetchone()
        if notes_row and notes_row['count'] > 0:
            stats['total_notes'] = notes_row['count']
            stats['total_chars'] = notes_row['chars']

        cur_log = conn.execute(
            """SELECT
                action,
                COUNT(id) as total_count,
                SUM(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END) as weekly_count
            FROM
                stats
            WHERE
                user_id = ?
            GROUP BY
                action""",
            (user_id,)
        )
        for row in cur_log.fetchall():
            action = row['action']

            stats[f"total_{action}"] = row['total_count']
            stats[f"weekly_{action}"] = row['weekly_count']

    return stats