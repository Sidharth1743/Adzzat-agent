from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class CancelOrderArgs(BaseModel):
    order_id: str


class SendEmailArgs(BaseModel):
    email: str
    message: str


class CancelOrderStep(BaseModel):
    tool: Literal["cancel_order"]
    args: CancelOrderArgs


class SendEmailStep(BaseModel):
    tool: Literal["send_email"]
    args: SendEmailArgs


PlanStep = Annotated[Union[CancelOrderStep, SendEmailStep], Field(discriminator="tool")]


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
