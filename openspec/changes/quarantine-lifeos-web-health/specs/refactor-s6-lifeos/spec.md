## ADDED Requirements

### Requirement: Single CLI Entry
The system SHALL run offline from `stark_cli.py` with direct `TASK_MODELS`
routing and no LifeOS, web, health-monitor, or multi-agent fan-out.

#### Scenario: Core stays offline
- **WHEN** the core path loads
- **THEN** no Notion, GCal, Flask, or health-monitor import executes

#### Scenario: Routing stays direct
- **WHEN** a query arrives
- **THEN** it routes via `TASK_MODELS` without Router-Arbiter fan-out
