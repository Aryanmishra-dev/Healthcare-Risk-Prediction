import json
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheService:
    """
    Abstract CacheService to decouple business logic from Redis.
    In development or tests without Redis, this falls back to executing
    the underlying function.
    """

    def __init__(self):
        self._redis = None
        self._enabled = False

    def init(self, redis_client=None):
        if redis_client:
            self._redis = redis_client
            self._enabled = True

    async def get(self, key: str) -> Optional[str]:
        if not self._enabled or not self._redis:
            return None
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None

    async def set(self, key: str, value: str, expire: int = 30) -> None:
        if not self._enabled or not self._redis:
            return
        try:
            await self._redis.set(key, value, ex=expire)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")

    async def delete(self, key: str) -> None:
        if not self._enabled or not self._redis:
            return
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")


cache_service = CacheService()


def cached(expire: int = 30):
    """
    Decorator to cache the result of an async function.
    The function must return a JSON-serializable dictionary or list.
    """

    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if not cache_service._enabled:
                return await func(*args, **kwargs)

            # Create a simple cache key from func name and args (excluding complex objects)
            # For admin endpoints, usually no args or simple kwargs are used.
            key_parts = [func.__name__]
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    key_parts.append(str(arg))
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float, bool)):
                    key_parts.append(f"{k}={v}")

            cache_key = ":".join(key_parts)

            cached_val = await cache_service.get(cache_key)
            if cached_val:
                try:
                    return json.loads(cached_val)
                except Exception:
                    pass

            result = await func(*args, **kwargs)

            try:
                await cache_service.set(cache_key, json.dumps(result), expire=expire)
            except Exception:
                pass

            return result

        return wrapper

    return decorator
