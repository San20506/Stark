# STARK Project Context

## Purpose

**STARK** (Self-Training Adaptive Reasoning Kernel) is a self-optimizing AI assistant that:
- Runs inference on **Qwen3-8B** with INT8 quantization
- Uses **Neuromorphic Memory** for brain-inspired associative recall
- **Learns continuously** from interactions via background LoRA training
- Provides **practical daily assistance**: error debugging, health monitoring, system control
- Operates **entirely offline** on consumer hardware (RTX 4060 / 24GB RAM)

The goal is to build an intelligent assistant that improves itself over time while remaining fully private and local.

---

## Tech Stack

### Core ML
| Library | Purpose |
|---------|---------|
| **PyTorch 2.1+** | Deep learning framework |
| **Transformers** | HuggingFace model loading (Qwen3-8B) |
| **PEFT** | LoRA adapters for task-specific fine-tuning |
| **BitsAndBytes** | INT8/INT4 quantization |

### Memory & Embeddings
| Library | Purpose |
|---------|---------|
| **Sentence Transformers** | Semantic embeddings (all-MiniLM-L6-v2) |
| **NumPy** | Activation spreading, decay calculations |
| **scikit-learn** | TF-IDF for task detection |

### Health Monitoring (Optional)
| Library | Purpose |
|---------|---------|
| **OpenCV** | Camera capture |
| **MediaPipe** | Pose/posture detection |

### System Control (Optional)
| Library | Purpose |
|---------|---------|
| **pyautogui** | Desktop automation |
| **psutil** | System resource monitoring |

### Configuration & Utilities
| Library | Purpose |
|---------|---------|
| **Pydantic** | Config validation |
| **PyYAML** | YAML configuration |
| **TensorBoard** | Training visualization |

---

## Project Conventions

### Code Style
- Follow **PEP 8** style guidelines
- Maximum line length: **100 characters**
- Use **4 spaces** for indentation
- **Type hints everywhere** - All function signatures must have type hints
- **Docstrings** on all public functions/classes (Google style)

### Module Independence
Each module testable independently:
```python
# Good: Memory works standalone
memory = NeuromorphicMemory(capacity=100_000)
memory.store("query", "response", task="debugging")

# Bad: Tight coupling
learner = ContinualLearner()
memory = learner.memory  # Don't do this
```

### Zero Hardcoding
All parameters in `core/constants.py`:
```python
# Good
from core.constants import BATCH_SIZE
batch = create_batch(BATCH_SIZE)

# Bad
batch = create_batch(32)  # Hardcoded!
```

### Thread Safety
Use synchronization in background threads:
```python
import threading
self.lock = threading.RLock()

with self.lock:
    self.memory.store(experience)
```

### Testing Strategy
- All tests in `tests/` directory
- Test files: `test_<module_name>.py`
- Run with: `pytest tests/ -v`

### Git Workflow
```
<type>(<scope>): <short summary>
```
Types: feat, fix, docs, style, refactor, test, chore

---

## Architecture Overview

### Core Modules (9)

| # | Module | Purpose | Key Files |
|---|--------|---------|-----------|
| 1 | Core Infrastructure | Configuration | `constants.py`, `config.py` |
| 2 | Base Model | Qwen3-8B loading & inference | `stark_base.py`, `inference_engine.py` |
| 3 | Neuromorphic Memory | Brain-inspired memory network | `neuromorphic_memory.py` |
| 4 | LoRA Adapters | Task-specific fine-tuning | `lora_adapter.py`, `adapter_manager.py` |
| 5 | Continuous Learning | Background training thread | `continual_learner.py`, `optimizer.py` |
| 6 | Task Detection | Query classification | `task_detector.py` |
| 7 | Capabilities | Domain-specific modules | `error_debugger.py`, `health_monitor.py` |
| 8 | Orchestration | Main STARK class | `main.py` |
| 9 | Utilities | Logging, checkpoints, metrics | `logger.py`, `checkpoint.py` |

### Task Categories (8)

| Category | Purpose | Examples |
|----------|---------|----------|
| `error_debugging` | Analyze & fix errors | "Fix this traceback" |
| `code_explanation` | Explain code | "What does this function do?" |
| `task_planning` | Create plans | "How do I build X?" |
| `research` | Find information | "Explain LoRA" |
| `health_monitoring` | Wellbeing tracking | Posture, breaks, screen time |
| `system_control` | Desktop automation | "Open VS Code" |
| `conversation` | General chat | "Hello", follow-ups |
| `math_reasoning` | Calculations | "What is 15% of 240?" |

---

## Key Algorithms

### 1. Neuromorphic Memory
- **Synaptic connections** between related memories
- **Activation spreading** for associative recall
- **Decay over time** - forgotten unimportant memories
- **Hebbian learning** - strengthens frequently used paths

### 2. LoRA Fine-Tuning
```
W' = W + (α/r) × A × B

W: Frozen base weights
A, B: Low-rank trainable matrices
r: Rank (8), α: Scale (16)
```

### 3. Task Detection
- TF-IDF vectorization of queries
- Cosine similarity to task centroids
- Threshold: 0.65 confidence for classification

### 4. Continuous Learning
- Background thread trains every 60 seconds
- Mixed sampling: 50% old + 50% new experiences
- Prevents catastrophic forgetting

---

## Important Constraints

### Hardware Targets
| Resource | Target |
|----------|--------|
| GPU | RTX 4060 (8GB VRAM) or better |
| RAM | 24GB system RAM |
| Inference | <100ms latency (Qwen3-8B) |
| VRAM | <5GB during inference |

### Resource Limits
| Resource | Limit |
|----------|-------|
| Base model | Qwen3-8B (~4-5GB INT8) |
| Active adapters | 5 max in VRAM |
| Total adapters | 50 on disk |
| Memory network | <4GB RAM |

### Build Timeline
| Week | Focus |
|------|-------|
| 1 | Foundation (Core + Base Model) |
| 2 | Memory & Learning |
| 3 | Task Detection & Capabilities |
| 4 | Integration & Utilities |
| 5 | Polish & Deployment |

---

## External Dependencies

### Required Services
**None** - STARK is fully offline

### Model Weights
- **Primary**: `Qwen/Qwen3-8B` (HuggingFace)
- **Fallback**: Any HuggingFace causal LM

### Optional Integrations
- TensorBoard for training visualization
- Camera for health monitoring
- System APIs for desktop control
