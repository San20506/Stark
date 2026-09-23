# Change: Quarantine Learning + RAG (S4)

## Why
`learning/` (torch/PEFT/bitsandbytes, ~1700 lines) is a PRD §5 non-goal that
"does not inform retrieval", and `rag/` duplicates `diary_store.query_semantic`.
Both are fully isolated (lazy imports only).

## What Changes
- Remove `learning/` + stub block `core/main.py:275-286` (degrade to `learning_active=False`)
- Remove `rag/` + lazy call in `agents/specialists.py:61`
- Fold one `query_semantic()` into diary

## Impact
- Affected specs: refactor-s4-learnrag (new)
- Affected code: `learning/`, `rag/`, two call sites above
- Must not touch: diary, thread_state, reflection, `predict()` pipeline
