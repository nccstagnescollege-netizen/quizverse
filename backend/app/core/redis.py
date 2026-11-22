"""
QUIZVERSE Redis Connection Manager
Handles serverless Redis connectivity (Upstash / Redis Cloud) with SSL/TLS support,
connection pooling, and graceful fallback when Redis is unconfigured or unreachable.
"""
from typing import Optional, Any
import json
from backend.app.core.config import settings
from backend.app.core.logging import logger

_redis_client: Optional[Any] = None
_redis_initialized: bool = False


def get_redis_client():
    """
    Returns a singleton Redis client instance.
    Gracefully returns None if REDIS_URL is not configured or if connection fails.
    """
    global _redis_client, _redis_initialized

    if _redis_initialized and _redis_client is not None:
        return _redis_client

    if not settings.REDIS_URL:
        _redis_initialized = True
        return None

    try:
        import redis

        url = settings.REDIS_URL.strip().strip('"').strip("'")
        # Ensure rediss:// for Upstash / cloud endpoints requiring TLS
        if "upstash.io" in url and url.startswith("redis://"):
            url = url.replace("redis://", "rediss://", 1)

        client = redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=3,
            socket_connect_timeout=3,
            ssl_cert_reqs=None,
            retry_on_timeout=True,
        )
        # Test connection with quick ping
        client.ping()
        _redis_client = client
        _redis_initialized = True
        logger.info("Successfully connected to Redis cache.")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis connection attempt failed: {e}. Falling back to direct database operations.")
        _redis_client = None
        _redis_initialized = True
        return None


def check_redis_connection() -> bool:
    """Verifies live Redis connectivity with a ping."""
    try:
        client = get_redis_client()
        if client:
            return bool(client.ping())
        return False
    except Exception:
        return False


def cache_get(key: str) -> Optional[Any]:
    """Retrieve and deserialize a JSON-cached value from Redis."""
    try:
        client = get_redis_client()
        if not client:
            return None
        val = client.get(key)
        if val:
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        return None
    except Exception as e:
        logger.debug(f"Redis cache_get failed for key '{key}': {e}")
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """Serialize and store a key-value pair in Redis with expiration."""
    try:
        client = get_redis_client()
        if not client:
            return False
        if isinstance(value, (dict, list)):
            val_str = json.dumps(value)
        else:
            val_str = str(value)
        client.set(key, val_str, ex=ttl_seconds)
        return True
    except Exception as e:
        logger.debug(f"Redis cache_set failed for key '{key}': {e}")
        return False


def cache_delete(key: str) -> bool:
    """Delete a key from Redis."""
    try:
        client = get_redis_client()
        if not client:
            return False
        client.delete(key)
        return True
    except Exception as e:
        logger.debug(f"Redis cache_delete failed for key '{key}': {e}")
        return False
