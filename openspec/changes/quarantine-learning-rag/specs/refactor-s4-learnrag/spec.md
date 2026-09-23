## ADDED Requirements

### Requirement: Learning-Free Startup
The system SHALL start and infer with no `learning/` or `rag/` packages
present, reporting `learning_active=False`.

#### Scenario: Entry files stay clean
- **WHEN** `core/main.py` and `stark_cli.py` load
- **THEN** no `from learning` or `from rag` import executes
