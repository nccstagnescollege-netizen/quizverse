from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings
from backend.app.core.logging import logger

Base = declarative_base()

# Connection pooling optimized for serverless / free-tier host (Render / Supabase pooler)
engine = None
SessionLocal = None

if settings.DATABASE_URL:
    try:
        # Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        engine = create_engine(
            db_url,
            pool_pre_ping=True,  # Detect and discard dead connections automatically
            pool_recycle=300,    # Recycle connections after 5 minutes
            pool_size=5,         # Modest pool size for free tier
            max_overflow=10,     # Allow burst headroom
            echo=False,
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("SQLAlchemy database engine initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize SQLAlchemy database engine: {e}")
        engine = None
        SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that yields a database session and safely closes it upon request completion.
    """
    if SessionLocal is None:
        raise RuntimeError("Database connection is not configured. Set DATABASE_URL.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Diagnostic helper to test real database connectivity.
    """
    if engine is None:
        return False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return False
