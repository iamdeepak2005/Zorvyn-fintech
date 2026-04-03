from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[ErrorDetail] = None

    @classmethod
    def ok(cls, data: Any = None, message: Optional[str] = None) -> "ApiResponse":
        return cls(success=True, data=data, message=message, error=None)

    @classmethod
    def fail(cls, code: str, message: str) -> "ApiResponse":
        return cls(success=False, data=None, error=ErrorDetail(code=code, message=message))


class PaginatedData(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int
