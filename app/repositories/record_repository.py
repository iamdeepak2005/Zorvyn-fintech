from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.financial_record import FinancialRecord, RecordType


class RecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, record_id: int, include_deleted: bool = False) -> Optional[FinancialRecord]:
        query = self.db.query(FinancialRecord).filter(FinancialRecord.id == record_id)
        if not include_deleted:
            query = query.filter(FinancialRecord.deleted_at.is_(None))
        return query.first()

    def get_filtered(
        self,
        user_id: Optional[int] = None,
        record_type: Optional[RecordType] = None,
        category: Optional[str] = None,
        start_date=None,
        end_date=None,
        search: Optional[str] = None,
        include_deleted: bool = False,
        sort_by: str = "date",
        order: str = "desc",
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[FinancialRecord], int]:
        query = self.db.query(FinancialRecord)

        if user_id is not None:
            query = query.filter(FinancialRecord.user_id == user_id)
        if not include_deleted:
            query = query.filter(FinancialRecord.deleted_at.is_(None))
        if record_type is not None:
            query = query.filter(FinancialRecord.type == record_type)
        if category is not None:
            query = query.filter(FinancialRecord.category.ilike(f"%{category}%"))
        if start_date is not None:
            query = query.filter(FinancialRecord.date >= start_date)
        if end_date is not None:
            query = query.filter(FinancialRecord.date <= end_date)
        if search is not None:
            search_term = f"%{search}%"
            query = query.filter(
                or_(FinancialRecord.notes.ilike(search_term), FinancialRecord.category.ilike(search_term))
            )

        total = query.count()

        sort_column = getattr(FinancialRecord, sort_by, FinancialRecord.date)
        query = query.order_by(sort_column.asc() if order == "asc" else sort_column.desc())

        offset = (page - 1) * limit
        records = query.offset(offset).limit(limit).all()
        return records, total

    def create(self, record: FinancialRecord) -> FinancialRecord:
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def update(self, record: FinancialRecord, update_data: dict) -> FinancialRecord:
        for key, value in update_data.items():
            if value is not None:
                setattr(record, key, value)
        self.db.flush()
        self.db.refresh(record)
        return record

    def soft_delete(self, record: FinancialRecord) -> FinancialRecord:
        record.deleted_at = datetime.now(timezone.utc)
        self.db.flush()
        self.db.refresh(record)
        return record

    def get_for_export(
        self,
        user_id: Optional[int] = None,
        record_type: Optional[RecordType] = None,
        category: Optional[str] = None,
        start_date=None,
        end_date=None,
        search: Optional[str] = None,
    ):
        """Generator for streaming CSV export — uses yield_per for memory efficiency."""
        query = self.db.query(FinancialRecord).filter(FinancialRecord.deleted_at.is_(None))

        if user_id is not None:
            query = query.filter(FinancialRecord.user_id == user_id)
        if record_type is not None:
            query = query.filter(FinancialRecord.type == record_type)
        if category is not None:
            query = query.filter(FinancialRecord.category.ilike(f"%{category}%"))
        if start_date is not None:
            query = query.filter(FinancialRecord.date >= start_date)
        if end_date is not None:
            query = query.filter(FinancialRecord.date <= end_date)
        if search is not None:
            search_term = f"%{search}%"
            query = query.filter(
                or_(FinancialRecord.notes.ilike(search_term), FinancialRecord.category.ilike(search_term))
            )

        query = query.order_by(FinancialRecord.date.desc())
        for record in query.yield_per(100):
            yield record
