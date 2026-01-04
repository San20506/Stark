# ALFRED → STARK Migration Data
## Collected: 2025-12-20

This document preserves valuable learnings and reusable code from the ALFRED project before the rebuild to STARK architecture.

---

## 1. Project Statistics (Before Reset)

### Codebase Size
- **agents/**: 13 files, ~120KB (mcp.py, brain.py, llm.py, scheduler.py, etc.)
- **core/**: 7 files, ~95KB (benchmark_tools.py, fast_nlu.py, tools.py, etc.)
- **memory/**: 5 files, ~55KB (semantic_memory.py, conversation_db.py, etc.)
- **skills/**: 7 files, ~36KB (skill_loader.py, skill_validator.py, etc.)
- **utils/**: 5 files, ~28KB (audio_processor.py, web_search.py, etc.)
- **launchers/**: 8 files, ~45KB
- **training/**: Various files ~50KB
- **Total**: ~430KB of Python code

---

## 2. Key Architectural Learnings

### What Worked Well
1. **Singleton Pattern** - `get_xxx()` factory functions prevented resource conflicts
2. **FastNLU** - Sentence Transformer embeddings for <10ms intent classification
3. **ChromaDB for Semantic Memory** - Effective vector search for context
4. **Modular Tool Registration** - Declarative tool definitions
5. **Type Hints Everywhere** - Made debugging much easier

### What Didn't Work Well
1. **Scattered Voice Code** - 5+ files for voice functionality
2. **No Experience Replay** - System didn't learn from interactions
3. **Monolithic MCP** - 600+ lines doing too much
4. **No Background Learning** - Static after deployment
5. **Tight Coupling** - Modules hard to test independently

### Migration to STARK
- ALFRED's MCP → STARK's Main Orchestration
- ALFRED's FastNLU → STARK's Task Detector
- ALFRED's Memory → STARK's Experience Buffer (much improved)
- ALFRED's Tools → STARK's Capability Modules
- NEW: LoRA Adapters for continuous learning
- NEW: Background learning thread

---

## 3. Reusable Code Snippets

### 3.1 FastNLU Intent Classification (Portable to Task Detector)
```python
# From core/fast_nlu.py - Can be adapted for STARK's TaskDetector
from sentence_transformers import SentenceTransformer
import numpy as np

class TaskDetector:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.task_embeddings = {}
        
    def classify(self, query: str) -> tuple[str, float]:
        query_embedding = self.model.encode(query)
        best_task = None
        best_score = 0.0
        
        for task, embeddings in self.task_embeddings.items():
            similarities = [self._cosine_sim(query_embedding, e) for e in embeddings]
            score = max(similarities)
            if score > best_score:
                best_score = score
                best_task = task
                
        return best_task, best_score
    
    def _cosine_sim(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

### 3.2 Semantic Memory Pattern (Portable to Experience Buffer)
```python
# From memory/semantic_memory.py - Pattern for STARK's Experience Buffer
import chromadb
from sentence_transformers import SentenceTransformer

class ExperienceStore:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("experiences")
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        
    def add(self, query: str, response: str, task: str, metadata: dict = None):
        embedding = self.encoder.encode(f"{query} {response}").tolist()
        self.collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[embedding],
            documents=[f"Q: {query}\nA: {response}"],
            metadatas=[{"task": task, **(metadata or {})}]
        )
        
    def sample_by_task(self, task: str, n: int = 10):
        results = self.collection.query(
            query_texts=[""],
            where={"task": task},
            n_results=n
        )
        return results
```

### 3.3 Tool Registration Pattern
```python
# From core/tools.py - Tool registry pattern
from typing import Dict, Any, Callable
from dataclasses import dataclass

@dataclass
class Tool:
    name: str
    description: str
    function: Callable
    parameters: Dict[str, Any]

TOOL_REGISTRY: Dict[str, Tool] = {}

def register_tool(name: str, description: str, parameters: Dict[str, Any]):
    def decorator(func: Callable):
        TOOL_REGISTRY[name] = Tool(
            name=name,
            description=description,
            function=func,
            parameters=parameters
        )
        return func
    return decorator

@register_tool("get_time", "Get current time", {})
def get_time() -> dict:
    return {"time": datetime.now().isoformat()}
```

### 3.4 LLM Client Pattern
```python
# From agents/llm.py - Ollama client pattern
import ollama

class LLMClient:
    def __init__(self, model: str = "deepseek-r1:1.5b"):
        self.model = model
        
    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            options={"num_predict": max_tokens}
        )
        return response["response"]
        
    def stream(self, prompt: str):
        for chunk in ollama.generate(
            model=self.model,
            prompt=prompt,
            stream=True
        ):
            yield chunk["response"]
```

### 3.5 Scheduler Pattern
```python
# From agents/scheduler.py - APScheduler pattern
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        
    def add_cron_job(self, func: Callable, cron_expr: str, job_id: str):
        trigger = CronTrigger.from_crontab(cron_expr)
        self.scheduler.add_job(func, trigger, id=job_id)
        
    def start(self):
        self.scheduler.start()
        
    def stop(self):
        self.scheduler.shutdown()
```

---

## 4. Useful Constants & Configurations

### From ALFRED's requirements.txt (Relevant for STARK)
```
# Core ML
torch>=2.0.0
transformers>=4.35.0
peft>=0.7.0
bitsandbytes>=0.41.0

# Embeddings
sentence-transformers>=2.2.0
chromadb>=0.4.0

# Utilities
numpy>=1.24.0
scikit-learn>=1.3.0
pyyaml>=6.0

# Optional: Audio
sounddevice>=0.4.6
faster-whisper>=1.0.0
piper-tts>=1.2.0
```

### Model Configurations
```python
# GPU: RTX 4060 with 8GB VRAM (actually 24GB system RAM)
# These settings were tested and working:

VRAM_CONFIGS = {
    "inference_only": {
        "quantization": "int8",
        "max_model_size": "7B",
        "batch_size": 1,
        "max_length": 512,
    },
    "inference_with_lora": {
        "quantization": "int8",
        "base_model": "frozen",
        "lora_rank": 8,
        "lora_alpha": 16,
    }
}
```

---

## 5. Training Data (Preserved)

### Location
- `data/training/pytorch_training.jsonl` - 80 PyTorch examples
- `data/training/_merged_training.jsonl` - Combined dataset
- `data/intent_library.json` - Intent examples for NLU

### Format
```json
{
    "instruction": "Write PyTorch code to: create a tensor",
    "output": "tensor = torch.tensor([1, 2, 3])",
    "source": "pytorch_docs"
}
```

---

## 6. OpenSpec Specifications (Worth Keeping)

### Created Specs
1. **cognitive-engine** - Intent detection, module routing, response formatting
2. **tool-system** - 42+ tools in 8 categories
3. **memory-system** - Short-term, semantic, conversation DB
4. **nlu-system** - Fast intent classification
5. **skill-system** - Dynamic skill loading
6. **scheduler** - Background task management

### Pending Changes
- `add-unified-voice-interface` - Voice interface proposal (27 tasks)

---

## 7. Key Files to Reference

| ALFRED File | STARK Equivalent | Notes |
|-------------|------------------|-------|
| `agents/mcp.py` | `core/main.py` | Main orchestrator |
| `core/fast_nlu.py` | `core/task_detector.py` | Intent/task classification |
| `memory/semantic_memory.py` | `memory/experience_buffer.py` | Vector-based recall |
| `agents/llm.py` | `models/stark_base.py` | Model loading |
| `core/benchmark_tools.py` | `capabilities/*.py` | Domain modules |
| `agents/scheduler.py` | Built into `learning/continual_learner.py` | Background processing |

---

## 8. Lessons for STARK Build

1. **Start with constants.py** - ALFRED had hardcoded values scattered everywhere
2. **Test each module independently** - ALFRED's tight coupling made debugging hard
3. **Background learning from Day 1** - ALFRED was static
4. **Experience replay is critical** - Without it, system can't improve
5. **Keep adapters small** - 5MB each max, modular by task
6. **Log everything** - ALFRED's logging was inconsistent

---

## 9. Git History Summary

Key milestones in ALFRED development:
- Initial JARVIS voice assistant
- Added FastNLU for intent classification
- Added semantic memory with ChromaDB
- Added skill system
- Added scheduler
- 7-tier JARVIS benchmark implementation
- OpenSpec integration

---

**This document should be preserved in the new STARK project as `docs/ALFRED_MIGRATION.md`**
