from typing import Generic, TypeVar

from pydantic import BaseModel, Field


DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    data: DataT
    request_id: str


class ListResponse(BaseModel, Generic[DataT]):
    items: list[DataT] = Field(default_factory=list)
    total: int
