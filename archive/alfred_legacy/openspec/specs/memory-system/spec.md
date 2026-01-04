# Memory System Specification

## Overview
ALFRED's memory system provides multi-tier persistent storage for conversations, user preferences, and semantic retrieval. It enables context-aware responses and long-term learning.

**Implementation**: `memory/semantic_memory.py`, `memory/conversation_db.py`, `memory/personality_adapter.py`, `agents/memory.py`

---

## Requirements

### Requirement: Short-Term Memory
The system SHALL maintain recent conversation history in RAM.

#### Scenario: Store recent exchanges
- **WHEN** a conversation exchange occurs
- **THEN** store user message and assistant response in memory

#### Scenario: Retrieve recent context
- **WHEN** processing a new query
- **THEN** include last 20 exchanges as context

#### Scenario: Context window limit
- **WHEN** memory exceeds 20 exchanges
- **THEN** oldest exchanges are dropped from RAM (but persisted)

---

### Requirement: Semantic Memory
The system SHALL provide vector-based semantic search using ChromaDB.

#### Scenario: Add exchange to semantic memory
- **WHEN** conversation exchange is complete
- **THEN** generate embedding and store in vector database

#### Scenario: Search similar exchanges
- **WHEN** processing new query
- **THEN** retrieve top-K semantically similar past exchanges

#### Scenario: Minimum similarity threshold
- **WHEN** searching for similar content
- **THEN** only return results with similarity >= 0.5

#### Scenario: Exclude recent duplicates
- **WHEN** retrieving semantic context
- **THEN** exclude last N exchanges to avoid duplication with short-term memory

#### Scenario: Persist across restarts
- **WHEN** system restarts
- **THEN** all semantic memory is preserved in ChromaDB

---

### Requirement: Conversation Database
The system SHALL persist full conversation history in SQLite.

#### Scenario: Store conversation
- **WHEN** exchange completes
- **THEN** save to SQLite with timestamp and metadata

#### Scenario: Query history
- **WHEN** user asks about past conversations
- **THEN** search conversation database by date, keyword, or topic

#### Scenario: Export conversations
- **WHEN** requested
- **THEN** export conversation history to JSON or text format

---

### Requirement: User Profile
The system SHALL maintain persistent user preferences.

#### Scenario: Store preference
- **WHEN** user expresses preference (e.g., "I prefer detailed answers")
- **THEN** save preference to user profile JSON

#### Scenario: Apply preferences
- **WHEN** generating response
- **THEN** adjust style based on stored preferences

#### Scenario: Learn from feedback
- **WHEN** user corrects or expresses satisfaction
- **THEN** update relevant preferences

---

### Requirement: Personality Adaptation
The system SHALL adapt response style based on user interactions.

#### Scenario: Track interaction patterns
- **WHEN** user interacts
- **THEN** record query type, length, formality level

#### Scenario: Adapt verbosity
- **WHEN** user consistently asks for more/less detail
- **THEN** adjust default response verbosity

#### Scenario: Adapt formality
- **WHEN** user uses informal language
- **THEN** mirror appropriate formality level

---

### Requirement: Memory Statistics
The system SHALL provide memory usage statistics.

#### Scenario: Get memory stats
- **WHEN** stats are requested
- **THEN** return count of exchanges, vector DB size, storage used

#### Scenario: Clear memory
- **WHEN** clear is requested with confirmation
- **THEN** wipe specified memory tier (with backup option)

---

### Requirement: Memory Consolidation
The system SHALL consolidate memories for efficient storage.

#### Scenario: Periodic consolidation
- **WHEN** memory exceeds threshold
- **THEN** summarize and consolidate older exchanges

#### Scenario: Importance scoring
- **WHEN** consolidating
- **THEN** preserve high-importance exchanges (corrections, preferences, key facts)
