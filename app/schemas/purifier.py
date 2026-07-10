from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PurifierBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=200)
    install_date: date
    status: str = "active"
    filter_life_percent: int = Field(default=100, ge=0, le=100)


class PurifierCreate(PurifierBase):
    pass


class PurifierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    model: str | None = Field(None, min_length=1, max_length=50)
    location: str | None = Field(None, min_length=1, max_length=200)
    install_date: date | None = None
    status: str | None = None
    filter_life_percent: int | None = Field(None, ge=0, le=100)


class PurifierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    model: str
    location: str
    install_date: date
    status: str
    filter_life_percent: int
