# 1. Use FastAPI for the Backend

Date: 2026-03-15

## Status
Accepted

## Context
We need a robust, high-performance web framework to serve both our UI views and our machine learning predictions (which can be computationally or memory-bound). The framework needs to support asynchronous request handling easily and provide good developer ergonomics (type hinting, auto-docs).

## Decision
We will use **FastAPI** as our core web framework.

## Consequences
- **Positive:** We get built-in request validation (Pydantic), automatic OpenAPI documentation, and excellent async support. It integrates cleanly with Uvicorn for ASGI serving.
- **Negative:** Slightly steeper learning curve regarding async/await semantics for Python developers more familiar with synchronous frameworks like Flask or Django.
- **Mitigation:** We will maintain clear patterns in `app/main.py` and `app/database.py` and rely on dependency injection for db sessions and API keys.
