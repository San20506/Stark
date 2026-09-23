# STARK Memory Module
"""Lazy exports (PEP 562) so `import memory.*` never pulls CUT modules implicitly."""

import importlib
from typing import Any

_LAZY_EXPORTS = {
    "MemoryNode": "memory.memory_node",
    "NeuromorphicMemory": "memory.neuromorphic_memory",
    "get_memory": "memory.neuromorphic_memory",
    "AppraisalEngine": "memory.appraisal_engine",
    "DiaryStore": "memory.diary_store",
    "DiaryEntry": "memory.diary_store",
    "DiaryRecord": "memory.diary_store",
    "ActivationScorer": "memory.activation_scorer",
    "EpisodeManager": "memory.episode_manager",
    "Episode": "memory.episode_manager",
    "ThreadStateManager": "memory.thread_state",
    "SessionState": "memory.thread_state",
    "get_thread_state_manager": "memory.thread_state",
    "ConceptNode": "memory.knowledge_graph",
    "KnowledgeGraph": "memory.knowledge_graph",
    "ReflectionLoop": "memory.reflection_loop",
    "ReflectionResult": "memory.reflection_loop",
    "ToolSchemaStore": "memory.tool_schema_store",
    "ToolSchema": "memory.tool_schema_store",
    "ConflictGroup": "memory.consolidation",
    "ConsolidationJob": "memory.consolidation",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module = importlib.import_module(_LAZY_EXPORTS[name])
        attr = getattr(module, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))

__all__ = [
    "MemoryNode",
    "NeuromorphicMemory",
    "get_memory",
    "AppraisalEngine",
    "DiaryStore",
    "DiaryEntry",
    "DiaryRecord",
    "get_diary_store",
    "ThreadStateManager",
    "SessionState",
    "get_thread_state_manager",
    "ActivationScorer",
    "EpisodeManager",
    "Episode",
    "ConceptNode",
    "KnowledgeGraph",
    "ReflectionLoop",
    "ReflectionResult",
    "ToolSchemaStore",
    "ToolSchema",
    "ConflictGroup",
    "ConsolidationJob",
]


_diary_store_instance = None


def get_diary_store():
    global _diary_store_instance
    if _diary_store_instance is None:
        from memory.diary_store import DiaryStore

        _diary_store_instance = DiaryStore()
    return _diary_store_instance
