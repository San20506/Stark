# STARK Project Status
**Generated:** 2026-03-31  
**Version:** v0.2.0 "Neuro-Memory"  
**Branch:** main

---

## TL;DR

All 9 memory v2 module files are written. The plan is complete on paper.
**Nothing runs** — `sentence_transformers` is not installed and breaks every memory import.
Pytest itself is broken (`pygments` missing). Core STARK (routing, config, orchestration) is healthy.

---

## Environment Health

| Check | Status | Detail |
|-------|--------|--------|
| `core.*` imports | ✅ OK | constants, config, main, router, task_detector all load |
| `memory.*` imports | ❌ BLOCKED | All 11/12 modules fail: `No module named 'sentence_transformers'` |
| pytest | ❌ BROKEN | `No module named 'pygments'` — test suite cannot execute |
| scikit-learn | ✅ Present | 1.8.0 |
| pluggy | ✅ Present | 1.6.0 |
| sentence_transformers | ❌ Missing | Required by every memory v2 module |
| networkx | ❌ Unknown | Required by `knowledge_graph.py` |
| chromadb | ❌ Unknown | Required by media-memory integration |

**Fix first:**
```bash
pip install sentence_transformers networkx pygments
```

---

## Plan Phase Completion

### Week 1 — Foundation Layer

| Phase | Description | Status |
|-------|-------------|--------|
| 1.1 | Constants + MemoryV2Config | ✅ Done — `ACTIR_DECAY_RATE`, all v2 constants present |
| 1.2 | `MEMORY_V2_ENABLED` feature flag | ✅ Done — defaults `False`, wired into `core/main.py` |
| 1.3 | `memory/thread_state.py` | ✅ Written — not importable (sentence_transformers) |
| 1.4 | Episodic DB schema migration | ✅ Written (`memory/episodic_schema.py`) — not importable |
| 1.5 | `memory/appraisal_engine.py` | ✅ Written — not importable |
| 1.6 | `memory/diary_store.py` | ✅ Written — not importable |

### Week 2 — Memory Intelligence Layer

| Phase | Description | Status |
|-------|-------------|--------|
| 2.1 | `memory/activation_scorer.py` | ✅ Written — not importable |
| 2.2 | `memory/episode_manager.py` | ✅ Written — not importable |
| 2.3 | `memory/knowledge_graph.py` | ✅ Written — not importable |

### Week 3 — Integration Layer

| Phase | Description | Status |
|-------|-------------|--------|
| 3.1 | `memory/reflection_loop.py` | ✅ Written — not importable |
| 3.2 | `memory/tool_schema_store.py` | ✅ Written — not importable |
| 3.3 | `memory/consolidation.py` | ✅ Written — not importable |
| 3.4 | Wire into `core/main.py` | ⚠️ Partial — module refs added, lazy-load stubs present; full pipeline not wired |
| 3.5 | Full test suite | ⚠️ Partial — all test files exist, pytest cannot run |

---

## Module Inventory

### `memory/` — All files present

```
memory_node.py          ✅ Importable (no sentence_transformers dep)
neuromorphic_memory.py  ❌ sentence_transformers
thread_state.py         ❌ sentence_transformers
appraisal_engine.py     ❌ sentence_transformers
diary_store.py          ❌ sentence_transformers
activation_scorer.py    ❌ sentence_transformers
episode_manager.py      ❌ sentence_transformers
knowledge_graph.py      ❌ sentence_transformers
reflection_loop.py      ❌ sentence_transformers
tool_schema_store.py    ❌ sentence_transformers
consolidation.py        ❌ sentence_transformers
episodic_schema.py      ❌ sentence_transformers
```

### `core/` — Healthy

```
constants.py            ✅ All v2 constants present
config.py               ✅ OK
main.py                 ✅ OK (v2 module refs present, lazy-loaded)
intent_classifier.py    ✅ OK
task_detector.py        ✅ OK
```

### `modules/life_os/` — Phases 1–5 done

```
scheduler.py            ✅ Written
context_manager.py      ✅ Written
voice_hooks.py          ✅ Written
web_routes.py           ✅ Written
agents/morning_agent.py ✅ Written
agents/evening_agent.py ✅ Written
agents/weekly_agent.py  ✅ Written
connectors/notion_connector.py  ✅ Written
connectors/gcal_connector.py    ✅ Written
```

### `tests/` — All files present, none runnable

```
test_thread_state.py        ✅ Exists
test_appraisal_engine.py    ✅ Exists
test_diary_store.py         ✅ Exists
test_activation_scorer.py   ✅ Exists
test_episode_manager.py     ✅ Exists
test_knowledge_graph.py     ✅ Exists
test_reflection_loop.py     ✅ Exists
test_tool_schema_store.py   ✅ Exists
test_consolidation.py       ✅ Exists
test_memory_integration.py  ✅ Exists
test_memory_v2.py           ✅ Exists
test_life_os.py             ✅ Exists
```

---

## Open Tasks

### Immediate (unblocks everything)

- [ ] `pip install sentence_transformers networkx pygments` — unblocks all memory imports and pytest
- [ ] Run `pytest tests/ -v --tb=short` — establish baseline

### Phase 3.4 — core/main.py wiring (incomplete)

`core/main.py` has placeholder references but the full predict() pipeline from STARK_PLAN.md is not wired:
- [ ] Step 1: `thread_state.get_or_create_session()` in predict()
- [ ] Step 2: `appraisal_engine.compute()` in predict()
- [ ] Step 3: `episode_manager.on_message()` in predict()
- [ ] Step 4: Replace old recall with scored diary + graph + episode context
- [ ] Step 5: Build unified LLM context from all memory sources
- [ ] Step 7: `thread_state.update()` after response
- [ ] `start()`: init all v2 modules, start reflection loop, schedule consolidation
- [ ] `stop()`: signal reflection loop, checkpoint sessions, persist graph + schemas

### life_os Phase 6

- [ ] Wire `start_scheduler()` into `core/main.py` startup
- [ ] Register `life_os_bp` in `web_server.py` at `/api/life_os`
- [ ] Fill `modules/life_os/context/profile.md`, `goals.md`, `habits.md`
- [ ] Set `NOTION_TOKEN`, `NOTION_TASKS_DB_ID`, `NOTION_WEEKLY_DB_ID`, `GCAL_CREDENTIALS_PATH`
- [ ] Route voice intents (morning/evening/weekly) through STARK pipeline

### Infrastructure

- [ ] Verify `research-scout` scheduled run is active
- [ ] Confirm `consolidate-memory` nightly timer is running

---

## Completion Checklist (from STARK_PLAN.md)

```
[x] Phase 1.1 — constants + config
[x] Phase 1.2 — feature flag
[x] Phase 1.3 — thread state manager (written, not validated)
[x] Phase 1.4 — episodic DB schema migration (written, not validated)
[x] Phase 1.5 — appraisal engine (written, not validated)
[x] Phase 1.6 — diary store (written, not validated)
[x] Phase 2.1 — ACT-R activation scorer (written, not validated)
[x] Phase 2.2 — EM-LLM episode manager (written, not validated)
[x] Phase 2.3 — A-MEM knowledge graph (written, not validated)
[x] Phase 3.1 — reflection loop (written, not validated)
[x] Phase 3.2 — tool schema store (written, not validated)
[x] Phase 3.3 — consolidation job (written, not validated)
[ ] Phase 3.4 — core/main.py integration (partial)
[ ] Phase 3.5 — full test suite (exists, not runnable)
[ ] pytest tests/ -v ALL GREEN
[ ] hardware budget verified ≤6GB VRAM / ≤12GB RAM
[ ] MEMORY_V2_ENABLED feature flag removed (integration is default)
[ ] README v0.2.0 section written
[ ] docs/v02/ documents committed to repo
```

---

## Next Session Priorities

1. **Fix env:** `pip install sentence_transformers networkx pygments`
2. **Run tests:** Get pytest green, assess module correctness
3. **Complete Phase 3.4:** Wire full predict() pipeline in core/main.py
4. **Validate end-to-end:** `MEMORY_V2_ENABLED=true python stark_cli.py`
5. **Measure latency:** Confirm <3s first-token with full memory stack
