# ALFRED Manual Testing Guide

## How to Test Each Feature

Run from `d:\ALFRED` directory.

---

## 1. NLU (Intent Detection)

**Test Command:**
```bash
python -c "
from core.nlu import IntentDetector
d = IntentDetector()
d.load_model('models/nlu_jarvis.h5', 'data/jarvis/vocab.pkl')

# Test these queries:
queries = [
    'what time is it',
    'what is the date',
    'calculate 25 times 4',
    'weather in Tokyo',
    'set an alarm for 7am',
    'remind me to call mom',
    'book a flight to Paris',
    'check my balance'
]

for q in queries:
    r = d.detect(q)
    print(f'{q:30} -> {r.intent:20} ({r.confidence:.0%})')
"
```

**Expected:** Each query returns correct intent with 70%+ confidence.

---

## 2. Time/Date Tools

**Test Command:**
```bash
python -c "from core.benchmark_tools import get_current_time, get_current_date; print('Time:', get_current_time()); print('Date:', get_current_date())"
```

**Expected:** Returns current time and date.

---

## 3. Math Calculator

**Test Command:**
```bash
python -c "from core.benchmark_tools import solve_math; print(solve_math('(25 * 4) + 100'))"
```

**Expected:** `{'expression': '(25 * 4) + 100', 'result': 200, ...}`

---

## 4. Web Search

**Test Command:**
```bash
python -c "from core.benchmark_tools import web_search; print(web_search('Python programming', 3))"
```

**Expected:** Returns 3 search results with titles and URLs.

---

## 5. Desktop Control - Get Windows

**Test Command:**
```bash
python -c "from agents.desktop_control import get_desktop_controller; c = get_desktop_controller(); print('Windows:'); [print(f'  {w.title[:50]}') for w in c.get_all_windows()[:5]]"
```

**Expected:** Lists open windows.

---

## 6. Desktop Control - Mouse Position

**Test Command:**
```bash
python -c "from agents.desktop_control import get_desktop_controller; c = get_desktop_controller(); print(f'Mouse: {c.get_mouse_position()}')"
```

**Expected:** Returns (x, y) coordinates.

---

## 7. Desktop Control - Open App (INTERACTIVE)

**Test Command:**
```bash
python -c "from agents.desktop_control import get_desktop_controller; c = get_desktop_controller(); c.open_app('notepad')"
```

**Expected:** Opens Notepad.

---

## 8. Desktop Control - Type Text (INTERACTIVE)

**CAUTION:** This will type text!

```bash
python -c "
from agents.desktop_control import get_desktop_controller
c = get_desktop_controller()
import time
c.open_app('notepad')
time.sleep(2)
c.type_text('Hello from ALFRED!')
"
```

**Expected:** Opens Notepad and types "Hello from ALFRED!".

---

## 9. Full Interactive Test

**Test Command:**
```bash
python tests/test_interactive.py
```

**Expected:** Interactive console to test ALFRED with natural language.

**Try these queries:**
- "what time is it?"
- "calculate 50 divided by 5"
- "weather in London"
- "search for Python tutorials"

---

## 10. Full Automated Test

**Test Command:**
```bash
python tests/quick_test.py
```

**Expected:** All 11 tests pass (100%).

---

## Quick Reference: All 46 Tools

| Category | Tools |
|----------|-------|
| **Retrieval** | time, date, convert, math, weather |
| **Language** | summarize, sentiment, entities, translate, detect_lang |
| **Documents** | pdf, ocr, image_objects, transcribe, screenshot, describe_image, describe_screen |
| **Reasoning** | answer, reason, multi_hop, explain |
| **Planning** | plan, email, todo, calendar, workflow |
| **Web** | search, facts, report |
| **Analytics** | csv, anomalies, chart, trends |
| **Safety** | uncertain, confidence, safe_check, explain_how |
| **Desktop** | click, type_text, press_key, hotkey, open_app, open_url, get_windows, activate_window, desktop_screenshot |

---

## Troubleshooting

### TensorFlow Warnings
Normal - can be ignored.

### Model Not Found
Run: `python training/train_jarvis.py` (takes ~30 min)

### ChromaDB Issues
Run: `pip install chromadb`

### Desktop Control Issues
Run: `pip install pyautogui pygetwindow`
