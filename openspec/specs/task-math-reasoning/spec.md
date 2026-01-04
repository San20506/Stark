# Task: Math Reasoning Specification

## Overview
Solve mathematical problems with step-by-step explanations.

**Priority**: Medium  
**Trigger**: Numbers, equations, "Calculate", "What is X + Y"

---

## Requirements

### Requirement: Calculation
The system SHALL perform mathematical calculations.

#### Scenario: Basic arithmetic
- **WHEN** given arithmetic expression
- **THEN** compute result accurately
- **AND** show work if complex

#### Scenario: Unit conversions
- **WHEN** asked to convert units
- **THEN** perform conversion
- **AND** show conversion factor

---

### Requirement: Step-by-Step Reasoning
The system SHALL show reasoning for complex problems.

#### Scenario: Algebra
- **WHEN** given algebraic problem
- **THEN** solve step by step
- **AND** explain each transformation

#### Scenario: Word problems
- **WHEN** given word problem
- **THEN** extract variables
- **AND** set up and solve equation

---

### Requirement: Verification
The system SHALL verify answers when possible.

#### Scenario: Answer check
- **WHEN** solution is found
- **THEN** verify by substitution if applicable
- **AND** note any assumptions made

---

## Example Queries
- "What is 15% of 240?"
- "Solve for x: 2x + 5 = 15"
- "Convert 5 miles to kilometers"
