import logging
import traceback

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.request_id import request_id_var

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            request_id = request_id_var.get("")
            logger.error(f"[{request_id}] Unhandled: {e}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False, "data": None,
                    "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."},
                },
                headers={"X-Request-ID": request_id},
            )
