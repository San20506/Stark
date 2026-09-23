# Change: Isolate Memory Keep-Set (S2)

## Why
`memory/__init__.py:2-16` eagerly imports all CUT modules plus
`sentence_transformers` (via `neuromorphic_memory.py:19`), so one missing dep
poisons every memory import. `neuromorphic_memory.py:24-25` top-level imports
CUT modules `ActivationScorer` and `EpisodeManager`.

## What Changes
- Make `memory/__init__.py` lazy so KEEP modules import standalone
- Lazy-guard `SentenceTransformer` and move CUT imports inside `recall_v2`/`__init__`
- KEEP = `diary_store`, `thread_state`, `neuromorphic_memory`, `reflection_loop`

## Impact
- Affected specs: refactor-s2-memkeep (new)
- Affected code: `memory/__init__.py`, `memory/neuromorphic_memory.py` import block only
- Must not touch: CUT module bodies, `core/main.py`
