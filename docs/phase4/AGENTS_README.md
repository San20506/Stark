# STARK Multi-Agent Framework

## Overview

STARK now has a **multi-agent architecture** that allows delegation of specialized tasks to dedicated sub-agents.

## Architecture

```
STARK (Main Orchestrator)
    ↓
 AgentOrchestrator
    ├─ FileAgent (file operations)
    ├─ [Future: CodeAgent]
    ├─ [Future: ResearchAgent]
    └─ [Future: WebAgent]
```

## Quick Start

```python
from agents.base_agent import get_orchestrator
from agents.file_agent import FileAgent

# Get orchestrator
orchestrator = get_orchestrator()

# Create and register an agent
file_agent = FileAgent(name="FileOps")
orchestrator.register_agent(file_agent)

# Use the agent
result = orchestrator.call_agent(
    "FileOps",
    "read /path/to/file.txt",
    context={"operation": "read", "path": "/path/to/file.txt"}
)

print(f"Success: {result.success}")
print(f"Output: {result.output}")
```

## Available Agents

### FileAgent ✅

**Capabilities:**
- Read files (with size limits)
- Write files (with safety checks)
- List directories
- Search for files (glob patterns)

**Safety Features:**
- Directory whitelist
- File size limits (default 10MB)
- Path validation

**Usage:**
\`\`\`python
file_agent = FileAgent(
    name="FileOps",
    allowed_directories=["/home/user/projects"],
    max_file_size_mb=5.0,
)
\`\`\`

## Creating Custom Agents

```python
from agents.base_agent import BaseAgent, AgentResult, AgentType

class MyAgent(BaseAgent):
    def __init__(self, name: str = "MyAgent"):
        super().__init__(
            name=name,
            agent_type=AgentType.GENERAL,
            description="What this agent does",
        )
    
    def execute(self, task: str, context: Dict = None) -> AgentResult:
        # Your agent logic here
        return AgentResult(
            success=True,
            output="Result",
            steps_taken=["step1", "step2"],
        )
```

## Agent Communication

Agents can call other agents:

```python
class CodeAgent(BaseAgent):
    def execute(self, task: str, context: Dict = None) -> AgentResult:
        # Read source file via FileAgent
        file_result = self.call_agent("FileOps", "read source.py")
        
        if not file_result.success:
            return AgentResult(success=False, error=file_result.error)
        
        # Process the file...
        return AgentResult(success=True, output="Processed")
```

## Testing

Run the demo:
\`\`\`bash
python3 test_agents.py
\`\`\`

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `agents/base_agent.py` | 420 | Base classes, orchestrator |
| `agents/file_agent.py` | 280 | File operations agent |
| `test_agents.py` | 90 | Demo/test script |

## Next Agents

- **CodeAgent** - Code generation, testing, debugging
- **ResearchAgent** - Web research, summarization
- **WebAgent** - Browser automation, data extraction

---

**Status:** Phase 4.1 Complete ✅
