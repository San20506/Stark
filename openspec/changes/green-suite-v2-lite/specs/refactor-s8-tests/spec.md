## ADDED Requirements

### Requirement: Green Keep-Set Suite
The KEEP-set test suite SHALL pass fully with ≥80% coverage on kept memory
modules and no CUT imports in kept tests.

#### Scenario: Keep tests pass
- **WHEN** the KEEP-set pytest selection runs
- **THEN** all tests pass with no `ModuleNotFoundError`

#### Scenario: Coverage holds
- **WHEN** coverage is measured on `memory`
- **THEN** kept modules report ≥80%
