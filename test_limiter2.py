import asyncio
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis
from fastapi_limiter.depends import RateLimiter
from fastapi import Depends

app = FastAPI()

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://255.255.255.255:6379", encoding="utf-8", decode_responses=True)
    try:
        await FastAPILimiter.init(redis)
    except Exception as e:
        print("Caught!")

@app.get("/", dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async def index():
    return {"msg": "Hello World"}
