import sqlite3
from datetime import datetime
from pathlib import Path

DB_FILE = Path(__file__).parent / "clinora.db"

VALID_USER_ROLES = ("patient", "provider")
VALID_SEVERITY_LEVELS = ("mild", "moderate", "severe")
VALID_AGENT_TYPES = ("interviewer", "diagnostician", "safety")


def get_db():
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso():
    return datetime.utcnow().isoformat()


def severity_to_level(value):
    if value is None:
        return "moderate"

    if isinstance(value, str):
        v = value.strip().lower()
        if v in VALID_SEVERITY_LEVELS:
            return v
        try:
            value = int(v)
        except ValueError:
            return "moderate"

    try:
        n = int(value)
    except (TypeError, ValueError):
        return "moderate"

    if n <= 3:
        return "mild"
    if n <= 6:
        return "moderate"
    return "severe"


def severity_to_score(level):
    lv = severity_to_level(level)
    if lv == "mild":
        return 2
    if lv == "severe":
        return 9
    return 5


def _column_exists(conn, table_name, column_name):
    rows = conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()
    return any(row[1] == column_name for row in rows)


def init_db():
    with get_db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                email       TEXT UNIQUE NOT NULL,
                password    TEXT NOT NULL,
                full_name   TEXT,
                role        TEXT NOT NULL DEFAULT 'patient' CHECK(role IN ('patient','provider')),
                birth_date  TEXT,
                age         INTEGER,
                sex         TEXT,
                height_cm   REAL,
                weight_kg   REAL,
                bmi         REAL,
                allergies   TEXT,
                chronic_conditions TEXT,
                phone       TEXT,
                data_authorization_accepted INTEGER NOT NULL DEFAULT 0,
                license_number TEXT,
                hospital    TEXT,
                department  TEXT,
                specialty   TEXT,
                years_experience INTEGER,
                title       TEXT,
                qualification_proof TEXT,
                verification_status TEXT NOT NULL DEFAULT 'active',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS patients (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                name        TEXT NOT NULL,
                dob         TEXT,
                gender      TEXT,
                blood_type  TEXT,
                allergies   TEXT,
                medications TEXT,
                conditions  TEXT,
                notes       TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                patient_id TEXT,
                symptoms TEXT NOT NULL,
                messages TEXT NOT NULL DEFAULT '[]',
                history TEXT NOT NULL DEFAULT '[]',
                turns INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'interviewing',
                severity_level TEXT NOT NULL DEFAULT 'moderate' CHECK(severity_level IN ('mild','moderate','severe')),
                diagnosis TEXT,
                review TEXT,
                refs TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE SET NULL
            )"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT,
                role TEXT NOT NULL CHECK(role IN ('user','agent','system')),
                agent_type TEXT CHECK(agent_type IN ('interviewer','diagnostician','safety')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at)")

        c.execute(
            """CREATE TABLE IF NOT EXISTS uploads (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL CHECK(file_type IN ('pdf','txt','image','audio','video')),
                file_path TEXT NOT NULL,
                extracted_text TEXT NOT NULL DEFAULT '',
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_uploads_session_uploaded ON uploads(session_id, uploaded_at)")

        # Migration: recreate uploads table if it lacks 'audio'/'video' in the file_type constraint.
        row = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='uploads'").fetchone()
        if row and ("'audio'" not in row["sql"] or "'video'" not in row["sql"]):
            c.execute("ALTER TABLE uploads RENAME TO uploads_old")
            c.execute(
                """CREATE TABLE uploads (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL CHECK(file_type IN ('pdf','txt','image','audio','video')),
                    file_path TEXT NOT NULL,
                    extracted_text TEXT NOT NULL DEFAULT '',
                    uploaded_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )"""
            )
            c.execute("INSERT INTO uploads SELECT * FROM uploads_old")
            c.execute("DROP TABLE uploads_old")
            c.execute("CREATE INDEX IF NOT EXISTS idx_uploads_session_uploaded ON uploads(session_id, uploaded_at)")

        c.execute(
            """CREATE TABLE IF NOT EXISTS eval_runs (
                id TEXT PRIMARY KEY,
                question_id TEXT NOT NULL,
                single_answer TEXT,
                single_reasoning TEXT,
                multi_answer TEXT,
                multi_reasoning TEXT,
                multi_pipeline TEXT,
                correct_answer TEXT,
                category TEXT,
                single_correct INTEGER,
                multi_correct INTEGER,
                created_at TEXT NOT NULL
            )"""
        )

        # Lightweight migration for existing prototype DBs.
        if not _column_exists(c, "sessions", "severity_level"):
            c.execute("ALTER TABLE sessions ADD COLUMN severity_level TEXT NOT NULL DEFAULT 'moderate'")
        if not _column_exists(c, "sessions", "cot"):
            c.execute("ALTER TABLE sessions ADD COLUMN cot TEXT")
        if not _column_exists(c, "sessions", "consent_to_provider_review"):
            c.execute("ALTER TABLE sessions ADD COLUMN consent_to_provider_review INTEGER NOT NULL DEFAULT 0")
        if not _column_exists(c, "sessions", "provider_verdict"):
            c.execute("ALTER TABLE sessions ADD COLUMN provider_verdict TEXT")
        if not _column_exists(c, "sessions", "provider_note"):
            c.execute("ALTER TABLE sessions ADD COLUMN provider_note TEXT")
        if not _column_exists(c, "sessions", "mistral_peer_review"):
            c.execute("ALTER TABLE sessions ADD COLUMN mistral_peer_review TEXT")
        if not _column_exists(c, "eval_runs", "mistral_verdict"):
            c.execute("ALTER TABLE eval_runs ADD COLUMN mistral_verdict TEXT")
        if not _column_exists(c, "eval_runs", "mistral_reasoning"):
            c.execute("ALTER TABLE eval_runs ADD COLUMN mistral_reasoning TEXT")
        if not _column_exists(c, "eval_runs", "mistral_correct"):
            c.execute("ALTER TABLE eval_runs ADD COLUMN mistral_correct INTEGER")

        user_migrations = {
            "birth_date": "TEXT",
            "age": "INTEGER",
            "sex": "TEXT",
            "height_cm": "REAL",
            "weight_kg": "REAL",
            "bmi": "REAL",
            "allergies": "TEXT",
            "chronic_conditions": "TEXT",
            "phone": "TEXT",
            "data_authorization_accepted": "INTEGER NOT NULL DEFAULT 0",
            "license_number": "TEXT",
            "hospital": "TEXT",
            "department": "TEXT",
            "specialty": "TEXT",
            "years_experience": "INTEGER",
            "title": "TEXT",
            "qualification_proof": "TEXT",
            "verification_status": "TEXT NOT NULL DEFAULT 'active'",
        }
        for column_name, column_type in user_migrations.items():
            if not _column_exists(c, "users", column_name):
                c.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")

        c.commit()
