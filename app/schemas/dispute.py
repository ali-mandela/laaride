"""Pydantic schemas for the dispute resolution system."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.dispute import DisputeType, DisputeStatus


class DisputeCreate(BaseModel):
    booking_id: str
    dispute_type: DisputeType
    description: str = Field(..., min_length=20, max_length=2000)


class DisputeMessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class DisputeResponse(BaseModel):
    id: str
    booking_id: str
    dispute_type: str
    description: str
    status: str
    complainant_name: str
    resolution_note: Optional[str]
    refund_amount: Optional[float]
    created_at: datetime
    updated_at: datetime


class DisputeResolve(BaseModel):
    resolution_note: str = Field(..., min_length=10)
    refund_amount: Optional[float] = Field(None, ge=0)
    status: DisputeStatus
