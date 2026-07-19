import asyncio

from fastapi import Depends, FastAPI, Request, Response
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis import asyncio as aioredis

app = FastAPI()


class OptionalRateLimiter:
    def __init__(self, times, seconds):
        self.limiter = RateLimiter(times=times, seconds=seconds)

    async def __call__(self, request: Request, response: Response):
        if not FastAPILimiter.redis:
            return
        try:
            await self.limiter(request, response)
        except Exception:
            pass


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(
        "redis://255.255.255.255:6379", encoding="utf-8", decode_responses=True
    )
    try:
        await FastAPILimiter.init(redis)
    except Exception as e:
        print("Caught!")


@app.get("/", dependencies=[Depends(OptionalRateLimiter(times=2, seconds=5))])
async def index():
    return {"msg": "Hello World"}
