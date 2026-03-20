# STARK — Project Initiation Document
**Version:** 0.2.0 — Neuro-Memory Integration  
**Status:** Initiated  
**Date:** 2026-03-20  
**Owner:** Sandy (San20506)

---

## 1. Project Identity

| Field | Value |
|---|---|
| Project name | STARK Neuro-Memory Integration |
| Change ID (openspec) | `add-neuro-memory-stack` |
| Parent project | STARK v0.1.0 (github.com/San20506/Stark) |
| Type | Integration — no new base model, extending existing architecture |
| Hardware target | RTX 4060 Laptop 8 GB / AMD Ryzen 7 / 24 GB RAM / CachyOS |
| Timeline | 3 weeks from initiation |
| Priority | P0 — core differentiator of STARK vs generic chatbot |

---

## 2. Problem Statement

STARK v0.1.0 has a working inference pipeline, task detection, and a neuromorphic memory stub. However, the memory system treats every conversation as isolated — there is no cross-session continuity, no temporal dynamics, no emotional context, and no growing knowledge graph. Without this, STARK cannot deliver the core promise of being a personalised assistant that improves over time.

The four research frameworks identified (EM-LLM, ACT-R, A-MEM, LangGraph) collectively solve all the missing pieces. This project integrates them.

---

## 3. Scope

### In scope
- EM-LLM episodic segmentation layer (within-session context manager)
- ACT-R activation scoring for diary retrieval (cross-session temporal decay)
- A-MEM Zettelkasten semantic knowledge graph (long-term distilled knowledge)
- LangGraph-pattern stateful agent loop with thread persistence and checkpointing
- Appraisal engine (Layer 1 + 2 emotion — behavioural signals + appraisal structure)
- Diary memory (append-only episodic store, extended `episodic.db`)
- Reflection loop (async, post-conversation, 3B model on CPU)
- Consolidation job (nightly or threshold-triggered)
- Tool learning engine (living schema with annotated delta history)
- Integration with existing `core/main.py`, `memory/neuromorphic_memory.py`, `rag/retriever.py`

### Out of scope
- Base model changes (Qwen3-8B stays)
- Voice interface changes
- New LoRA adapter training
- MCP server/client changes
- Any UI changes

---

## 4. Deliverables

| # | Deliverable | Location | Format |
|---|---|---|---|
| D1 | PRD | `docs/v02/STARK_PRD.md` | Markdown |
| D2 | PID (this doc) | `docs/v02/STARK_PID.md` | Markdown |
| D3 | Agent Rules | `docs/v02/STARK_AGENT_RULES.md` | Markdown |
| D4 | Integration Plan | `docs/v02/STARK_PLAN.md` | Markdown |
| D5 | OpenSpec change proposal | `openspec/changes/add-neuro-memory-stack/` | OpenSpec format |
| D6 | Appraisal engine module | `memory/appraisal_engine.py` | Python |
| D7 | EM-LLM episode manager | `memory/episode_manager.py` | Python |
| D8 | ACT-R retrieval scorer | `memory/activation_scorer.py` | Python |
| D9 | A-MEM knowledge graph | `memory/knowledge_graph.py` | Python |
| D10 | Diary memory store | `memory/diary_store.py` | Python |
| D11 | Reflection loop | `memory/reflection_loop.py` | Python |
| D12 | Consolidation job | `memory/consolidation.py` | Python |
| D13 | Tool schema store | `memory/tool_schema_store.py` | Python |
| D14 | Thread state manager | `memory/thread_state.py` | Python |
| D15 | Updated `core/main.py` | `core/main.py` | Python (modified) |
| D16 | Updated constants/config | `core/constants.py`, `core/config.py` | Python (modified) |
| D17 | Test suite | `tests/test_memory_v2.py` | Python |
| D18 | Integration test | `tests/test_memory_integration.py` | Python |

---

## 5. Technical Architecture — Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    STARK v0.2.0 MEMORY STACK                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PERCEPTION                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  user input → signal extraction → appraisal_engine.py   │    │
│  │  outputs: appraisal_vector (6D float)                    │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             ↓                                     │
│  WORKING CONTEXT                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  thread_state.py — session thread + checkpoint           │    │
│  │  episode_manager.py — EM-LLM segmentation + retrieval   │    │
│  │  inputs: appraisal_vector + retrieved memories + tools   │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             ↓                                     │
│  LONG-TERM MEMORY (three parallel stores)                         │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐    │
│  │ diary_store  │  │ activation_    │  │ knowledge_graph  │    │
│  │ .py          │  │ scorer.py      │  │ .py (A-MEM)      │    │
│  │ append-only  │  │ ACT-R formula  │  │ Zettelkasten     │    │
│  │ episodic log │  │ retrieval rank │  │ semantic graph   │    │
│  └──────┬───────┘  └───────┬────────┘  └────────┬─────────┘    │
│         └──────────────────┴──────────────────────┘              │
│                             ↓                                     │
│  INFERENCE                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  core/main.py — STARK.predict() (extended)              │    │
│  │  LLM context = system_prompt + appraisal + memories     │    │
│  │               + tool_schemas + conversation_history      │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             ↓                                     │
│  ASYNC REFLECTION (post-conversation)                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  reflection_loop.py — 3B model, CPU, ≤30s after end     │    │
│  │  writes diary entry, updates tool schemas, flags KB      │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             ↓                                     │
│  NIGHTLY CONSOLIDATION                                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  consolidation.py — 7B model, GPU, nightly/on-threshold  │    │
│  │  promotes diary patterns → knowledge_graph with quorum   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Resource Budget

| Resource | Budget | Allocation |
|---|---|---|
| VRAM (active inference) | 6.0 GB | LLM weights: 3.8 GB, KV cache: 1.1 GB, embeddings: 0.7 GB, buffer: 0.4 GB |
| VRAM (consolidation, offline) | 5.0 GB | 7B model Q4 during consolidation window only |
| System RAM (active) | 11.5 GB | LLM CPU offload: 0, diary DB: 2 GB, semantic graph: 1 GB, reflection model: 1.8 GB, OS: 4 GB, tools: 0.5 GB, misc: 2.2 GB |
| CPU (idle, background) | ~14% | Reflection loop, ACT-R scoring, A-MEM indexing |
| Storage | ~8 GB | Models: 5.6 GB, diary: 0.2 GB/yr, graph: 1 GB, tool schemas: 0.1 GB |

---

## 7. Dependencies

### New Python packages (to add to requirements.txt)
| Package | Purpose | Replaces/extends |
|---|---|---|
| `chromadb>=0.4.0` | Vector store for diary + semantic graph | Already commented out in requirements.txt — uncomment |
| `langgraph>=0.1.0` | Stateful agent loop with thread persistence | New |
| `langchain-core>=0.1.0` | Shared primitives for LangGraph | New |
| `networkx>=3.0` | Knowledge graph traversal for A-MEM | New |

### Existing packages already present
- `sentence-transformers` — embeddings for diary + semantic similarity
- `numpy` — activation spreading, decay calculations  
- `sqlite3` — episodic diary storage (stdlib)
- `threading` — reflection loop, already used in continual_learner

### No new external services
Everything runs locally. No API keys, no cloud, no network calls from memory subsystem.

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| VRAM overflow during consolidation + inference overlap | Medium | High | Consolidation only runs when no active conversation detected; mutex lock on GPU |
| Diary grows unboundedly on disk | Low | Medium | Soft cap at 10 GB triggers archival to cold Parquet storage (from alfred_legacy pattern) |
| ACT-R activation scores diverge (all memories either max or min) | Low | Medium | Clip scores to [-3.0, 3.0]; periodic re-normalisation in consolidation |
| Knowledge graph develops false links from noisy embeddings | Medium | Medium | Link threshold 0.75 (conservative); human approval on consolidation promotions |
| Reflection loop's 3B model produces low-quality diary entries | Medium | Medium | Diary quality review in consolidation; bad entries detectable by low semantic coherence |
| LangGraph thread state file corruption on crash | Low | High | SQLite WAL mode for thread state; checkpoint before every write |
| Integration breaks existing `core/main.py` predict() pipeline | Medium | High | Feature flag: `MEMORY_V2_ENABLED=false` defaults to v0.1.0 path until all tests pass |

---

## 9. Timeline

| Week | Focus | Key milestones |
|---|---|---|
| Week 1 | Foundation | Appraisal engine, diary store, thread state, constants/config updates |
| Week 2 | Memory layers | EM-LLM episode manager, ACT-R activation scorer, A-MEM knowledge graph |
| Week 3 | Integration + async | Reflection loop, consolidation, tool schema store, integrate into core/main.py, full test suite |

Each week ends with `openspec validate --strict` passing and a smoke test confirming no regression on existing `tests/` suite.

---

## 10. Definition of Done

- [ ] All 18 deliverables complete
- [ ] All 8 functional requirements from PRD pass acceptance criteria  
- [ ] Hardware budget verified via `utils/profiler.py`
- [ ] Existing test suite (`pytest tests/ -v`) still fully green
- [ ] New test suite coverage ≥ 80%
- [ ] `openspec validate add-neuro-memory-stack --strict` passes
- [ ] 10-session integration test demonstrates memory continuity
- [ ] README updated with v0.2.0 architecture section
- [ ] `FEATURE_FLAG: MEMORY_V2_ENABLED` removed (integration is default)
