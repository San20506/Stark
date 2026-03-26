# STARK — Integration Plan
**Version:** 0.2.0 — Neuro-Memory Integration  
**Status:** Ready for execution  
**Date:** 2026-03-20

This is the ground-level execution plan. It tells you exactly what to build, in what order, and why that order. Follow it sequentially — each phase is a dependency for the next.

---

## Pre-flight Checklist

Before starting Week 1, verify:

```bash
pytest tests/ -v --tb=short          # all existing tests green
openspec list                         # no conflicting active changes
python -c "from core.config import get_config; print('config OK')"
python -c "from memory.neuromorphic_memory import NeuromorphicMemory; print('memory OK')"
```

Create the OpenSpec change:
```bash
mkdir -p openspec/changes/add-neuro-memory-stack/specs/neuromorphic-memory
# write proposal.md, tasks.md per AGENTS.md format
```

Create the docs directory:
```bash
mkdir -p docs/v02
# move the four planning documents here
```

---

## Week 1 — Foundation Layer

**Goal:** Everything STARK needs to run memory v2 is in place. No actual memory intelligence yet — just the infrastructure that every higher module depends on.

### Phase 1.1 — Constants and Config (Day 1)

**What:** Add all v0.2.0 parameters to `core/constants.py` and `core/config.py`.

**Why first:** Every subsequent module imports from constants. Do this once, do it right, nothing breaks later.

**What to add to `core/constants.py`** under a `# === MEMORY V2 ===` section:
```
ACTIR_DECAY_RATE              = 0.5
ACTIR_ACTIVATION_FLOOR        = -2.0
ACTIR_ACTIVATION_CEILING      = 3.0
ACTIR_NOISE_STD               = 0.1
APPRAISAL_SMOOTHING_WINDOW    = 5
APPRAISAL_NOVELTY_THRESHOLD   = 0.65
EPISODE_SURPRISE_THRESHOLD    = 0.65
EPISODE_RETRIEVAL_SEM_WEIGHT  = 0.70
EPISODE_RETRIEVAL_TEMP_WEIGHT = 0.30
AMEM_LINK_SIMILARITY_THRESH   = 0.75
AMEM_PROMOTION_QUORUM         = 5
AMEM_PROMOTION_SESSION_MIN    = 3
DIARY_MAX_ENTRIES_SOFT_CAP    = 50000
REFLECTION_TRIGGER_DELAY_SEC  = 30
REFLECTION_MODEL_NAME         = "qwen2.5:3b"   # or whatever 3B model is available via Ollama
CONSOLIDATION_CONFLICT_THRESH = 10
CONSOLIDATION_SCHEDULE        = "02:00"        # nightly at 2am
TOOL_SCHEMA_CONFIDENCE_DECAY  = 0.5            # per 30 days without confirmation
TOOL_SCHEMA_STALENESS_DAYS    = 30
```

**What to add to `core/config.py`** — a new `MemoryV2Config` Pydantic model and add it as a field on `STARKConfig`.

**Done when:** `python -c "from core.constants import ACTIR_DECAY_RATE; print(ACTIR_DECAY_RATE)"` works.

---

### Phase 1.2 — Feature Flag (Day 1)

**What:** Add `MEMORY_V2_ENABLED` flag that defaults to `False`. Every new code path in `core/main.py` checks this flag. Allows safe rollout without breaking existing behaviour.

**Where:** `core/constants.py` and checked in `core/main.py` `predict()` method.

**Done when:** `MEMORY_V2_ENABLED=true python stark_cli.py` starts without errors (even if memory v2 does nothing yet).

---

### Phase 1.3 — Thread State Manager (Day 2)

**What:** `memory/thread_state.py`

**What it does:**
- Assigns a unique `session_id` (UUID) to every conversation
- Maintains a per-session state dict: `{messages, emotion_vector, active_tool_schemas, retrieved_memory_ids, episode_boundaries}`
- Checkpoints state to `.stark/sessions/<session_id>.json` after every exchange using SQLite WAL mode
- Provides `load_session(session_id)` and `new_session()` methods
- Detects "conversation ended" — last message was >5 minutes ago, triggers reflection

**Edge cases to handle:**
- Session file missing on load → start fresh session, log warning
- Concurrent write during checkpoint → use file lock
- Session state grows too large (>10 MB) → compress oldest messages into summary

**Done when:** Unit test creates session, writes 10 exchanges, simulates crash, reloads session, verifies all 10 exchanges present.

---

### Phase 1.4 — Extend Episodic DB Schema (Day 2)

**What:** Migrate `data/memory/episodic.db` to add new columns for v0.2.0.

**New columns on `episodes` table:**
```sql
session_id          TEXT,
emotion_vector      TEXT,    -- JSON serialised 6D float list
episode_ids         TEXT,    -- JSON list of EM-LLM episode boundary IDs
tool_schemas_used   TEXT,    -- JSON list of tool names touched
insights            TEXT,    -- reflection-generated insight text
tags                TEXT,    -- JSON list of topic tags
neutral_embedding   BLOB,    -- embedding without emotion context (for retrieval)
contextual_embedding BLOB    -- embedding with emotion context (for self-modelling)
```

**Migration:** Non-destructive ALTER TABLE adds — existing rows get NULL in new columns, which is valid.

**Done when:** `data/memory/episodic.db` has new schema; existing `NeuromorphicMemory.recall()` still works unchanged.

---

### Phase 1.5 — Appraisal Engine (Day 3)

**What:** `memory/appraisal_engine.py`

**What it does:**
- Accepts: user input text, previous N messages (for context), current session state
- Computes 6D appraisal vector: `{novelty, valence, agency, coping, certainty, goal_relevance}`
- Each dimension computed by a lightweight classifier (not an LLM call):
  - `novelty` → cosine distance between current embedding and rolling mean of last N=20 embeddings
  - `valence` → VADER sentiment score × goal alignment (dot product against goal embedding)
  - `agency` → rule-based entity attribution (pronouns, verb subjects)
  - `coping` → 1 - (task_complexity / rolling_success_rate) where task_complexity from `task_detector`
  - `certainty` → 1 - entropy of task detection distribution
  - `goal_relevance` → dot product between input embedding and stored goal embeddings
- Maintains rolling smoothing window of N=5 appraisals (from constants)
- Returns a named dict, never raises

**Emotion label:** Nearest neighbour in a pre-computed 6D emotion atlas (30 emotion categories). For reference only — the vector itself is what gets stored and passed to LLM context.

**Performance target:** <10ms on CPU.

**Done when:** Unit test passes 20 varied inputs and gets valid vectors for all; latency test confirms <10ms.

---

### Phase 1.6 — Diary Store (Day 4–5)

**What:** `memory/diary_store.py`

**What it does:**
- Wraps the extended `episodic.db` with a clean write/read/search API
- `write(DiaryEntry)` — append-only insert, never updates existing rows
- `query_semantic(text, top_k)` → returns top-K entries by semantic similarity using neutral_embedding
- `query_timerange(start, end)` → returns entries by timestamp
- `query_emotion(emotion_range_dict)` → returns entries matching emotion vector range
- `query_tags(tags)` → returns entries matching any tag
- All queries combine via a unified scoring function:
  ```
  final_score = 0.7 × semantic_sim + 0.2 × recency_weight + 0.1 × emotional_resonance
  ```
  where `recency_weight = 1 / (1 + log(days_since + 1))`
- Soft cap: when entry count > `DIARY_MAX_ENTRIES_SOFT_CAP`, oldest entries archived to cold storage (reuse Parquet pattern from `archive/alfred_legacy/memory/neuromorphic_memory.py`)

**Integration:** `NeuromorphicMemory` in `memory/neuromorphic_memory.py` delegates diary writes to this module. Existing `store()` method extended to call `diary_store.write()` after storing the node.

**Done when:** Unit test writes 100 entries, queries by each method, verifies correct ranking; soft cap test verifies archival triggers correctly.

---

## Week 2 — Memory Intelligence Layer

**Goal:** The three core memory frameworks are implemented and independently functional.

### Phase 2.1 — ACT-R Activation Scorer (Day 6–7)

**What:** `memory/activation_scorer.py`

**What it does:**
- Implements: `A(m) = ln(Σ tᵢ⁻ᵈ) + semantic_sim + emotional_resonance + noise`
- `score_entries(query, candidate_entries, emotion_vector)` → returns entries with activation scores
- Maintains access log per entry (timestamps of every retrieval) in a separate `activation_log` table in `episodic.db`
- Updates access log on every retrieval (reinforces memory, per ACT-R)
- Scheduled decay computation: runs every hour in background thread, updates stored activation estimates
- `ACTIR_DECAY_RATE`, `ACTIR_NOISE_STD`, floor/ceiling from constants

**The emotional resonance term:**
```
emotional_resonance = cosine_similarity(query_emotion_vector, entry.emotion_vector) × 0.3
```
This is the addition beyond vanilla ACT-R — rewards retrieving memories that were formed in a similar emotional context.

**Edge cases:**
- Entry never accessed → `Σ tᵢ⁻ᵈ = 0` → `ln(0)` undefined → use `ln(epsilon)` where `epsilon = 1e-10`
- All entries near activation floor → re-normalise the batch scores before ranking (don't change stored values)
- Entry has no emotion vector (legacy entry) → emotional_resonance term = 0.0

**Done when:** Unit test with 50 entries, mixed access histories, confirms recently accessed entries rank higher; confirms entries with matching emotion vectors rank higher when emotion vector provided.

---

### Phase 2.2 — EM-LLM Episode Manager (Day 8–9)

**What:** `memory/episode_manager.py`

**What it does:**
- Tracks active conversation in real-time, computing surprise score per message
- `on_message(text, session_id)` → updates rolling embedding mean, computes surprise, may emit episode boundary
- `get_active_context(session_id, query)` → returns the most relevant episodes from current session as context
- Episode boundary creates a new `Episode` object: `{id, start_token_idx, end_token_idx, summary, surprise_score, timestamp}`
- `get_episodes(session_id)` → all episodes for a session
- Context compression: when active session context > 80% of configured context window, calls 3B reflection model (async) to summarise oldest 40% into a compact episode summary. Raw messages still logged to diary.

**Retrieval scoring:**
```
episode_score = 0.70 × cosine_sim(query_embed, episode_embed) 
              + 0.30 × temporal_contiguity_bonus
```
`temporal_contiguity_bonus` is highest for the episode immediately before/after the most relevant episode — this mirrors human memory's associative temporal structure.

**Storage:** Episodes stored in `.stark/sessions/<session_id>_episodes.json` — lightweight, session-scoped, discarded after diary entry written.

**Done when:** Unit test simulates a 40-message conversation with 3 clear topic shifts, verifies 3+ episode boundaries correctly detected.

---

### Phase 2.3 — A-MEM Knowledge Graph (Day 10–12)

**What:** `memory/knowledge_graph.py`

**What it does:**
- NetworkX directed graph where each node is a `KnowledgeNode`: `{id, content, embedding, tags, keywords, links, created_at, version_history}`
- `add_node(content, tags, keywords)` → creates node, auto-generates links to existing nodes above `AMEM_LINK_SIMILARITY_THRESH`
- `update_node(node_id, new_content)` → appends version entry, updates embedding and links, preserves history
- `flag_conflict(node_id_a, node_id_b, reason)` → writes to conflict log, emits notification, does NOT auto-resolve
- `query(text, top_k)` → returns top-K nodes by embedding similarity
- `traverse(seed_node_id, depth=2)` → BFS from seed node, returns neighbourhood
- Persisted to `.stark/knowledge_graph/graph.pkl` (NetworkX pickle) + `.stark/knowledge_graph/embeddings.npy` (NumPy array for fast similarity)
- Rebuild index on load if embeddings file is newer than graph pickle

**Link generation:**
Links are created lazily at node insertion — the new node's embedding is compared to all existing node embeddings in batch (fast NumPy matmul). Links are bidirectional. Link weight = cosine similarity at time of creation.

**Edge cases:**
- Very large graph (>100K nodes) → chunked similarity computation, not full matmul
- Duplicate content → detected by near-identical embedding (sim > 0.95), merge prompt shown to user
- Node with no links → isolated node, valid — will link when related content added later

**Done when:** Unit test adds 30 nodes with known relationships, verifies correct link formation, updates a node and verifies version history, traverses from seed node.

---

## Week 3 — Integration Layer

**Goal:** All components wired together in the main pipeline. Async loops running. Full test coverage.

### Phase 3.1 — Reflection Loop (Day 13–14)

**What:** `memory/reflection_loop.py`

**What it does:**
- Runs as a background thread, monitors `thread_state.py` for conversation-ended signal
- On conversation end: waits `REFLECTION_TRIGGER_DELAY_SEC` seconds, then runs reflection
- Calls the 3B model (via Ollama, separate model from primary LLM) with a structured prompt:
  ```
  Given this conversation summary and episode list, generate:
  1. A concise diary entry (3-5 sentences, what happened, what was learned)
  2. Any tool schema observations (if tools were used)
  3. Any knowledge conflicts detected (contradictions with existing knowledge)
  4. 3-5 topic tags
  Output as JSON only.
  ```
- Parses JSON response, writes to `diary_store`, updates `tool_schema_store`, flags conflicts in `knowledge_graph`
- If 3B model unavailable → rule-based fallback: generates minimal diary entry from conversation metadata only

**Concurrency safety:**
- Reflection loop never accesses VRAM — it uses the 3B model on CPU RAM
- If primary STARK is mid-conversation when reflection tries to run → wait, don't skip
- One reflection job at a time — semaphore prevents queue buildup

**Done when:** Integration test verifies diary entry written within 60 seconds of conversation end; verifies entry contains valid emotion vector; verifies tool observations captured when tool was used.

---

### Phase 3.2 — Tool Schema Store (Day 15)

**What:** `memory/tool_schema_store.py`

**What it does:**
- Stores living tool schemas as versioned JSON in `.stark/tool_schemas/<tool_name>.json`
- `get_schema(tool_name)` → returns current schema with all annotations
- `update_annotation(tool_name, observation, cause)` → appends annotation with timestamp; `cause` in `{tool, self, network, unknown}`
- `decay_confidence(tool_name)` → applies `TOOL_SCHEMA_CONFIDENCE_DECAY` to annotations older than `TOOL_SCHEMA_STALENESS_DAYS` without recent confirmation
- `flag_stale(tool_name)` → marks schema for re-verification when confidence below threshold
- Schema format:
  ```json
  {
    "name": "web_search",
    "version": 3,
    "base_schema": {...},
    "annotations": [
      {"observation": "limit > 20 causes timeout", "confidence": 0.9, "cause": "tool", "timestamp": "...", "observed_count": 3}
    ],
    "success_rate": 0.72,
    "avg_latency_ms": 340,
    "last_verified": "..."
  }
  ```

**Done when:** Unit test creates schema, adds 5 annotations from different causes, applies decay, verifies only `cause: tool` annotations affect success_rate.

---

### Phase 3.3 — Consolidation Job (Day 16)

**What:** `memory/consolidation.py`

**What it does:**
- Runs nightly at `CONSOLIDATION_SCHEDULE` or when `knowledge_graph.conflict_count >= CONSOLIDATION_CONFLICT_THRESH`
- Runs as a separate process (not thread) to avoid GIL during GPU use
- Three jobs in sequence:
  1. **Conflict resolution** — for each flagged conflict, call 7B LLM to generate resolution proposal; emit notification with proposal; gate write on user approval
  2. **Pattern promotion** — scan last 30 diary entries; identify phrases/concepts appearing ≥ `AMEM_PROMOTION_QUORUM` times across ≥ `AMEM_PROMOTION_SESSION_MIN` sessions; for each candidate, emit notification; gate `knowledge_graph.add_node()` on user approval
  3. **Activation decay** — run ACT-R decay update across all diary entries; update stored activation estimates; archive entries below floor to cold storage
- Writes a consolidation report to `.stark/consolidation_logs/<date>.json`

**GPU safety:**
- Checks `.stark/sessions/active_session.lock` before starting
- If active session exists → defer consolidation, retry in 30 minutes
- Releases all GPU memory before process exits

**Done when:** Integration test simulates 15 diary entries with 3 repeated patterns, runs consolidation, verifies 3 promotion notifications emitted; verifies consolidation defers when active session lock present.

---

### Phase 3.4 — Wire into core/main.py (Day 17)

**What:** Extend `STARK.predict()` and `STARK.start()/stop()` to integrate all memory v2 modules.

**Changes to `predict()`:**
```
Step 0: Check MEMORY_V2_ENABLED flag
  if False → existing v0.1.0 path unchanged

Step 1 (new): Get/create session thread state
  state = thread_state.get_or_create_session()

Step 2 (new): Compute appraisal vector
  appraisal = appraisal_engine.compute(query, state.recent_messages)

Step 3 (new): EM-LLM episode update
  episode_manager.on_message(query, state.session_id)

Step 4 (extended): Memory retrieval (replaces old recall)
  diary_candidates = diary_store.query_semantic(query, top_k=20)
  scored_candidates = activation_scorer.score(query, diary_candidates, appraisal)
  graph_context = knowledge_graph.query(query, top_k=5)
  episode_context = episode_manager.get_active_context(state.session_id, query)

Step 5 (extended): Build LLM context
  context = build_context(appraisal, scored_candidates[:5], graph_context, episode_context)

Step 6: Existing generate_response() — unchanged

Step 7 (new): Update thread state
  thread_state.update(state.session_id, query, response, appraisal)
```

**Changes to `start()`:**
- Initialise all memory v2 modules
- Start reflection loop thread
- Schedule consolidation job

**Changes to `stop()`:**
- Signal reflection loop to complete current job then stop
- Checkpoint all thread states
- Save knowledge graph and tool schemas

**Done when:** `pytest tests/ -v` still fully green with `MEMORY_V2_ENABLED=true`; latency test confirms first-token latency ≤ 3 seconds with full memory stack.

---

### Phase 3.5 — Full Test Suite (Day 18–20)

**What:** Write all tests per the testing rules in `STARK_AGENT_RULES.md`.

**Test files to create:**
- `tests/test_appraisal_engine.py`
- `tests/test_diary_store.py`
- `tests/test_activation_scorer.py`
- `tests/test_episode_manager.py`
- `tests/test_knowledge_graph.py`
- `tests/test_reflection_loop.py`
- `tests/test_tool_schema_store.py`
- `tests/test_consolidation.py`
- `tests/test_thread_state.py`
- `tests/test_memory_integration.py` (10-session end-to-end)
- `tests/test_hardware_budget.py` (VRAM + RAM profiling)

**Coverage target:** ≥ 80% on all new modules.

**Done when:** `pytest tests/ -v --cov=memory --cov-report=term` shows ≥ 80% coverage; all tests green.

---

## Completion Checklist

```
[ ] Phase 1.1 — constants + config
[ ] Phase 1.2 — feature flag
[ ] Phase 1.3 — thread state manager
[ ] Phase 1.4 — episodic DB schema migration
[ ] Phase 1.5 — appraisal engine
[ ] Phase 1.6 — diary store
[ ] Phase 2.1 — ACT-R activation scorer
[ ] Phase 2.2 — EM-LLM episode manager
[ ] Phase 2.3 — A-MEM knowledge graph
[ ] Phase 3.1 — reflection loop
[ ] Phase 3.2 — tool schema store
[ ] Phase 3.3 — consolidation job
[ ] Phase 3.4 — core/main.py integration
[ ] Phase 3.5 — full test suite
[ ] pytest tests/ -v ALL GREEN
[ ] hardware budget verified ≤ 6 GB VRAM / ≤ 12 GB RAM
[ ] MEMORY_V2_ENABLED feature flag removed (integration is default)
[ ] README v0.2.0 section written
[ ] docs/v02/ documents committed to repo
```

---

## Appendix — Key File Reference

```
memory/
  appraisal_engine.py     ← Phase 1.5
  thread_state.py         ← Phase 1.3
  diary_store.py          ← Phase 1.6
  activation_scorer.py    ← Phase 2.1
  episode_manager.py      ← Phase 2.2
  knowledge_graph.py      ← Phase 2.3
  reflection_loop.py      ← Phase 3.1
  tool_schema_store.py    ← Phase 3.2
  consolidation.py        ← Phase 3.3
  neuromorphic_memory.py  ← EXISTING, extended in phases 1.4 + 3.4

core/
  constants.py            ← Phase 1.1 (add MEMORY V2 section)
  config.py               ← Phase 1.1 (add MemoryV2Config)
  main.py                 ← Phase 3.4 (extend predict/start/stop)

.stark/
  sessions/               ← thread state files
  knowledge_graph/        ← A-MEM persistence
  tool_schemas/           ← tool schema JSONs
  consolidation_logs/     ← consolidation reports

docs/v02/
  STARK_PRD.md
  STARK_PID.md
  STARK_AGENT_RULES.md
  STARK_PLAN.md           ← this file

openspec/changes/add-neuro-memory-stack/
  proposal.md
  tasks.md
  design.md
  specs/neuromorphic-memory/spec.md
```
