"""Error handling middleware."""

import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from api.schemas.campaign_bot import ErrorResponse


logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling and logging errors."""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Re-raise HTTP exceptions to be handled by FastAPI
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)

            # Return user-friendly error response
            error_response = ErrorResponse(
                error="internal_server_error",
                message="An unexpected error occurred. Please try again later.",
                details={"type": type(e).__name__} if logger.isEnabledFor(logging.DEBUG) else None,
            )

            return JSONResponse(
                status_code=500,
                content=error_response.model_dump(),
            )


def add_error_handling_middleware(app: FastAPI) -> None:
    """Add error handling middleware to FastAPI app."""
    app.add_middleware(ErrorHandlingMiddleware)
