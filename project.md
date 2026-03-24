# Project: Mini Agent Orchestrator (LFM + Google ADK)

## Goal
Build a lightweight, event-driven order‑processing agent that:
- Accepts a natural language request at a single HTTP endpoint.
- Uses an LLM planner to turn the request into actionable steps.
- Executes mock async tools in order with guardrails.

Example input: `Cancel my order #9921 and email me the confirmation at user@example.com.`

## Required Stack
- **Language**: Python
- **Framework**: FastAPI
- **LLM**: LiquidAI LFM2.5 via **vLLM OpenAI‑compatible server**
- **Agent framework**: **Google ADK** (use ADK to define the agent, tools, and orchestration)
- **No heavy agent frameworks** (no LangChain, etc.)

## LLM Serving (vLLM OpenAI‑Compatible)
Run the model locally via vLLM:
```bash
vllm serve LiquidAI/LFM2.5-1.2B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto
```
Optional:
- `--max-model-len L`
- `--gpu-memory-utilization 0.9`

OpenAI‑compatible client config:
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # vLLM doesn't require auth by default
)
```

## ADK‑Based Agent Design
Use Google ADK to:
- Define an **agent** that receives the user’s request.
- Register **tools** for order cancellation and email sending.
- Route from planner output to tool execution.

### Tools (Async)
Implement the following async tools (with mock behavior):
- `cancel_order(order_id: str) -> dict`
  - Simulate 20% failure rate.
  - Return `{ "ok": true/false, "order_id": "...", "reason": "..." }`.
- `send_email(email: str, message: str) -> dict`
  - Simulate latency with `asyncio.sleep(1)`.
  - Return `{ "ok": true, "email": "..." }`.

### Planner Contract
The LLM should return a **structured plan** (JSON) with steps such as:
```json
{
  "steps": [
    {"tool": "cancel_order", "args": {"order_id": "9921"}},
    {"tool": "send_email", "args": {"email": "user@example.com", "message": "..."}}
  ]
}
```
Use ADK to parse, validate, and execute this plan.

### Guardrails
- If `cancel_order` fails, **do not** call `send_email`.
- Return a clear failure response with error context.

## API
Expose one endpoint:
- `POST /agent`
- Input body: `{ "message": "<user request>" }`
- Response body:
  - Success: `{ "ok": true, "result": { ... }, "steps": [...] }`
  - Failure: `{ "ok": false, "error": "...", "steps": [...] }`

## Deliverables
1. Clean repository with code and a minimal ADK‑based agent.
2. `README.md` documenting:
   - Architecture
   - Async workflow
   - Error handling and guardrails
   - LLM reliability strategy
3. 2–3 minute demo video showing the API working.

## Notes
- Prefer direct LLM calls through the OpenAI‑compatible client.
- Keep the planner simple and deterministic (low temperature).
- Use explicit JSON schema validation before tool execution.
