# Mini Agent Orchestrator (LFM + Google ADK)

## Overview
This project implements a lightweight, event‑driven order‑processing agent using:
- FastAPI for the HTTP API
- Google ADK for LLM‑driven planning
- vLLM serving LiquidAI LFM2.5 via an OpenAI‑compatible API

The agent accepts a natural language request, asks the planner LLM for a JSON plan, then executes mock tools with guardrails.

## Requirements
- Python 3.13+
- A running vLLM server for the LFM model
- SMTP access for real email sending

## Run the LFM Model (vLLM)
```bash
vllm serve LiquidAI/LFM2.5-1.2B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto
```

Optional:
- `--max-model-len L`
- `--gpu-memory-utilization 0.9`

## Install Dependencies
```bash
pip install -U pip
pip install -e .
```

## Configure Environment (.env)
Create a `.env` file (see `.env.example`) and fill in your SMTP and vLLM values.
## Start the API
```bash
python main.py
```
The API listens on `http://localhost:8080`.

## Example Request
```bash
curl -X POST http://localhost:8080/agent \
  -H "Content-Type: application/json" \
  -d '{"message":"Cancel my order #9921 and email me at user@example.com"}'
```

## Environment Variables
- `VLLM_MODEL` (default: `LiquidAI/LFM2.5-1.2B-Instruct`)
- `VLLM_BASE_URL` (default: `http://localhost:8000/v1`)
- `VLLM_API_KEY` (default: `dummy`)
- `SMTP_HOST` (e.g. `smtp.gmail.com`)
- `SMTP_PORT` (587 for STARTTLS, 465 for SSL)
- `SMTP_USER`
- `SMTP_PASS` (app password, not your normal password)
- `SMTP_FROM` (default: `SMTP_USER`)

## SMTP Setup (Generic)
1. Enable SMTP on your email account.
2. Create an app password or OAuth credentials (app password is simplest).
3. Set the SMTP values in `.env`.
4. Start the API and send a request. The `send_email` tool will send a real email.

## Architecture Notes
- **Planner**: A Google ADK `LlmAgent` prompts the LFM model to return a strict JSON plan.
- **Orchestrator**: Executes steps in order and stops on `cancel_order` failure.
- **Tools**: `cancel_order` simulates a 20% failure rate; `send_email` uses SMTP and adds a 1s delay.
- **Logging**: Structured JSON logs with `request_id`, tool start/end, and latencies.

## Response Tracing
The API response includes a `steps` array with:
- Planner raw output and validated plan
- Tool start/end entries with durations
- A final `total` step with end-to-end latency

## Files
- `app.py`: FastAPI app and route handler.
- `agent.py`: ADK planner setup and plan execution.
- `orchestrator.py`: Tool orchestration and guardrails.
- `tools.py`: Mock async tools.
- `schemas.py`: Request/response and plan schemas.
