# STARK Agent Development Guide

This file contains build commands, code style guidelines, development conventions, and project-specific patterns for agentic coding assistants working in the STARK repository.

## Quick Start

**Install dependencies:**
```bash
pip install -r requirements.txt
npm install  # For OpenSpec
```

**Run tests:**
```bash
pytest                                    # Run all tests
pytest tests/test_utilities.py            # Specific test file
pytest tests/test_utilities.py::TestClass # Specific test class
pytest -v                                 # Verbose output
pytest --cov=.                            # With coverage
```

**Run STARK:**
```bash
python stark_cli.py      # CLI interface
python run_voice.py      # Voice mode
python web_server.py     # Web interface
```

## Project Overview

STARK (Self-Training Adaptive Reasoning Kernel) is a self-optimizing AI system that:
- Runs inference in <100ms per query
- Learns continuously via background training
- Uses LoRA adapters for task-specific specialization
- Manages neuromorphic memory with 100K+ nodes
- Operates entirely offline on consumer hardware (RTX 4060 + 24GB RAM)

### Key Integration Points

The system coordinates multiple specialized agents:
- **CodeAgent** - Code generation, testing, auto-fixing (in `agents/code_agent.py`)
- **FileAgent** - File system operations (in `agents/file_agent.py`)
- **WebAgent** - Web scraping/interaction (in `agents/web_agent.py`)
- **RouterAgent** - Task routing and orchestration (in `agents/router_agent.py`)
- **Specialists** - Retriever, FastAnswer, Planner, Arbiter agents (in `agents/specialists.py`)

All agents extend `BaseAgent` and return structured `AgentResult` objects.

## Code Style Guidelines

### Import Organization

Always follow this order:
1. Standard library (logging, time, pathlib, typing, etc.)
2. Third-party (torch, transformers, pydantic, etc.)
3. Local imports (core.*, utils.*, models.*, etc.)

```python
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

import torch
from transformers import AutoModel
from peft import LoraConfig

from core.constants import PROJECT_ROOT, MAX_LENGTH
from core.config import get_config
from utils.logger import get_logger
```

### Naming Conventions

- **Classes**: `PascalCase` (`STARKLogger`, `CodeAgent`, `NeuromorphicMemory`)
- **Functions/variables**: `snake_case` (`execute_task`, `get_config`, `latency_ms`)
- **Constants**: `UPPER_SNAKE_CASE` with `Final` type hint (required!)
  ```python
  from typing import Final
  MAX_LENGTH: Final[int] = 2048
  BATCH_SIZE: Final[int] = 32
  ```
- **Private members**: Prefix with underscore (`_config`, `_cache`)
- **Enums**: `PascalCase` (`AgentType`, `AgentStatus`)

### Type Hints (Required)

All public function signatures must have type hints:
```python
def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
    """Execute a task.
    
    Args:
        task: Task description
        context: Optional execution context
        
    Returns:
        AgentResult with success/error/output
        
    Raises:
        TimeoutError: If execution exceeds timeout
    """
```

Use these patterns:
- `Optional[T]` for nullable values (not `Union[T, None]`)
- `Dict[str, Any]` for generic dictionaries
- `List[T]` for lists
- `Final[T]` for constants (in `core/constants.py`)

### Error Handling

```python
try:
    result = self.execute(task, context)
    return result
except TimeoutError:
    self.status = AgentStatus.TIMEOUT
    logger.error(f"Task timeout after {self.timeout}s", exc_info=True)
    return AgentResult(success=False, error="Timeout")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return AgentResult(success=False, error=str(e))
```

Key principles:
- Use specific exception types (not bare `except:`)
- Always log with context using `exc_info=True`
- For agents, return structured `AgentResult` instead of raising
- Include relevant metadata (task name, duration, agent type) in logs

### Documentation

Use Google/NumPy style docstrings for all public classes and functions:

```python
class CodeAgent(BaseAgent):
    """
    Intelligent code generation agent with testing and auto-fixing.
    
    Features:
    - Generate code from natural language descriptions
    - Auto-generate and run tests
    - Iterative error fixing (up to 3 attempts)
    - Uses thinking model for complex code
    
    Args:
        name: Agent instance name
        max_fix_attempts: Maximum auto-fix iterations before giving up
        
    Attributes:
        status: Current execution status
        timeout: Max execution time in seconds
    """
```

### File Structure

Keep files focused on single responsibility. Use section dividers:

```python
"""
Module Docstring
================
One-line purpose.
Extended explanation if needed.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_ATTEMPTS: Final[int] = 3

# =============================================================================
# CLASSES
# =============================================================================

class MyClass:
    pass

# =============================================================================
# FUNCTIONS
# =============================================================================

def my_function():
    pass

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pass
```

## Project Architecture

### Core Modules

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `core/` | System infrastructure | constants.py, config.py, main.py, task_detector.py |
| `models/` | Model loading & inference | stark_base.py, inference_engine.py |
| `memory/` | Experience storage | neuromorphic_memory.py, memory_node.py |
| `learning/` | Continuous learning | lora_adapter.py, adapter_manager.py, continual_learner.py |
| `agents/` | Multi-agent framework | base_agent.py, code_agent.py, file_agent.py, web_agent.py, router_agent.py, specialists.py |
| `capabilities/` | Domain-specific modules | error_debugger.py, code_explanation.py, health_monitor.py |
| `automation/` | Desktop automation | app_launcher.py, window_control.py, keyboard_mouse.py |
| `rag/` | Semantic search | document_indexer.py, retriever.py, chunker.py |
| `voice/` | Audio I/O | speech_to_text.py, text_to_speech.py, wake_word.py |
| `utils/` | Utilities | logger.py, checkpoint.py, metrics.py, profiler.py |
| `tests/` | Test suite | test_*.py, phase4/ subdirectory |

### Configuration System

**How to add constants:**
1. Define in `core/constants.py` with `Final[type]` type hint
2. Always include a comment explaining the constant
3. Group related constants with section dividers

**How configuration flows:**
```
core/constants.py (base values)
    ↓
core/config.py (Pydantic validation)
    ↓
Environment variables (STARK_SECTION_KEY pattern)
    ↓
Runtime config in get_config()
```

Example environment variables:
```bash
export STARK_MODEL_NAME="llama3.2:3b"
export STARK_LOG_LEVEL="DEBUG"
export STARK_LORA_RANK="8"
export STARK_LEARNING_BATCH_SIZE="32"
```

### Agent Framework

**Agent execution flow:**

```
User query
    ↓
RouterAgent determines task type
    ↓
Select specialized agent (Code/File/Web/etc)
    ↓
Agent.execute(task, context) → AgentResult
    ↓
Structured result with metadata
```

**Agent structure:**
```python
from agents.base_agent import BaseAgent, AgentResult, AgentType

class MyAgent(BaseAgent):
    def __init__(self, name: str = "MyAgent"):
        super().__init__(
            name=name,
            agent_type=AgentType.CODE,  # or appropriate type
            description="What this agent does",
            timeout=60.0  # seconds
        )
    
    def execute(self, task: str, context: Dict[str, Any]) -> AgentResult:
        """Execute a task."""
        start_time = time.time()
        try:
            # Do work
            output = "result"
            elapsed = (time.time() - start_time) * 1000
            
            return AgentResult(
                success=True,
                output=output,
                agent_type=self.agent_type,
                agent_name=self.name,
                execution_time_ms=elapsed,
                steps_taken=["step1", "step2"],
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"Agent {self.name} failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                agent_type=self.agent_type,
                agent_name=self.name,
                execution_time_ms=elapsed,
            )
```

**Agent result fields:**
- `success`: Boolean indicating success
- `output`: Main result string
- `error`: Error message if failed (None if successful)
- `agent_type`: Which agent produced this
- `agent_name`: Agent instance name
- `execution_time_ms`: Duration in milliseconds
- `steps_taken`: List of execution steps for debugging
- `artifacts_created`: List of files/resources created
- `sub_agents_called`: List of other agents invoked

**Agent types (defined in `agents/base_agent.py`):**
- `RESEARCH` - Information gathering
- `CODE` - Code generation/fixing
- `FILE` - File operations
- `WEB` - Web operations
- `GENERAL` - Generic tasks

**Agent statuses:**
- `IDLE` - Ready to execute
- `RUNNING` - Currently executing
- `SUCCESS` - Completed successfully
- `FAILED` - Execution failed
- `TIMEOUT` - Exceeded time limit

### Memory System

STARK uses a neuromorphic memory system (not traditional RAG):

```python
from memory.neuromorphic_memory import NeuromorphicMemory

memory = NeuromorphicMemory()
memory.remember(query="user input", response="model output", relevance=0.95)
memories = memory.recall(query="similar input", top_k=5)
```

**Key concepts:**
- Memories are nodes with activation values
- Activation spreads through semantic connections
- Automatic decay (forget less-used memories)
- Background garbage collection every 60 seconds
- Stored in `data/memory/` as JSON

### Learning System

STARK continuously learns via LoRA adapters:

```python
from learning.adapter_manager import AdapterManager

adapters = AdapterManager()
adapter = adapters.create_adapter("task_name")  # Creates 5-10MB adapter
adapters.activate_adapter("task_name")  # Load into VRAM
# Training happens in background thread
adapters.deactivate_adapter("task_name")  # Free VRAM
```

**Key facts:**
- Each adapter is ~5-10MB on disk
- Up to 5 adapters can be active simultaneously in memory
- Max 50 total adapters stored (oldest auto-removed)
- Training happens asynchronously via `ContinualLearner`
- Uses replay buffer to prevent catastrophic forgetting

### Logging

Always use the standard logger:

```python
from utils.logger import get_logger

logger = get_logger(__name__)

logger.debug("Detailed trace info")
logger.info("Normal operation", extra={"task": task_id})
logger.warning("Recovered from error", extra={"recovery_action": "retry"})
logger.error("Something failed", exc_info=True)
logger.critical("System failure - immediate action needed")
```

**Logging setup:**
- Called once at startup in `core/main.py`
- Logs to console + file rotation (10MB max per file, 5 backups)
- Format: `[TIMESTAMP] [LEVEL] [MODULE] - MESSAGE`
- File location: `logs/stark.log`
- Level controlled by `LOG_LEVEL` constant (default INFO)

### Testing

**Test organization:**
```
tests/
├── test_utilities.py         # Logger, checkpoint, metrics
├── test_learning.py          # LoRA adapters, training
├── test_neuromorphic.py      # Memory system
├── test_task_detector.py     # Task classification
├── test_orchestration.py     # Agent coordination
└── phase4/
    └── test_phase4_smoke.py  # Comprehensive integration
```

**Test patterns:**
```python
class TestFeatureName:
    """Group related tests in a class."""
    
    def test_happy_path(self):
        """Test success case."""
        result = function_under_test(valid_input)
        assert result.success
        assert result.value == expected
    
    def test_error_case(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
    
    def test_with_fixtures(self, tmp_path):
        """Use pytest fixtures for setup."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: value")
        result = load_config(config_file)
        assert result.key == "value"
```

**Running tests:**
```bash
pytest                                    # All tests
pytest tests/test_utilities.py::TestSTARKLogger  # Specific class
pytest tests/test_utilities.py::TestSTARKLogger::test_setup_logging  # Specific test
pytest -xvs                              # Stop on first failure, verbose, no capture
pytest --cov=. --cov-report=html         # Coverage report
```

## Common Patterns

### Singleton Pattern

Used for global instances like logger, config, memory:

```python
_instance: Optional[MyClass] = None

def get_instance() -> MyClass:
    global _instance
    if _instance is None:
        _instance = MyClass()
    return _instance
```

See: `core/config.py` (get_config), `utils/logger.py` (setup_logging)

### Context Managers

For resource management:

```python
with profiler.measure("operation_name"):
    # Code here is timed
    pass
```

### Dataclasses for Data Transfer

Used for agent results, config, and inference data:

```python
from dataclasses import dataclass, field

@dataclass
class Result:
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

See: `agents/base_agent.py` (AgentResult), `models/inference_engine.py` (InferenceRequest/Result)

## Important Gotchas & Patterns

### 1. **Ollama Integration**

STARK uses Ollama for inference, not direct Hugging Face models:
- Ollama API: `http://127.0.0.1:11434`
- Models are task-routed (see `TASK_MODELS` in `core/constants.py`)
- Different models for fast vs reasoning tasks
- Ollama must be running before STARK starts

```python
from core.constants import OLLAMA_BASE_URL, TASK_MODELS

# To call Ollama:
import requests
response = requests.post(
    f"{OLLAMA_BASE_URL}/api/generate",
    json={"model": "llama3.2:3b", "prompt": "..."}
)
```

### 2. **Path Handling**

Always use `pathlib.Path`, never string paths:

```python
from pathlib import Path
from core.constants import PROJECT_ROOT, DATA_DIR

# Good
config_file = PROJECT_ROOT / "config.yaml"
data_file = DATA_DIR / "training_data.json"

# Bad - avoid
config_file = os.path.join(PROJECT_ROOT, "config.yaml")
```

### 3. **Configuration Management**

Never hardcode values - use `core/constants.py`:

```python
# Good
from core.constants import MAX_LENGTH
max_len = MAX_LENGTH

# Bad - avoid
max_len = 2048
```

### 4. **Async Operations**

Learning runs in a background thread (not async/await):

```python
# ContinualLearner runs in its own thread
# Start it once at startup:
learner = ContinualLearner()
learner.start()

# Check status:
if learner.is_training:
    print("Training in progress")

# Stop it:
learner.stop()
```

### 5. **Memory Management**

Multiple components track VRAM usage. Always clean up:

```python
# Activate only when needed
adapter_manager.activate_adapter("task_name")
try:
    result = use_adapter()
finally:
    adapter_manager.deactivate_adapter("task_name")  # Always cleanup
```

### 6. **Agent Timeouts**

Agents have configurable timeouts. Be aware of these limits:

```python
# Default timeout: 60 seconds
# For code agents with multiple attempts: increase timeout
code_agent = CodeAgent(max_fix_attempts=3)  # ~60-180s total
```

### 7. **Result Chaining**

Agents can call other agents. Always check success:

```python
def execute(self, task: str, context: Dict[str, Any]) -> AgentResult:
    # Call another agent
    sub_result = self.code_agent.execute(task, context)
    
    if not sub_result.success:
        return AgentResult(
            success=False,
            error=f"Sub-agent failed: {sub_result.error}",
            sub_agents_called=[sub_result.agent_name]
        )
    
    # Process sub_result.output
    return AgentResult(success=True, output=processed_output)
```

### 8. **Testing External Services**

Mock Ollama calls in tests:

```python
from unittest.mock import patch, MagicMock

def test_inference():
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {
            'response': 'mock output'
        }
        result = inference_engine.generate("test")
        assert result.success
```

### 9. **Error Messages**

Be specific in error messages for better debugging:

```python
# Good
logger.error(f"Failed to load adapter '{adapter_name}' from {adapter_path}: {e}")

# Bad
logger.error("Failed to load adapter")
```

### 10. **Dataclass vs Regular Classes**

Use dataclasses for data containers, regular classes for behavior:

```python
# Use dataclass for data transfer
@dataclass
class Config:
    model_name: str
    batch_size: int

# Use class for logic
class Agent:
    def execute(self):
        pass
```

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Inference latency | <100ms | Per query to Ollama |
| VRAM usage | <8GB | Managed by Ollama |
| System RAM | <16GB | Peak during training |
| Task accuracy | >90% | After 100+ examples |
| Memory capacity | 100K+ nodes | With 4GB RAM limit |
| Adapter loading | <500ms | Into VRAM |

## Hardware Requirements

- **GPU**: RTX 4060 (8GB) or better with CUDA 12.x
- **RAM**: 16-24GB system RAM minimum
- **Storage**: 10GB for models + adapters
- **OS**: Linux/Windows with CUDA support
- **CPU**: Modern quad-core minimum for background training

## Safety & Limits

- Max query length: 2048 tokens
- Max response length: 4096 tokens
- Request timeout: 30 seconds
- Max concurrent Ollama requests: 4
- VRAM critical threshold: 7.5GB (stop accepting new tasks)
- Memory garbage collection interval: 60 seconds

## OpenSpec Integration

This project uses OpenSpec for spec-driven development. When working on significant features or breaking changes:

1. Check existing specs: `openspec list`, `openspec list --specs`
2. Create change proposal: Add `.md` file in `openspec/changes/`
3. Validate: `openspec validate [change-id] --strict`
4. Implement after approval
5. See `openspec/AGENTS.md` for detailed workflow

## Development Tips

1. **Always read existing code before adding features** - Follow established patterns
2. **Test after every change** - Run relevant test suite immediately
3. **Use type hints** - All function signatures must have them (enforced)
4. **Log with context** - Include relevant data in log messages
5. **Handle errors specifically** - Don't use bare except, use specific exception types
6. **Keep functions focused** - Single responsibility principle
7. **Use descriptive names** - Variable/function names should be self-documenting
8. **Document complex logic** - Docstrings required for public functions/classes
9. **Mock external services** - Tests should not depend on Ollama/network
10. **Check resource cleanup** - No file handles/connections left open
11. **Verify agent results** - Always check `success` before using `output`
12. **Profile performance** - Use `utils.profiler.measure()` for critical paths

## Testing Checklist

When adding new functionality, ensure:

- [ ] Unit tests for all public functions/classes
- [ ] Integration tests for component interactions
- [ ] Error handling tests (success + failure cases)
- [ ] Mock external dependencies (Ollama, files, network)
- [ ] Test both success and failure scenarios
- [ ] Verify logging output includes relevant context
- [ ] Check resource cleanup (no dangling connections/files)
- [ ] Run full test suite: `pytest -v` passes
- [ ] Coverage is >80%: `pytest --cov=. tests/`
- [ ] No new warnings/errors in logs

## Git Workflow

- Branch names: `feature/xyz`, `bugfix/xyz`, `docs/xyz`
- Commit messages: "Brief description" + optional longer explanation
- Always run tests before committing
- Don't commit data files (checkpoints, large models) - use .gitignore
- Keep commits focused on single logical change

## File Locations Quick Reference

| What | Where |
|------|-------|
| System constants | `core/constants.py` |
| Runtime config | `core/config.py` + environment variables |
| Logging setup | `utils/logger.py` |
| Base agent class | `agents/base_agent.py` |
| Model inference | `models/inference_engine.py` |
| Memory system | `memory/neuromorphic_memory.py` |
| Learning system | `learning/lora_adapter.py` |
| Tests | `tests/test_*.py` |
| Documentation | `docs/`, `README.md`, this file |
