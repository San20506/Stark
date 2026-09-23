## ADDED Requirements

### Requirement: Minimal V2 Hot Path
The v2 inference path SHALL use diary recall plus recent session messages only,
with no appraisal, episode, graph, consolidation, or tool-schema calls.

#### Scenario: Pre-context build
- **WHEN** `predict()` runs with v2 enabled
- **THEN** `_run_v2_pipeline` returns diary top-K plus last 4 session messages

#### Scenario: Post-state update
- **WHEN** a response completes
- **THEN** `_update_v2_state` checkpoints thread state and triggers reflection only
