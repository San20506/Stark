## ADDED Requirements

### Requirement: Standalone Keep-Set Imports
KEEP memory modules SHALL import without pulling CUT modules or hard
third-party deps at module top level.

#### Scenario: Diary imports cleanly
- **WHEN** `sentence_transformers` is absent
- **THEN** `import memory.diary_store`, `memory.thread_state`, and `memory.reflection_loop` succeed

#### Scenario: Neuromorphic degrades gracefully
- **WHEN** the encoder package is missing
- **THEN** `memory.neuromorphic_memory` imports and degrades instead of raising
