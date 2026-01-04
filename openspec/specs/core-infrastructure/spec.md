# Module 1: Core Infrastructure Specification

## Overview
Centralized configuration management for the entire STARK system. All parameters defined in one place with no hardcoded values elsewhere.

**Implementation**: `core/constants.py`, `core/config.py`  
**Build Time**: 1-2 hours  
**Lines of Code**: ~500

---

## Requirements

### Requirement: System Constants
The system SHALL define all configurable parameters in a single constants file with no hardcoded values elsewhere in the codebase.

#### Scenario: Load constants successfully
- **WHEN** the system imports `core.constants`
- **THEN** all configuration values are accessible
- **AND** no import errors occur

#### Scenario: Type safety with Final
- **WHEN** constants are defined
- **THEN** they use `typing.Final` for immutability
- **AND** type hints are present on all values

#### Scenario: Organized by category
- **WHEN** reviewing constants.py
- **THEN** values are grouped by category (paths, model, LoRA, learning, etc.)
- **AND** each section has clear documentation

---

### Requirement: Dynamic Configuration
The system SHALL support runtime configuration from multiple sources with proper priority.

#### Scenario: Configuration priority
- **WHEN** configuration is loaded
- **THEN** environment variables override YAML file
- **AND** YAML file overrides default constants

#### Scenario: YAML configuration loading
- **WHEN** `config.yaml` exists in project root
- **THEN** values are loaded and merged with defaults
- **AND** missing keys fall back to constants

#### Scenario: Environment variable overrides
- **WHEN** `STARK_*` environment variables are set
- **THEN** they override corresponding config values
- **AND** proper type conversion occurs (int, float, str)

---

### Requirement: Configuration Validation
The system SHALL validate all configuration values using Pydantic models.

#### Scenario: Invalid quantization type
- **WHEN** quantization is set to invalid value
- **THEN** validation error is raised
- **AND** error message lists allowed values

#### Scenario: Out-of-range values
- **WHEN** numeric value is outside allowed range
- **THEN** validation error is raised with bounds
- **AND** configuration loading fails gracefully

#### Scenario: Missing required fields
- **WHEN** required field is missing
- **THEN** default value from constants is used
- **AND** no error is raised

---

### Requirement: Directory Management
The system SHALL create and manage required directories automatically.

#### Scenario: Ensure directories exist
- **WHEN** `ensure_directories()` is called
- **THEN** data, models, checkpoints, logs directories are created
- **AND** existing directories are not modified

#### Scenario: Path configuration
- **WHEN** configuration is loaded
- **THEN** all paths are absolute Path objects
- **AND** paths are cross-platform compatible

---

### Requirement: Configuration Singleton
The system SHALL provide a global configuration singleton for consistent access.

#### Scenario: Get configuration
- **WHEN** `get_config()` is called multiple times
- **THEN** the same configuration object is returned
- **AND** configuration is loaded only once

#### Scenario: Reload configuration
- **WHEN** `reload_config()` is called
- **THEN** configuration is reloaded from disk
- **AND** new values take effect

---

## Success Criteria

- [x] Load from constants.py works
- [x] Load from YAML works
- [x] Validation passes for valid config
- [x] Validation fails for invalid config
- [x] Environment variable overrides work
- [x] No hardcoded values anywhere
- [x] All type hints present
- [x] Docstrings on all classes/functions
