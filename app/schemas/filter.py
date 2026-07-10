from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class FilterBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str
    purifier_id: int
    stage: int = Field(ge=1)
    life_percent: int = Field(default=100, ge=0, le=100)
    lifespan_days: int = Field(default=180, ge=1)
    installed_date: date
    last_replaced_date: date
    notes: str | None = None


class FilterCreate(FilterBase):
    pass


class FilterUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    type: str | None = None
    purifier_id: int | None = None
    stage: int | None = Field(None, ge=1)
    life_percent: int | None = Field(None, ge=0, le=100)
    lifespan_days: int | None = Field(None, ge=1)
    installed_date: date | None = None
    last_replaced_date: date | None = None
    notes: str | None = None


class FilterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    purifier_id: int
    purifier_name: str
    stage: int
    life_percent: int
    lifespan_days: int
    installed_date: date
    last_replaced_date: date
    notes: str | None = None
