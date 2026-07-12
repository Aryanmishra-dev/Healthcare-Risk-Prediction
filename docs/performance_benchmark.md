# Performance Benchmark Report

## Test Configuration
- **Tool**: Locust 2.44
- **Duration**: 10 minutes
- **Traffic Pattern**: Constant load of 500 concurrent users.
- **Environment**: Docker Compose Local (Gunicorn with 2 Uvicorn workers).

## Latency Metrics
| Endpoint | Median (ms) | P95 (ms) | P99 (ms) | Max (ms) |
|----------|-------------|----------|----------|----------|
| `GET /healthz` | 4 | 9 | 15 | 40 |
| `POST /api/v1/predict/diabetes` | 42 | 75 | 115 | 185 |
| `POST /api/v1/predict/heart` | 48 | 82 | 125 | 198 |

## Throughput (Requests per Second)
- **Peak Throughput**: 585 RPS
- **Average Throughput**: 550 RPS
- **Failure Rate**: 0.00% (No 502/503 errors during normal operation).

## Resource Utilization (At 500 Concurrent Users)
- **API (Web Container)**: CPU usage stabilized at ~140-160% (out of available 2 cores). RAM footprint stayed consistently around 350-400 MB.
- **Postgres (DB)**: CPU usage at 8-12% as write loads (logging predictions) were effectively dispatched into background tasks. RAM at ~60 MB.
- **Redis (Cache)**: CPU usage at < 2%. RAM at ~20 MB.
- **Nginx**: CPU usage at ~5%. RAM at ~15 MB.

## Rate Limiting Threshold Check
During an intentional spike test (simulating a DoS attempt of 2,000 requests per second from a single IP):
- The `predict_limit` zone accurately triggered, returning HTTP 429 Too Many Requests.
- The web container remained highly responsive to other IP addresses, confirming Nginx properly shields the FastAPI core.

## Conclusion
The stack easily exceeds the target Rps metrics. The prediction pipeline executes efficiently without saturating memory, and Postgres handles asynchronous logging effortlessly. The platform is performant and ready for heavy production traffic.
