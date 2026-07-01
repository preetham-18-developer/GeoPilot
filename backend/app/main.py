from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import (
    projects,
    analysis_results,
    analysis_questions,
    analysis_keywords,
    analysis_geo,
    analysis_analytics,
    analysis_reliability,
    analysis_execution,
    analysis_optimization,
    reports,
    blogs
)
from supabase import create_client, ClientOptions
from app.core.supabase import _client_ctx, _global_client
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# HTTP middleware to intercept Authorization header and set request-scoped Supabase client
@app.middleware("http")
async def supabase_client_middleware(request: Request, call_next):
    authorization = request.headers.get("authorization")
    client = _global_client
    
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            if token.startswith("mock-"):
                # Mock/demo session: use service_role key to bypass RLS entirely.
                # App-level .eq("user_id", user_id) checks in each router remain
                # the real access-control gate for mock requests.
                mock_user_id = token.replace("mock-", "")
                service_key = settings.SUPABASE_SERVICE_ROLE_KEY
                if not service_key:
                    logger.warning(
                        "[AUTH] SUPABASE_SERVICE_ROLE_KEY is not set — "
                        "mock requests will fall back to anon key and may hit RLS errors. "
                        "Add SUPABASE_SERVICE_ROLE_KEY to backend/.env from the Supabase dashboard."
                    )
                    service_key = settings.SUPABASE_KEY
                    logger.debug("[AUTH] mock-token request → using KEY TYPE: anon (fallback, service_role missing)")
                else:
                    logger.debug("[AUTH] mock-token request → using KEY TYPE: service_role (RLS bypassed)")
                client = create_client(
                    settings.SUPABASE_URL,
                    service_key,
                    options=ClientOptions(
                        headers={"X-Mock-User": mock_user_id}
                    )
                )
            else:
                # Real Supabase JWT: use anon key + forward the JWT so RLS
                # auth.uid() = user_id policy applies correctly.
                logger.debug("[AUTH] real JWT request → using KEY TYPE: anon + forwarded JWT (RLS active)")
                client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY,
                    options=ClientOptions(
                        headers={"Authorization": f"Bearer {token}"}
                    )
                )
                
    ctx_token = _client_ctx.set(client)
    try:
        response = await call_next(request)
        return response
    finally:
        _client_ctx.reset(ctx_token)


# Setup CORS middleware
from app.core.middleware import PerformanceMetricsMiddleware
app.add_middleware(PerformanceMetricsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://geo-pilot-nine.vercel.app",
    ],
    allow_origin_regex=r"https://geo-pilot[\w\-]*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(analysis_results.router, prefix=settings.API_V1_STR)
app.include_router(analysis_questions.router, prefix=settings.API_V1_STR)
app.include_router(analysis_keywords.router, prefix=settings.API_V1_STR)
app.include_router(analysis_geo.router, prefix=settings.API_V1_STR)
app.include_router(analysis_analytics.router, prefix=settings.API_V1_STR)
app.include_router(analysis_reliability.router, prefix=settings.API_V1_STR)
app.include_router(analysis_execution.router, prefix=settings.API_V1_STR)
app.include_router(analysis_optimization.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(blogs.router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}
