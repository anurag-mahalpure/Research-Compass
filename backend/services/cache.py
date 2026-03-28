from upstash_redis.asyncio import Redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_url = os.environ.get("UPSTASH_REDIS_REST_URL")
redis_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

redis = None
if redis_url and redis_token:
    redis = Redis(url=redis_url, token=redis_token)

async def cache_get(key: str) -> str | None:
    if not redis:
        return None
    try:
        return await redis.get(key)
    except Exception:
        return None  # Fail open — never block the pipeline on cache failure

async def cache_set(key: str, value: str, ttl: int = 86400) -> None:
    if not redis:
        return
    try:
        await redis.set(key, value, ex=ttl)
    except Exception:
        pass  # Fail silently — cache is an optimization, not a requirement
