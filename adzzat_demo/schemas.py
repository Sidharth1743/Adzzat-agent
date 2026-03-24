from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    tool: Literal["cancel_order", "send_email"]
    args: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    steps: list[PlanStep] = Field(default_factory=list)


class AgentRequest(BaseModel):
    message: str


class AgentResponse(BaseModel):
    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str | None = None
