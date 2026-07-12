import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from backend.app.services.cache_service import CacheService, cached, cache_service

@pytest.mark.anyio
async def test_cache_service_disabled():
    cs = CacheService()
    assert await cs.get("key") is None
    await cs.set("key", "val")
    await cs.delete("key")

@pytest.mark.anyio
async def test_cache_service_enabled():
    cs = CacheService()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "val"
    cs.init(mock_redis)
    
    assert await cs.get("key") == "val"
    mock_redis.get.assert_awaited_once_with("key")
    
    await cs.set("key", "val2", expire=10)
    mock_redis.set.assert_awaited_once_with("key", "val2", ex=10)
    
    await cs.delete("key")
    mock_redis.delete.assert_awaited_once_with("key")

@pytest.mark.anyio
async def test_cache_service_exceptions():
    cs = CacheService()
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("error")
    mock_redis.set.side_effect = Exception("error")
    mock_redis.delete.side_effect = Exception("error")
    cs.init(mock_redis)
    
    assert await cs.get("key") is None
    await cs.set("key", "val")
    await cs.delete("key")

@pytest.mark.anyio
async def test_cached_decorator_disabled():
    cache_service._enabled = False
    
    @cached(expire=10)
    async def my_func():
        return {"a": 1}
        
    assert await my_func() == {"a": 1}

@pytest.mark.anyio
async def test_cached_decorator_miss_and_hit():
    mock_redis = AsyncMock()
    # First get returns None (miss), second returns cached json
    mock_redis.get.side_effect = [None, '{"a": 2}']
    cache_service.init(mock_redis)
    
    call_count = 0
    @cached(expire=10)
    async def my_func(arg1, kwarg1=None):
        nonlocal call_count
        call_count += 1
        return {"a": 1}
        
    # Miss
    assert await my_func(123, kwarg1="test") == {"a": 1}
    assert call_count == 1
    mock_redis.set.assert_awaited_once()
    
    # Hit
    assert await my_func(123, kwarg1="test") == {"a": 2}
    assert call_count == 1 # didn't increment
    
    cache_service._enabled = False

@pytest.mark.anyio
async def test_cached_decorator_invalid_json():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "invalid json"
    cache_service.init(mock_redis)
    
    @cached(expire=10)
    async def my_func():
        return {"a": 1}
        
    # Should fall back to calling function
    assert await my_func() == {"a": 1}
    
    cache_service._enabled = False
