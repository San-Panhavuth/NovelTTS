import logging

from fastapi import FastAPI

from app.config import settings
from app.deps.auth import get_supabase_url_debug
from app.logging_setup import configure_logging
from app.routers.books import router as books_router
from app.routers.generation import router as generation_router
from app.routers.health import router as health_router
from app.routers.voice_settings import router as voice_settings_router

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.include_router(health_router)
app.include_router(books_router)
app.include_router(voice_settings_router)
app.include_router(generation_router)


@app.on_event("startup")
async def log_startup_config() -> None:
	has_url, source = get_supabase_url_debug()
	logger.info("startup config: supabase_url_resolved=%s source=%s", has_url, source)
