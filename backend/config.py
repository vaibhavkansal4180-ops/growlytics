import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Load .env if present
load_dotenv(PROJECT_ROOT / ".env")

class Config:
    """Base application configuration for Growlytics."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or "growlytics-super-secret-key-retail-intelligence-2026-prod"
    ENV = os.environ.get("FLASK_ENV", "development").lower()
    DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")

    # Environment detection
    IS_VERCEL = (os.environ.get("VERCEL") or "") == "1"
    IS_PRODUCTION = (
        ENV == "production"
        or IS_VERCEL
        or (os.environ.get("ENV") or "").lower() == "production"
        or (os.environ.get("NODE_ENV") or "").lower() == "production"
    )

    # Session cookie configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0").lower() in ("1", "true", "yes")

    # CORS configuration
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # AI Copilot configuration
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

    # Database configuration
    # Check all common PostgreSQL environment variables (Neon, Supabase, Vercel Postgres, Render, Railway)
    candidates = [
        os.environ.get("DATABASE_URL"),
        os.environ.get("POSTGRES_URL"),
        os.environ.get("DATABASE_POSTGRES_URL"),
        os.environ.get("POSTGRES_PRISMA_URL"),
        os.environ.get("DATABASE2_DATABASE_URL"),
        os.environ.get("DATABASE2_POSTGRES_URL"),
        os.environ.get("DATABASE_URL_UNPOOLED"),
    ]

    db_url = ""
    for cand in candidates:
        if cand and isinstance(cand, str) and cand.strip():
            c_clean = cand.strip()
            if c_clean.startswith("postgres://") or c_clean.startswith("postgresql://") or c_clean.startswith("sqlite"):
                db_url = c_clean
                break

    if db_url:
        # Standardize postgres:// to postgresql+psycopg2:// for SQLAlchemy 2.x
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

        # Enforce SSL for managed cloud databases (like Neon / Supabase)
        if ("neon.tech" in db_url or "supabase.co" in db_url) and "sslmode" not in db_url:
            sep = "&" if "?" in db_url else "?"
            db_url = f"{db_url}{sep}sslmode=require"

        SQLALCHEMY_DATABASE_URI = db_url
    else:
        # Development / Serverless fallback to SQLite
        if IS_VERCEL:
            # On Vercel serverless, /var/task is read-only; writable SQLite must live in /tmp
            tmp_db = Path("/tmp") / "growlytics.db"
            bundled_db = BASE_DIR / "growlytics.db"
            if not tmp_db.exists() and bundled_db.exists():
                try:
                    import shutil
                    shutil.copyfile(bundled_db, tmp_db)
                except Exception:
                    pass
            local_db_path = tmp_db
        else:
            local_db_path = BASE_DIR / "growlytics.db"

        SQLALCHEMY_DATABASE_URI = f"sqlite:///{local_db_path.as_posix()}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    } if "sqlite" not in SQLALCHEMY_DATABASE_URI else {}


class TestingConfig(Config):
    """Configuration for automated test suite."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key-growlytics"
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
