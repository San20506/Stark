# Change: Slim V2 Pipeline (S3)

## Why
The hot path calls appraisal, EM-LLM surprise, ACT-R threads, A-MEM pickle
graph, consolidation, and tool schemas on every query — none proven, all
latency and ops cost against G10 (≤3s first token).

## What Changes
- `_load_modules_v2` loads diary + thread + reflection + Hebbian only
- `_run_v2_pipeline:684-717` = session → `diary.query_semantic(20)` → `_build_context`
- `_update_v2_state:719-753` = `thread_state.update` + `reflection.trigger`
- CUT calls removed from hot path (deferred, not deleted elsewhere)

## Impact
- Affected specs: refactor-s3-pipeline (new)
- Affected code: `core/main.py:325-406,455-461,552-557,684-794`
- Must not touch: `predict()` body outside two call sites, Ollama gen `584-682`
