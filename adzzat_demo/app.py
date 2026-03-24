import time
import uuid

from dotenv import load_dotenv

# Load .env before importing modules that read environment variables.
load_dotenv()

from fastapi import FastAPI

from adzzat_demo.agent import PlanError, plan_request
from adzzat_demo.logging_utils import log_event
from adzzat_demo.orchestrator import execute_plan
from adzzat_demo.schemas import AgentRequest, AgentResponse

app = FastAPI(title="Mini Agent Orchestrator")


@app.post("/agent", response_model=AgentResponse)
async def run_agent(request: AgentRequest) -> AgentResponse:
    request_id = uuid.uuid4().hex
    start_time = time.perf_counter()
    log_event("request_received", request_id, message=request.message)
    try:
        planner_start = time.perf_counter()
        plan, debug = await plan_request(request.message)
        planner_duration_ms = int((time.perf_counter() - planner_start) * 1000)
    except PlanError as exc:
        log_event("planner_error", request_id, error=str(exc))
        planner_debug = exc.debug or {}
        steps = []
        if planner_debug:
            steps.append({"stage": "planner", "details": planner_debug, "ts": time.time()})
        return AgentResponse(ok=False, error=str(exc), steps=steps, request_id=request_id)

    pre_steps = [
        {"stage": "planner", "details": debug, "duration_ms": planner_duration_ms, "ts": time.time()},
    ]
    response = await execute_plan(plan, pre_steps=pre_steps, request_id=request_id)
    duration_ms = int((time.perf_counter() - start_time) * 1000)
    response.steps.append({"stage": "total", "duration_ms": duration_ms, "ts": time.time()})
    log_event(
        "request_completed",
        request_id,
        ok=response.ok,
        duration_ms=duration_ms,
        error=response.error,
    )
    response.request_id = request_id
    return response
