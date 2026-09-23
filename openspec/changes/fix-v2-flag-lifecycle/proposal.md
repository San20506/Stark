# Change: Fix V2 Flag + Lifecycle (S1)

## Why
`core/main.py:25,304` reads frozen `MEMORY_V2_ENABLED=False` from constants,
so `STARK_MEMORY_V2_ENABLED=true` is a no-op. `start()` never launches the
reflection loop or consolidation; `stop()` never drains reflection or persists
graph/schemas.

## What Changes
- Read `self.config.memory_v2.enabled` (`core/config.py:224,320`) in `predict()` guards
- `start()/start_async()` launches reflection loop + schedules consolidation
- `stop()` drains reflection, checkpoints thread state, persists graph + schemas

## Impact
- Affected specs: refactor-s1-lifecycle (new)
- Affected code: `core/main.py:109-254` lifecycle + flag reads at `:304,457,532,545,553`
- Must not touch: `256-323` loader, `325-406` v2 loader, `684-794` pipeline bodies
