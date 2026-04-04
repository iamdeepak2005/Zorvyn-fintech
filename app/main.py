"""
FastAPI application entry point.
Registers middleware, exception handlers, routers, and handles initial database seeding.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.health import router as health_router
from app.api.v1.records import router as records_router
from app.core.config import get_settings
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limiter import limiter
from app.middleware.request_id import RequestIDMiddleware
from app.seed import seed_database
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()
seed_database()
tags_metadata = [
    {
        "name": "Dashboard Analytics",
        "description": "Endpoints to compute aggregated financial data.\n\n**Visibility Scope (`view_scope`):**\n- **Analysts & Admins:** By default fetch personal data (`view_scope=own`). Explicitly pass `?view_scope=all` to compute metrics across the entire application database.\n- **Viewers:** Strictly locked to viewing their own personal metrics.\n",
    },
    {
        "name": "Financial Records",
        "description": "Manage individual financial transactions.\n\n**Role Capabilities & Constraints:**\n- **Create/Update/Delete:** All users, regardless of role (including Admin), can **only** mutate records directly belonging to their own `user_id`.\n- **Read / List:** Paginated lists & exports support the `?view_scope=own|all` query argument for Analyst/Admin roles to query globally or personally. Viewers can only query their own data.",
    },
    {
        "name": "Admin - User Management",
        "description": "System-wide administration. Strictly reserved for `ADMIN` role only.",
    },
]

app = FastAPI(
    title="Zorvyn Fintech - Finance Dashboard Platform",
    description="Production-grade backend for financial record management, dashboard analytics, and RBAC.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
)

# Middleware stack (order matters)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = "; ".join(f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "data": None, "error": {"code": "VALIDATION_ERROR", "message": message}},
    )


# Routes — all under /api/v1
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(records_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    logger.info("Zorvyn Fintech API starting up...")
    try:
        from app.core.database import SessionLocal
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        db = SessionLocal()
        try:
            if not db.query(User).filter(User.role == UserRole.ADMIN).first():
                db.add(User(
                    name=settings.ADMIN_NAME, email=settings.ADMIN_EMAIL,
                    password_hash=hash_password(settings.ADMIN_PASSWORD), role=UserRole.ADMIN, is_active=True,
                ))
                db.commit()
                logger.info(f"Default admin user created: {settings.ADMIN_EMAIL}")
            else:
                logger.info("Admin user already exists, skipping seed.")
        except Exception as e:
            db.rollback()
            logger.warning(f"Could not seed admin user: {e}")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database not available for seeding: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Zorvyn Fintech API shutting down...")
