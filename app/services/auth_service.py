import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_service = AuditService(db)

    def authenticate(self, email: str, password: str) -> dict:
        user = self.user_repo.get_by_email(email)

        if user is None:
            logger.warning(f"Login attempt with non-existent email: {email}")
            raise ValueError("Invalid email or password")

        if not user.is_active:
            logger.warning(f"Login attempt by inactive user: {email}")
            raise ValueError("Account is deactivated. Contact an administrator.")

        if not verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for: {email}")
            raise ValueError("Invalid email or password")

        token = create_access_token(data={"user_id": user.id, "role": user.role.value})

        self.audit_service.log_action(user_id=user.id, action="LOGIN", entity="user", entity_id=user.id)
        self.db.commit()

        logger.info(f"Successful login: user_id={user.id}")

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user.id,
            "role": user.role.value,
        }
