import enum
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, Enum, ForeignKey,
    Index, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class RecordType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    type = Column(Enum(RecordType, name="record_type", create_type=True), nullable=False)
    category = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_amount_positive"),
        Index("idx_records_date", "date"),
        Index("idx_records_category", "category"),
        Index("idx_records_type", "type"),
        Index("idx_records_user_id", "user_id"),
        Index("idx_records_not_deleted", "id", postgresql_where=Column("deleted_at").is_(None)),
    )

    user = relationship("User", back_populates="financial_records")

    def __repr__(self):
        return f"<FinancialRecord(id={self.id}, amount={self.amount}, type='{self.type}')>"
