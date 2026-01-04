# STARK CLI - Native Terminal Interface

## Overview

Native Linux terminal interface for the STARK Adaptive Orchestrator. Beautiful, interactive, and terminal-native.

## Usage

```bash
# Start interactive mode
python3 stark_cli.py

# Start with debug output
python3 stark_cli.py --debug
```

## Features

### Interactive Commands
- `/help` - Show available commands
- `/stats` - Display system statistics
- `/arch` - Show architecture diagram
- `/clear` - Clear screen
- `/quit` - Exit STARK

### Visual Elements
- ✅ ASCII art banner
- ✅ Color-coded output
- ✅ Tables for routing decisions
- ✅ Panels for responses
- ✅ Spinners for processing
- ✅ Architecture diagrams

### Example Session

```
╔═══════════════════════════════════════════════════════════╗
║                    STARK v0.1.0                           ║
║           Adaptive Orchestrator                           ║
╚═══════════════════════════════════════════════════════════╝

STARK> Hello!
  
  ┌─ Routing Decision ─────────────┐
  │ Task:      conversation        │
  │ Confidence: 95.0%              │
  │ Model:     llama3.2:3b         │
  │ Method:    Direct              │
  │ Latency:   2450ms              │
  └────────────────────────────────┘

  ╭─ Response ─────────────────────╮
  │ Hello! How can I help you?     │
  ╰────────────────────────────────╯

STARK> /stats

  ┌─ System Statistics ────────────┐
  │ Running:          Yes          │
  │ Queries:          1            │
  │ Memories:         17           │
  │ Uptime:           0h 2m        │
  └────────────────────────────────┘
```

## Dependencies

- `rich` - Beautiful terminal formatting (already installed)

## Why CLI Instead of Web?

STARK is Linux-native software designed to run on developer workstations:

1. **Terminal-first workflow** - Integrates with Linux environment
2. **No browser required** - Lightweight and fast
3. **SSH-friendly** - Works over remote connections
4. **Native feel** - Fits Linux tool philosophy
5. **Resource efficient** - No web server overhead

## Architecture

The CLI is a thin wrapper around STARK core:

```
stark_cli.py (Terminal UI)
    ↓
core/main.py (STARK orchestrator)
    ↓
core/adaptive_router.py (Intelligent routing)
    ↓
Ollama models (llama3.2, qwen3)
```

## Advanced Usage

### Pipe queries from file
```bash
cat queries.txt | python3 stark_cli.py
```

### Single query mode
```python
from core.main import get_stark
stark = get_stark()
stark.start()
result = stark.predict("Your query")
print(result.response)
```

---

**Native Linux software, as it should be.**
