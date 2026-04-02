import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log_action(self, user_id: int, action: str, entity: str, entity_id: Optional[int] = None) -> AuditLog:
        audit_log = AuditLog(user_id=user_id, action=action, entity=entity, entity_id=entity_id)
        self.repo.create(audit_log)
        logger.info(f"Audit: user_id={user_id} action={action} entity={entity} entity_id={entity_id}")
        return audit_log
