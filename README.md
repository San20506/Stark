# 🚀 STARK: Self-Training Adaptive Reasoning Kernel

**Version 0.1.0 - Genesis** | Built: 2025-12-20

A self-optimizing AI system that learns continuously from interactions. Built for RTX 4060 (8GB VRAM) + 24GB RAM.

---

## 🎯 What is STARK?

STARK is a **self-improving AI system** that:
- Runs inference in **<50ms** per query
- **Learns continuously** from interactions without forgetting
- Uses **LoRA adapters** for task-specific intelligence
- Stores **1M+ experiences** for replay training
- Operates **entirely offline** on consumer hardware

---

## 📂 Project Structure

```
STARK/
├── core/                   # Core infrastructure
│   ├── constants.py        # ✅ All system constants
│   ├── config.py           # ✅ Dynamic configuration
│   └── main.py             # Main orchestration (Week 4)
│
├── models/                 # Model loading & inference
│   ├── stark_base.py       # Base model loader (Week 1)
│   └── inference_engine.py # Optimized inference (Week 1)
│
├── memory/                 # Experience storage
│   ├── experience_buffer.py # 1M replay buffer (Week 2)
│   └── memory_manager.py   # VRAM optimization (Week 2)
│
├── learning/               # Continuous learning
│   ├── lora_adapter.py     # LoRA implementation (Week 2)
│   ├── adapter_manager.py  # Multi-adapter management (Week 2)
│   ├── continual_learner.py # Background training (Week 2)
│   └── optimizer.py        # Training loop (Week 2)
│
├── capabilities/           # Domain-specific modules
│   ├── task_detector.py    # Query classification (Week 3)
│   ├── nlp_interface.py    # Natural language (Week 3)
│   ├── code_assistant.py   # Code generation (Week 3)
│   └── reasoning.py        # Chain-of-thought (Week 3)
│
├── utils/                  # Utilities
│   ├── logger.py           # Structured logging (Week 4)
│   ├── checkpoint.py       # Save/load state (Week 4)
│   ├── metrics.py          # Performance tracking (Week 4)
│   └── profiler.py         # Memory profiling (Week 4)
│
├── tests/                  # Test suite
│   ├── test_models.py
│   ├── test_learning.py
│   ├── test_capabilities.py
│   └── test_integration.py
│
├── archive/                # Legacy code (ALFRED backup)
│   └── alfred_legacy/      # Previous implementation
│
├── data/                   # Training data
├── checkpoints/            # Model checkpoints
├── logs/                   # System logs
│
├── requirements.txt        # Dependencies
├── config.yaml            # Runtime configuration
└── README.md              # This file
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/San20506/Stark.git
cd Stark
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
npm install  # For Node.js dependencies
```

### 3. Download Large Files (Required)

Some large files are excluded from the repository due to GitHub's size limits. Download them manually:

#### GloVe Word Embeddings (~2GB)
```bash
mkdir -p data/glove
cd data/glove

# Download GloVe embeddings
wget https://nlp.stanford.edu/data/glove.6B.zip
unzip glove.6B.zip

cd ../..
```

#### Voice Model (GPT-SoVITS) (~100MB)
```bash
mkdir -p models/voice/gptsovits

# Download the voice model (replace with your actual model source)
# Option 1: From Hugging Face (example)
# wget https://huggingface.co/YOUR_MODEL_PATH/sovits_model.pth -O models/voice/gptsovits/sovits_model.pth

# Option 2: If you have a local backup, copy it to:
# models/voice/gptsovits/sovits_model.pth
```

> **Note**: The voice model is optional if you don't need text-to-speech functionality.

### 4. Verify Installation
```bash
python -c "from core.config import get_config; print('✅ Config OK')"
```

### 5. Run STARK
```bash
# CLI Mode
python stark_cli.py

# Voice Mode
python run_voice.py

# Web Interface
python web_server.py
```

---

## 📦 Files Excluded from Repository

The following files are in `.gitignore` to keep the repo under GitHub's limits:

| Path | Size | Purpose | Download |
|------|------|---------|----------|
| `node_modules/` | ~115MB | Node.js deps | `npm install` |
| `data/glove/*.txt` | ~2GB | Word embeddings | See above |
| `data/glove/*.zip` | ~800MB | Embeddings archive | See above |
| `models/**/*.pth` | ~100MB+ | Model weights | See above |
| `models/**/*.bin` | Varies | Binary models | Train or download |

---

## 📈 Build Progress

### Week 1: Foundation ⏳
- [x] Module 1: Core Infrastructure
  - [x] constants.py
  - [x] config.py
  - [ ] Unit tests
- [ ] Module 2: Base Model
  - [ ] stark_base.py
  - [ ] inference_engine.py
  - [ ] <50ms inference verified

### Week 2: Memory & Learning
- [ ] Module 3: Experience Replay
- [ ] Module 4: LoRA Adapters
- [ ] Module 5: Continuous Learning

### Week 3: Intelligence
- [ ] Module 6: Task Detection
- [ ] Module 7: Capability Modules

### Week 4: Integration
- [ ] Module 8: Orchestration
- [ ] Module 9: Utilities

### Week 5: Polish
- [ ] Documentation
- [ ] Error handling
- [ ] Performance tuning
- [ ] Stress testing

---

## 🎯 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Inference latency | <50ms | - |
| VRAM usage | <2GB | - |
| System RAM | <8GB | - |
| Task accuracy | >90% | - |
| Experience buffer | 1M+ | - |

---

## 🔧 Configuration

### Environment Variables
```bash
export STARK_MODEL_NAME="deepseek-ai/deepseek-coder-1.3b-instruct"
export STARK_MODEL_QUANTIZATION="int8"
export STARK_LORA_RANK="8"
export STARK_LEARNING_BATCH_SIZE="32"
export STARK_LOG_LEVEL="INFO"
```

### YAML Configuration (config.yaml)
```yaml
model:
  name: "deepseek-ai/deepseek-coder-1.3b-instruct"
  quantization: "int8"
  max_length: 512

lora:
  rank: 8
  alpha: 16
  dropout: 0.1

learning:
  batch_size: 32
  learning_rate: 0.0001
  replay_ratio: 0.5
```

---

## 📚 Documentation

- **Build Guide**: See `stark_complete_guide.md`
- **Legacy Code**: See `archive/alfred_legacy/` for previous implementation
- **Migration Data**: See `ALFRED_MIGRATION_DATA.md` for reusable patterns

---

## 🤖 Key Differences from ALFRED

| Aspect | ALFRED | STARK |
|--------|--------|-------|
| Learning | Static | Continuous |
| Memory | 20 exchanges | 1M experiences |
| Adapters | None | 50+ LoRA adapters |
| Training | Offline only | Background thread |
| Forgetting | N/A | Prevented via replay |

---

## ⚡ Hardware Requirements

- **GPU**: RTX 4060 (8GB) or better
- **RAM**: 16-24GB system RAM
- **Storage**: 10GB for models + adapters
- **OS**: Windows/Linux with CUDA 12.x

---

**Built from scratch. Learning never stops. 🚀**
