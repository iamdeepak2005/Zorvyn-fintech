from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired authentication token"},
        )

    user_id: int = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token payload is missing user_id"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_INACTIVE", "message": "Your account has been deactivated. Contact an administrator."},
        )

    return user


def require_roles(*roles: UserRole):
    """Dependency factory: enforces role-based access before business logic."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Requires one of: {', '.join(r.value for r in roles)}",
                },
            )
        return current_user
    return role_checker


def get_admin_user(current_user: User = Depends(require_roles(UserRole.ADMIN))) -> User:
    return current_user


def get_analyst_or_admin(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
) -> User:
    return current_user

def get_viewer_or_admin_or_analyst(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VIEWER, UserRole.ANALYST)),
) -> User:
    return current_user

def get_any_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
