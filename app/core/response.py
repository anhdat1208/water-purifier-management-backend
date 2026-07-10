from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T
    message: str | None = None


def success(data: Any, message: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"data": data}
    if message:
        payload["message"] = message
    return payload
