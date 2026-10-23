import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "placement_agent.db"

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS profile (
          id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
          company TEXT DEFAULT '', location TEXT DEFAULT '',
          job_type TEXT DEFAULT 'Full-time', experience TEXT DEFAULT '',
          graduation_years TEXT DEFAULT '[]', required_skills TEXT DEFAULT '[]',
          description TEXT DEFAULT '', source_url TEXT DEFAULT '',
          source TEXT DEFAULT 'Manual', created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS applications (
          id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL UNIQUE,
          status TEXT NOT NULL DEFAULT 'Saved', notes TEXT DEFAULT '',
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL,
          details TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
          body TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'info',
          read INTEGER NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS review_requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL,
          action TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, reviewed_at TEXT,
          FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS discovered_sources (
          id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL UNIQUE,
          source_type TEXT NOT NULL DEFAULT 'manual', enabled INTEGER NOT NULL DEFAULT 1,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS naukri_discovery_config (
          id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0,
          interval_hours INTEGER NOT NULL DEFAULT 6,
          last_run TEXT DEFAULT '', last_status TEXT DEFAULT 'Not started',
          last_added INTEGER NOT NULL DEFAULT 0, last_error TEXT DEFAULT ''
        );
        INSERT OR IGNORE INTO naukri_discovery_config(id,enabled,interval_hours,last_status)
          VALUES(1,0,6,'Disabled');
        """)
        # Safe migrations for an existing database from the earlier MVP.
        columns = {r["name"] for r in db.execute("PRAGMA table_info(jobs)")}
        if "deadline" not in columns:
            db.execute("ALTER TABLE jobs ADD COLUMN deadline TEXT DEFAULT ''")
