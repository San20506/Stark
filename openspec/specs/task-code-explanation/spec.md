# Task: Code Explanation Specification

## Overview
Explain code functionality, patterns, and logic in clear, understandable terms.

**Priority**: Medium  
**Trigger**: "What does this do", "Explain this code", "How does X work"

---

## Requirements

### Requirement: Code Walkthrough
The system SHALL explain code step by step.

#### Scenario: Function explanation
- **WHEN** user provides a function
- **THEN** explain purpose, inputs, outputs
- **AND** walk through logic flow

#### Scenario: Line-by-line breakdown
- **WHEN** user asks for detailed explanation
- **THEN** explain each significant line
- **AND** note any hidden complexity

---

### Requirement: Pattern Recognition
The system SHALL identify and explain design patterns.

#### Scenario: Identify patterns
- **WHEN** code uses common patterns
- **THEN** name the pattern (singleton, factory, etc.)
- **AND** explain why it's used

---

### Requirement: Complexity Assessment
The system SHALL assess code complexity.

#### Scenario: Complexity report
- **WHEN** analyzing code
- **THEN** note complexity (time/space)
- **AND** suggest simplifications if applicable

---

## Example Queries
- "What does this function do?"
- "Explain this class"
- "Walk me through this algorithm"
