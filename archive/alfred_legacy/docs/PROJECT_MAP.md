# 🗺️ ALFRED Project Map - Quick Reference

**Last Updated:** 2025-12-15

---

## 🎯 I Want To...

| Goal | Location | Command |
|------|----------|---------|
| **Start ALFRED** | `launchers/alfred.py` | `python launchers/alfred.py` |
| **Understand architecture** | `docs/ROADMAP_TO_JARVIS.md` | Open and read |
| **See all tools** | `core/benchmark_tools.py` | View file (42 tools) |
| **Add a skill** | `skills/examples/` | Create new .py file |
| **Modify the brain** | `agents/brain.py` | Edit cognitive engine |
| **Run tests** | `tests/smoke_test.py` | `python tests/smoke_test.py` |
| **Read docs** | `docs/` | Browse directory |
| **Check memory** | `memory/` | View memory systems |

---

## 📊 Project at a Glance

```
ALFRED (Root)
│
├── 📄 README.md                  ⭐ START HERE - Project overview
├── 📄 requirements.txt           📦 Dependencies
│
├── 🚀 launchers/        [6 files]   Entry points
│   ├── alfred.py                    ⭐ Main launcher
│   ├── alfred_pro.py                Autonomous mode
│   ├── alfred_hybrid.py             Voice mode
│   ├── alfred_hud.py                HUD interface
│   ├── quick_start.py               Quick test
│   └── run_alfred.bat               Windows launcher
│
├── 🧠 agents/           [4 files]   Cognitive architecture
│   ├── brain.py                     ⭐ Cognitive engine (30KB)
│   ├── llm.py                       LLM client
│   ├── memory.py                    Context management
│   └── researcher.py                Autonomous research
│
├── 🔧 core/             [3 files]   Tools & reasoning
│   ├── tools.py                     8 core tools
│   ├── benchmark_tools.py           ⭐ 34 JARVIS tools
│   └── reasoning.py                 Reflection logic
│
├── 🎯 skills/           [15 files]  Skill system
│   ├── skill_adapter.py             Convert code to skills
│   ├── skill_generator.py           Generate new skills
│   ├── skill_loader.py              Load skills dynamically
│   ├── skill_searcher.py            Find relevant skills
│   ├── skill_validator.py           Validate skills
│   ├── skill_request.py             Handle requests
│   └── examples/                    Example skills
│       ├── get_weather.py
│       ├── send_email.py
│       ├── text_translator.py
│       └── unit_converter.py
│
├── 💾 memory/           [3 files]   Memory systems
│   ├── semantic_memory.py           ChromaDB search
│   ├── conversation_db.py           SQLite history
│   └── personality_adapter.py       User preferences
│
├── 🛠️ utils/            [4 files]   Utilities
│   ├── audio_processor.py           Audio I/O
│   ├── hybrid_input.py              Voice + text
│   ├── web_search.py                Web utilities
│   └── debug_stack.py               Debugging
│
├── 🧪 tests/            [7 files]   Test suite
│   ├── smoke_test.py                Quick tests
│   ├── test_benchmark.py            Tool tests
│   ├── test_react.py                ReAct tests
│   └── ... (4 more)
│
├── 📚 docs/             [23 files]  Documentation
│   ├── ROADMAP_TO_JARVIS.md         ⭐ Complete roadmap
│   ├── STRUCTURE.md                 📖 Detailed structure guide
│   ├── PROJECT_MAP.md               🗺️ This map
│   ├── REORGANIZATION_SUMMARY.md    📋 Change summary
│   ├── FINAL_SUMMARY.md             Architecture
│   ├── RUNNING_ALFRED.md            How to run
│   ├── SETUP_GUIDE.md               Installation
│   └── ... (16 more)
│
└── 📦 archive/          [4 files]   Deprecated
    ├── main.py                      Old version
    └── ... (test files)
```

---

## 🎨 Color Legend

- ⭐ = **Essential/Start here**
- 🚀 = **Entry points**
- 🧠 = **Core intelligence**
- 🔧 = **Tools & capabilities**
- 🎯 = **Extensibility**
- 💾 = **Memory & learning**
- 🛠️ = **Supporting utilities**
- 🧪 = **Testing**
- 📚 = **Documentation**
- 📦 = **Archive**

---

## 📈 File Count by Directory

| Directory | Files | Purpose |
|-----------|-------|---------|
| `launchers/` | 6 | All ways to start ALFRED |
| `agents/` | 4 | Core cognitive architecture |
| `core/` | 3 | 42 tools + reasoning |
| `skills/` | 15 | Skill system (6) + examples (9) |
| `memory/` | 3 | Memory & personality |
| `utils/` | 4 | Supporting utilities |
| `tests/` | 7 | Test suite |
| `docs/` | 20 | All documentation |
| `archive/` | 4 | Old files |
| **Total** | **66** | **Organized files** |

---

## 🔄 Data Flow

```
User Input
    ↓
launchers/alfred.py
    ↓
agents/brain.py (Perceive)
    ↓
agents/brain.py (Plan)
    ↓
agents/brain.py (Execute)
    ├→ core/tools.py (8 tools)
    ├→ core/benchmark_tools.py (34 tools)
    ├→ skills/skill_loader.py (dynamic skills)
    ├→ agents/researcher.py (research)
    └→ agents/llm.py (LLM calls)
    ↓
agents/brain.py (Reflect)
    ↓
memory/semantic_memory.py (store)
memory/conversation_db.py (log)
    ↓
Response to User
```

---

## 🎓 Learning Path

### 🟢 Beginner (30 min)
1. Read `README.md`
2. Run `python launchers/alfred.py`
3. Try: "What's the weather?" or "Calculate 15 * 23"
4. Browse `docs/FINAL_SUMMARY.md`

### 🟡 Intermediate (2 hours)
1. Read `docs/ROADMAP_TO_JARVIS.md`
2. Explore `agents/brain.py` (cognitive engine)
3. Check `core/benchmark_tools.py` (42 tools)
4. Create a custom skill in `skills/examples/`

### 🔴 Advanced (1 day)
1. Study entire `agents/` directory
2. Understand tool orchestration in `core/`
3. Implement a new memory system in `memory/`
4. Contribute to the cognitive architecture

---

## 🚦 Quick Commands

```bash
# Start ALFRED (main)
python launchers/alfred.py

# Start in chat mode
python launchers/alfred.py --mode chat

# Start voice mode
python launchers/alfred_hybrid.py

# Run tests
python tests/smoke_test.py

# Quick test
python launchers/quick_start.py
```

---

## 📝 Key Files to Know

| File | Size | Importance | Description |
|------|------|------------|-------------|
| `agents/brain.py` | 30KB | ⭐⭐⭐⭐⭐ | The cognitive engine - most important |
| `core/benchmark_tools.py` | 27KB | ⭐⭐⭐⭐⭐ | 34 JARVIS-level tools |
| `launchers/alfred.py` | 6KB | ⭐⭐⭐⭐⭐ | Main entry point |
| `docs/ROADMAP_TO_JARVIS.md` | 14KB | ⭐⭐⭐⭐ | Complete roadmap & vision |
| `agents/researcher.py` | 3KB | ⭐⭐⭐⭐ | Autonomous research |
| `memory/semantic_memory.py` | 11KB | ⭐⭐⭐ | Intelligent memory |
| `skills/skill_loader.py` | 6KB | ⭐⭐⭐ | Dynamic skill system |

---

## 🎯 Common Modifications

### Change LLM Model
**File:** `launchers/alfred.py`  
**Line:** ~15-20  
**Change:** `LLM_MODEL = "deepseek-r1:1.5b"` → your model

### Add New Tool
**File:** `core/benchmark_tools.py`  
**Action:** Add function + register in `get_all_tools()`

### Create Custom Skill
**File:** `skills/examples/my_skill.py`  
**Action:** Follow pattern from existing skills

### Modify Cognitive Behavior
**File:** `agents/brain.py`  
**Functions:** `perceive()`, `plan()`, `execute()`, `reflect()`

### Add Memory Type
**File:** Create new file in `memory/`  
**Action:** Implement storage/retrieval interface

---

## ✅ Reorganization Summary

### What Changed
- **Before:** 51 files in root directory (chaos)
- **After:** 2 files in root + 9 organized directories (clean)

### Key Improvements
1. ✅ 96% reduction in root files
2. ✅ Clear separation of concerns
3. ✅ Easy navigation
4. ✅ Professional structure
5. ✅ No duplicates

### Files Moved
- 20 docs → `docs/`
- 6 launchers → `launchers/`
- 4 agents → `agents/`
- 3 core tools → `core/`
- 15 skill files → `skills/`
- 3 memory systems → `memory/`
- 4 utilities → `utils/`
- 7 tests → `tests/`
- 4 old files → `archive/`

---

## 🔗 Related Documents

- **README.md** - Main project overview
- **STRUCTURE.md** - Detailed structure guide
- **REORGANIZATION_SUMMARY.md** - What changed
- **docs/ROADMAP_TO_JARVIS.md** - Complete roadmap
- **docs/FINAL_SUMMARY.md** - Architecture summary

---

## 💡 Pro Tips

1. **Always start from root** - `cd d:\ALFRED`
2. **Use relative paths** - `python launchers/alfred.py`
3. **Check docs/STRUCTURE.md** - When lost, read this
4. **Read docstrings** - All code is well-documented
5. **Follow patterns** - Look at existing files before creating new ones

---

**Quick Reference Complete!** 🎉

*For detailed information, see the full documentation in `docs/`*
