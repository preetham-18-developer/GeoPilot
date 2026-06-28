# 🚀 GeoPilot / AIVOP Production Deployment Guide

This document maps out deployment configurations, container setups, database audits, and operations structures for staging and production hosting.

---

## 1. Containerized Infrastructure (`docker-compose.yml`)

For self-hosted or virtual private server (VPS) architectures, GeoPilot compiles backend components inside **Docker**:

```yaml
version: '3.8'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    depends_on:
      - redis
      - qdrant
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  worker:
    build: ./backend
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    depends_on:
      - redis
      - qdrant
    command: celery -A app.core.celery_app worker --loglevel=info

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  qdrant:
    image: qdrant/qdrant:v1.7.4
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

---

## 2. Production Checklist

### 2.1. Security Configurations
*   **Supabase PostgreSQL RLS**: Enable Row-Level Security (RLS) on all user-interactive tables. Verify that child table access is gated via owner verification checks matching `auth.uid()`.
*   **Database Hygiene**: Drop the 6 unused legacy tables (`colleges`, `course_fees`, `placement_stats`, `admission_cutoffs`, `reviews`, `shortlist_sessions`) from the database project to eliminate security vulnerabilities from disabled RLS policies.
*   **API CORS Restriction**: Restrict `allow_origins=["*"]` inside `backend/app/main.py` to target only the specific client domains in production.

### 2.2. Environment Variables
Ensure all production variables are populated in your hosting provider (e.g. Vercel, Render, AWS ECS):
*   `GEMINI_API_KEY`: Production Gemini service key.
*   `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`: Service accounts.
*   `NEXT_PUBLIC_API_URL`: Targets `https://api.yourdomain.com/api/v1`.

---

## 3. Health Monitoring & Observability

*   **FastAPI Health Endpoint**: `GET /health` returns JSON `{"status": "ok"}` when the API is running. Configure load balancer target group checks to hit this path.
*   **Redis Caching Health**: Track Cache Hit/Miss metrics.
*   **Celery Worker Tracking**: Use Celery inspect pings to verify active worker clusters:
    ```bash
    celery -A app.core.celery_app status
    ```
