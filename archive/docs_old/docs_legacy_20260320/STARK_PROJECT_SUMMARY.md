# STARK: Self-Training Adaptive Reasoning Kernel
## Comprehensive Project Documentation

**Version:** 0.1.0 "Genesis" | **Started:** 2025-12-20 | **Target Hardware:** RTX 4060 (8GB) + 24GB RAM

---

## 🎯 Mission Statement

STARK is a **self-improving AI assistant** that runs entirely offline on consumer hardware. Unlike static AI systems, STARK continuously learns from user interactions without forgetting previous knowledge, using brain-inspired memory networks and parameter-efficient fine-tuning.

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Breakdown](#module-breakdown)
3. [Technical Specifications](#technical-specifications)
4. [Memory System](#memory-system)
5. [Learning Pipeline](#learning-pipeline)
6. [Task Detection](#task-detection)
7. [Performance Targets](#performance-targets)
8. [Build Progress](#build-progress)
9. [Technology Stack](#technology-stack)
10. [Migration from ALFRED](#migration-from-alfred)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     STARK SYSTEM (RTX 4060)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              USER INPUT / EXTERNAL SYSTEMS               │  │
│   └──────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              STARK MAIN ORCHESTRATOR                     │  │
│   │            (core/main.py - STARK class)                 │  │
│   └────────────────┬──────────────────────────┬──────────────┘  │
│                    │                          │                 │
│        ┌───────────┼──────────────┬───────────┘                 │
│        │           │              │                             │
│        ▼           ▼              ▼                             │
│   ┌─────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐  │
│   │ Base    │ │ Adapter      │ │ Neuromorphic │ │Learning  │  │
│   │ Model   │ │ Manager      │ │ Memory       │ │Pipeline  │  │
│   │ (Qwen3) │ │ (LoRA)       │ │ (100K nodes) │ │(Thread)  │  │
│   └────┬────┘ └──────┬───────┘ └──────┬───────┘ └────┬─────┘  │
│        │             │                │              │          │
│        └─────────────┼────────────────┼──────────────┘          │
│                      │                │                         │
│        ┌─────────────┼────────────────┘                         │
│        │             │                                          │
│        ▼             ▼                                          │
│   ┌──────────────────────────────────┐                         │
│   │   INFERENCE ENGINE               │                         │
│   │  - Token generation              │                         │
│   │  - <100ms latency target         │                         │
│   │  - KV cache management           │                         │
│   └──────────────────────────────────┘                         │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │                 CAPABILITY MODULES                        │ │
│   │  ┌──────────┐ ┌────────────┐ ┌─────────┐ ┌───────────┐   │ │
│   │  │Error     │ │Code        │ │Health   │ │System     │   │ │
│   │  │Debugger  │ │Explanation │ │Monitor  │ │Control    │   │ │
│   │  └──────────┘ └────────────┘ └─────────┘ └───────────┘   │ │
│   └──────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Module Breakdown

### 9 Core Modules (~4,000+ lines planned, ~2,410 implemented)

| # | Module | Purpose | Files | Status | Lines |
|---|--------|---------|-------|--------|-------|
| 1 | **Core Infrastructure** | Configuration management | `constants.py`, `config.py` | ✅ Complete | 527 |
| 2 | **Base Model** | Qwen3-8B loading & inference | `stark_base.py`, `inference_engine.py` | ✅ Complete | 700 |
| 3 | **Neuromorphic Memory** | Brain-inspired associative memory | `memory_node.py`, `neuromorphic_memory.py` | ✅ Complete | 700 |
| 4 | **LoRA Adapters** | Task-specific fine-tuning | `lora_adapter.py`, `adapter_manager.py` | ✅ Complete | 530 |
| 5 | **Continuous Learning** | Background training thread | `continual_learner.py`, `optimizer.py` | ⏳ Partial | 447 |
| 6 | **Task Detection** | Query classification | `task_detector.py` | ✅ Complete | 550 |
| 7 | **Capabilities** | Domain-specific modules | `error_debugger.py`, `health_monitor.py`, etc. | ⏳ Pending | - |
| 8 | **Orchestration** | Main STARK class | `main.py` | ⏳ Pending | - |
| 9 | **Utilities** | Logging, checkpoints, metrics | `logger.py`, `checkpoint.py`, `metrics.py` | ⏳ Pending | - |

---

## 🔧 Technical Specifications

### Module 1: Core Infrastructure

**File:** `core/constants.py` (198 lines)

| Category | Constants | Description |
|----------|-----------|-------------|
| Paths | `PROJECT_ROOT`, `DATA_DIR`, `MODELS_DIR`, `ADAPTERS_DIR` | Project directory structure |
| Model | `OLLAMA_MODEL="qwen3:8b"`, `MAX_LENGTH=2048`, `MAX_NEW_TOKENS=512` | Inference settings |
| LoRA | `LORA_RANK=8`, `LORA_ALPHA=16`, `MAX_ACTIVE_ADAPTERS=5` | Adapter configuration |
| Memory | `MEMORY_MAX_NODES=100,000`, `ACTIVATION_DECAY_RATE=0.05` | Neuromorphic settings |
| Learning | `BATCH_SIZE=32`, `LEARNING_RATE=1e-4`, `TRAIN_INTERVAL=60s` | Training parameters |
| Hardware | `GPU_DEVICE="cuda:0"`, `VRAM_LIMIT=8GB`, `RAM_LIMIT=16GB` | Resource limits |

**File:** `core/config.py` (329 lines)

- Pydantic models for validated configuration
- YAML file loading with environment variable overrides
- Configuration sections: `ModelConfig`, `LoRAConfig`, `LearningConfig`, `TaskConfig`, `HardwareConfig`, `LoggingConfig`
- Singleton pattern via `get_config()` factory function

---

### Module 2: Base Model

**File:** `models/stark_base.py` (471 lines)

```python
class STARKBaseModel:
    """Base language model wrapper for STARK."""
    
    def __init__(self, model_name="qwen3:8b", quantization="int8", lazy_load=False)
    def load(self) -> None
    def unload(self) -> None
    def generate(self, prompt: str, max_new_tokens=512, temperature=0.7) -> Dict
    def generate_stream(self, prompt: str) -> Generator
    def get_embeddings(self, text: str) -> Tensor
    def warmup(self, prompt="Hello") -> float  # Returns latency in ms
    def get_memory_usage_gb(self) -> float
    def get_stats(self) -> Dict
```

**Key Features:**
- INT8 quantization via bitsandbytes (~4-5GB VRAM)
- Lazy loading for memory efficiency
- KV cache management for fast inference
- Streaming token generation
- Singleton access via `get_model()`

---

### Module 3: Neuromorphic Memory

**File:** `memory/neuromorphic_memory.py` (578 lines)

**Brain-Inspired Design:**
- Synaptic connections between related memories
- Activation spreading for associative recall
- Natural decay for forgetting unimportant memories
- Hebbian learning strengthens frequently used paths

```python
class NeuromorphicMemory:
    """Distributed memory system with synaptic connections."""
    
    def store(self, query: str, response: str, task: str) -> str  # Returns node_id
    def recall(self, query: str, task=None, top_k=5) -> List[Tuple[MemoryNode, float]]
    def recall_by_task(self, task: str, top_k=10) -> List[MemoryNode]
    def save(self, path=None) -> None
    def load(self, path=None) -> bool
    def get_stats(self) -> Dict
```

**Memory Node Structure:**
```python
@dataclass
class MemoryNode:
    id: str
    query: str
    response: str
    task: str
    embedding: np.ndarray
    activation: float = 1.0
    decay_rate: float = 0.05
    access_count: int = 0
    connections: Dict[str, float] = {}  # node_id -> weight
    created_at: datetime
    last_accessed: datetime
```

**Key Algorithms:**
- **Activation Spreading:** When a query arrives, matching nodes activate and spread activation to connected nodes
- **Hebbian Update:** Connections strengthen when nodes are co-activated
- **Garbage Collection:** Low-activation nodes are pruned to maintain capacity

---

### Module 4: LoRA Adapters

**File:** `learning/adapter_manager.py` (422 lines)

**LoRA Formula:**
```
W' = W + (α/r) × A × B

W:  Frozen base weights (Qwen3-8B, ~4GB)
A, B: Low-rank trainable matrices (~5-10MB per adapter)
r:  Rank (8)
α:  Scale (16)
```

```python
class AdapterManager:
    """Manages multiple LoRA adapters with LRU eviction."""
    
    def create_adapter(self, name: str, rank=8, alpha=16) -> LoRAAdapter
    def load_adapter(self, name: str) -> bool
    def unload_adapter(self, name: str, save=True) -> bool
    def switch_adapter(self, name: str) -> bool
    def save_adapter(self, name: str) -> bool
    def delete_adapter(self, name: str) -> bool
    def create_task_adapters(self) -> List[str]  # Creates all 8 task adapters
    def list_adapters(self) -> List[Dict]
```

**Resource Management:**
- Maximum 5 active adapters in VRAM (LRU eviction)
- Maximum 50 adapters on disk
- Each adapter ~5-10MB
- Automatic discovery of existing adapters

---

### Module 5: Continuous Learning

**File:** `learning/continual_learner.py` (447 lines)

```python
class ContinualLearner:
    """Background thread for continuous improvement."""
    
    def start(self) -> None
    def stop(self, timeout=5.0) -> None
    def add_feedback(self, query: str, response: str, task: str, score: float) -> None
    def add_positive_example(self, query: str, response: str, task: str) -> None
    def export_training_data(self, min_score=0.5) -> List[Dict]
    def export_to_jsonl(self, path: str, min_score=0.5) -> int
    def get_stats(self) -> TrainingStats
```

**Learning Pipeline:**
1. User provides query → STARK generates response
2. Implicit/explicit feedback collected (score: -1 to 1)
3. High-quality examples stored in memory
4. Background thread processes feedback every 60s
5. Positive examples exported for fine-tuning

---

### Module 6: Task Detection

**File:** `core/task_detector.py` (550 lines)

**8 Task Categories:**

| Task | Description | Example Queries |
|------|-------------|-----------------|
| `error_debugging` | Analyze & fix errors | "Fix this traceback", "Why is this crashing?" |
| `code_explanation` | Explain code | "What does this function do?" |
| `task_planning` | Create plans | "How should I structure this project?" |
| `research` | Find information | "Explain LoRA", "Best practices for X" |
| `health_monitoring` | Wellbeing tracking | "Remind me to take a break", "Check posture" |
| `system_control` | Desktop automation | "Open VS Code", "Launch browser" |
| `conversation` | General chat | "Hello", "Thanks!", "Goodbye" |
| `math_reasoning` | Calculations | "What is 15% of 240?" |

**Detection Algorithm:**
1. TF-IDF vectorization of query
2. Cosine similarity to task centroids (built from example phrases)
3. Keyword matching as fallback
4. Hybrid scoring combines both methods
5. Threshold: 0.15 minimum confidence

```python
class TaskDetector:
    def detect(self, query: str) -> DetectionResult
    def get_top_tasks(self, query: str, top_k=3) -> List[Tuple[str, float]]
```

---

## 🧠 Memory System

### Neuromorphic vs. Traditional Experience Replay

| Feature | Experience Replay (ALFRED) | Neuromorphic Memory (STARK) |
|---------|---------------------------|------------------------------|
| Structure | Ring buffer | Graph network |
| Recall | Random sampling | Associative spreading |
| Decay | None (fixed capacity) | Time-based with consolidation |
| Learning | Uniform sampling | Hebbian strengthening |
| Task grouping | Task indices | Hub nodes with connections |
| Capacity | 1M flat entries | 100K interconnected nodes |

### Memory Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `MEMORY_MAX_NODES` | 100,000 | Max memory nodes |
| `MEMORY_RAM_LIMIT_GB` | 4.0 | RAM allocation |
| `ACTIVATION_INITIAL` | 1.0 | New memory activation |
| `ACTIVATION_THRESHOLD` | 0.1 | Forget threshold |
| `ACTIVATION_DECAY_RATE` | 0.05 | Decay per hour |
| `ACTIVATION_SPREAD_FACTOR` | 0.3 | Spreading proportion |
| `CONNECTION_SIMILARITY_THRESHOLD` | 0.6 | Min similarity to connect |
| `CONNECTION_HEBBIAN_RATE` | 0.1 | Learning rate |
| `GC_INTERVAL_SECONDS` | 300 | Garbage collection interval |

---

## 📚 Learning Pipeline

### Data Flow: Inference Path (<100ms target)

```
User Input
    │
    ▼
Tokenization (via Ollama)
    │
    ▼
Task Detection (TF-IDF + keywords)
    │
    ▼
Switch to Task Adapter (if needed)
    │
    ▼
Qwen3-8B Inference (INT8)
    │
    ▼
Token Streaming
    │
    ▼
Store Experience in Memory
    │
    ▼
User Output
```

### Data Flow: Learning Path (Background)

```
Feedback Collection
    │
    ▼
Buffer in ContinualLearner
    │
    ▼
Process every 60 seconds
    │
    ▼
Store high-quality examples in NeuromorphicMemory
    │
    ▼
Form synaptic connections
    │
    ▼
Export for fine-tuning (periodic)
    │
    ▼
Update LoRA adapter weights (external process)
```

---

## 🎯 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Inference latency | <100ms | - |
| VRAM usage | <5GB | ~4-5GB (Qwen3-8B INT8) |
| System RAM | <16GB | ~8-10GB (memory network) |
| Task accuracy | >90% | - |
| Learning loss decrease | 0.5-1.5% per 100 exp | - |
| Memory stability | No crashes/1M queries | - |
| Concurrent adapters | 5 max | ✓ |

---

## 📈 Build Progress

### Week 1: Foundation ✅ Complete
- [x] Module 1: Core Infrastructure (480 lines)
- [x] Module 2: Base Model (700 lines)

### Week 2: Memory & Learning 🔄 In Progress
- [x] Module 3: Neuromorphic Memory (700 lines)
- [x] Module 4: LoRA Adapters (530 lines)
- [ ] Module 5: Continuous Learning (partial ~450 lines)

### Week 3: Intelligence ⏳ Pending
- [x] Module 6: Task Detection (550 lines) - Done early
- [ ] Module 7: Capability Modules

### Week 4: Integration ⏳ Pending
- [ ] Module 8: Orchestration
- [ ] Module 9: Utilities

### Week 5: Polish ⏳ Pending
- [ ] Documentation
- [ ] Error handling
- [ ] Performance tuning
- [ ] Stress testing

---

## 🛠️ Technology Stack

### Core ML

| Library | Version | Purpose |
|---------|---------|---------|
| PyTorch | ≥2.1.0 | Deep learning framework |
| Transformers | ≥4.35.0 | HuggingFace model loading |
| PEFT | ≥0.7.0 | LoRA/QLoRA adapters |
| BitsAndBytes | ≥0.41.0 | INT8/INT4 quantization |
| Accelerate | ≥0.24.0 | Multi-GPU support |

### Data & Embeddings

| Library | Version | Purpose |
|---------|---------|---------|
| NumPy | ≥1.24.0 | Numerical operations |
| SciPy | ≥1.11.0 | Scientific computing |
| scikit-learn | ≥1.3.0 | TF-IDF vectorization |
| Sentence Transformers | ≥2.2.0 | Semantic embeddings |

### Configuration & Utilities

| Library | Version | Purpose |
|---------|---------|---------|
| Pydantic | ≥2.0.0 | Config validation |
| PyYAML | ≥6.0 | YAML config files |
| TensorBoard | ≥2.14.0 | Training visualization |
| tqdm | ≥4.66.0 | Progress bars |
| pytest | ≥7.4.0 | Testing |

### Optional

| Library | Purpose |
|---------|---------|
| ChromaDB | Vector storage |
| sounddevice, faster-whisper, piper-tts | Voice interface |
| OpenCV, MediaPipe | Health monitoring camera |
| pyautogui, psutil | System control |

---

## 🔄 Migration from ALFRED

### Architectural Evolution

| Component | ALFRED | STARK |
|-----------|--------|-------|
| Main Orchestrator | `agents/mcp.py` (600+ lines) | `core/main.py` (modular) |
| Intent Detection | `core/fast_nlu.py` | `core/task_detector.py` |
| Memory | `memory/semantic_memory.py` (static) | `memory/neuromorphic_memory.py` (dynamic) |
| Learning | None | Background thread with LoRA |
| Model Loading | `agents/llm.py` | `models/stark_base.py` |
| Tools | `core/tools.py` | `capabilities/*.py` |

### Key Improvements

| Aspect | ALFRED | STARK |
|--------|--------|-------|
| Learning | Static | Continuous |
| Memory | 20 exchanges | 100K+ nodes |
| Adapters | None | 50+ LoRA adapters |
| Training | Offline only | Background thread |
| Forgetting | N/A | Prevented via decay + consolidation |
| Modularity | Tight coupling | Independent modules |

### Preserved Patterns

From ALFRED, these patterns proved valuable:
- Singleton pattern with `get_xxx()` factory functions
- Sentence Transformer embeddings for intent classification
- Declarative tool registration
- Type hints throughout codebase

---

## 📁 Project Structure

```
STARK/
├── core/                       # Core infrastructure
│   ├── __init__.py
│   ├── constants.py           # All system constants (198 lines)
│   ├── config.py              # Pydantic configuration (329 lines)
│   └── task_detector.py       # Query classification (550 lines)
│
├── models/                     # Model loading & inference
│   ├── __init__.py
│   ├── stark_base.py          # Qwen3-8B loader (471 lines)
│   └── inference_engine.py    # Optimized inference
│
├── memory/                     # Neuromorphic memory
│   ├── __init__.py
│   ├── memory_node.py         # Node dataclass
│   └── neuromorphic_memory.py # Main memory (578 lines)
│
├── learning/                   # Continuous learning
│   ├── __init__.py
│   ├── lora_adapter.py        # LoRA implementation
│   ├── adapter_manager.py     # Multi-adapter management (422 lines)
│   └── continual_learner.py   # Background training (447 lines)
│
├── capabilities/               # Domain-specific modules
│   └── (pending)
│
├── utils/                      # Utilities
│   └── (pending)
│
├── tests/                      # Test suite
│   ├── test_models.py
│   ├── test_learning.py
│   ├── test_capabilities.py
│   └── test_integration.py
│
├── archive/                    # Legacy code (ALFRED backup)
│   └── alfred_legacy/
│
├── openspec/                   # Specifications
│   ├── project.md             # Project context
│   └── specs/                 # 18 spec directories
│
├── data/                       # Training data
├── docs/                       # Documentation
│   ├── stark_complete_guide.md
│   ├── stark_build_start.md
│   ├── PROGRESS.md
│   └── ALFRED_MIGRATION_DATA.md
│
├── requirements.txt            # Dependencies
├── config.yaml                 # Runtime configuration
└── README.md
```

---

## 🔑 Key Implementation Rules

1. **Module Independence**: Each module testable standalone
2. **Type Hints Everywhere**: All function signatures typed
3. **Zero Hardcoding**: All parameters in `constants.py`
4. **Structured Logging**: `logging.getLogger(__name__)`
5. **Thread Safety**: `threading.RLock()` for shared resources
6. **Singleton Pattern**: `get_xxx()` factory functions

---

## 🔗 OpenSpec Specifications

18 specification directories covering all components:

| Category | Specs |
|----------|-------|
| **Core Modules** | `core-infrastructure`, `base-model`, `neuromorphic-memory`, `lora-adapters`, `continuous-learning`, `task-detection`, `orchestration`, `utilities`, `capabilities`, `experience-replay` |
| **Task Types** | `task-error-debugging`, `task-code-explanation`, `task-planning`, `task-research`, `task-health-monitoring`, `task-system-control`, `task-conversation`, `task-math-reasoning` |

Each spec includes:
- Requirements with Given/When/Then scenarios
- Architecture diagrams
- Success criteria checklist
- Implementation notes

---

## 📞 Quick Reference

### Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Verify Module 1
python -c "from core.config import get_config; print('✅ Config OK')"

# Run tests
pytest tests/ -v

# Start TensorBoard
tensorboard --logdir=logs/
```

### Configuration

```yaml
# config.yaml example
model:
  name: "qwen3:8b"
  max_length: 2048

lora:
  rank: 8
  alpha: 16

learning:
  batch_size: 32
  learning_rate: 0.0001
  train_interval_seconds: 60
```

### Environment Variables

```bash
export STARK_MODEL_NAME="qwen3:8b"
export STARK_LORA_RANK="8"
export STARK_LEARNING_BATCH_SIZE="32"
export STARK_LOG_LEVEL="INFO"
```

---

**Built from scratch. Learning never stops. 🚀**

*Generated: 2025-12-24*
