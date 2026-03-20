# STARK — Product Requirements Document
**Version:** 0.2.0 — Neuro-Memory Integration  
**Status:** Draft  
**Author:** Sandy (San20506)  
**Date:** 2026-03-20  
**Repo:** github.com/San20506/Stark

---

## 1. Product Vision

STARK (Self-Training Adaptive Reasoning Kernel) is a fully local, privacy-first AI assistant that runs entirely on consumer hardware (RTX 4060 / 24 GB RAM). The v0.2.0 integration upgrades the existing neuromorphic memory stub into a production-grade, four-layer memory system modelled on human cognitive architecture — combining EM-LLM episodic segmentation, ACT-R activation scoring, A-MEM semantic graph storage, and LangGraph-style stateful orchestration.

The result is an assistant that does not merely retrieve — it **remembers**, **forgets naturally**, **connects knowledge associatively**, and **grows more personalised over time** without ever leaving the user's machine.

---

## 2. Background & Current State

### What exists (v0.1.0)
- `memory/neuromorphic_memory.py` — Hebbian node network with synaptic connections, activation spreading, and task-based clustering. **Implemented but not integrated with the four cognitive memory frameworks.**
- `archive/alfred_legacy/memory/neuromorphic_memory.py` — Three-tier hot/warm/cold storage (LRU → SQLite → Parquet) with ChromaDB semantic layer. **Archived but contains reusable patterns.**
- `core/main.py` — Orchestrator that calls `memory.recall()` and `memory.store()` — minimal, no appraisal, no diary, no reflection loop.
- `rag/` — Basic RAG chunker + retriever. **Operates independently, not connected to memory system.**
- `agents/autonomous_orchestrator.py` — Multi-agent routing. **Has no access to long-term memory state.**
- `learning/continual_learner.py` — Background LoRA training thread. **Trains on experiences but does not inform memory retrieval.**

### The gap
The existing codebase has the skeleton of a memory system but none of the four research-backed cognitive frameworks described below. Memory is treated as a flat retrieval store rather than a structured, evolving knowledge graph with temporal dynamics, emotional tagging, and session-boundary awareness.

---

## 3. Target User

Sandy — CSE/IT student, 2nd year, St. Joseph's College of Engineering. Developer running CachyOS (Arch-based) with RTX 4060 Laptop GPU (8 GB VRAM), 24 GB RAM, AMD Ryzen 7. Primary use cases: exam prep, DSA/algorithm study, code debugging, project building (STARK itself), and general daily assistance. All data must remain fully local and private.

---

## 4. Goals

| # | Goal | Metric |
|---|------|--------|
| G1 | Four-layer memory system fully operational | All four frameworks integrated, passing unit tests |
| G2 | Context overflow handled gracefully | No conversation loss beyond context window |
| G3 | Cross-session memory persists correctly | Memory survives restart, loads in <2s |
| G4 | Retrieval respects temporal decay | ACT-R activation scores demonstrably influence ranking |
| G5 | Knowledge graph builds over time | A-MEM nodes link associatively after 10+ sessions |
| G6 | Appraisal engine produces valid emotion vectors | 6-dimensional vector present on every inference call |
| G7 | Reflection loop writes diary entries async | Diary written within 30s of conversation end |
| G8 | Consolidation promotes patterns to semantic memory | Promotion requires quorum of 5 diary entries |
| G9 | All components fit within hardware budget | VRAM ≤ 6 GB, RAM ≤ 12 GB during active use |
| G10 | Response latency to first token ≤ 3 seconds | Measured end-to-end on Ryzen 7 / RTX 4060 |

---

## 5. Non-Goals

- Cloud sync or remote storage of any kind
- Multi-user support
- Replacing the Ollama inference backend
- Fine-tuning or modifying the base LLM weights as part of this integration
- Implementing Layer 3–5 emotion (neural correlates, dynamics, qualia)
- Mobile or web deployment

---

## 6. Functional Requirements

### FR-1: EM-LLM Episodic Segmentation
The system SHALL segment active conversation context into discrete episodes using surprise-based boundary detection.

**Acceptance criteria:**
- Surprise score computed as cosine distance between current token embedding and rolling mean of last N embeddings
- Boundary triggered when surprise > configurable threshold (default: 0.65)
- Episodes stored with start/end token indices, summary, and surprise score
- Retrieval combines semantic similarity (70%) and temporal continuity (30%)
- System handles context overflow by compressing oldest episodes, never truncating raw diary

### FR-2: ACT-R Activation Scoring
The system SHALL score every diary entry using the ACT-R activation formula augmented with emotional salience.

**Acceptance criteria:**
- Base formula: `A(m) = ln(Σ tᵢ⁻ᵈ) + semantic_sim + emotional_resonance + noise`
- Decay parameter d = 0.5 (configurable in constants.py)
- Emotional resonance term sourced from appraisal engine's stored emotion vector
- Activation scores update on every retrieval (access reinforces memory)
- Memories below activation floor (default: -2.0) flagged for consolidation review, never auto-deleted

### FR-3: A-MEM Semantic Knowledge Graph
The system SHALL maintain a Zettelkasten-inspired knowledge graph where every semantic memory node links to related nodes.

**Acceptance criteria:**
- Each node contains: content, embedding, tags, keywords, links (bidirectional), creation timestamp, version history
- New node creation triggers automatic link generation via embedding similarity (threshold: 0.75)
- Node modification appends a version entry — original content never overwritten
- Conflict between nodes flagged for human review, not silently resolved
- Knowledge graph queryable by node, by tag, and by traversal from a seed node

### FR-4: Stateful Agent Loop (LangGraph-pattern)
The system SHALL maintain persistent conversation threads with checkpointing.

**Acceptance criteria:**
- Each conversation assigned a unique thread ID
- State checkpointed after every exchange (not just on shutdown)
- Crash recovery restores to last checkpoint within 5 seconds
- Short-term message history separated from long-term memory stores
- Thread state includes: messages, current emotion vector, active tool schemas, retrieved memory IDs

### FR-5: Appraisal Engine
The system SHALL compute a 6-dimensional appraisal vector for every user input.

**Acceptance criteria:**
- Dimensions: novelty, valence, agency, coping, certainty, goal_relevance (all float, ranges documented in constants.py)
- Computed from: semantic distance, sentiment analysis, entity attribution, task complexity estimate
- Smoothing window of N=5 inputs prevents single-message destabilisation
- Appraisal vector stored with every diary entry
- Appraisal vector injected into LLM context as structured prefix

### FR-6: Diary Memory
The system SHALL maintain an append-only episodic diary.

**Acceptance criteria:**
- Every conversation produces exactly one diary entry on reflection
- Entry schema: timestamp, session_id, summary, raw_episode_ids, emotion_vector, tool_schemas_touched, insights, tags
- Diary stored in SQLite (reusing existing `data/memory/episodic.db` schema, extended)
- Entries never deleted — only activation scores change
- Diary searchable by semantic similarity, time range, emotion range, and tag

### FR-7: Reflection Loop
The system SHALL run an asynchronous reflection process after every conversation.

**Acceptance criteria:**
- Triggered ≤ 30 seconds after last message in a conversation
- Uses the 3B reflection model (CPU, system RAM) — does not compete with primary LLM for VRAM
- Produces: 1 diary entry, 0–N tool schema deltas, 0–N knowledge conflict flags
- Runs as a background thread, never blocking the main inference path
- Reflection model configurable in config.yaml

### FR-8: Consolidation
The system SHALL periodically distill diary patterns into the semantic knowledge graph.

**Acceptance criteria:**
- Runs nightly (configurable) or when conflict flags exceed threshold (default: 10)
- Pattern promotion requires quorum: ≥5 diary entries, ≥3 distinct sessions
- Promotions surface as human-readable notifications before being written
- User can approve, reject, or modify a promoted pattern
- Raw diary entries always preserved regardless of promotion outcome

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | First token latency ≤ 3s; memory retrieval ≤ 100ms |
| VRAM | Active inference ≤ 6 GB (leaves 2 GB headroom on 8 GB card) |
| System RAM | Full system ≤ 12 GB (leaves ~12 GB for OS, gaming, video editing) |
| Storage | Diary growth ≤ 200 MB/year; semantic graph ≤ 1 GB total |
| Privacy | Zero network calls from memory subsystem; all embeddings computed locally |
| Reliability | Crash recovery to last checkpoint; no memory corruption on unclean exit |
| Testability | Every memory subsystem independently testable without LLM running |
| Code style | PEP 8, 100-char line limit, type hints everywhere, Google-style docstrings (per project.md) |

---

## 8. Integration Points with Existing Codebase

| Existing module | Integration action |
|---|---|
| `memory/neuromorphic_memory.py` | Extend — add ACT-R activation scoring, appraisal tagging, diary write-back |
| `data/memory/episodic.db` | Extend schema — add emotion_vector, session_id, episode_boundaries columns |
| `core/main.py` | Extend `predict()` — inject appraisal vector, pass thread state, trigger async reflection |
| `rag/retriever.py` | Extend — add A-MEM graph traversal alongside vector similarity |
| `learning/continual_learner.py` | Connect — diary entries feed training corpus; consolidation output informs adapter selection |
| `core/constants.py` | Add — all new thresholds, decay params, model paths following zero-hardcoding rule |
| `core/config.py` | Add — reflection model config, consolidation schedule, appraisal weights |
| `agents/autonomous_orchestrator.py` | Extend — pass memory context and emotion state to agent loop |
| `archive/alfred_legacy/memory/` | Reference only — extract hot/warm/cold tiering patterns, do not import directly |

---

## 9. Out of Scope for v0.2.0

- Voice interface changes
- Health monitoring changes
- Web server changes
- New LoRA adapter types
- MCP server/client changes

---

## 10. Success Definition

v0.2.0 is complete when:
1. All 8 functional requirements pass their acceptance criteria
2. A 10-session integration test demonstrates memory persisting, retrieving, and growing correctly
3. Hardware budget (G9) verified with `utils/profiler.py`
4. All new modules have >80% test coverage in `tests/`
5. `openspec validate --strict` passes on all new change proposals
