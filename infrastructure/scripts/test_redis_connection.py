"""
QUIZVERSE Upstash Redis Diagnostic Script
Tests connectivity, latency, SET/GET operations, and TTL with your Upstash Redis database.
"""
import os
import sys
import time

def test_redis():
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url and len(sys.argv) > 1:
        redis_url = sys.argv[1]

    if not redis_url:
        # Try loading from backend/.env
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("REDIS_URL="):
                            redis_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass

    if not redis_url:
        print("=" * 60)
        print("QUIZVERSE Redis Diagnostic")
        print("=" * 60)
        print("[!] No REDIS_URL provided.")
        print("\nUsage:")
        print("  python infrastructure/scripts/test_redis_connection.py <REDIS_URL>")
        print("Or set REDIS_URL in backend/.env or your environment variables.")
        return False

    print("=" * 60)
    print("QUIZVERSE Upstash Redis Connectivity Diagnostic")
    print("=" * 60)
    # Mask password for display
    masked_url = redis_url
    if "@" in redis_url:
        try:
            prefix, host = redis_url.split("@", 1)
            scheme, credentials = prefix.split("://", 1)
            user = credentials.split(":")[0] if ":" in credentials else "default"
            masked_url = f"{scheme}://{user}:*****@{host}"
        except Exception:
            masked_url = "rediss://*****"
    print(f"Connecting to: {masked_url}")

    try:
        import redis
    except ImportError:
        print("[ERR] 'redis' package is not installed. Run: pip install redis")
        return False

    try:
        start = time.time()
        client = redis.from_url(redis_url, decode_responses=True, socket_timeout=5, ssl_cert_reqs=None)
        ping_ok = client.ping()
        elapsed_ms = round((time.time() - start) * 1000, 1)

        if ping_ok:
            print(f"[OK] PING succeeded ({elapsed_ms} ms) -> Redis is ONLINE & CONNECTED!")
        else:
            print(f"[ERR] PING returned False.")
            return False

        # Test write & read
        test_key = "quizverse:health_probe"
        test_val = f"test_{int(time.time())}"
        client.set(test_key, test_val, ex=60)
        retrieved = client.get(test_key)

        if retrieved == test_val:
            print(f"[OK] Read/Write test passed: Successfully wrote and retrieved test key.")
            client.delete(test_key)
        else:
            print(f"[ERR] Data mismatch: expected {test_val}, got {retrieved}")
            return False

        print("=" * 60)
        print("All Redis diagnostics PASSED! Your website is successfully connected.")
        return True

    except Exception as e:
        print(f"[ERR] Failed to connect to Redis: {e}")
        print("\nTroubleshooting Tips:")
        print("1. Ensure your URL starts with 'rediss://' (with double 's' for TLS encryption).")
        print("2. Verify that your password and endpoint hostname from Upstash are exact.")
        print("3. Check that your Upstash database state is 'Active' in console.upstash.com.")
        return False

if __name__ == "__main__":
    test_redis()
