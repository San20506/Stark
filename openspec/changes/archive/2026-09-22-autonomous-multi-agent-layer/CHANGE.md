# OpenSpec Change: Autonomous Multi-Agent Router-Arbiter Layer

**Change ID:** `autonomous-multi-agent-layer`  
**Status:** Proposed  
**Created:** 2025-12-30  
**Author:** AI Assistant  
**Type:** Feature Addition

---

## Summary

Implement hierarchical multi-agent routing with Router-Arbiter architecture for autonomous query processing. This adds intelligent path selection (Fast/Deep/Both) with specialized agent clusters for low-latency and deep-reasoning workflows.

---

## Motivation

Current STARK uses simple task detection → single model inference. This lacks:
- **Adaptive complexity handling**: Simple queries waste thinking model capacity
- **Multi-agent coordination**: No agent collaboration for complex tasks
- **Response quality selection**: No mechanism to choose best answer from multiple sources

The Router-Arbiter architecture enables:
- **Sparse routing**: Only activate agents needed for the query
- **Parallel processing**: Fast answers while deep analysis continues
- **Quality arbitration**: Select best response from multiple candidates

---

## Proposed Changes

### Architecture

```
User Query
    ↓
RouterAgent (path selection)
    ↓
├─→ Fast Path (Retriever + FastAnswer - llama3.2:3b)
└─→ Deep Path (Planner + Tools + Reasoner - qwen3:4b)
    ↓
ArbiterAgent (best answer selection)
    ↓
Final Response
```

### New Components

#### 1. **RouterAgent** (`agents/router_agent.py`)
- Uses `AdaptiveRouter` for intelligent path selection
- Returns: `fast`, `deep`, or `both`
- Triggers:
  - Fast: greetings, factual Q&A, high-confidence queries
  - Deep: code generation, planning, analysis, debugging
  - Both: Medium confidence or critical queries

#### 2. **Specialist Agents** (`agents/specialists.py`)
- **RetrieverAgent**: RAG-based document retrieval
- **FastAnswerAgent**: Quick responses using llama3.2:3b
- **PlannerAgent**: Task decomposition using qwen3:4b
- **ArbiterAgent**: Response selection by confidence

#### 3. **AutonomousOrchestrator** (`agents/autonomous_orchestrator.py`)
- Implements Router → Paths → Arbiter flow
- Manages agent lifecycle and coordination
- Returns structured response with metadata

### Integration Points

**Core Integration** (`core/main.py`):
```python
# Option 1: Replace predict() entirely
def predict(self, query: str) -> PredictionResult:
    from agents.autonomous_orchestrator import get_autonomous_orchestrator
    orchestrator = get_autonomous_orchestrator()
    return orchestrator.predict(query)

# Option 2: Hybrid (use autonomous for complex queries)
def predict(self, query: str) -> PredictionResult:
    if self._should_use_autonomous(query):
        return self._autonomous_predict(query)
    else:
        return self._simple_predict(query)  # Current flow
```

### File Changes

| File | Type | Lines | Description |
|------|------|-------|-------------|
| `agents/router_agent.py` | NEW | ~160 | Path selection logic |
| `agents/specialists.py` | NEW | ~400 | Specialist agent implementations |
| `agents/autonomous_orchestrator.py` | NEW | ~250 | Autonomous flow orchestration |
| `agents/__init__.py` | MODIFY | +10 | Export new agents |
| `core/main.py` | MODIFY | ~20 | Integration option |

**Total**: ~810 new lines

---

## Benefits

### Performance
- **Fast responses**: Simple queries → 200-500ms (llama3.2:3b only)
- **Deep analysis**: Complex queries → 2-5s (full planning + reasoning)
- **Parallel processing**: Show fast answer immediately, refine with deep path

### Quality
- **Better answers**: Arbiter selects highest-confidence response
- **Context-aware**: RAG retrieval for grounded responses
- **Task-appropriate**: Right model for the job (3B vs 4B)

### Scalability
- **Sparse activation**: Only run agents needed for query
- **Extensible**: Easy to add new specialist agents
- **Hierarchical**: Clear separation of concerns

---

## Risks & Mitigation

### Risk 1: Increased Latency
- **Concern**: Routing overhead adds latency
- **Mitigation**: RouterAgent uses cached AdaptiveRouter (<50ms overhead)

### Risk 2: Complex Debugging
- **Concern**: Multi-agent flows harder to debug
- **Mitigation**: Comprehensive logging, stats tracking, test suite

### Risk 3: Memory Usage
- **Concern**: Multiple agents in memory
- **Mitigation**: Lazy loading, singleton pattern, ~100MB total overhead

---

## Testing Strategy

### Unit Tests (`tests/phase4/test_autonomous_routing.py`)
- RouterAgent path selection logic
- Specialist agent execution
- Arbiter selection algorithm

### Integration Tests (`tests/phase4/test_autonomous_integration.py`)
- End-to-end fast path flow
- End-to-end deep path flow
- Both paths + arbiter selection

### Manual Verification
- Latency benchmarks (fast vs deep)
- Response quality comparison
- CLI live demo

---

## Migration Plan

### Phase 1: Parallel Deployment
- Keep current `predict()` as default
- Add `autonomous_predict()` as optional flag
- Collect metrics on both approaches

### Phase 2: A/B Testing
- Route 50% queries to autonomous system
- Compare latency and quality
- Iterate on routing logic

### Phase 3: Full Migration
- Replace `predict()` with autonomous flow
- Remove old simple flow
- Update documentation

---

## Future Extensions

### Short-term
- **Tool execution**: Connect PlannerAgent to FileAgent, Automation
- **Deep reasoning**: Add multi-step execution loop
- **Streaming**: Show fast answer, then refined answer

### Long-term
- **Code generation**: CodeAgent in deep path
- **Web research**: WebAgent for fact-checking
- **Multi-modal**: Vision agents for image analysis

---

## Dependencies

- Existing: `AdaptiveRouter`, `AgentOrchestrator`, `RAG system`
- New: None (uses existing infrastructure)

---

## Rollback Plan

1. Set environment variable: `STARK_USE_AUTONOMOUS=false`
2. Revert to simple `predict()` flow
3. No data migration needed (stateless)

---

## Success Criteria

- ✅ Fast queries: <500ms latency
- ✅ Deep queries: High-quality responses
- ✅ 90%+ routing accuracy
- ✅ All tests passing
- ✅ No regression in memory usage

---

## Approval

- [ ] Technical review
- [ ] Performance validation
- [ ] User acceptance testing

---

**Next Steps**: Approve → Implement integration → Test → Deploy
