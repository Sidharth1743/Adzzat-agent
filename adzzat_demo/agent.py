from __future__ import annotations

import json
import os
import uuid
from typing import Optional, Tuple

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from adzzat_demo.schemas import Plan

load_dotenv()

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
- Extract concrete values from the user message.
- For cancel_order, args MUST include: {{"order_id": "<id>"}}.
- For send_email, args MUST include: {{"email": "<email>", "message": "<text>"}}.
- Do NOT output schema fragments or JSON Schema keywords like "title", "type", "additionalProperties".
- Output ONLY the JSON plan. No prose, no code fences.

Example output:
{{
  "steps": [
    {{"tool": "cancel_order", "args": {{"order_id": "9921"}}}},
    {{"tool": "send_email", "args": {{"email": "user@example.com", "message": "Your order 9921 was cancelled."}}}}
  ]
}}
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
        response_mime_type="application/json",
    ),
)

session_service = InMemorySessionService()
planner_runner = Runner(agent=planner_agent, app_name=APP_NAME, session_service=session_service)


class PlanError(RuntimeError):
    def __init__(self, message: str, debug: dict | None = None) -> None:
        super().__init__(message)
        self.debug = debug or {}


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
        raise PlanError("Planner returned no response.", {"planner_raw": None})

    try:
        plan = Plan.model_validate_json(final_text)
    except ValidationError as exc:
        raise PlanError(
            "Planner output failed schema validation.",
            {"planner_raw": final_text},
        ) from exc

    debug = {
        "planner_raw": final_text,
        "final_plan": plan.model_dump(),
    }

    return plan, debug
