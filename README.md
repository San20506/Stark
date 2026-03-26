# 🚀 STARK: Self-Training Adaptive Reasoning Kernel

**Version 0.2.0 — Neuro-Memory** | Built: 2025-12-20 | Current: 2026-03-20

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
├── mcp/                    # Model Context Protocol
│   ├── __init__.py         # MCP server/client implementation
│   ├── server.py           # STARK MCP server
│   ├── client.py           # External MCP client
│   └── agent.py            # MCP orchestration agent

├── utils/                  # Utilities
│   ├── logger.py           # Structured logging (Week 4)
│   ├── checkpoint.py       # Save/load state (Week 4)
│   ├── metrics.py          # Performance tracking (Week 4)
│   └── profiler.py         # Memory profiling (Week 4)

├── tests/                  # Test suite
│   ├── test_models.py
│   ├── test_learning.py
│   ├── test_capabilities.py
│   ├── test_integration.py
│   └── test_mcp.py         # MCP functionality tests

├── archive/                # Legacy code (ALFRED backup)
│   └── alfred_legacy/      # Previous implementation

├── data/                   # Training data
├── checkpoints/            # Model checkpoints
├── logs/                   # System logs

├── requirements.txt        # Dependencies
├── config.yaml            # Runtime configuration
└── README.md              # This file
```

---

## 🧠 v0.2.0 Memory Stack Architecture

STARK v0.2.0 adds a four-layer cognitive memory system modelled on human episodic and semantic memory:

```
┌─────────────────────────────────────────────────────────────────┐
│                 STARK v0.2.0 MEMORY STACK                      │
├─────────────────────────────────────────────────────────────────┤
│  PERCEPTION                                                     │
│  user input → appraisal_engine.py → 6D appraisal vector          │
│                                                                 │
│  WORKING CONTEXT                                               │
│  thread_state.py — session checkpoint / crash recovery           │
│  episode_manager.py — EM-LLM surprise-based segmentation        │
│                                                                 │
│  LONG-TERM MEMORY (three parallel stores)                       │
│  diary_store.py — append-only episodic SQLite log                │
│  activation_scorer.py — ACT-R retrieval ranking (0.7 sem + 0.3 temporal) │
│  knowledge_graph.py — A-MEM semantic graph with Zettelkasten links │
│                                                                 │
│  INFERENCE                                                      │
│  core/main.py — MEMORY_V2_ENABLED gated predict() path          │
│                                                                 │
│  ASYNC REFLECTION (post-conversation, ≤30s)                     │
│  reflection_loop.py — 3B CPU model, writes diary + tool schemas  │
│                                                                 │
│  NIGHTLY CONSOLIDATION                                          │
│  consolidation.py — promotes diary patterns → knowledge graph     │
└─────────────────────────────────────────────────────────────────┘
```

### Memory Modules

| Module | File | Description |
|--------|------|-------------|
| Appraisal Engine | `memory/appraisal_engine.py` | 6D emotion vector: novelty, valence, agency, coping, certainty, goal_relevance |
| Episode Manager | `memory/episode_manager.py` | EM-LLM surprise-based session segmentation |
| ACT-R Scorer | `memory/activation_scorer.py` | Base-level activation: log(sum(t_i^-d)) + semantic + noise |
| Knowledge Graph | `memory/knowledge_graph.py` | A-MEM graph: bidirectional links, episodic→semantic promotion |
| Diary Store | `memory/diary_store.py` | Append-only SQLite episodic log with semantic/time/emotion/tag query |
| Reflection Loop | `memory/reflection_loop.py` | Async post-conversation LLM summarization |
| Consolidation | `memory/consolidation.py` | Background daemon: conflict detection, pattern promotion |
| Tool Schema Store | `memory/tool_schema_store.py` | Schema CRUD with staleness eviction and confidence-weighted ranking |
| Thread State | `memory/thread_state.py` | Session persistence with SQLite WAL checkpointing |

### Feature Flag

`MEMORY_V2_ENABLED` in `core/constants.py` (default: `False`) gates the v0.2 path in `core/main.py`. Set to `True` to enable.

### Hardware Budget

| Resource | Budget | Allocation |
|----------|--------|-----------|
| VRAM (inference) | ≤ 6.0 GB | LLM + KV cache + embeddings |
| System RAM | ≤ 12 GB | Diary DB, graph, reflection model, OS |

### v0.2.0 Deliverables

| # | Deliverable | Location |
|---|-------------|----------|
| D5 | Appraisal engine | `memory/appraisal_engine.py` |
| D6 | EM-LLM episode manager | `memory/episode_manager.py` |
| D7 | ACT-R retrieval scorer | `memory/activation_scorer.py` |
| D8 | A-MEM knowledge graph | `memory/knowledge_graph.py` |
| D9 | Diary memory store | `memory/diary_store.py` |
| D10 | Reflection loop | `memory/reflection_loop.py` |
| D11 | Consolidation job | `memory/consolidation.py` |
| D12 | Tool schema store | `memory/tool_schema_store.py` |
| D13 | Thread state manager | `memory/thread_state.py` |
| D14 | Updated core/main.py | `core/main.py` |
| D15 | Updated constants/config | `core/constants.py`, `core/config.py` |
| D16 | Test suite | `tests/test_memory_v2.py` |
| D17 | Integration test | `tests/test_memory_integration.py` |

Full plan: `STARK_PLAN.md` | PID: `STARK_PID.md` | PRD: `STARK_PRD.md`

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

### 3. Install MCP Dependencies (Optional)

If you want to enable MCP (Model Context Protocol) support:

```bash
# MCP Python SDK
pip install mcp>=1.12.0

# Optional: Common MCP servers
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-git
npm install -g @modelcontextprotocol/server-sqlite
```

### 4. Download Large Files (Required)

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

# Download voice model (replace with your actual model source)
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

# Web Interface (includes MCP management)
python web_server.py

# MCP Server Only
python -m mcp.server

# MCP Client Test
python -m mcp.client
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
# Core Configuration
export STARK_MODEL_NAME="deepseek-ai/deepseek-coder-1.3b-instruct"
export STARK_MODEL_QUANTIZATION="int8"
export STARK_LORA_RANK="8"
export STARK_LEARNING_BATCH_SIZE="32"
export STARK_LOG_LEVEL="INFO"

# MCP Configuration
export STARK_MCP_SERVER_ENABLED="true"
export STARK_MCP_SERVER_HOST="localhost"
export STARK_MCP_SERVER_PORT="8080"
export STARK_MCP_CLIENT_ENABLED="true"
export STARK_MCP_CLIENT_TIMEOUT="30"
export STARK_MCP_MAX_SERVERS="10"
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

mcp:
  server:
    enabled: true
    host: "localhost"
    port: 8080
    name: "STARK"
  
  client:
    enabled: true
    timeout_seconds: 30
    max_servers: 10
```

---

## 🔌 MCP (Model Context Protocol)

STARK now supports MCP for seamless integration with external tools and applications.

### What MCP Enables

**As MCP Server**: Expose STARK capabilities to external applications:
- Code generation and analysis tools
- File system operations with safety checks
- Web scraping and interaction
- Memory access and learning
- Health monitoring and system control

**As MCP Client**: Access external tools and services:
- File system operations via `@modelcontextprotocol/server-filesystem`
- Git operations via `@modelcontextprotocol/server-git`
- Database access via `@modelcontextprotocol/server-sqlite`
- And thousands of community MCP servers

### MCP Usage Examples

#### Connect External MCP Server to STARK
```python
from core.main import get_stark
import asyncio

stark = get_stark()
stark.start()

# Connect to filesystem server
await stark.connect_mcp_server(
    server_id="filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/project"]
)

# Use enhanced query with external tools
result = await stark.process_query_with_mcp(
    "Read config.yaml and analyze the settings",
    use_external_tools=True
)
```

#### Access STARK via External MCP Client
```python
from mcp.client.stdio import stdio_client
from mcp import ClientSession

async def access_stark():
    server_params = {
        "command": "python",
        "args": ["-m", "stark.mcp.server"],
    }
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Use STARK's tools
            result = await session.call_tool(
                "stark_query",
                {"query": "Explain this code", "task_type": "code_explanation"}
            )
            
            print(result.content[0].text)
```

#### Web Interface MCP Management
```bash
# Start STARK with web interface
python web_server.py

# Access MCP endpoints
curl http://localhost:5000/api/mcp/status
curl http://localhost:5000/api/mcp/servers

# Connect to external server via web API
curl -X POST http://localhost:5000/api/mcp/connect \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
  }'
```

### Available STARK MCP Tools

| Tool | Description | Example |
|------|-------------|---------|
| `stark_query` | General STARK query with routing | `{"query": "What is machine learning?"}` |
| `stark_code_generate` | Code generation in any language | `{"prompt": "Create REST API", "language": "python"}` |
| `stark_file_read` | Safe file reading | `{"file_path": "config.yaml"}` |
| `stark_web_scrape` | Web content extraction | `{"url": "https://example.com"}` |
| `stark_memory_recall` | Neuromorphic memory search | `{"query": "previous conversations", "top_k": 5}` |

### MCP Resources

- `stark://config` - System configuration
- `stark://stats` - Runtime statistics  
- `stark://agents` - Available agents and capabilities

### Configuration

Enable/disable MCP features via environment variables or `config.yaml`:

```yaml
mcp:
  server:
    enabled: true        # Expose STARK as MCP server
    host: "localhost"
    port: 8080
  
  client:
    enabled: true        # Access external MCP servers
    timeout_seconds: 30
    max_servers: 10
```

---

## 📚 Documentation

- **Build Guide**: See `stark_complete_guide.md`
- **Legacy Code**: See `archive/alfred_legacy/` for previous implementation
- **Migration Data**: See `ALFRED_MIGRATION_DATA.md` for reusable patterns
- **MCP Guide**: See `mcp/README.md` for detailed MCP usage

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
