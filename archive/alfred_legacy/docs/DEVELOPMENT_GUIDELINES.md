# 📐 ALFRED Development Guidelines

**Version:** 1.0  
**Last Updated:** 2025-12-15

---

## 🎯 Purpose

This document establishes the rules and best practices for developing within the ALFRED project. Following these guidelines ensures the codebase remains clean, consistent, and easy to navigate.

---

## 📂 Directory Structure Rules

The project is organized into specific directories, each with a defined purpose. **Always place files in the correct location.**

| Directory | Purpose | File Types |
|-----------|---------|------------|
| `launchers/` | Application entry points | `.py`, `.bat` |
| `agents/` | Core cognitive architecture (brain, LLM, memory, research) | `.py` |
| `core/` | Tool definitions and reasoning logic | `.py` |
| `skills/` | Skill system framework | `.py` |
| `skills/examples/` | Reusable skill implementations | `.py` |
| `memory/` | Persistent memory systems (semantic, conversation, personality) | `.py` |
| `utils/` | Supporting utilities (audio, input, web, debug) | `.py` |
| `tests/` | All test and verification scripts | `.py` |
| `docs/` | **ALL documentation** | `.md`, `.txt` |
| `archive/` | Deprecated files (for reference only) | Any |

### ⚠️ Critical Rules

1.  **Root Directory is Sacred:**
    *   Only `README.md` and `requirements.txt` may exist in the project root.
    *   All other files MUST be placed in the appropriate subdirectory.

2.  **Documentation Location:**
    *   **ALL** Markdown (`.md`) files go into `docs/`.
    *   The only exception is the root `README.md`.

3.  **No Orphan Files:**
    *   Every file must belong to a logical directory.
    *   If a file doesn't fit, re-evaluate its purpose or create an appropriate location via discussion.

---

## 🐍 Python Coding Standards

### General

*   Follow **PEP 8** style guidelines.
*   Maximum line length: **100 characters**.
*   Use **4 spaces** for indentation (no tabs).

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | `snake_case` | `user_input`, `response_text` |
| Functions | `snake_case` | `get_weather()`, `process_audio()` |
| Classes | `PascalCase` | `CognitiveEngine`, `SkillLoader` |
| Constants | `UPPER_SNAKE_CASE` | `LLM_MODEL`, `MAX_RETRIES` |
| Private | `_leading_underscore` | `_internal_helper()` |

### Type Hints

*   Use type hints for all function signatures.

```python
# Good
def process_query(query: str, max_tokens: int = 100) -> dict:
    ...

# Avoid
def process_query(query, max_tokens=100):
    ...
```

### Docstrings

*   Every public function, class, and module must have a docstring.
*   Use Google-style docstrings.

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
    ...
```

---

## 🧪 Testing Guidelines

### Location

*   All tests go in the `tests/` directory.

### Naming

*   Test files: `test_<module_name>.py`
*   Test functions: `test_<functionality_being_tested>()`

### Running Tests

```bash
# Run all smoke tests
python tests/smoke_test.py

# Run specific test file
python tests/test_benchmark.py
```

### Before Committing

1.  Run smoke tests to ensure no regressions.
2.  Add new tests for any new functionality.

---

## 🔧 Adding New Components

### Adding a New Tool

1.  Open `core/benchmark_tools.py`.
2.  Add your function with a complete docstring.
3.  Register the tool in `get_all_tools()`.
4.  Add a test in `tests/test_benchmark.py`.

### Adding a New Skill

1.  Create a new file in `skills/examples/` (e.g., `my_new_skill.py`).
2.  Follow the pattern of existing skills (`get_weather.py`).
3.  ALFRED will auto-load it at runtime.

### Adding a New Agent/Module

1.  Place the file in `agents/` if it's part of cognitive architecture.
2.  Place the file in `utils/` if it's a supporting utility.
3.  Update imports in the relevant launcher or brain module.

### Adding Documentation

1.  Create your `.md` file in `docs/`.
2.  Link to it from `README.md` if it's essential.

---

## 📝 Git Commit Standards

### Commit Message Format

```
<type>(<scope>): <short summary>

<optional body>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |

### Examples

```
feat(skills): add weather forecast skill
fix(brain): resolve infinite loop in planning phase
docs: update DEVELOPMENT_GUIDELINES.md
refactor(memory): consolidate semantic memory classes
test(benchmark): add tests for new NLP tools
```

---

## 🚀 Development Workflow

### 1. Before Starting

```bash
cd d:\ALFRED
```

### 2. Make Changes

*   Edit files in the appropriate directory.
*   Follow all naming and style conventions.

### 3. Test

```bash
python tests/smoke_test.py
```

### 4. Verify Structure

*   Ensure no new files are in the root directory.
*   Ensure all `.md` files are in `docs/`.

### 5. Commit

```bash
git add .
git commit -m "feat(scope): description"
```

---

## 📋 Quick Reference Checklist

Before submitting any change:

- [ ] Code follows PEP 8 style
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] New files are in the correct directory
- [ ] No new files in root (except README.md, requirements.txt)
- [ ] All `.md` files are in `docs/`
- [ ] Tests pass
- [ ] Commit message follows convention

---

## 🔗 Related Documents

*   [README.md](../README.md) - Project overview
*   [STRUCTURE.md](STRUCTURE.md) - Detailed structure guide
*   [ROADMAP_TO_JARVIS.md](ROADMAP_TO_JARVIS.md) - Future development roadmap

---

*These guidelines ensure ALFRED remains a clean, professional, and maintainable project.*
