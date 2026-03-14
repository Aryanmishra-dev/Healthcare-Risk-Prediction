import re
with open("app/main.py", "r") as f:
    code = f.read()

# 1. Add caching and rate limiting imports
imports = """from sqlalchemy.orm import Session
import json

from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter"""

code = code.replace("from sqlalchemy.orm import Session\nimport json", imports)

# 2. Modify lifespan
old_lifespan = """@asynccontextmanager
async def lifespan(app: FastAPI):
    \"\"\"Load ML models at startup.\"\"\"
    setup_logging()
    logger.info("application_startup", version="3.0.0")
    load_models()
    load_explainers()
    logger.info("models_loaded")
    yield
    logger.info("application_shutdown")"""

new_lifespan = """RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    \"\"\"Load ML models at startup.\"\"\"
    setup_logging()
    logger.info("application_startup", version="3.0.0")
    
    # Initialize Redis CACHE and LIMITER
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        redis_client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        FastAPICache.init(RedisBackend(redis_client), prefix="healthpredict-cache")
        await FastAPILimiter.init(redis_client)
        logger.info("redis_connected", url=redis_url)
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        
    load_models()
    load_explainers()
    logger.info("models_loaded")
    yield
    logger.info("application_shutdown")"""

code = code.replace(old_lifespan, new_lifespan)

# 3. Remove old rate limit logic
old_rate_vars = """# ── Rate limiting ──────────────────────────────────────────────────────────
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
_request_log: dict[str, list[float]] = defaultdict(list)
_MAX_TRACKED_IPS = 10_000"""

code = code.replace(old_rate_vars, "")

old_mw = re.compile(r'# ── Rate-limit middleware ──────────────────────────────────────────────────.*?return response\n\n\n', re.DOTALL)
code = old_mw.sub('', code)

# 4. Add RateLimiter and @cache to HTMX endpoints
code = code.replace('@app.post("/predict/diabetes")', '@app.post("/predict/diabetes", dependencies=[Depends(RateLimiter(times=RATE_LIMIT, seconds=60))])\n@cache(expire=3600)')
code = code.replace('@app.post("/predict/heart")', '@app.post("/predict/heart", dependencies=[Depends(RateLimiter(times=RATE_LIMIT, seconds=60))])\n@cache(expire=3600)')
code = code.replace('@app.post("/predict/lung")', '@app.post("/predict/lung", dependencies=[Depends(RateLimiter(times=RATE_LIMIT, seconds=60))])\n@cache(expire=3600)')

# Add RateLimiter and @cache to JSON endpoints
code = code.replace('@app.post("/api/v1/predict/diabetes"', '@app.post("/api/v1/predict/diabetes", dependencies=[Depends(RateLimiter(times=RATE_LIMIT, seconds=60))]\n')
code = code.replace('@app.post("/api/v1/predict/heart"', '@app.post("/api/v1/predict/heart", dependencies=[Depends(RateLimiter(times=RATE_LIMIT, seconds=60))]\n')
code = code.replace('@app.post("/api/v1/predict/lung"', '@app.post("/api/v1/predict/lung", dependencies=[Depends(RateLimiter(times=RATE_LIMIT, seconds=60))]\n')

with open("app/main.py", "w") as f:
    f.write(code)
