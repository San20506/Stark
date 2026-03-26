# STARK Memory Module
from memory.memory_node import MemoryNode
from memory.neuromorphic_memory import NeuromorphicMemory, get_memory
from memory.appraisal_engine import AppraisalEngine
from memory.diary_store import DiaryStore, DiaryEntry, DiaryRecord
from memory.activation_scorer import ActivationScorer
from memory.episode_manager import EpisodeManager, Episode
from memory.thread_state import (
    ThreadStateManager,
    SessionState,
    get_thread_state_manager,
)
from memory.knowledge_graph import ConceptNode, KnowledgeGraph
from memory.reflection_loop import ReflectionLoop, ReflectionResult
from memory.tool_schema_store import ToolSchemaStore, ToolSchema
from memory.consolidation import ConflictGroup, ConsolidationJob

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
        _diary_store_instance = DiaryStore()
    return _diary_store_instance
