# NLU System Specification

## Overview
The NLU (Natural Language Understanding) system provides fast intent classification using Sentence Transformers. It enables sub-10ms query classification without retraining.

**Implementation**: `core/fast_nlu.py`, `core/nlu.py`, `core/intent_router.py`

---

## Requirements

### Requirement: Intent Classification
The system SHALL classify user queries into predefined intents.

#### Scenario: High confidence match
- **WHEN** query embedding matches intent embedding with confidence > 0.65
- **THEN** return intent name and confidence score

#### Scenario: Low confidence match
- **WHEN** best match confidence is < 0.65
- **THEN** classify as "unknown" intent and log query

#### Scenario: Processing speed
- **WHEN** classifying any query
- **THEN** complete classification in < 10ms

---

### Requirement: Intent Library
The system SHALL maintain a JSON-based intent library.

#### Scenario: Load intent library
- **WHEN** system starts
- **THEN** load intents and examples from `data/intent_library.json`

#### Scenario: Default intents
- **WHEN** no library exists
- **THEN** create default library with common intents:
  - greeting, farewell, thanks
  - time_query, date_query, weather_query
  - web_search, calculate, code_request
  - help, capabilities

#### Scenario: Pre-compute embeddings
- **WHEN** library is loaded
- **THEN** pre-compute embeddings for all intent examples

---

### Requirement: Dynamic Intent Management
The system SHALL support runtime intent modification.

#### Scenario: Add new intent
- **WHEN** calling add_intent(name, examples)
- **THEN** add intent to library and compute embeddings

#### Scenario: Add example to intent
- **WHEN** calling add_example(intent_name, example)
- **THEN** add example and update embeddings

#### Scenario: Persist changes
- **WHEN** intents are modified
- **THEN** save updated library to JSON file

---

### Requirement: Unknown Query Handling
The system SHALL track and cluster unknown queries.

#### Scenario: Log unknown query
- **WHEN** query classified as unknown
- **THEN** log to `data/unknown_queries.json` with timestamp

#### Scenario: Cluster unknown queries
- **WHEN** analyzing unknown queries
- **THEN** use K-means clustering on embeddings to find patterns

#### Scenario: Suggest new intents
- **WHEN** clusters have 5+ similar queries
- **THEN** suggest as candidate for new intent

---

### Requirement: Semantic Similarity
The system SHALL use cosine similarity for matching.

#### Scenario: Compute similarity
- **WHEN** comparing query to intent examples
- **THEN** use cosine similarity on 384-dimension embeddings

#### Scenario: Best match selection
- **WHEN** multiple intents match
- **THEN** return intent with highest average similarity

---

### Requirement: Model Configuration
The system SHALL use configurable embedding model.

#### Scenario: Default model
- **WHEN** no model specified
- **THEN** use "all-MiniLM-L6-v2" (fast, 384 dimensions)

#### Scenario: Custom model
- **WHEN** model_name specified
- **THEN** load specified Sentence Transformer model

#### Scenario: Lazy loading
- **WHEN** model first needed
- **THEN** load model on demand (not at import time)

---

### Requirement: Slot Extraction
The system SHALL extract parameters from classified queries.

#### Scenario: Extract city for weather
- **WHEN** intent is weather_query
- **THEN** extract city name from query

#### Scenario: Extract expression for math
- **WHEN** intent is calculate
- **THEN** extract mathematical expression

#### Scenario: Extract search terms
- **WHEN** intent is web_search
- **THEN** extract search query terms
