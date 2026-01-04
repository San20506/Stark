# Module 9: Utilities Specification

## Overview
System management utilities for logging, checkpointing, metrics tracking, and performance profiling.

**Implementation**: `utils/logger.py`, `utils/checkpoint.py`, `utils/metrics.py`, `utils/profiler.py`  
**Build Time**: 2 hours  
**Lines of Code**: ~300

---

## Requirements

### Requirement: Structured Logging
The system SHALL provide consistent, structured logging across all modules.

#### Scenario: Logger configuration
- **WHEN** logging is initialized
- **THEN** format includes timestamp, module, level, message
- **AND** configurable via LOG_LEVEL

#### Scenario: File logging
- **WHEN** LOG_TO_FILE is enabled
- **THEN** logs are written to logs/ directory
- **AND** files rotate at 10MB

#### Scenario: Log levels
- **WHEN** logging at different levels
- **THEN** DEBUG, INFO, WARNING, ERROR, CRITICAL work
- **AND** filtering respects configured level

#### Scenario: Module-specific loggers
- **WHEN** module creates logger
- **THEN** `logger = logging.getLogger(__name__)` pattern
- **AND** logger inherits root configuration

---

### Requirement: Checkpointing
The system SHALL save and restore complete system state.

#### Scenario: Save checkpoint
- **WHEN** `save_checkpoint()` is called
- **THEN** save all adapter weights
- **AND** save optimizer states
- **AND** save experience buffer state

#### Scenario: Load checkpoint
- **WHEN** `load_checkpoint()` is called
- **THEN** restore all saved state
- **AND** system continues from saved point

#### Scenario: Atomic saves
- **WHEN** checkpoint is being saved
- **THEN** write to temp file first
- **AND** rename only on success (atomic)

#### Scenario: Checkpoint versioning
- **WHEN** multiple checkpoints exist
- **THEN** keep last N checkpoints
- **AND** delete older ones

---

### Requirement: Metrics Tracking
The system SHALL track and expose key performance metrics.

#### Scenario: Tracked metrics
- **WHEN** metrics are recorded
- **THEN** track all TRACKED_METRICS:
  - inference_latency_ms
  - training_loss
  - vram_usage_mb
  - experiences_count
  - active_adapters
  - task_accuracy

#### Scenario: TensorBoard integration
- **WHEN** TENSORBOARD_ENABLED is true
- **THEN** metrics are logged to TensorBoard
- **AND** viewable via tensorboard --logdir logs/

#### Scenario: Metrics aggregation
- **WHEN** metrics are queried
- **THEN** provide mean, min, max, p50, p99
- **AND** for configurable time windows

#### Scenario: Metric flush interval
- **WHEN** running continuously
- **THEN** flush metrics every 30 seconds
- **AND** persist for analysis

---

### Requirement: Performance Profiling
The system SHALL provide tools for performance analysis.

#### Scenario: Memory profiling
- **WHEN** `profile_memory()` is called
- **THEN** report VRAM usage breakdown
- **AND** report system RAM usage

#### Scenario: Latency profiling
- **WHEN** `profile_latency()` is called
- **THEN** measure each pipeline stage
- **AND** identify bottlenecks

#### Scenario: GPU utilization
- **WHEN** profiling GPU
- **THEN** report compute utilization
- **AND** report memory bandwidth

#### Scenario: Profiling decorators
- **WHEN** function is decorated with @profile
- **THEN** automatically log timing
- **AND** aggregate for analysis

---

### Requirement: Memory Management
The system SHALL manage memory proactively.

#### Scenario: VRAM monitoring
- **WHEN** VRAM exceeds threshold (7.5GB)
- **THEN** trigger cleanup
- **AND** unload unused adapters

#### Scenario: Garbage collection
- **WHEN** memory pressure detected
- **THEN** force garbage collection
- **AND** clear CUDA cache

#### Scenario: Memory alerts
- **WHEN** memory is critical
- **THEN** log warning
- **AND** prevent OOM errors

---

## Success Criteria

- [x] Logging configured and working
- [x] Log files rotate correctly
- [x] Checkpoints save/load correctly
- [x] Atomic checkpoint saves work
- [x] Metrics are tracked
- [x] TensorBoard integration works
- [x] Memory profiling shows expected usage
- [x] Latency profiling identifies stages
