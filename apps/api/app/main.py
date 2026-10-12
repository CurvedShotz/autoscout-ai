from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.search import router as search_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import SearchRateLimitMiddleware

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend foundation for AutoScout AI",
    debug=settings.debug
    and settings.environment.strip().lower() not in {"prod", "production"},
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    SearchRateLimitMiddleware,
    max_requests=settings.search_rate_limit_requests,
    window_seconds=settings.search_rate_limit_window_seconds,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(search_router)
