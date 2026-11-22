"""Pydantic schemas for every /api/v1 endpoint (shapes first; routers come in Phase 5+)."""

from app.schemas.common import ErrorBody, ErrorResponse, TraceEntry

__all__ = ["ErrorBody", "ErrorResponse", "TraceEntry"]