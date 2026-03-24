from __future__ import annotations

import json
import os
import uuid
import re
from typing import Optional, Tuple

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from adzzat_demo.schemas import Plan

APP_NAME = "order_orchestrator"
USER_ID = "api_user"

MODEL_NAME = os.getenv("VLLM_MODEL", "LiquidAI/LFM2.5-1.2B-Thinking")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "dummy")

PLAN_SCHEMA_JSON = json.dumps(Plan.model_json_schema(), indent=2)

PLANNER_INSTRUCTION = f"""
You are a planner for an order-processing system.
Convert the user request into a JSON plan that matches this schema:
{PLAN_SCHEMA_JSON}

Rules:
- Only use the tools: "cancel_order" and "send_email".
- If the user asks to cancel an order, include a cancel_order step with an order_id.
- If the user asks to send confirmation, include a send_email step with email and message.
- Output ONLY valid JSON. No extra text.
""".strip()

planner_agent = LlmAgent(
    name="order_planner",
    model=LiteLlm(
        model=MODEL_NAME,
        api_base=VLLM_BASE_URL,
        api_key=VLLM_API_KEY,
    ),
    description="Plans order cancellation requests into executable steps.",
    instruction=PLANNER_INSTRUCTION,
    output_schema=Plan,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=256,
    ),
)

session_service = InMemorySessionService()
planner_runner = Runner(agent=planner_agent, app_name=APP_NAME, session_service=session_service)


class PlanError(RuntimeError):
    pass


def _new_session_id() -> str:
    return f"session_{uuid.uuid4().hex}"


async def plan_request(message: str) -> Tuple[Plan, dict]:
    session_id = _new_session_id()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    content = types.Content(role="user", parts=[types.Part(text=message)])
    final_text: Optional[str] = None

    async for event in planner_runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text

    if not final_text:
        raise PlanError("Planner returned no response.")

    try:
        plan = Plan.model_validate_json(final_text)
    except ValidationError as exc:
        raise PlanError("Planner output failed schema validation.") from exc

    order_id_match = re.search(r"#?(\\d{3,})", message)
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}", message, re.IGNORECASE)
    order_id = order_id_match.group(1) if order_id_match else None
    email = email_match.group(0) if email_match else None
    wants_cancel = "cancel" in message.lower()
    wants_email = "email" in message.lower()

    for step in plan.steps:
        if step.tool == "cancel_order" and not str(step.args.get("order_id", "")).strip() and order_id:
            step.args["order_id"] = order_id
        if step.tool == "send_email" and not str(step.args.get("email", "")).strip() and email:
            step.args["email"] = email

    tools_in_plan = {step.tool for step in plan.steps}
    if wants_cancel and "cancel_order" not in tools_in_plan and order_id:
        plan.steps.insert(0, {"tool": "cancel_order", "args": {"order_id": order_id}})
    if wants_email and "send_email" not in tools_in_plan and email:
        plan.steps.append({"tool": "send_email", "args": {"email": email}})

    debug = {
        "planner_raw": final_text,
        "extracted_fields": {"order_id": order_id, "email": email},
        "final_plan": plan.model_dump(),
    }

    return plan, debug
