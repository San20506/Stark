# STARK Project Structure

```
Stark/
├── core/                    # Core AI engine
│   ├── main.py             # STARK main class
│   ├── task_detector.py    # Task classification
│   ├── adaptive_router.py  # Smart routing
│   ├── safety_filter.py    # Safety validation
│   └── action_validator.py # Action approval
│
├── agents/                  # Phase 4: Multi-agent framework
│   ├── base_agent.py       # Agent orchestrator
│   └── file_agent.py       # File operations agent
│
├── automation/              # Phase 4: Desktop automation
│   ├── window_control.py   # Window management
│   ├── app_launcher.py     # Application control
│   └── keyboard_mouse.py   # Input simulation
│
├── rag/                     # Phase 4: RAG system
│   ├── chunker.py          # Document chunking
│   ├── document_indexer.py # Vector indexing
│   └── retriever.py        # Semantic search
│
├── memory/                  # Neuromorphic memory
├── learning/                # Continual learning
├── voice/                   # Voice I/O
├── capabilities/            # Task capabilities
├── models/                  # ML models & adapters
│   └── voice/
│       └── gptsovits/      # Custom voice models
├── data/                    # Training data
├── docs/                    # Documentation
│   ├── phase4/             # Phase 4 docs
│   └── setup/              # Setup guides
├── tests/                   # Test suite
│   └── phase4/             # Phase 4 tests
│
├── stark_cli.py            # CLI interface
├── run_voice.py            # Voice mode launcher
├── web_server.py           # Web interface
└── README.md               # Main documentation
```

## Key Files

- **stark_cli.py** - Native Linux terminal interface
- **run_voice.py** - Voice interaction mode
- **web_server.py** - Web demo server

## Test Files

Located in `tests/phase4/`:
- test_agents.py - Agent framework tests
- test_automation.py - Desktop automation tests
- test_rag.py - RAG system tests
- test_safety.py - Safety system tests
- test_phase4_smoke.py - Comprehensive smoke test

## Documentation

Located in `docs/`:
- setup/VOICE_SETUP.md - Voice configuration
- setup/CLI_README.md - CLI usage guide
- setup/WEB_DEMO_README.md - Web demo guide
- phase4/PHASE4_PROGRESS.md - Phase 4 progress
- phase4/AGENTS_README.md - Agent framework docs
