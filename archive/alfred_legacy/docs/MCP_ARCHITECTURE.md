# ALFRED MCP Architecture

## Overview

ALFRED now uses the **Master Control Program (MCP)** architecture, a modular agentic system where specialized modules handle different types of queries.

Based on: *"Proposed Architecture for a Local Offline Jarvis AI System"*

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              MASTER CONTROL PROGRAM (MCP)                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           INTENT DETECTION (Rule-based)              │   │
│  │  • Pattern matching for time, date, weather, math    │   │
│  │  • Extracts arguments from query                     │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │              MODULE ROUTING                          │   │
│  └──────────────────────┬──────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │
     ┌────────┬───────────┼───────────┬────────┬────────┐
     ▼        ▼           ▼           ▼        ▼        ▼
┌────────┐┌────────┐┌──────────┐┌────────┐┌────────┐┌────────┐
│  TIME  ││  MATH  ││  WEATHER ││ VISION ││ SEARCH ││  LLM   │
│  DATE  ││ MODULE ││  MODULE  ││ MODULE ││ MODULE ││FALLBACK│
└────────┘└────────┘└──────────┘└────────┘└────────┘└────────┘
```

## Modules

| Module | Function | Tool Used |
|--------|----------|-----------|
| TIME_DATE | Current time and date | `time`, `date` |
| MATH | Calculations | `math` (supports "times", "plus", etc.) |
| WEATHER | Weather forecasts | `weather` |
| VISION | Screenshots & analysis | `describe_screen` |
| SEARCH | Web search | `search` |
| TASK | Todo lists | `todo` |
| CODE | Code generation | LLM with code prompt |
| CONVERSATIONAL | General chat | LLM fallback |

## Key Benefits

1. **Reliable Tool Execution**: Rule-based routing ensures tools like `time` are always called (no LLM guessing)
2. **Fast Response**: Direct tool calls skip LLM inference for factual queries
3. **Modular**: Add new modules without changing core logic
4. **Scalable**: Each module is independent

## Usage

```bash
# Run with MCP (default)
python launchers/alfred.py

# Run with legacy ReAct mode
python launchers/alfred.py --mode legacy

# Quiet mode (less output)
python launchers/alfred.py -q
```

## Files

- `agents/mcp.py` - Master Control Program
- `launchers/alfred.py` - Unified launcher
- `core/benchmark_tools.py` - Tool implementations
- `agents/vision.py` - Vision module
- `archive/brain_react_legacy.py` - Old ReAct implementation (archived)
