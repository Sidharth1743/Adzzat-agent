from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from adzzat_demo.agent import PlanError, plan_request
from adzzat_demo.orchestrator import execute_plan
from adzzat_demo.schemas import AgentRequest, AgentResponse

app = FastAPI(title="Mini Agent Orchestrator")


@app.post("/agent", response_model=AgentResponse)
async def run_agent(request: AgentRequest) -> AgentResponse:
    try:
        plan, debug = await plan_request(request.message)
    except PlanError as exc:
        return AgentResponse(ok=False, error=str(exc), steps=[])

    pre_steps = [
        {"stage": "planner", "details": debug},
    ]
    return await execute_plan(plan, pre_steps=pre_steps)
