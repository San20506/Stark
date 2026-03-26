# STARK — Agent Rules
**For:** AI coding assistants (Claude Code, Cursor, etc.) working on STARK v0.2.0  
**Authority:** These rules take precedence over general coding conventions  
**Sync with:** `openspec/AGENTS.md` (OpenSpec workflow rules) and `openspec/project.md` (project conventions)  
**Updated:** 2026-03-20

---

## 0. Before You Touch Anything

Run this checklist. No exceptions.

```bash
openspec list                        # what changes are in flight?
openspec list --specs                # what capabilities exist?
cat openspec/project.md              # project conventions
cat docs/v02/STARK_PRD.md            # what we're building
cat docs/v02/STARK_PLAN.md           # what phase we're in
pytest tests/ -v --tb=short          # confirm baseline is green
```

If baseline tests are failing before you start — **stop and report**. Do not proceed with integration work on a broken foundation.

---

## 1. Cardinal Rules — Never Violate

**R1 — Never delete memory data.**  
Diary entries, knowledge graph nodes, and tool schema versions are append-only / versioned. If you find yourself writing a `DELETE FROM episodes` or overwriting a node's content field directly — stop. Use soft-delete flags or version entries instead.

**R2 — Never hardcode parameters.**  
All thresholds, model paths, decay rates, batch sizes, and timing constants go in `core/constants.py`. No bare numbers in logic code. The project convention is zero hardcoding — this applies doubly to memory subsystem parameters because they are tunable by design.

**R3 — Never block the inference path.**  
The reflection loop, consolidation, and any A-MEM link generation that takes >10ms must run asynchronously. The `STARK.predict()` call must return within 3 seconds. If you are writing synchronous code inside `predict()` that calls a model or traverses a graph — it goes async or it doesn't go in.

**R4 — Never let memory subsystem crash STARK.**  
Every memory operation is wrapped in try/except with graceful degradation. If the diary store fails, STARK still answers. If the knowledge graph is corrupt, STARK still answers. Memory is enhancement, not infrastructure. The inference path must be bulletproof.

**R5 — Never write to the inference GPU during consolidation.**  
Consolidation uses the 7B model on GPU. It must only run when `_running_conversation = False`. Use the mutex in `thread_state.py`. Overlapping GPU access between inference and consolidation causes VRAM overflow on the 8 GB card.

**R6 — Never bypass the OpenSpec workflow for capability-level changes.**  
Adding a new module, changing an existing module's public API, or touching `core/main.py` requires a proposal in `openspec/changes/`. Bug fixes and tests do not. When in doubt, create a proposal — it takes 5 minutes and prevents scope creep.

OpenSpec validation timing is implementation-owned: you may run `openspec validate <change-id> --strict` after implementation work as part of your verification pass, rather than before sharing the proposal.

---

## 2. Memory Subsystem Rules

**M1 — Appraisal runs before retrieval, always.**  
In `core/main.py`, the call order in `predict()` is: (1) appraisal, (2) retrieval, (3) LLM. Appraisal vector must be computed and available before the memory retrieval call because it is an input to the ACT-R activation scorer.

**M2 — Emotion vectors are stored, not computed at retrieval time.**  
When a diary entry is written, the appraisal vector at that moment is serialised into the entry. During retrieval, the stored vector is used directly. Never re-compute emotion state retroactively from text alone.

**M3 — ACT-R activation is a scoring function, not a filter.**  
Activation scores rank memories — they do not gate retrieval. A memory with low activation is retrieved less often but is still retrievable when semantically relevant. Never write `WHERE activation > threshold` queries. Score first, rank second, return top-K.

**M4 — A-MEM links are probabilistic, not authoritative.**  
A link between two knowledge graph nodes means "these are probably related." It does not mean they are logically equivalent or that one implies the other. When injecting graph context into LLM prompts, label links as "possibly related" not "is connected to."

**M5 — Episode boundaries reset between sessions, not within.**  
EM-LLM surprise-based segmentation operates within a single conversation session. Cross-session continuity is handled by the diary + ACT-R layer. Do not attempt to compute episode boundaries across sessions.

**M6 — The tool schema store is the only authoritative source of tool knowledge.**  
Do not let the LLM's training knowledge override a learned tool annotation. If `tool_schema_store.py` says "endpoint X returns XML in legacy mode," that annotation takes precedence over whatever the model thinks it knows.

**M7 — Consolidation promotions require Sandy's approval.**  
Before writing any pattern to the semantic knowledge graph from a consolidation run, emit a notification via `utils/notifications.py`. The write is gated on user acknowledgment. Automated silent promotion is never allowed.

---

## 3. Module Independence Rules

Every new memory module must be independently testable without loading the LLM or Ollama:

```python
# This must work without Ollama running
from memory.diary_store import DiaryStore
store = DiaryStore(db_path="tests/fixtures/test_diary.db")
store.write(entry)
results = store.query("Sandy likes deep dives")
assert len(results) > 0
```

If your module imports from `core/main.py` or calls `_generate_response()` — it is too coupled. Refactor the dependency inward.

---

## 4. Thread Safety Rules

Every memory module that is accessed from both the main inference thread and the background reflection thread uses an `RLock`:

```python
# Required pattern in every memory module
self._lock = threading.RLock()

def write(self, entry):
    with self._lock:
        # write operation
```

The consolidation job runs in a separate process (not thread) to avoid GIL contention during GPU use. Inter-process communication via a simple file-based flag in `.stark/consolidation_state.json`.

---

## 5. Configuration Rules

**Config hierarchy (highest priority first):**
1. Environment variables (`STARK_*` prefix)
2. `config.yaml` runtime values
3. `core/constants.py` defaults

New constants for v0.2.0 must be added to `core/constants.py` under a clearly labelled `# MEMORY V2` section. New config options must be added to the `STARKConfig` Pydantic model in `core/config.py` with documented defaults and validation.

---

## 6. Testing Rules

**T1 — Every new module gets a `tests/test_<module>.py`.**  
Minimum: happy path, edge case (empty input), failure path (corrupted state).

**T2 — Integration test simulates 10 sessions.**  
`tests/test_memory_integration.py` must simulate 10 sequential conversations and verify:
- Memory persists across restarts
- ACT-R decay demonstrably changes retrieval order by session 5
- Knowledge graph has at least 3 linked nodes by session 10
- Diary has exactly 10 entries after 10 sessions

**T3 — Hardware budget test is mandatory.**  
`tests/test_hardware_budget.py` uses `utils/profiler.py` to verify VRAM ≤ 6 GB and RAM ≤ 12 GB during active inference with full memory stack loaded.

**T4 — Never mock the memory stores in integration tests.**  
Unit tests may mock. Integration tests use real SQLite, real ChromaDB, real NetworkX graph. The point of integration tests is to catch real persistence and retrieval bugs.

---

## 7. Error Handling Rules

Use this pattern for all memory operations. Never let a memory failure surface as a user-visible error:

```python
# Standard memory operation pattern
try:
    result = self._diary_store.write(entry)
    logger.debug(f"Diary entry written: {entry.id}")
except Exception as e:
    logger.warning(f"Diary write failed (non-fatal): {e}")
    result = None
# execution always continues
```

Log at `WARNING` level for degraded-mode failures (memory unavailable but inference continues). Log at `ERROR` level for failures that affect the response. Never `raise` from a memory operation into `predict()`.

---

## 8. Naming Conventions

| Thing | Convention | Example |
|---|---|---|
| New memory modules | `memory/<function>_<type>.py` | `memory/diary_store.py` |
| New constants | `UPPER_SNAKE` under `# MEMORY V2` section | `ACTIR_DECAY_RATE = 0.5` |
| New config keys | `memory_v2.subsystem.param` in YAML | `memory_v2.diary.max_entries` |
| OpenSpec change IDs | verb-led kebab-case | `add-appraisal-engine` |
| Test fixtures | `tests/fixtures/<module>/` | `tests/fixtures/diary/` |
| New data files | `.stark/<subsystem>/` | `.stark/knowledge_graph/` |

---

## 9. What to Do When Stuck

1. Re-read the relevant spec in `openspec/specs/<capability>/spec.md`
2. Check `archive/alfred_legacy/memory/` for prior implementation patterns — especially `neuromorphic_memory.py` (tiered storage) and `semantic_memory.py` (ChromaDB patterns)
3. Check `archive/alfred_legacy/openspec/specs/memory-system/spec.md` — it contains the original memory architecture decisions
4. Run `openspec show <change-id> --json --deltas-only` to verify spec delta is correctly formed
5. If the right path is still unclear — **write a comment explaining the ambiguity and stop**. Do not guess on memory architecture. Memory bugs are silent and hard to debug.

---

## 10. Quick Reference — What Goes Where

| Task | File |
|---|---|
| Add threshold / constant | `core/constants.py` |
| Add config option | `core/config.py` |
| Within-session context | `memory/episode_manager.py` |
| Cross-session retrieval scoring | `memory/activation_scorer.py` |
| Long-term knowledge storage | `memory/knowledge_graph.py` |
| Episodic diary | `memory/diary_store.py` |
| Emotion appraisal | `memory/appraisal_engine.py` |
| Thread / session state | `memory/thread_state.py` |
| Tool knowledge | `memory/tool_schema_store.py` |
| Post-conversation processing | `memory/reflection_loop.py` |
| Pattern distillation | `memory/consolidation.py` |
| Wire everything together | `core/main.py` (extend, not replace) |
