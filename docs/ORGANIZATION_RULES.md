# STARK Project Organization Rules

## Directory Structure Standards

### Core Modules (`/core`)
**Purpose:** Core AI engine and orchestration
**Contents:**
- main.py - STARK main class
- task_detector.py - Task classification
- adaptive_router.py - Smart routing
- safety_filter.py - Input/output validation
- action_validator.py - Action approval system
- constants.py - System constants
- config.py - Configuration loader

**Rule:** No feature-specific code. Only core orchestration logic.

---

### Agents (`/agents`)
**Purpose:** Multi-agent framework (Phase 4)
**Contents:**
- base_agent.py - BaseAgent class and AgentOrchestrator
- *_agent.py - Specialized agents (file, code, web, etc.)
- __init__.py - Module exports

**Rule:** Each agent is self-contained in one file.

---

### Automation (`/automation`)
**Purpose:** Desktop automation (Phase 4)
**Contents:**
- window_control.py - Window management
- app_launcher.py - Application control
- keyboard_mouse.py - Input simulation
- __init__.py - Module exports

**Rule:** Linux-native tools only (wmctrl, xdotool, psutil).

---

### RAG (`/rag`)
**Purpose:** Document retrieval (Phase 4)
**Contents:**
- chunker.py - Document chunking
- document_indexer.py - Vector indexing (ChromaDB)
- retriever.py - Semantic search
- __init__.py - Module exports

**Rule:** All RAG data stored in `.stark/rag_index/`

---

### Memory (`/memory`)
**Purpose:** Neuromorphic memory system
**Contents:**
- neuromorphic_memory.py - Graph-based memory
- memory_node.py - Node representation
- __init__.py

**Rule:** Memory persisted to `data/memory.json`

---

### Learning (`/learning`)
**Purpose:** Continual learning
**Contents:**
- continual_learner.py - Background learning
- adapter_manager.py - LoRA adapters
- __init__.py

**Rule:** Adapters stored in `models/adapters/`

---

### Voice (`/voice`)
**Purpose:** Voice I/O
**Contents:**
- speech_to_text.py - STT
- text_to_speech.py - TTS (original)
- enhanced_tts.py - Enhanced TTS (ElevenLabs/edge-tts)
- gptsovits_tts.py - Custom voice (GPT-SoVITS)
- wake_word.py - Wake word detection
- audio_io.py - Audio handling
- __init__.py

**Rule:** Voice models in `models/voice/`

---

### Capabilities (`/capabilities`)
**Purpose:** Task execution modules
**Contents:**
- file_ops.py - File operations
- web_search.py - Web search
- email_handler.py - Email
- code_executor.py - Code execution

**Rule:** Each capability is independent and testable.

---

### Models (`/models`)
**Purpose:** ML models and adapters
**Structure:**
```
models/
├── adapters/          # LoRA adapters
├── voice/
│   ├── gptsovits/    # Custom voice models
│   └── Modelfile.*   # Ollama model configs
└── embeddings/        # Cached embeddings
```

**Rule:** Large files only. No code.

---

### Data (`/data`)
**Purpose:** Runtime data and training samples
**Contents:**
- memory.json - Persisted memory
- training_samples.json - Continual learning data
- feedback.json - User feedback

**Rule:** JSON format. Git-ignored for privacy.

---

### Docs (`/docs`)
**Purpose:** Documentation
**Structure:**
```
docs/
├── setup/            # Setup guides
├── phase4/           # Phase 4 documentation
├── architecture/     # System design docs
└── *.md             # Comprehensive guides
```

**Rule:** Markdown only. Keep updated.

---

### Tests (`/tests`)
**Purpose:** Test suite
**Structure:**
```
tests/
├── phase4/          # Phase 4 tests
├── unit/            # Unit tests
├── integration/     # Integration tests
└── *.py            # Test scripts
```

**Rule:** Mirror source structure. One test file per module.

---

### Root Level Files

**Allowed:**
- README.md - Main documentation
- PROJECT_STRUCTURE.md - This file
- requirements.txt - Python dependencies
- stark_cli.py - CLI interface
- run_voice.py - Voice launcher
- web_server.py - Web interface
- package.json - Node dependencies (minimal)

**Not Allowed:**
- Test files (→ tests/)
- Documentation (→ docs/)
- Random scripts (→ utils/ or delete)

---

## File Organization Rules

### 1. Documentation
**Before:** Root level READMEs scattered
**After:** All docs in `docs/`
- Setup guides → `docs/setup/`
- Phase docs → `docs/phase4/`
- Architecture → `docs/architecture/`

### 2. Test Files
**Before:** test_*.py in root
**After:** All in `tests/`
- Phase 4 tests → `tests/phase4/`
- Unit tests → `tests/unit/`
- Integration tests → `tests/integration/`

### 3. Temporary/Training Files
**Before:** .training/ with 450MB
**After:** Delete after use
- Export models to `models/`
- Save logs to `docs/`
- Clean working directory

### 4. Compiled Files
**Always clean:**
```bash
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete
```

---

## Naming Conventions

### Files
- Python modules: `snake_case.py`
- Documentation: `UPPERCASE.md` or `Title_Case.md`
- Tests: `test_module_name.py`

### Directories
- All lowercase: `automation/`, `agents/`, `rag/`
- No spaces or special chars

### Classes
- PascalCase: `BaseAgent`, `DocumentRetriever`

### Functions
- snake_case: `get_orchestrator()`, `search_documents()`

---

## Import Rules

### Absolute Imports
```python
from core.main import get_stark
from agents.base_agent import get_orchestrator
from rag.retriever import get_retriever
```

### Relative Imports (within module)
```python
from .base_agent import BaseAgent
from .file_agent import FileAgent
```

---

## Git Ignore Patterns

```
# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# Data
/data/*.json
/.stark/

# Models (large files)
/models/adapters/*.safetensors
/models/voice/*/models/

# Training artifacts
/.training/

# IDE
.vscode/
.idea/

# Node
node_modules/
```

---

## Cleanup Checklist

Before committing:
- [ ] Move docs to `docs/`
- [ ] Move tests to `tests/`
- [ ] Delete temp/training files
- [ ] Clean `__pycache__`
- [ ] Update PROJECT_STRUCTURE.md
- [ ] Run `tests/phase4/test_phase4_smoke.py`

---

## Module Dependencies

**Core → Nothing** (base layer)
**Agents → Core** (orchestration)
**Automation → None** (standalone)
**RAG → None** (standalone)
**Capabilities → Core, Agents** (execution)
**Memory → Core** (persistence)
**Learning → Core, Memory** (adaptation)
**Voice → None** (I/O)

**Rule:** No circular dependencies. Keep layers clean.
