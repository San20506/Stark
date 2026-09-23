## 1. Flag Wiring
- [x] 1.1 Replace frozen `MEMORY_V2_ENABLED` reads with `self.config.memory_v2.enabled`
- [x] 1.2 Keep `core/constants.py:118` default `False` (R6: no default flip without approval)

## 2. Lifecycle Glue
- [x] 2.1 `start()` inits v2 modules, starts reflection loop, schedules consolidation
- [x] 2.2 `stop()` drains reflection, checkpoints sessions, persists graph + schemas

## 3. Verify
- [x] 3.1 `STARK_MEMORY_V2_ENABLED=true` enables the v2 path end-to-end
- [x] 3.2 Clean shutdown persists state with no data loss
