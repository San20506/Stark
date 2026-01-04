# Module 6: Task Detection Specification

## Overview
Classify incoming queries into task categories for appropriate adapter routing and capability module selection.

**Implementation**: `capabilities/task_detector.py`  
**Build Time**: 1 hour  
**Lines of Code**: ~150

---

## Requirements

### Requirement: Query Classification
The system SHALL classify queries into predefined task categories.

#### Scenario: Known task detection
- **WHEN** query matches known task pattern
- **THEN** return task category with confidence score
- **AND** confidence > TASK_DETECTION_THRESHOLD (0.65)

#### Scenario: Unknown task handling
- **WHEN** no task matches above threshold
- **THEN** return "unknown" category
- **AND** log query for future training

#### Scenario: Classification speed
- **WHEN** classifying any query
- **THEN** classification completes in <5ms
- **AND** does not block inference

---

### Requirement: Task Categories
The system SHALL support configurable task categories.

#### Scenario: Default categories
- **WHEN** system starts
- **THEN** following categories are available:
  - general_chat
  - code_generation
  - code_review
  - math_reasoning
  - research
  - task_planning
  - suit_control (JARVIS-style)
  - health_monitoring (JARVIS-style)

#### Scenario: Add new category
- **WHEN** new task type is discovered
- **THEN** category can be added dynamically
- **AND** examples can be provided for training

---

### Requirement: TF-IDF Classification
The system SHALL use TF-IDF vectorization with cosine similarity.

#### Scenario: Vectorize query
- **WHEN** query is provided
- **THEN** TF-IDF vector is computed
- **AND** compared against category centroids

#### Scenario: Cosine similarity matching
- **WHEN** comparing query to categories
- **THEN** cosine similarity is computed
- **AND** highest similarity category is selected

#### Scenario: Category examples
- **WHEN** category is created
- **THEN** example queries are vectorized
- **AND** used to form category representation

---

### Requirement: Confidence Scoring
The system SHALL provide confidence scores for classification.

#### Scenario: High confidence detection
- **WHEN** query clearly matches one category
- **THEN** confidence is high (>0.8)
- **AND** classification is reliable

#### Scenario: Ambiguous query
- **WHEN** query matches multiple categories
- **THEN** confidence reflects uncertainty
- **AND** top categories are ranked

#### Scenario: Confidence threshold
- **WHEN** confidence < TASK_DETECTION_THRESHOLD
- **THEN** query is flagged as uncertain
- **AND** may require manual review

---

### Requirement: Adapter Routing
The system SHALL route to appropriate LoRA adapter based on task.

#### Scenario: Route to task adapter
- **WHEN** task is detected
- **THEN** corresponding adapter is identified
- **AND** adapter manager is notified

#### Scenario: Fallback adapter
- **WHEN** no specific adapter exists
- **THEN** use general-purpose adapter
- **AND** log for future adapter training

---

## Success Criteria

- [x] Detects known tasks correctly (>90% accuracy)
- [x] Confidence scores are reasonable (0-1 range)
- [x] New task detection works (emergent category)
- [x] Routes to correct adapter
- [x] Classification speed <5ms
- [x] Categories are configurable
- [x] Examples can be added dynamically
