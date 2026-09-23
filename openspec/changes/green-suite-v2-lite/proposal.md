# Change: Green Suite V2 Lite (S8)

## Why
Final gate: prove the KEEP set (diary, thread, Hebbian, reflection) is green
at ≥80% without CUT modules masking the signal.

## What Changes (tests only)
- Keep: `test_diary_store`, `test_thread_state`, `test_neuromorphic`,
  `test_reflection_loop`, `test_episodic_schema`, lite `test_memory_integration`
- Skip CUT tests (appraisal, episode, activation, knowledge_graph,
  consolidation, tool_schema, full v2/integration)

## Impact
- Affected specs: refactor-s8-tests (new)
- Affected code: `tests/` selection only
- Depends on: S0+S2 (env + imports), S1+S3 (flag + pipeline); runs last
