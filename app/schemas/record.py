from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.financial_record import RecordType


class RecordCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    type: RecordType
    category: str = Field(..., min_length=1, max_length=100)
    date: date
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"amount": 1500.00, "type": "INCOME", "category": "Salary", "date": "2026-03-15", "notes": "Monthly salary"}]
        }
    }


class RecordUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    type: Optional[RecordType] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    date: Optional[date] = None
    notes: Optional[str] = None


class RecordResponse(BaseModel):
    id: int
    user_id: int
    amount: Decimal
    type: RecordType
    category: str
    date: date
    notes: Optional[str] = None
    deleted_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecordFilterParams(BaseModel):
    type: Optional[RecordType] = None
    category: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    search: Optional[str] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = Field("date", pattern="^(date|amount|created_at)$")
    order: Optional[str] = Field("desc", pattern="^(asc|desc)$")
    include_deleted: bool = False

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v, info):
        if v and info.data.get("start_date") and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v
