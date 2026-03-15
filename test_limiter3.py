import asyncio
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis
from fastapi_limiter.depends import RateLimiter
from fastapi import Depends, Request

app = FastAPI()

class OptionalRateLimiter:
    def __init__(self, times, seconds):
        self.limiter = RateLimiter(times=times, seconds=seconds)
    async def __call__(self, request: Request):
        if not FastAPILimiter.redis: return
        try:
            await self.limiter(request)
        except Exception:
            pass

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://255.255.255.255:6379", encoding="utf-8", decode_responses=True)
    try:
        await FastAPILimiter.init(redis)
    except Exception as e:
        print("Caught!")

@app.get("/", dependencies=[Depends(OptionalRateLimiter(times=2, seconds=5))])
async def index():
    return {"msg": "Hello World"}
