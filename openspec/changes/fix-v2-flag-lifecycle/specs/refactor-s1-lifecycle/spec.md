## ADDED Requirements

### Requirement: Runtime V2 Flag
The system SHALL gate the v2 path on `self.config.memory_v2.enabled`
(honoring `STARK_MEMORY_V2_ENABLED`) instead of the frozen constant import.

#### Scenario: Env enables v2
- **WHEN** `STARK_MEMORY_V2_ENABLED=true` is set
- **THEN** `predict()` takes the v2 pre/post pipeline branches

### Requirement: Managed Async Lifecycle
The system SHALL start the reflection loop on `start()` and drain plus persist
all memory state on `stop()`.

#### Scenario: Graceful shutdown
- **WHEN** `stop()` is called after a session
- **THEN** reflection drains, thread states checkpoint, graph and schemas persist
