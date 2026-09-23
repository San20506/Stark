## 1. Break Import Cascade
- [x] 1.1 Convert `memory/__init__.py` eager exports to lazy `__getattr__`
- [x] 1.2 Lazy-guard `from sentence_transformers import SentenceTransformer`
- [x] 1.3 Move `ActivationScorer`/`EpisodeManager` imports inside `recall_v2`/`__init__`

## 2. Verify
- [ ] 2.1 `import memory.diary_store`, `thread_state`, `reflection_loop` succeed without `sentence_transformers`
- [ ] 2.2 `tests/test_diary_store.py`, `test_thread_state.py`, `test_reflection_loop.py` collect
