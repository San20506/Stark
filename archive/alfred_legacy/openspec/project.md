# Project Context

## Purpose

ALFRED (Autonomous AI Assistant) is a JARVIS-level autonomous AI assistant featuring:
- **Cognitive Planning** - Autonomous goal decomposition and multi-step execution
- **42+ Integrated Tools** - Time, Math, Weather, Search, NLP, Analysis, and more
- **Persistent Memory** - Short-term (RAM), Long-term (SQLite), and Semantic (ChromaDB)
- **Multi-modal Input** - Voice, Text, and Hybrid interaction modes
- **Dynamic Skills** - Runtime skill loading and generation
- **Autonomous Research** - Parallel web research with source citation

The goal is to achieve JARVIS-level parity (~60-70% complete) with a focus on reasoning, proactive behavior, and multimodal capabilities.

## Tech Stack

### Core Technologies
- **Python 3.11+** - Primary language
- **Ollama** - Local LLM inference (deepseek-r1:1.5b default)
- **ChromaDB** - Vector database for semantic memory
- **SQLite** - Conversation history persistence
- **PyTorch** - ML framework for training/inference

### Speech & Audio
- **faster-whisper** - Speech-to-text (CPU optimized)
- **piper-tts** - Neural text-to-speech
- **edge-tts** - Cloud TTS fallback
- **silero-vad** - Voice activity detection
- **openwakeword** - Wake word detection

### GUI & Visualization
- **PyQt6** - GUI framework
- **pyqtgraph** - Scientific plotting

### Web & Research
- **beautifulsoup4** - HTML parsing
- **requests** - HTTP client
- **googlesearch-python** - Google search API

### Training & Fine-tuning
- **transformers** - HuggingFace models
- **peft** - LoRA fine-tuning
- **bitsandbytes** - Quantization
- **tensorflow** - NLU model training

## Project Conventions

### Code Style
- Follow **PEP 8** style guidelines
- Maximum line length: **100 characters**
- Use **4 spaces** for indentation (no tabs)
- Use **snake_case** for variables and functions
- Use **PascalCase** for classes
- Use **UPPER_SNAKE_CASE** for constants
- Use **_leading_underscore** for private members

### Type Hints
All function signatures must include type hints:
```python
def process_query(query: str, max_tokens: int = 100) -> dict:
    ...
```

### Docstrings
Use Google-style docstrings for all public functions and classes:
```python
def analyze_sentiment(text: str) -> dict:
    """Analyzes the sentiment of the given text.

    Args:
        text: The input text to analyze.

    Returns:
        A dictionary containing 'sentiment' (str) and 'confidence' (float).

    Raises:
        ValueError: If text is empty.
    """
```

### Architecture Patterns
- **Singleton Pattern** - Used for services (`get_xxx()` factory functions)
- **Cognitive Loop** - Perceive → Plan → Execute → Reflect
- **Tool Registry** - Declarative tool definitions with automatic discovery
- **Event-driven** - Async event handling for sensors and triggers

### Testing Strategy
- All tests go in `tests/` directory
- Test files: `test_<module_name>.py`
- Test functions: `test_<functionality_being_tested>()`
- Run smoke tests before committing: `python tests/smoke_test.py`
- Add new tests for any new functionality

### Git Workflow
Commit message format:
```
<type>(<scope>): <short summary>

<optional body>
```

Types:
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |

## Domain Context

### Cognitive Architecture
The brain (`agents/brain.py`) implements a 4-phase cognitive loop:
1. **Perceive** - Understand user intent and context
2. **Plan** - Decompose goals into executable subtasks
3. **Execute** - Run tasks using available tools
4. **Reflect** - Verify results and improve if needed

### Memory Hierarchy
- **Short-term** - Last 20 interactions (RAM, ConversationMemory)
- **User Profile** - Persistent preferences (JSON file)
- **Semantic Memory** - Intelligent retrieval (ChromaDB vectors)
- **Conversation DB** - Full history (SQLite)

### Tool System
- **Core Tools** (8) - Essential utilities in `core/tools.py`
- **Benchmark Tools** (34) - Advanced capabilities in `core/benchmark_tools.py`
- **Dynamic Skills** - User-defined in `skills/examples/`

### 7-Tier JARVIS Benchmark
| Tier | Name | Status |
|------|------|--------|
| 1 | Foundations | ✅ PASSED |
| 2 | Research | ✅ PASSED |
| 3 | Planning | ✅ PASSED |
| 4 | Tool Orchestra | ✅ PASSED |
| 5 | Cognitive | ✅ PASSED |
| 6 | Autonomy | ✅ PASSED |
| 7 | Reasoning | ⚠️ BASIC |

## Important Constraints

### Directory Structure Rules
| Directory | Purpose |
|-----------|---------|
| `launchers/` | Application entry points only |
| `agents/` | Core cognitive architecture |
| `core/` | Tool definitions and reasoning logic |
| `skills/` | Skill system framework |
| `memory/` | Persistent memory systems |
| `utils/` | Supporting utilities |
| `tests/` | All test scripts |
| `docs/` | ALL documentation (`.md` files) |
| `archive/` | Deprecated files (reference only) |
| `training/` | Model training scripts and data |
| `data/` | Training data and caches |
| `models/` | Trained model weights |

### Critical Rules
1. **Root Directory is Sacred** - Only `README.md` and `requirements.txt` in root
2. **Documentation Location** - ALL `.md` files go in `docs/` (except root README.md)
3. **No Orphan Files** - Every file must belong to a logical directory

### Hardware Constraints
- **GPU VRAM**: 24GB available
- **CUDA Version**: 13.0 (some packages require CUDA 12.x or lower)
- **Target Models**: Nemotron-3-Nano (preferred), DeepSeek-Coder-V2-Lite (alternative)

## External Dependencies

### Required Services
- **Ollama** - Must be running (`ollama serve`) for LLM inference
- **Internet** - Required for web research features

### Key External APIs
- **HuggingFace** - Model downloads (authenticated via `hf auth login`)
- **Google Search** - Web search functionality
- **Edge TTS** - Microsoft cloud-based text-to-speech

### Model Weights
- **Ollama Models**: `deepseek-r1:1.5b` (default)
- **Fine-tuning Target**: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`
- **LoRA Weights**: Saved to `models/codebrain_lora/`

### Data Files
- **Training Data**: `data/training/*.jsonl`
- **Intent Library**: `data/intent_library.json`
- **Doc Cache**: `data/doc_cache/` (scraped documentation)
