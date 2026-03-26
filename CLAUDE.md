# STARK — Claude Code Instructions

## What This Is
STARK (Self-Training Adaptive Reasoning Kernel) is a **fully offline, self-improving AI assistant**.
It routes queries to local LLMs via Ollama, stores experiences in a neuromorphic memory network,
and fine-tunes LoRA adapters in a background thread.

Current version: **v0.2.0 "Neuro-Memory"** — adding a 4-layer cognitive memory stack.

## Before You Touch Anything

```bash
pytest tests/ -v --tb=short          # baseline must be green before starting
python -c "from core.config import get_config; print('config OK')"
python -c "from memory.neuromorphic_memory import NeuromorphicMemory; print('memory OK')"
cat openspec/project.md               # conventions
cat STARK_PLAN.md                     # current phase
```

If baseline tests are red — **stop and report**. Do not proceed on a broken foundation.

## Cardinal Rules — Never Violate

| Rule | Constraint |
|------|-----------|
| **R1** | Memory data is append-only. Never `DELETE FROM episodes`. Use soft-delete flags. |
| **R2** | Zero hardcoding. Every threshold/constant goes in `core/constants.py`. |
| **R3** | `predict()` must return in <3s. Reflection/consolidation/graph ops are async only. |
| **R4** | Memory failures must degrade gracefully. Inference path never crashes. |
| **R5** | No GPU writes during consolidation. Use the mutex in `thread_state.py`. |
| **R6** | API-level changes (new module, public API change, `core/main.py`) require an OpenSpec proposal in `openspec/changes/`. Bug fixes do not. |

## Code Style

- PEP 8, **100-char line limit**, 4-space indent
- **Type hints on every function signature**
- Google-style docstrings on all public functions/classes
- No bare numbers in logic — import from `core/constants.py`

## Architecture

```
stark_cli.py / run_voice.py / web_server.py
    └── core/main.py  (STARK singleton via get_stark())
            ├── core/intent_classifier.py   (fast-path actions)
            ├── core/task_detector.py       (TF-IDF → 8 categories)
            ├── core/adaptive_router.py     (low-confidence routing)
            ├── agents/autonomous_orchestrator.py  (complex tasks)
            ├── memory/*                    (gated by MEMORY_V2_ENABLED)
            └── Ollama API (task-routed model selection via TASK_MODELS)
```

## Feature Flag

`MEMORY_V2_ENABLED` in `core/constants.py` defaults to `False`.
Every new memory v2 code path in `core/main.py` must check this flag.

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `core/` | Constants, config, task detection, routing, orchestration |
| `memory/` | v0.2.0 neuromorphic + cognitive memory stack |
| `agents/` | Specialist agents, autonomous orchestrator |
| `learning/` | LoRA adapters, continual learner |
| `capabilities/` | Domain modules (code, health, debugging) |
| `voice/` | STT, TTS, wake word |
| `mcp/` | MCP server + client |
| `openspec/` | Change proposal workflow |

## Testing

```bash
pytest tests/ -v --tb=short       # all tests
pytest tests/test_memory_v2.py    # memory v2 specifically
```

Test files: `tests/test_<module>.py`. Run tests before and after every change.

## Adding Parameters

All parameters live in `core/constants.py`. Pattern:
```python
from core.constants import MY_CONSTANT   # import
result = my_func(MY_CONSTANT)            # use
# never: result = my_func(0.65)          # hardcoded - forbidden
```

## OpenSpec Workflow

For capability-level changes:
```bash
mkdir -p openspec/changes/<change-id>/specs/<spec-name>
# write proposal.md per openspec/AGENTS.md format
```

Bug fixes and test additions do not need a proposal.

## Running STARK

```bash
python stark_cli.py                    # CLI
python run_voice.py                    # voice mode
python web_server.py                   # web UI + MCP API
MEMORY_V2_ENABLED=true python stark_cli.py  # with memory v2
ruff check .                           # lint
```
