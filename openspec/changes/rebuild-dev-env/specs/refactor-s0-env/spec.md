## ADDED Requirements

### Requirement: Installable Dev Environment
The system SHALL provide a pinned, installable dev environment on Python 3.11
with no `*.py` changes.

#### Scenario: Config imports after install
- **WHEN** the documented venv install completes
- **THEN** `from core.config import get_config` succeeds

#### Scenario: Test collection runs
- **WHEN** `python -m pytest --collect-only -q` runs
- **THEN** collection succeeds without `ModuleNotFoundError`
