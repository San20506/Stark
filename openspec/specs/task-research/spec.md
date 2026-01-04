# Task: Research Specification

## Overview
Find, synthesize, and summarize information on topics from various sources.

**Priority**: Medium  
**Trigger**: "Research", "Find info about", "What is", "Summarize"

---

## Requirements

### Requirement: Information Gathering
The system SHALL gather relevant information on topics.

#### Scenario: Topic research
- **WHEN** user asks about a topic
- **THEN** provide comprehensive overview
- **AND** cite sources when possible

#### Scenario: Comparison research
- **WHEN** comparing options (tools, approaches)
- **THEN** list pros/cons of each
- **AND** provide recommendation

---

### Requirement: Summarization
The system SHALL summarize lengthy content.

#### Scenario: Document summary
- **WHEN** given long text
- **THEN** extract key points
- **AND** condense to user-specified length

---

### Requirement: Fact Verification
The system SHALL indicate confidence in facts.

#### Scenario: Confidence indication
- **WHEN** providing factual information
- **THEN** indicate certainty level
- **AND** note if information may be outdated

---

## Example Queries
- "Research transformer architectures"
- "Compare PostgreSQL vs MongoDB"
- "What is LoRA fine-tuning?"
