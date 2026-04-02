"""
Business logic layer for Financial Records.
Coordinates database access, ensures actions are idempotent, manages audit logging,
and applies role-based access rules (e.g. IDOR protection).
"""
import json
import logging
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session

from app.models.financial_record import FinancialRecord, RecordType
from app.models.idempotency_key import IdempotencyKey
from app.models.user import User, UserRole
from app.repositories.record_repository import RecordRepository
from app.schemas.record import RecordCreate, RecordFilterParams, RecordResponse, RecordUpdate
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class RecordService:
    def __init__(self, db: Session):
        self.db = db
        self.record_repo = RecordRepository(db)
        self.audit_service = AuditService(db)

    def create_record(self, data: RecordCreate, user: User, idempotency_key: Optional[str] = None) -> Tuple[dict, bool]:
        """
        Creates a new financial record securely.
        
        Business Logic Flow:
        1. IDEMPOTENCY: Safely searches `idempotency_keys` for duplicate key submissions. 
           If a duplicate request is matched, it immediately shorts the process and returns the original payload instead of double-crediting an account. (Returns bool=True flag)
        2. DATABASE COMMIt: Inserts a new row with strictly formatted fields.
        3. AUDIT LOGGING: Irrevocably traces the action as "CREATE" explicitly tying the user back to the record.
        4. CACHING: Saves the 201 response body locally so identical requests within an hour are instantly satisfied mapping to the idempotency system.
        """
        # Idempotency check
        if idempotency_key:
            existing_key = (
                self.db.query(IdempotencyKey)
                .filter(IdempotencyKey.key == idempotency_key, IdempotencyKey.user_id == user.id)
                .first()
            )
            if existing_key and existing_key.response_body:
                logger.info(f"Idempotency hit: key={idempotency_key}")
                return json.loads(existing_key.response_body), True

        record = FinancialRecord(
            user_id=user.id, amount=data.amount, type=data.type,
            category=data.category, date=data.date, notes=data.notes,
        )

        try:
            created_record = self.record_repo.create(record)
            self.audit_service.log_action(user_id=user.id, action="CREATE", entity="financial_record", entity_id=created_record.id)

            if idempotency_key:
                response_data = RecordResponse.model_validate(created_record).model_dump(mode="json")
                self.db.add(IdempotencyKey(
                    key=idempotency_key, user_id=user.id,
                    response_body=json.dumps(response_data), status_code=201,
                ))

            self.db.commit()
            logger.info(f"Record created: id={created_record.id}, user_id={user.id}")
            return RecordResponse.model_validate(created_record).model_dump(mode="json"), False
        except Exception:
            self.db.rollback()
            raise

    def get_records(self, filters: RecordFilterParams, user: User) -> Tuple[List[dict], int]:
        user_id = None if user.role == UserRole.ADMIN else user.id
        include_deleted = filters.include_deleted and user.role == UserRole.ADMIN

        records, total = self.record_repo.get_filtered(
            user_id=user_id, record_type=filters.type, category=filters.category,
            start_date=filters.start_date, end_date=filters.end_date, search=filters.search,
            include_deleted=include_deleted, sort_by=filters.sort_by or "date",
            order=filters.order or "desc", page=filters.page, limit=filters.limit,
        )
        return [RecordResponse.model_validate(r).model_dump(mode="json") for r in records], total

    def get_record_by_id(self, record_id: int, user: User) -> dict:
        """
        Fetches an individual explicit record by ID.
        
        Business Logic Flow:
        - Prevents IDOR (Insecure Direct Object Reference) structurally by evaluating if the requested 
          asset conceptually "belongs" to the user, except when the user carries the global `ADMIN` badge.
        """
        record = self.record_repo.get_by_id(record_id)
        if not record:
            raise ValueError(f"Record with id {record_id} not found")

        # IDOR prevention
        if user.role != UserRole.ADMIN and record.user_id != user.id:
            raise PermissionError("You do not have access to this record")

        return RecordResponse.model_validate(record).model_dump(mode="json")

    def update_record(self, record_id: int, data: RecordUpdate, user: User) -> dict:
        record = self.record_repo.get_by_id(record_id)
        if not record:
            raise ValueError(f"Record with id {record_id} not found")

        # Ensure user can only update their own records unless they are ADMIN
        if user.role != UserRole.ADMIN and record.user_id != user.id:
            raise PermissionError("You do not have permission to update this record")

        try:
            updated_record = self.record_repo.update(record, data.model_dump(exclude_unset=True))
            self.audit_service.log_action(user_id=user.id, action="UPDATE", entity="financial_record", entity_id=record_id)
            self.db.commit()
            logger.info(f"Record updated: id={record_id}")
            return RecordResponse.model_validate(updated_record).model_dump(mode="json")
        except Exception:
            self.db.rollback()
            raise

    def delete_record(self, record_id: int, user: User) -> None:
        """
        Initiates a 'Soft Delete' of a financial record safely.
        
        Business Logic Flow:
        1. Validates physical file possession (raises PermissionError for IDOR violations).
        2. Never executes a hardcore SQL `DELETE`. Updates a `deleted_at` timestamp. 
        3. Fires off an explicit "DELETE" Audit trace indicating exactly who soft-removed it.
        """
        record = self.record_repo.get_by_id(record_id)
        if not record:
            raise ValueError(f"Record with id {record_id} not found")

        # Ensure user can only delete their own records unless they are ADMIN
        if user.role != UserRole.ADMIN and record.user_id != user.id:
            raise PermissionError("You do not have permission to delete this record")

        try:
            self.record_repo.soft_delete(record)
            self.audit_service.log_action(user_id=user.id, action="DELETE", entity="financial_record", entity_id=record_id)
            self.db.commit()
            logger.info(f"Record soft-deleted: id={record_id}")
        except Exception:
            self.db.rollback()
            raise

    def get_export_records(self, user: User, record_type: Optional[RecordType] = None,
                           category: Optional[str] = None, start_date=None, end_date=None, search: Optional[str] = None):
        user_id = None if user.role == UserRole.ADMIN else user.id
        yield from self.record_repo.get_for_export(
            user_id=user_id, record_type=record_type, category=category,
            start_date=start_date, end_date=end_date, search=search,
        )
