# About STARK (Self-Training Adaptive Reasoning Kernel)

## 📍 Project Location
**Path:** `/home/sandy/Projects/Stark`

## 🧠 What is STARK?
STARK is an advanced, offline-first, self-optimizing AI system designed to run entirely on consumer-grade hardware (specifically optimized for an RTX 4060 8GB GPU and 16-24GB of system RAM). Unlike static LLM wrappers, STARK learns continuously from natural interactions, retains knowledge through a custom memory system, and seamlessly coordinates specialized agents to execute complex tasks autonomously.

### Key Capabilities
- **Ultra-Fast Inference:** Designed to achieve < 50ms - 100ms latency per query via optimized Ollama integration.
- **Continuous Learning:** Uses background threads to train LoRA (Low-Rank Adaptation) adapters on the fly, avoiding catastrophic forgetting through a 1M+ experience replay buffer.
- **Neuromorphic Memory:** Stores over 100K semantic memory nodes with activation tracking, dynamic decay, and background garbage collection.
- **Multi-Agent Orchestration:** A sophisticated `RouterAgent` coordinates specialized autonomous agents (CodeAgent, FileAgent, WebAgent, RAG, Desktop Automation) to plan and execute multi-step goals.
- **MCP Integration:** Fully supports the Model Context Protocol (MCP) as both a client and a server, enabling it to control external tools (like filesystems and SQL) and be utilized by other MCP-compatible AI systems.

## 🏗️ Architecture & Core Components
The project follows a highly modular, decoupled architecture:

1. **Agents (`agents/`)**: The execution brain of STARK. Includes highly specialized agents for coding (with auto-testing/fixing), local file operations, web scraping, and general research.
2. **Learning System (`learning/`)**: Handles creation, activation, and asynchronous background training of lightweight (5-10MB) LoRA adapters. Up to 5 adapters can be dynamically loaded into VRAM simultaneously to swap specialized "skills".
3. **Memory (`memory/`)**: Neuromorphic associative memory that maps relationships between user queries and AI responses, automatically forgetting less relevant data.
4. **Capabilities (`capabilities/`)**: Domain-specific application logic, including complex reasoning, code generation/explanation, system health monitoring, and error debugging.
5. **RAG & Automation (`rag/`, `automation/`)**: Local embedding-based semantic search over documents, and OS-level desktop/window interaction capabilities.
6. **Voice (`voice/`)**: Integrated Speech-to-Text and Text-to-Speech (utilizing models like GPT-SoVITS) for fully hands-free interactions.

## ⚙️ Hardware Limits & Safety
- **GPU:** NVIDIA RTX 4060 (8GB VRAM) or better. Includes a hard limit to stop accepting new tasks if VRAM usage exceeds 7.5GB.
- **System Memory:** Maintains a strict <16GB RAM overhead during peak background training.
- **Storage:** Requires roughly 10GB for base models and LoRA adapters.
- **Failsafes:** Agents are wrapped in strict, configured execution timeouts (e.g., maximum 3 retries for the CodeAgent) and return strongly-typed `AgentResult` objects ensuring no unhandled crashes.

## 📂 Code Layout Highlights
- `core/` - Global system constants (`constants.py`), environment-aware configuration (`config.py`), and the core orchestrator.
- `models/` - Hooks into the underlying AI inference engine (interacting heavily with the local Ollama API).
- `mcp/` - Server and client implementations for standardized tool execution.
- `tests/` - Comprehensive `pytest` test suite containing unit, integration, and full "smoke tests" for the multi-agent pipelines.

## 🚀 How to Interface with STARK
STARK is accessible through three primary system interfaces depending on user preference:
1. **CLI Mode** (`python stark_cli.py`): Native Linux terminal interactive session.
2. **Voice Mode** (`python run_voice.py`): Audio-only pipeline utilizing voice models.
3. **Web API & UI** (`python web_server.py`): Browser-based graphical interface and REST endpoints (which also hosts the MCP management dashboard).

---

*This document serves as a high-level topographical map. For deep-dive developer guidelines, configuration mechanisms, and code styles, please consult `AGENTS.md` and `README.md`.*
