# Module 4: LoRA Adapters Specification

## Overview
Implement Low-Rank Adaptation (LoRA) for task-specific fine-tuning with minimal memory overhead (~5-10MB per adapter).

**Implementation**: `learning/lora_adapter.py`, `learning/adapter_manager.py`  
**Build Time**: 2-3 hours  
**Lines of Code**: ~300

---

## Requirements

### Requirement: LoRA Layer Implementation
The system SHALL implement LoRA layers that can be attached to frozen base model weights.

#### Scenario: Create LoRA adapter
- **WHEN** `create_adapter(task_name)` is called
- **THEN** new LoRA adapter is created for specified task
- **AND** adapter has rank=8, alpha=16 by default

#### Scenario: Low-rank decomposition
- **WHEN** adapter is created
- **THEN** uses matrices A (rank × input) and B (output × rank)
- **AND** effective weight change = alpha/rank * A × B

#### Scenario: Memory footprint
- **WHEN** adapter is loaded
- **THEN** memory usage is ~5-10MB
- **AND** base model remains frozen

---

### Requirement: Adapter Management
The system SHALL manage multiple task-specific adapters efficiently.

#### Scenario: Load adapter
- **WHEN** `load_adapter(task_name)` is called
- **THEN** adapter weights are loaded from disk
- **AND** attached to base model

#### Scenario: Save adapter
- **WHEN** `save_adapter(task_name)` is called
- **THEN** adapter weights are saved to disk
- **AND** file size is ~5-10MB

#### Scenario: Switch adapters
- **WHEN** switching from task A to task B
- **THEN** adapter A is detached
- **AND** adapter B is loaded and attached

#### Scenario: Maximum adapters
- **WHEN** more than MAX_ACTIVE_ADAPTERS (5) are loaded
- **THEN** least recently used adapter is unloaded
- **AND** system continues functioning

---

### Requirement: Multi-Adapter System
The system SHALL support up to 50 adapters on disk with 5 active in memory.

#### Scenario: Adapter discovery
- **WHEN** `list_adapters()` is called
- **THEN** all saved adapters are listed with metadata
- **AND** includes task name, size, last modified

#### Scenario: Adapter routing
- **WHEN** query is classified
- **THEN** appropriate adapter is selected
- **AND** loaded if not already active

#### Scenario: Default adapter
- **WHEN** no task-specific adapter exists
- **THEN** general-purpose adapter is used
- **AND** new adapter can be trained on-the-fly

---

### Requirement: Training Integration
The system SHALL support adapter training with frozen base model.

#### Scenario: Trainable parameters
- **WHEN** adapter is attached
- **THEN** only LoRA parameters are trainable
- **AND** base model gradients are disabled

#### Scenario: Parameter count
- **WHEN** adapter is created
- **THEN** trainable params ≈ 0.01% of base model
- **AND** exact count is logged

#### Scenario: Gradient flow
- **WHEN** backward pass occurs
- **THEN** gradients flow only through LoRA matrices
- **AND** base model is unchanged

---

### Requirement: PEFT Integration
The system SHALL integrate with HuggingFace PEFT library.

#### Scenario: PEFT compatibility
- **WHEN** using PEFT library
- **THEN** standard LoraConfig is used
- **AND** get_peft_model() works correctly

#### Scenario: Target modules
- **WHEN** adapter is created
- **THEN** targets: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- **AND** all specified layers have LoRA attached

---

## Success Criteria

- [x] Create new adapter succeeds
- [x] Load/save adapter works
- [x] Trainable params count correct (~0.01% of base)
- [x] Memory footprint ~5-10MB per adapter
- [x] Multi-adapter routing works
- [x] LRU eviction when limit reached
- [x] PEFT integration verified
- [x] Gradient flow only through LoRA
