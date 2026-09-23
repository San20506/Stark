# Change: Quarantine LifeOS Web Health (S6)

## Why
`modules/life_os/` (APScheduler + Notion/GCal OAuth), Flask demo, health
monitor, and Router-Arbiter fan-out violate offline non-goals, double entry
points, and break G10 (≤3s) with 3 LLM calls. Zero imports in entry files —
fully isolated.

## What Changes
- Delete `modules/life_os/`, `web_server.py`, `web/`, `capabilities/health_monitor.py`
- Remove `core/main.py:491-528` orchestrator branch; keep direct `TASK_MODELS` routing

## Impact
- Affected specs: refactor-s6-lifeos (new)
- Affected code: dirs above + one `predict()` branch
- Must not touch: `455-461`/`552-557` v2 call sites, Ollama gen `584-682`
