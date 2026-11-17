from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings
from backend.app.core.logging import logger

Base = declarative_base()

def sanitize_database_url(url: str) -> str:
    """
    Sanitizes database connection URLs:
    1. Normalizes postgres:// and postgresql:// to postgresql+psycopg2://
    2. Corrects unencoded special characters (e.g. '@' in passwords) that break RFC 3986 parsing
       and cause psycopg2 to misidentify parts of the password as the host.
    3. Enforces sslmode=require for Supabase / cloud database endpoints.
    4. Handles IPv6-only Supabase endpoints gracefully when DNS resolution drops.
    """
    if not url or "://" not in url:
        return url

    # Normalize driver prefix
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    scheme, remainder = url.split("://", 1)
    if "@" in remainder:
        # The host and database appear after the LAST '@'
        last_at_idx = remainder.rfind("@")
        auth_part = remainder[:last_at_idx]
        host_part = remainder[last_at_idx + 1:]

        if ":" in auth_part:
            from urllib.parse import quote, unquote
            user, pwd = auth_part.split(":", 1)
            # unquote first to prevent double-encoding, then quote with safe=""
            clean_user = quote(unquote(user), safe="")
            clean_pwd = quote(unquote(pwd), safe="")
            url = f"{scheme}://{clean_user}:{clean_pwd}@{host_part}"

    # Ensure SSL requirement on cloud databases (Supabase, Neon, etc.)
    if ("supabase.co" in url or "pooler.supabase.com" in url) and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    # For db.alkyogizjqdtbynzlsvd.supabase.co, attempt DNS resolution;
    # if it fails or running on Windows, bypass DNS lookup using direct IPv6 literal
    if "db.alkyogizjqdtbynzlsvd.supabase.co" in url:
        import platform
        use_literal = platform.system() == "Windows"
        if not use_literal:
            try:
                import socket
                socket.getaddrinfo("db.alkyogizjqdtbynzlsvd.supabase.co", 5432)
            except Exception:
                use_literal = True
        if use_literal:
            url = url.replace(
                "db.alkyogizjqdtbynzlsvd.supabase.co",
                "[2406:da14:1d4f:7401:d9d6:9c42:8e0c:763c]"
            )

    return url


# Connection pooling optimized for serverless / free-tier host (Render / Supabase pooler)
engine = None
SessionLocal = None

if settings.DATABASE_URL:
    try:
        db_url = sanitize_database_url(settings.DATABASE_URL)

        engine = create_engine(
            db_url,
            pool_pre_ping=True,  # Detect and discard dead connections automatically
            pool_recycle=300,    # Recycle connections after 5 minutes
            pool_size=5,         # Modest pool size for free tier
            max_overflow=10,     # Allow burst headroom
            connect_args={"connect_timeout": 10},
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
