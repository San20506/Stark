# STARK Adaptive Orchestrator - Interactive Demo

## 🎯 What is This?

An **interactive web interface** to demonstrate STARK's Adaptive Orchestrator - an intelligent multi-model routing system that automatically selects the best AI model based on your query's complexity.

## 🚀 Quick Start

### 1. Start the Server

```bash
python3 web_server.py
```

### 2. Open Your Browser

Navigate to: **http://localhost:5000**

### 3. Try Some Queries!

- **"Hello STARK!"** → Fast model (llama3.2:3b, ~2-5s)
- **"Debug this IndexError"** → Thinking model (qwen3:4b, ~30-60s)
- **"Make me a sandwich"** → Edge case (Router analyzes intent)

## 📊 What You'll See

The web interface shows:

1. **Query Input** - Type or click example queries
2. **Routing Decision** - See which model was selected and why
   - Task detected
   - Confidence score
   - Model selected
   - Routing method (Direct vs Adaptive Router)
   - Response latency
3. **Response** - The AI's answer
4. **Architecture Diagram** - Visual flow of the routing logic

## 🧠 How It Works

```
Your Query
    ↓
TaskDetector (Fast TF-IDF)
    ↓
[High Confidence > 0.6?]
    ├─ YES → Direct to specialized model
    │         • conversation → llama3.2:3b (Fast)
    │         • code_* → qwen3:4b (Thinking)
    │
    └─ NO  → AdaptiveRouter
              • LLM analyzes intent
              • Detects complexity
              • Smart model selection
```

## 🎨 Features

- ✅ **Real-time** query processing
- ✅ **Visual feedback** on routing decisions
- ✅ **Multiple models** working together
- ✅ **Intelligent routing** based on complexity
- ✅ **Example queries** for quick testing
- ✅ **Beautiful UI** with glassmorphism design

## 📁 Files

| File | Purpose |
|------|---------|
| `web_server.py` | Flask backend server |
| `web/orchestrator_demo.html` | Interactive frontend |
| `core/adaptive_router.py` | Intelligent routing logic |
| `core/task_detector.py` | Fast task classification |

## 🔧 API Endpoints

- `GET /` - Serve the demo page
- `POST /api/predict` - Process a query
- `GET /api/stats` - Get system statistics
- `GET /api/health` - Health check

## 💡 Tips

1. **First query is slow** - Models need to load into memory
2. **Subsequent queries are faster** - Models stay warm
3. **Try edge cases** - See how the router handles unknowns
4. **Watch the confidence** - See when AdaptiveRouter kicks in

## 🛑 Stopping the Server

Press `Ctrl+C` in the terminal running the server.

## 📝 Example API Usage

```python
import requests

response = requests.post('http://localhost:5000/api/predict', json={
    'query': 'Hello STARK!'
})

print(response.json())
# {
#   'task': 'conversation',
#   'confidence': 0.95,
#   'model': 'llama3.2:3b',
#   'routing_method': 'Direct Routing',
#   'response': 'Hello! How can I help you today?',
#   'latency_ms': 2450
# }
```

---

**Built with**: Python, Flask, HTML/CSS/JavaScript
