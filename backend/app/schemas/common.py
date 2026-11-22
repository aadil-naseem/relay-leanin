"""Shared schema pieces: trace entries and the uniform error envelope."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class TraceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: str
    detail: str
    inputs: Any | None = None
    output: Any | None = None


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody