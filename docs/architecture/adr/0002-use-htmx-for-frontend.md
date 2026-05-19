# 2. Use HTMX for the Frontend

Date: 2026-03-15

## Status
Accepted

## Context
The project requires a dynamic, single-page-like application feel for the predictive forms (Diabetes, Heart Disease, Lung Cancer). Creating a full React/Vue/Angular frontend introduces significant overhead, dual state management, and requires separate build pipelines.

## Decision
We will use **HTMX** combined with TailwindCSS and Jinja2 templates.

## Consequences
- **Positive:** Massive reduction in JavaScript boilerplate. State remains on the server. The forms can be progressively enhanced, and the UI responds smoothly without full page reloads.
- **Negative:** Tighter coupling of frontend UI and backend routes. FastAPI must return HTML fragments instead of pure JSON for some endpoints.
- **Mitigation:** We logically separate API schema boundaries (`/predict/...`) returning HTML partials in standard template directories, keeping `backend/app/main.py` highly organized.
