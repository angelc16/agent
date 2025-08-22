"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.middlewares.cors import add_cors_middleware
from api.middlewares.error_handler import add_error_handling_middleware
from api.routes.campaign_bot import router as campaign_bot_router
from api.schemas.campaign_bot import HealthResponse
from app.core.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""

    logger.info("Starting Lukia Campaign Bot API")

    # Initialize Telegram bot
    telegram_service = None
    try:
        from app.modules.telegram_module.application.telegram_service import (
            TelegramBotService,
        )

        telegram_service = TelegramBotService()

        if await telegram_service.initialize():
            logger.info("Telegram bot initialized successfully")
            # Start polling in background
            await telegram_service.start_polling()
        else:
            logger.warning("Telegram bot not initialized - token may be missing")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}")

    yield

    # # Cleanup
    if telegram_service:
        try:
            await telegram_service.stop()
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")

    logger.info("Shutting down Lukia Campaign Bot API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Lukia Campaign Bot API",
        description="AI-powered campaign creation bot with LangGraph integration",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add middlewares
    add_cors_middleware(app)
    add_error_handling_middleware(app)

    # Add routes
    app.include_router(campaign_bot_router)

    # Health check endpoint
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(status="healthy")

    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info",
    )
