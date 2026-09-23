## 1. Quarantine Learning
- [x] 1.1 Delete `learning/` and stub `core/main.py:275-286` with `learning_active=False` degrade

## 2. Quarantine RAG
- [x] 2.1 Delete `rag/` and lazy import in `agents/specialists.py:61`
- [x] 2.2 Confirm single `query_semantic()` lives in diary

## 3. Verify
- [x] 3.1 `grep -r "from learning\|from rag" core/ stark_cli.py` returns empty
- [x] 3.2 No `torch`/`peft`/`chromadb` import from entry files
