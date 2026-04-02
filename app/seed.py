import logging

from app.core.config import get_settings
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.financial_record import FinancialRecord  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.idempotency_key import IdempotencyKey  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


def seed_database():
    """
    Initializes the database schema models and injects the first physical Super Admin identity.
    
    Business Logic Flow:
    1. Programmatically mounts `Base.metadata.create_all` matching the Python DB Models to the PostgreSQL engine.
    2. Searches the `users` table for the target `ADMIN_EMAIL` referenced in your `.env` configuration.
    3. If none exists, inherently constructs the first tier-1 access user via bcrypt encryption so 
       new deployments instantly own a functional interface authentication flow.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == settings.ADMIN_EMAIL).first():
            logger.info(f"Admin user '{settings.ADMIN_EMAIL}' already exists.")
            return

        db.add(User(
            name=settings.ADMIN_NAME, email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD), role=UserRole.ADMIN, is_active=True,
        ))
        db.commit()
        logger.info(f"Default admin user created: {settings.ADMIN_EMAIL}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
