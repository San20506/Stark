# Cognitive Engine Specification

## Overview
The Cognitive Engine (MCP - Master Control Program) is ALFRED's central controller implementing the modular agentic architecture. It receives user input, classifies intent, routes to specialized modules, and returns formatted responses.

**Implementation**: `agents/mcp.py`

---

## Requirements

### Requirement: Intent Detection
The system SHALL classify user queries into specific intent categories using the NLU system.

#### Scenario: High confidence classification
- **WHEN** a user query matches a known intent pattern with confidence > 0.65
- **THEN** the query is routed to the appropriate module
- **AND** the confidence score is logged

#### Scenario: Low confidence fallback
- **WHEN** intent confidence is below threshold
- **THEN** the query falls back to conversational LLM processing

#### Scenario: Unknown intent logging
- **WHEN** no matching intent is found
- **THEN** the query is logged for future intent discovery

---

### Requirement: Module Routing
The system SHALL route classified intents to specialized processing modules.

#### Scenario: Route to time/date module
- **WHEN** intent is TIME_DATE (e.g., "what time is it")
- **THEN** execute time/date module and return formatted time

#### Scenario: Route to math module
- **WHEN** intent is MATH (e.g., "calculate 25 * 47")
- **THEN** execute math module and return computed result

#### Scenario: Route to weather module
- **WHEN** intent is WEATHER (e.g., "weather in London")
- **THEN** execute weather module with extracted city parameter

#### Scenario: Route to search module
- **WHEN** intent is SEARCH (e.g., "search for Python tutorials")
- **THEN** execute web search module and return formatted results

#### Scenario: Route to code module
- **WHEN** intent is CODE (e.g., "write a Python function")
- **THEN** execute code generation via LLM with specialized prompt

---

### Requirement: Response Formatting
The system SHALL format module outputs into human-readable responses.

#### Scenario: Format time response
- **WHEN** time module returns data
- **THEN** response includes time, date, and timezone in natural language

#### Scenario: Format math response
- **WHEN** math module returns calculation result
- **THEN** response shows expression and result clearly

#### Scenario: Format weather response
- **WHEN** weather module returns forecast
- **THEN** response describes temperature, conditions, and outlook

---

### Requirement: Conversational Fallback
The system SHALL use LLM for queries that don't match specialized modules.

#### Scenario: General conversation
- **WHEN** query is conversational (e.g., "how are you")
- **THEN** respond using LLM with personality context

#### Scenario: Complex reasoning
- **WHEN** query requires multi-step reasoning
- **THEN** use LLM with chain-of-thought prompting

---

### Requirement: Module Types
The system SHALL support the following module types:

- CONVERSATIONAL - General chat
- MEMORY - Context retrieval
- MATH - Calculations
- LOGIC - Reasoning
- CODE - Code generation
- VISION - Image understanding
- TIME_DATE - Time queries
- WEATHER - Weather forecasts
- SEARCH - Web search
- TASK - Todo/project management

#### Scenario: Module enumeration
- **WHEN** system initializes
- **THEN** all module types are registered and available

---

### Requirement: Response Metadata
The system SHALL return responses with execution metadata.

#### Scenario: Include execution time
- **WHEN** a response is generated
- **THEN** MCPResponse includes execution_time in seconds

#### Scenario: Include modules used
- **WHEN** multiple modules contribute to response
- **THEN** MCPResponse lists all modules_used

#### Scenario: Include confidence score
- **WHEN** response is generated
- **THEN** MCPResponse includes overall confidence score
