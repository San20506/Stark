# STARK Adaptive Orchestrator

## Overview
Intelligent multi-model routing system that automatically selects the best model based on task complexity and confidence.

## Architecture

```
User Query
    |
    v
TaskDetector (TF-IDF + Keywords)
    |
    +---> High Confidence (>0.6) -----> Direct Model Routing
    |                                   (conversation → llama3.2:3b)
    |                                   (code_* → qwen3:4b)
    |
    +---> Low Confidence (<0.6) -----> AdaptiveRouter (LLM Analysis)
                                          |
                                          v
                                   JSON Decision:
                                   - Task classification
                                   - Complexity analysis
                                   - Multi-intent detection
                                   - Clarification needs
                                          |
                                          v
                                   Smart Model Selection
```

## Components

### 1. TaskDetector (`core/task_detector.py`)
- **Fast classification** using TF-IDF + keyword matching
- Returns `confidence` score (0-1)
- Flags `is_emergent` for unknown patterns
- **120 training examples** across 8 categories

### 2. AdaptiveRouter (`core/adaptive_router.py`)
- **LLM-based** routing for ambiguous queries
- Uses `llama3.2:3b` for fast analysis
- Returns structured `RoutingDecision`
- Handles:
  - Multi-intent queries
  - Clarification requests
  - Safety checks
  - Complexity estimation

### 3. Multi-Model Backend (`core/constants.py`)
```python
TASK_MODELS = {
    # Fast model for simple tasks
    "conversation": "llama3.2:3b",
    "greeting": "llama3.2:3b",
    
    # Reasoning model for complex tasks
    "error_debugging": "qwen3:4b",
    "code_explanation": "qwen3:4b",
    "code_generation": "qwen3:4b",
}
```

## Usage

```python
from core.main import get_stark

stark = get_stark()
stark.start()

# Simple query → Fast model
result = stark.predict("Hello!")
# Task: conversation, Model: llama3.2:3b (~2-5s)

# Complex query → Thinking model
result = stark.predict("Debug this IndexError")
# Task: error_debugging, Model: qwen3:4b (~30-60s, better reasoning)

# Unknown query → AdaptiveRouter analysis
result = stark.predict("Make me a sandwich")
# Router analyzes, routes to best match or asks for clarification

stark.stop()
```

##Benefits

| Feature | Benefit |
|---------|---------|
| **Multi-Model** | Specialized models for specialized tasks |
| **Adaptive** | Handles unknowns gracefully |
| **Fast** | 2-5s for simple queries (vs 30-60s universal) |
| **Smart** | Deep reasoning when needed |
| **Scalable** | Easy to add new models/tasks |

## Performance

| Query Type | Model | Speed | Reasoning |
|------------|-------|-------|-----------|
| "Hello" | llama3.2:3b | 2-5s | ⭐⭐⭐ |
| "Debug error" | qwen3:4b | 30-60s | ⭐⭐⭐⭐⭐ |
| Unknown | Router → Best | 5-10s | ⭐⭐⭐⭐ |

## Future Extensions

- [ ] Add CodeLlama for code generation
- [ ] Add vision model for UI screenshots
- [ ] Add specialized math model
- [ ] Cache routing decisions
- [ ] Learn from routing patterns
