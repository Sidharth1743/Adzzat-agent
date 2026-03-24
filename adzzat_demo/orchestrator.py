from __future__ import annotations

import time
from typing import Any

from adzzat_demo.logging_utils import log_event
from adzzat_demo.schemas import AgentResponse, Plan
from adzzat_demo.tools import cancel_order, send_email


def _default_email_message(order_id: str) -> str:
    return f"Your order {order_id} has been cancelled."


async def execute_plan(
    plan: Plan,
    pre_steps: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> AgentResponse:
    steps_log: list[dict[str, Any]] = list(pre_steps or [])
    if not plan.steps:
        steps_log.append({"stage": "validation", "error": "No actionable steps in plan."})
        return AgentResponse(ok=False, error="No actionable steps in plan.", steps=steps_log)
    last_result: dict[str, Any] | None = None

    for step in plan.steps:
        if step.tool == "cancel_order":
            order_id = str(step.args.order_id).strip()
            if not order_id:
                steps_log.append(
                    {
                        "stage": "validation",
                        "tool": step.tool,
                        "error": "Missing order_id",
                        "args": step.args.model_dump(),
                    }
                )
                return AgentResponse(
                    ok=False,
                    error="Plan missing order_id for cancel_order.",
                    steps=steps_log,
                )
            start = time.perf_counter()
            steps_log.append({"stage": "tool_start", "tool": step.tool, "args": step.args.model_dump(), "ts": time.time()})
            if request_id:
                log_event("tool_start", request_id, tool=step.tool, args=step.args.model_dump())
            result = await cancel_order(order_id)
            duration_ms = int((time.perf_counter() - start) * 1000)
            if request_id:
                log_event("tool_end", request_id, tool=step.tool, result=result)
            steps_log.append(
                {
                    "stage": "tool_end",
                    "tool": step.tool,
                    "args": step.args.model_dump(),
                    "result": result,
                    "duration_ms": duration_ms,
                    "ts": time.time(),
                }
            )
            last_result = result
            if not result.get("ok"):
                return AgentResponse(
                    ok=False,
                    error="cancel_order failed; skipping send_email.",
                    steps=steps_log,
                )

        elif step.tool == "send_email":
            email = str(step.args.email).strip()
            if not email:
                steps_log.append(
                    {
                        "stage": "validation",
                        "tool": step.tool,
                        "error": "Missing email",
                        "args": step.args.model_dump(),
                    }
                )
                return AgentResponse(
                    ok=False,
                    error="Plan missing email for send_email.",
                    steps=steps_log,
                )
            message = str(step.args.message or "").strip()
            if not message:
                order_id = ""
                for logged in steps_log:
                    if logged.get("tool") == "cancel_order":
                        order_id = str(logged.get("args", {}).get("order_id", "")).strip()
                        break
                message = _default_email_message(order_id) if order_id else "Your order has been cancelled."
            start = time.perf_counter()
            steps_log.append({"stage": "tool_start", "tool": step.tool, "args": step.args.model_dump(), "ts": time.time()})
            if request_id:
                log_event("tool_start", request_id, tool=step.tool, args=step.args.model_dump())
            result = await send_email(email=email, message=message)
            duration_ms = int((time.perf_counter() - start) * 1000)
            if request_id:
                log_event("tool_end", request_id, tool=step.tool, result=result)
            steps_log.append(
                {
                    "stage": "tool_end",
                    "tool": step.tool,
                    "args": step.args.model_dump(),
                    "result": result,
                    "duration_ms": duration_ms,
                    "ts": time.time(),
                }
            )
            last_result = result
            if not result.get("ok"):
                return AgentResponse(
                    ok=False,
                    error="send_email failed.",
                    steps=steps_log,
                )

        else:
            return AgentResponse(
                ok=False,
                error=f"Unsupported tool in plan: {step.tool}",
                steps=steps_log,
            )

    return AgentResponse(ok=True, result=last_result, steps=steps_log)
