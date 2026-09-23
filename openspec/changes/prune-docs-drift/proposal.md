# Change: Prune Docs Drift (S7)

## Why
Docs prescribe what S6 deletes and what code no longer does: 2GB GloVe
download vs 80MB MiniLM reality, `networkx` install for a hand-rolled graph,
and `qwen2.5:3b` vs `qwen3:4b/llama3.2:3b` tag mismatch.

## What Changes (docs only, strictly after S6)
- `STATUS.md:26-27,71-86`: drop NetworkX + "11/12 blocked" claims
- `README.md:192-202`: MiniLM 80MB replaces GloVe 2GB block
- Reconcile `REFLECTION_MODEL_NAME` tag across constants/config/docs

## Impact
- Affected specs: refactor-s7-docs (new)
- Affected code: none (`*.py` untouched)
- Depends on: S6 (must run after S6 completes)
