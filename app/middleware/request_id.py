import uuid
import contextvars
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)
        logger.info(f"[{request_id}] {request.method} {request.url.path} - started")

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(f"[{request_id}] {request.method} {request.url.path} - status={response.status_code}")
        return response
