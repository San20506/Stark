## 1. Select Suite
- [x] 1.1 Keep KEEP-set test files; skip CUT test files listed in proposal
  - Measured 2026-09-22: ran KEEP set incl. `test_episodic_schema.py` (5 files, 33 tests); no implementation `*.py` edited; no test files edited.

## 2. Gate
- [x] 2.1 `pytest tests/test_diary_store.py tests/test_thread_state.py tests/test_neuromorphic.py tests/test_reflection_loop.py -v` green
  - Measured 2026-09-22 (venv Python 3.11.16, plus `test_episodic_schema.py`): 33 passed — `test_diary_store.py` 3/3, `test_thread_state.py` 4/4, `test_neuromorphic.py` 10/10, `test_reflection_loop.py` 14/14, `test_episodic_schema.py` 2/2.
- [ ] 2.2 `pytest --cov=memory --cov-report=term` shows ≥80% on kept modules
  - Measured 2026-09-22: NOT MET — TOTAL 49% (1341 stmts, 682 miss). Kept modules: `diary_store.py` 90%, `episodic_schema.py` 100%, `memory_node.py` 80%, `neuromorphic_memory.py` 60%, `reflection_loop.py` 96%, `thread_state.py` 80%, `episode_manager.py` 58%; CUT modules at 0% (`appraisal_engine`, `consolidation`, `knowledge_graph`, `tool_schema_store`).
- [x] 2.3 `MEMORY_V2_ENABLED=true python stark_cli.py` boots without errors
  - Measured 2026-09-22: `MEMORY_V2_ENABLED=true .venv/bin/python stark_cli.py --help` exit 0; `MEMORY_V2_ENABLED=true .venv/bin/python -c "from core.main import get_stark; get_stark()"` printed `boot OK` (Ollama down, placeholder fallback).
