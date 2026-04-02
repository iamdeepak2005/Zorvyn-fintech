import logging
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_service = AuditService(db)

    def create_user(self, data: UserCreate, admin_id: int) -> User:
        if self.user_repo.get_by_email(data.email):
            raise ValueError(f"User with email '{data.email}' already exists")

        user = User(
            name=data.name, email=data.email, password_hash=hash_password(data.password),
            role=data.role, is_active=data.is_active,
        )
        try:
            created_user = self.user_repo.create(user)
            self.audit_service.log_action(user_id=admin_id, action="CREATE", entity="user", entity_id=created_user.id)
            self.db.commit()
            logger.info(f"User created: id={created_user.id}, email={data.email}")
            return created_user
        except Exception:
            self.db.rollback()
            raise

    def get_users(self, page: int = 1, limit: int = 20) -> Tuple[List[User], int]:
        skip = (page - 1) * limit
        users = self.user_repo.get_all(skip=skip, limit=limit)
        total = self.user_repo.count()
        return users, total

    def get_user_by_id(self, user_id: int) -> User:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        return user

    def update_user(self, user_id: int, data: UserUpdate, admin_id: int) -> User:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] != user.email:
            if self.user_repo.get_by_email(update_data["email"]):
                raise ValueError(f"Email '{update_data['email']}' is already in use")

        if "password" in update_data:
            update_data["password_hash"] = hash_password(update_data.pop("password"))

        try:
            updated_user = self.user_repo.update(user, update_data)
            self.audit_service.log_action(user_id=admin_id, action="UPDATE", entity="user", entity_id=user_id)
            self.db.commit()
            logger.info(f"User updated: id={user_id}")
            return updated_user
        except Exception:
            self.db.rollback()
            raise

    def delete_user(self, user_id: int, admin_id: int) -> None:
        if user_id == admin_id:
            raise ValueError("Cannot delete your own account")

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        try:
            self.audit_service.log_action(user_id=admin_id, action="DELETE", entity="user", entity_id=user_id)
            self.user_repo.delete(user)
            self.db.commit()
            logger.info(f"User deleted: id={user_id}")
        except Exception:
            self.db.rollback()
            raise
