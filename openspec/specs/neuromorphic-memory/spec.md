# Neuromorphic Memory Specification

## Overview
Distributed, brain-inspired memory system that replaces simple Experience Replay with associative, decaying memory networks.

**Implementation**: `memory/neuromorphic_memory.py`  
**Replaces**: Module 3 (Experience Replay) - enhanced version

---

## Requirements

### Requirement: Memory Node Structure
The system SHALL organize memories as interconnected nodes with synaptic weights.

#### Scenario: Create memory node
- **WHEN** experience is stored
- **THEN** create node with embedding, content, and connections
- **AND** initialize activation level

#### Scenario: Memory structure
- **WHEN** node is created
- **THEN** include: content, embedding, activation, decay_rate, connections
- **AND** timestamp for age tracking

---

### Requirement: Synaptic Connections
The system SHALL form weighted connections between related memories.

#### Scenario: Connection formation
- **WHEN** new memory is similar to existing
- **THEN** create bidirectional connection
- **AND** weight by similarity score

#### Scenario: Connection strengthening
- **WHEN** connected memories are co-activated
- **THEN** increase connection weight (Hebbian learning)
- **AND** cap at maximum weight

#### Scenario: Connection pruning
- **WHEN** connection weight falls below threshold
- **THEN** remove connection
- **AND** free resources

---

### Requirement: Activation Spreading
The system SHALL spread activation through network for associative recall.

#### Scenario: Query activation
- **WHEN** query is made
- **THEN** activate matching nodes
- **AND** spread activation to connected nodes

#### Scenario: Activation decay
- **WHEN** time passes without access
- **THEN** activation decays exponentially
- **AND** eventually reaches baseline

#### Scenario: Retrieval by activation
- **WHEN** retrieving memories
- **THEN** return nodes above activation threshold
- **AND** rank by activation level

---

### Requirement: Memory Decay
The system SHALL naturally forget unimportant memories.

#### Scenario: Importance-weighted decay
- **WHEN** memory ages
- **THEN** decay rate depends on importance
- **AND** frequently accessed memories decay slower

#### Scenario: Consolidation
- **WHEN** memory is accessed multiple times
- **THEN** reduce decay rate
- **AND** strengthen connections

#### Scenario: Garbage collection
- **WHEN** memory activation below threshold
- **THEN** mark for removal
- **AND** clean up periodically

---

### Requirement: Task-Based Clustering
The system SHALL cluster memories by task for efficient retrieval.

#### Scenario: Task indexing
- **WHEN** memory is stored with task
- **THEN** add to task cluster
- **AND** connect to task hub node

#### Scenario: Task-based retrieval
- **WHEN** querying for task-specific memories
- **THEN** start activation from task hub
- **AND** spread to related memories

---

### Requirement: Persistence
The system SHALL save and restore the memory network.

#### Scenario: Save network
- **WHEN** checkpoint requested
- **THEN** serialize nodes, connections, and activations
- **AND** preserve network topology

#### Scenario: Load network
- **WHEN** starting from checkpoint
- **THEN** restore full network state
- **AND** resume decay timers

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   NEUROMORPHIC MEMORY                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Memory   │◄──►│ Memory   │◄──►│ Memory   │              │
│  │ Node 1   │    │ Node 2   │    │ Node 3   │              │
│  │ (code)   │    │ (debug)  │    │ (plan)   │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │                      │
│       └───────────────┼───────────────┘                      │
│                       │                                      │
│                       ▼                                      │
│               ┌──────────────┐                              │
│               │  Task Hub    │                              │
│               │  (research)  │                              │
│               └──────────────┘                              │
│                                                              │
│  Activation spreads through connections                      │
│  Decay affects inactive nodes                                │
│  Hebbian learning strengthens used paths                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

- [x] Memory nodes created with proper structure
- [x] Connections form between related memories
- [x] Activation spreads through network
- [x] Inactive memories decay over time
- [x] Frequently accessed memories persist
- [x] Task-based clustering works
- [x] Network can be saved/loaded
- [x] Memory usage stays bounded
