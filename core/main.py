"""
STARK Main Orchestrator
========================
Single entry point integrating all STARK modules into a unified system.

Module 8 of 9 - Orchestration
"""

import logging
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, Generator, List
from dataclasses import dataclass

from core.constants import (
    STARK_VERSION,
    STARK_CODENAME,
    TARGET_INFERENCE_LATENCY_MS,
    OLLAMA_BASE_URL,
    TASK_MODELS,
    OLLAMA_DEFAULT_MODEL,
    MCP_SERVER_ENABLED,
    MCP_CLIENT_ENABLED,
    MEMORY_V2_ENABLED,
)
from core.config import get_config, STARKConfig
from core.task_detector import get_detector, TaskDetector

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PredictionResult:
    """Result from a prediction call."""

    response: str
    task: str
    confidence: float
    latency_ms: float
    adapter_used: Optional[str] = None
    memory_stored: bool = False
    relevant_memories: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response,
            "task": self.task,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "adapter_used": self.adapter_used,
            "memory_stored": self.memory_stored,
            "relevant_memories": self.relevant_memories,
            "error": self.error,
        }


@dataclass
class SystemStatus:
    """Current system status."""

    running: bool
    uptime_seconds: float
    queries_processed: int
    memories_stored: int
    active_adapter: Optional[str]
    learning_active: bool
    vram_usage_gb: float
    last_query_time: Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "queries_processed": self.queries_processed,
            "memories_stored": self.memories_stored,
            "active_adapter": self.active_adapter,
            "learning_active": self.learning_active,
            "vram_usage_gb": round(self.vram_usage_gb, 2),
            "last_query_time": self.last_query_time.isoformat()
            if self.last_query_time
            else None,
        }


# =============================================================================
# MAIN STARK CLASS
# =============================================================================


class STARK:
    """
    Main STARK orchestrator integrating all modules.

    Usage:
        stark = get_stark()
        stark.start()
        result = stark.predict("How do I fix this IndexError?")
        print(result.response)
        stark.stop()
    """

    def __init__(self, lazy_load: bool = True):
        """Initialize STARK system."""
        self.config: STARKConfig = get_config()
        self._lazy_load = lazy_load

        # Module references (lazy loaded)
        self._task_detector: Optional[TaskDetector] = None
        self._memory = None  # NeuromorphicMemory
        self._learner = None  # ContinualLearner
        self._notifier = None  # NotificationManager
        self._mcp_manager = None  # MCPManager
        self._media_store = None  # MediaMemory (Gemini Embedding 2 + ChromaDB)
        self._ollama_available = False

        # Memory v2 cognitive pipeline modules (lazy loaded)
        self._appraisal_engine = None  # AppraisalEngine (6D emotion vector)
        self._knowledge_graph = None  # KnowledgeGraph (A-MEM)
        self._reflection_loop = None  # ReflectionLoop (async reflection)
        self._consolidation = None  # ConsolidationJob (background thread)
        self._thread_state_mgr = None  # ThreadStateManager (session checkpointing)
        self._diary_store = None  # DiaryStore (append-only episodic log)
        self._activation_scorer = None  # ActivationScorer (ACT-R retrieval ranking)
        self._episode_manager = None  # EpisodeManager (EM-LLM segmentation)
        self._tool_schema_store = None  # ToolSchemaStore (schema CRUD)
        self._current_session_id: Optional[str] = None

        # State
        self._running = False
        self._start_time: Optional[datetime] = None
        self._queries_processed = 0
        self._last_query_time: Optional[datetime] = None
        self._lock = threading.RLock()

        if not lazy_load:
            self._load_modules()

        logger.info(f"STARK v{STARK_VERSION} '{STARK_CODENAME}' initialized")

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    async def start_async(self) -> None:
        """Start STARK system and all background services (async version)."""
        with self._lock:
            if self._running:
                logger.warning("STARK already running")
                return

            logger.info("Starting STARK system...")
            self._load_modules()

            if self._learner is not None:
                self._learner.start()
                logger.info("Background learning thread started")

            # Start MCP manager if enabled
            if MCP_SERVER_ENABLED or MCP_CLIENT_ENABLED:
                try:
                    from mcp import get_mcp_manager

                    self._mcp_manager = get_mcp_manager()
                    await self._mcp_manager.start()
                    logger.info("MCP Manager started")
                except Exception as e:
                    logger.warning(f"Failed to start MCP Manager: {e}")

            self._running = True
            self._start_time = datetime.now()
            logger.info("STARK system started successfully")

    def start(self) -> None:
        """Start STARK system and all background services."""
        with self._lock:
            if self._running:
                logger.warning("STARK already running")
                return

            logger.info("Starting STARK system...")
            self._load_modules()

            if self._learner is not None:
                self._learner.start()
                logger.info("Background learning thread started")

            # Start MCP manager if enabled
            if MCP_SERVER_ENABLED or MCP_CLIENT_ENABLED:
                try:
                    import asyncio
                    from mcp import get_mcp_manager

                    self._mcp_manager = get_mcp_manager()

                    # Start MCP in background thread
                    def start_mcp():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self._mcp_manager.start())
                        loop.close()

                    mcp_thread = threading.Thread(target=start_mcp, daemon=True)
                    mcp_thread.start()
                    logger.info("MCP Manager started in background")
                except Exception as e:
                    logger.warning(f"Failed to start MCP Manager: {e}")

            self._running = True
            self._start_time = datetime.now()
            logger.info("STARK system started successfully")

    def stop(self) -> None:
        """Stop STARK system gracefully."""
        with self._lock:
            if not self._running:
                logger.warning("STARK not running")
                return

            logger.info("Stopping STARK system...")

            if self._learner is not None and self._learner.is_running():
                self._learner.stop(timeout=5.0)
                logger.info("Background learning thread stopped")

            if self._mcp_manager is not None:
                try:
                    self._mcp_manager.stop()
                    logger.info("MCP Manager stopped")
                except Exception as e:
                    logger.error(f"Failed to stop MCP Manager: {e}")

            if self._memory is not None:
                try:
                    self._memory.save()
                    logger.info("Memory state saved")
                except Exception as e:
                    logger.error(f"Failed to save memory: {e}")

            try:
                from memory.thread_state import get_thread_state_manager

                get_thread_state_manager().checkpoint_all()
            except Exception as e:
                logger.warning(f"Failed to checkpoint thread states: {e}")

            self._running = False
            logger.info("STARK system stopped")

    def _load_modules(self) -> None:
        """Load all required modules."""
        if self._task_detector is None:
            self._task_detector = get_detector()
            logger.info("TaskDetector loaded")

        if self._memory is None:
            try:
                from memory.neuromorphic_memory import NeuromorphicMemory

                self._memory = NeuromorphicMemory(lazy_load=False)
                self._memory.load()
                logger.info(
                    f"NeuromorphicMemory loaded: {self._memory.get_stats()['total_nodes']} nodes"
                )
            except Exception as e:
                logger.warning(f"Failed to load NeuromorphicMemory: {e}")
                self._memory = None

        if self._learner is None and self._memory is not None:
            try:
                from learning.continual_learner import ContinualLearner

                self._learner = ContinualLearner(
                    memory=self._memory,
                    ollama_url=OLLAMA_BASE_URL,
                )
                logger.info("ContinualLearner loaded")
            except Exception as e:
                logger.warning(f"Failed to load ContinualLearner: {e}")
                self._learner = None

        if self._media_store is None:
            try:
                import sys
                from pathlib import Path

                sys.path.insert(0, str(Path.home() / "media-memory"))
                import media_memory as _mm

                self._media_store = _mm
                logger.info("MediaMemory loaded (Gemini Embedding 2 + ChromaDB)")
            except Exception as e:
                logger.warning(
                    f"MediaMemory unavailable (set GEMINI_API_KEY to enable): {e}"
                )
                self._media_store = None

        if MEMORY_V2_ENABLED:
            self._load_modules_v2()

        self._check_ollama()

    def _check_ollama(self) -> bool:
        """Check if Ollama is available."""
        try:
            import requests

            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
            self._ollama_available = response.status_code == 200
            if self._ollama_available:
                logger.info("Ollama connection verified")
            else:
                logger.warning(f"Ollama returned status {response.status_code}")
        except Exception as e:
            self._ollama_available = False
            logger.warning(f"Ollama not available: {e}")
        return self._ollama_available

    def _load_modules_v2(self) -> None:
        """Load memory v2 cognitive pipeline modules."""
        if self._appraisal_engine is None:
            try:
                from memory.appraisal_engine import AppraisalEngine

                self._appraisal_engine = AppraisalEngine()
                logger.info("AppraisalEngine loaded")
            except Exception as e:
                logger.warning(f"Failed to load AppraisalEngine: {e}")

        if self._thread_state_mgr is None:
            try:
                from memory.thread_state import get_thread_state_manager

                self._thread_state_mgr = get_thread_state_manager()
                logger.info("ThreadStateManager loaded")
            except Exception as e:
                logger.warning(f"Failed to load ThreadStateManager: {e}")

        if self._diary_store is None:
            try:
                from memory.diary_store import get_diary_store

                self._diary_store = get_diary_store()
                logger.info("DiaryStore loaded")
            except Exception as e:
                logger.warning(f"Failed to load DiaryStore: {e}")

        if self._activation_scorer is None:
            try:
                from memory.activation_scorer import ActivationScorer

                self._activation_scorer = ActivationScorer()
                logger.info("ActivationScorer loaded")
            except Exception as e:
                logger.warning(f"Failed to load ActivationScorer: {e}")

        if self._episode_manager is None:
            try:
                from memory.episode_manager import EpisodeManager

                self._episode_manager = EpisodeManager()
                logger.info("EpisodeManager loaded")
            except Exception as e:
                logger.warning(f"Failed to load EpisodeManager: {e}")

        if self._knowledge_graph is None:
            try:
                from memory.knowledge_graph import KnowledgeGraph

                self._knowledge_graph = KnowledgeGraph()
                logger.info("KnowledgeGraph loaded")
            except Exception as e:
                logger.warning(f"Failed to load KnowledgeGraph: {e}")

        if self._tool_schema_store is None:
            try:
                from memory.tool_schema_store import ToolSchemaStore

                self._tool_schema_store = ToolSchemaStore()
                logger.info("ToolSchemaStore loaded")
            except Exception as e:
                logger.warning(f"Failed to load ToolSchemaStore: {e}")

        if self._reflection_loop is None:
            try:
                from memory.reflection_loop import ReflectionLoop

                self._reflection_loop = ReflectionLoop()
                logger.info("ReflectionLoop loaded")
            except Exception as e:
                logger.warning(f"Failed to load ReflectionLoop: {e}")

        if self._consolidation is None:
            try:
                from memory.consolidation import ConsolidationJob

                self._consolidation = ConsolidationJob()
                logger.info("ConsolidationJob loaded")
            except Exception as e:
                logger.warning(f"Failed to load ConsolidationJob: {e}")

    # =========================================================================
    # PREDICTION
    # =========================================================================

    def predict(self, query: str) -> PredictionResult:
        """Main prediction pipeline."""
        start_time = time.perf_counter()

        if self._task_detector is None:
            self._load_modules()

        try:
            with self._lock:
                self._queries_processed += 1
                self._last_query_time = datetime.now()

            # Step 0: Check for actionable intents (FAST PATH for system control)
            # This bypasses the slow LLM entirely for actions like "open firefox"
            try:
                from core.intent_classifier import get_intent_classifier
                from agents.action_executor import get_action_executor

                classifier = get_intent_classifier()
                intent = classifier.classify(query)

                if intent.is_actionable and intent.confidence >= 0.8:
                    logger.info(
                        f"Direct action: {intent.type.value} (target: {intent.target})"
                    )
                    executor = get_action_executor()
                    result = executor.execute(intent)

                    return PredictionResult(
                        response=result.message,
                        task=intent.type.value,
                        confidence=intent.confidence,
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                        memory_stored=False,
                    )
            except Exception as e:
                logger.debug(f"Action executor not available: {e}")

            # Step 1: Detect task
            detection = self._task_detector.detect(query)
            task = detection.task
            confidence = detection.confidence

            # Step 1.5: Memory v2 pipeline (appraisal + episode + scored recall)
            v2_context = ""
            if MEMORY_V2_ENABLED and self._thread_state_mgr is not None:
                try:
                    v2_context = self._run_v2_pipeline(query, task, confidence)
                except Exception as e:
                    logger.warning(f"Memory v2 pipeline failed: {e}")

            # Step 1.5: Adaptive routing for low-confidence queries
            if detection.is_emergent or confidence < 0.6:
                try:
                    from core.adaptive_router import get_router

                    router = get_router()

                    routing = router.route(query, task, confidence)

                    # Check if clarification needed
                    if routing.needs_clarification:
                        logger.info(
                            f"Clarification needed: {routing.clarification_prompt}"
                        )
                        return PredictionResult(
                            response=routing.clarification_prompt,
                            task="clarification",
                            confidence=routing.confidence,
                            latency_ms=(time.perf_counter() - start_time) * 1000,
                        )

                    # Update task and log reasoning
                    task = routing.task
                    logger.info(
                        f"Adaptive routing: {task} (reasoning: {routing.reasoning})"
                    )

                    # Check if we should use autonomous orchestrator for complex tasks
                    complex_tasks = [
                        "code_generation",
                        "error_debugging",
                        "system_control",
                        "research",
                    ]
                    if task in complex_tasks or confidence < 0.5:
                        try:
                            from agents.autonomous_orchestrator import (
                                get_autonomous_orchestrator,
                            )

                            logger.info(
                                "Using autonomous orchestrator for complex task"
                            )

                            orchestrator = get_autonomous_orchestrator()
                            result = orchestrator.predict(query)

                            return PredictionResult(
                                response=result.get(
                                    "response", "No response generated"
                                ),
                                task=task,
                                confidence=result.get("confidence", confidence),
                                latency_ms=result.get(
                                    "latency_ms",
                                    (time.perf_counter() - start_time) * 1000,
                                ),
                                memory_stored=False,
                            )
                        except Exception as e:
                            logger.warning(
                                f"Autonomous orchestrator failed: {e}, falling back to simple path"
                            )

                except ImportError:
                    logger.warning("AdaptiveRouter not available, using fast path")

            # Step 2: Recall relevant memories
            relevant_memories = []
            if MEMORY_V2_ENABLED and self._memory is not None:
                try:
                    memories = self._memory.recall(query, task=task, top_k=3)
                    relevant_memories = memories
                except Exception as e:
                    logger.warning(f"Memory recall failed: {e}")

            # Step 3: Generate response
            context = v2_context if v2_context else ""
            response = self._generate_response(query, task, relevant_memories, context)

            # Step 4: Store experience + update v2 state
            memory_stored = False
            if MEMORY_V2_ENABLED and self._memory is not None and response:
                try:
                    self._memory.store(query, response, task)
                    memory_stored = True
                except Exception as e:
                    logger.warning(f"Memory store failed: {e}")

            # Step 4.5: Update thread state + episode segmentation
            if MEMORY_V2_ENABLED and self._thread_state_mgr is not None and response:
                try:
                    self._update_v2_state(query, response, confidence)
                except Exception as e:
                    logger.warning(f"Memory v2 state update failed: {e}")

            latency_ms = (time.perf_counter() - start_time) * 1000

            if latency_ms > TARGET_INFERENCE_LATENCY_MS:
                logger.warning(f"Latency {latency_ms:.1f}ms exceeds target")

            return PredictionResult(
                response=response,
                task=task,
                confidence=confidence,
                latency_ms=latency_ms,
                memory_stored=memory_stored,
                relevant_memories=len(relevant_memories),
            )

        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            latency_ms = (time.perf_counter() - start_time) * 1000
            return PredictionResult(
                response="I encountered an error processing your request.",
                task="error",
                confidence=0.0,
                latency_ms=latency_ms,
                error=str(e),
            )

    def predict_stream(self, query: str) -> Generator[str, None, None]:
        """Stream prediction tokens as they're generated."""
        if self._task_detector is None:
            self._load_modules()

        try:
            detection = self._task_detector.detect(query)
            task = detection.task

            context = ""
            if self._memory is not None:
                memories = self._memory.recall(query, task=task, top_k=2)
                if memories:
                    context = "\n".join(
                        [
                            f"- {m[0].query}: {m[0].response[:100]}..."
                            for m in memories[:2]
                        ]
                    )

            prompt = self._build_prompt(query, task, context)

            if self._ollama_available:
                import requests
                import json

                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": self.config.model.name,
                        "prompt": prompt,
                        "stream": True,
                    },
                    stream=True,
                    timeout=30,
                )

                full_response = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        token = data.get("response", "")
                        full_response += token
                        yield token
                        if data.get("done", False):
                            break

                if self._memory is not None and full_response:
                    self._memory.store(query, full_response, task)
            else:
                yield "[Ollama not available]"

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"[Error: {e}]"

    def _generate_response(
        self, query: str, task: str, relevant_memories: List, context: str = ""
    ) -> str:
        """Generate response using Ollama with task-based model routing."""
        if not context and relevant_memories:
            context = "\n".join(
                [
                    f"- {m[0].query}: {m[0].response[:100]}..."
                    for m in relevant_memories[:3]
                ]
            )

        # Select model based on task
        model = TASK_MODELS.get(task, TASK_MODELS.get("default", OLLAMA_DEFAULT_MODEL))
        logger.debug(f"Task '{task}' -> Model '{model}'")

        prompt = self._build_prompt(query, task, context)

        if self._ollama_available:
            try:
                import requests

                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=60,
                )
                if response.status_code == 200:
                    return response.json().get("response", "")
            except Exception as e:
                logger.error(f"Ollama call failed: {e}")

        return f"[Task: {task}] I'm ready to help with: {query[:50]}..."

    def _build_prompt(self, query: str, task: str, context: str = "") -> str:
        """Build the prompt for the LLM."""
        system = (
            f"You are STARK, a helpful AI assistant specialized in {task}. Be concise."
        )

        if context:
            return f"{system}\n\nContext:\n{context}\n\nUser: {query}\n\nAssistant:"
        return f"{system}\n\nUser: {query}\n\nAssistant:"

    def _run_v2_pipeline(self, query: str, task: str, confidence: float) -> str:
        """Run the 7-step memory v2 pipeline and return assembled LLM context."""
        session = self._thread_state_mgr.get_or_create_session(self._current_session_id)
        self._current_session_id = session.session_id

        appraisal = self._appraisal_engine.compute(
            query, session.messages, {"task_confidence": confidence}
        )
        emotion_vector = list(appraisal.values())

        if self._episode_manager.should_segment(confidence):
            episode = self._episode_manager.create_episode_from_session(session)
            self._episode_manager.commit_episode(episode)

        scored_candidates = []
        if self._diary_store is not None:
            diary_records = self._diary_store.query_semantic(
                query, top_k=20, query_emotion_vector=emotion_vector
            )
            scored_candidates = diary_records

        graph_results = []
        if self._knowledge_graph is not None:
            import numpy as np
            from memory.appraisal_engine import _hash_embedding

            query_embedding = _hash_embedding(query)
            graph_results = self._knowledge_graph.query_associative(
                query_embedding, top_k=5
            )

        return self._build_v2_context(
            appraisal, scored_candidates[:5], graph_results, session.messages[-4:]
        )

    def _update_v2_state(self, query: str, response: str, confidence: float) -> None:
        """Update thread state and episode segmentation after response."""
        if self._thread_state_mgr is None or self._current_session_id is None:
            return

        appraisal = (
            self._appraisal_engine.compute(query) if self._appraisal_engine else {}
        )
        emotion_vector = list(appraisal.values()) if appraisal else []

        if self._episode_manager and self._episode_manager.should_segment(confidence):
            session = self._thread_state_mgr.load_session(self._current_session_id)
            episode = self._episode_manager.create_episode_from_session(session)
            episode_id = self._episode_manager.commit_episode(episode)
            self._thread_state_mgr.update(
                self._current_session_id,
                query,
                response,
                emotion_vector=emotion_vector,
                episode_boundary=episode_id,
            )
        else:
            self._thread_state_mgr.update(
                self._current_session_id,
                query,
                response,
                emotion_vector=emotion_vector,
            )

        if (
            self._reflection_loop is not None
            and self._thread_state_mgr.is_conversation_ended(self._current_session_id)
        ):
            session = self._thread_state_mgr.load_session(self._current_session_id)
            self._reflection_loop.trigger(session)

    def _build_v2_context(
        self,
        appraisal: Dict[str, float],
        diary_records: list,
        graph_results: list,
        recent_messages: list,
    ) -> str:
        """Assemble LLM context from memory v2 sources."""
        parts = []

        if diary_records:
            diary_lines = []
            for record in diary_records:
                tags_str = ", ".join(record.tags[:3]) if record.tags else ""
                suffix = f" [tags: {tags_str}]" if tags_str else ""
                diary_lines.append(f"- {record.content[:200]}{suffix}")
            parts.append("Relevant memories:\n" + "\n".join(diary_lines))

        if graph_results:
            graph_lines = []
            for node_id, sim in graph_results[:3]:
                node = (
                    self._knowledge_graph._nodes.get(node_id)
                    if self._knowledge_graph
                    else None
                )
                if node:
                    graph_lines.append(f"- {node.content[:200]} (sim={sim:.2f})")
            if graph_lines:
                parts.append("Related concepts:\n" + "\n".join(graph_lines))

        if recent_messages:
            msg_lines = []
            for msg in recent_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")[:150]
                msg_lines.append(f"{role}: {content}")
            parts.append("Recent conversation:\n" + "\n".join(msg_lines))

        return "\n\n".join(parts) if parts else ""

    # =========================================================================
    # STATUS & MONITORING
    # =========================================================================

    def status(self) -> SystemStatus:
        """Get current system status."""
        uptime = 0.0
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()

        memories_stored = 0
        if self._memory is not None:
            try:
                memories_stored = self._memory.get_stats().get("total_nodes", 0)
            except Exception:
                pass

        learning_active = False
        if self._learner is not None:
            learning_active = self._learner.is_running()

        return SystemStatus(
            running=self._running,
            uptime_seconds=uptime,
            queries_processed=self._queries_processed,
            memories_stored=memories_stored,
            active_adapter=None,  # Future: from adapter_manager
            learning_active=learning_active,
            vram_usage_gb=0.0,  # Managed by Ollama
            last_query_time=self._last_query_time,
        )

    def health_check(self) -> Dict[str, bool]:
        """Verify all modules are functional."""
        results = {
            "config": False,
            "task_detector": False,
            "memory": False,
            "learner": False,
            "ollama": False,
        }

        # Check config
        try:
            _ = self.config.model.name
            results["config"] = True
        except Exception:
            pass

        # Check task detector
        if self._task_detector is not None:
            try:
                _ = self._task_detector.detect("test")
                results["task_detector"] = True
            except Exception:
                pass

        # Check memory
        if self._memory is not None:
            try:
                _ = self._memory.get_stats()
                results["memory"] = True
            except Exception:
                pass

        # Check learner
        if self._learner is not None:
            results["learner"] = True

        # Check Ollama
        results["ollama"] = self._check_ollama()

        return results

    # =========================================================================
    # NOTIFICATIONS (Phase 2)
    # =========================================================================

    def _get_notifier(self):
        """Get or create notification manager."""
        if self._notifier is None:
            try:
                from utils.notifications import get_notifier

                self._notifier = get_notifier()
            except ImportError:
                logger.debug("Notifications not available")
        return self._notifier

    def notify(self, title: str, message: str, level: str = "info") -> bool:
        """
        Send a desktop notification.

        Args:
            title: Notification title
            message: Notification message
            level: One of "info", "success", "warning", "error", "alert"

        Returns:
            True if notification was sent
        """
        notifier = self._get_notifier()
        if notifier is None:
            logger.info(f"[{level.upper()}] {title}: {message}")
            return False

        level_map = {
            "info": notifier.info,
            "success": notifier.success,
            "warning": notifier.warning,
            "error": notifier.error,
            "alert": notifier.alert,
        }

        method = level_map.get(level, notifier.info)
        return method(title, message)

    def alert(self, title: str, message: str, speak: bool = True) -> bool:
        """
        Send a high-priority alert.

        Args:
            title: Alert title
            message: Alert message
            speak: Also speak the alert via TTS

        Returns:
            True if alert was sent
        """
        result = self.notify(title, message, level="alert")

        if speak:
            self.speak(f"{title}. {message}")

        return result

    # =========================================================================
    # VOICE INTERFACE (Phase 2)
    # =========================================================================

    def predict_voice(self, max_duration: float = 10.0) -> PredictionResult:
        """
        Listen for voice input, transcribe, and generate response.

        Args:
            max_duration: Maximum recording duration in seconds

        Returns:
            PredictionResult from the transcribed query
        """
        try:
            from voice.audio_io import get_audio_input
            from voice.speech_to_text import get_stt

            audio_input = get_audio_input()
            stt = get_stt()

            if not audio_input.is_available():
                return PredictionResult(
                    response="Voice input not available.",
                    task="error",
                    confidence=0.0,
                    latency_ms=0.0,
                    error="Audio input unavailable",
                )

            if not stt.is_available():
                return PredictionResult(
                    response="Speech recognition not available.",
                    task="error",
                    confidence=0.0,
                    latency_ms=0.0,
                    error="STT unavailable",
                )

            # Record utterance
            logger.info("Listening for voice input...")
            audio = audio_input.record_utterance(max_duration=max_duration)

            if audio is None or len(audio) == 0:
                return PredictionResult(
                    response="No speech detected.",
                    task="error",
                    confidence=0.0,
                    latency_ms=0.0,
                    error="No speech",
                )

            # Transcribe
            transcription = stt.transcribe(audio)
            logger.info(f"Transcribed: {transcription.text}")

            if not transcription.text:
                return PredictionResult(
                    response="Could not understand speech.",
                    task="error",
                    confidence=0.0,
                    latency_ms=transcription.latency_ms,
                    error="Empty transcription",
                )

            # Get prediction
            result = self.predict(transcription.text)
            return result

        except ImportError as e:
            return PredictionResult(
                response="Voice modules not installed.",
                task="error",
                confidence=0.0,
                latency_ms=0.0,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Voice prediction failed: {e}")
            return PredictionResult(
                response="Voice processing error.",
                task="error",
                confidence=0.0,
                latency_ms=0.0,
                error=str(e),
            )

    def speak(self, text: str) -> bool:
        """
        Speak text using TTS.

        Args:
            text: Text to speak

        Returns:
            True if speech started successfully
        """
        try:
            from voice.enhanced_tts import get_enhanced_tts

            tts = get_enhanced_tts()
            return tts.speak(text)
        except ImportError:
            logger.warning("TTS not available")
            return False
        except Exception as e:
            logger.error(f"Speech failed: {e}")
            return False

    def run_voice_mode(self, wake_word_enabled: bool = True) -> None:
        """
        Run continuous voice interaction mode.

        Listens for wake word (if enabled), then processes voice commands.
        Press Ctrl+C to exit.

        Args:
            wake_word_enabled: Use wake word detection before listening
        """
        logger.info("Starting voice mode...")

        try:
            from voice.wake_word import get_wake_word_detector
            from voice.text_to_speech import get_tts

            tts = get_tts()

            # Greeting
            if tts.is_available():
                tts.speak("STARK voice mode activated, sir.")

            if wake_word_enabled:
                detector = get_wake_word_detector()
                if detector.is_available():
                    # Callback when wake word detected
                    def on_wake(event):
                        logger.info(f"Wake word: {event.word}")
                        result = self.predict_voice()
                        if result.response:
                            logger.info(f"Response: {result.response}")
                            self.speak(result.response)

                    detector.on_wake(on_wake)
                    detector.start()

                    logger.info("Listening for wake word... (Ctrl+C to exit)")
                    try:
                        while True:
                            time.sleep(0.1)
                    except KeyboardInterrupt:
                        pass
                    finally:
                        detector.stop()
                else:
                    logger.warning(
                        "Wake word not available, falling back to continuous mode"
                    )
                    wake_word_enabled = False

            if not wake_word_enabled:
                # Continuous listening without wake word
                logger.info("Continuous voice mode... (Ctrl+C to exit)")
                try:
                    while True:
                        result = self.predict_voice()
                        if result.response and result.task != "error":
                            logger.info(f"Response: {result.response}")
                            self.speak(result.response)
                        time.sleep(0.5)
                except KeyboardInterrupt:
                    pass

            # Goodbye
            if tts.is_available():
                tts.speak("Voice mode deactivated.")

        except ImportError as e:
            logger.error(f"Voice modules not available: {e}")
        except Exception as e:
            logger.error(f"Voice mode error: {e}")

        logger.info("Voice mode ended")

    # =========================================================================
    # MCP INTEGRATION
    # =========================================================================

    async def process_query_with_mcp(
        self,
        query: str,
        task_type_hint: Optional[str] = None,
        use_external_tools: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a query using both STARK and external MCP tools.

        Args:
            query: User query
            task_type_hint: Optional task type hint
            use_external_tools: Whether to use external MCP tools

        Returns:
            Combined result with external tool usage
        """
        # First, get STARK's response
        stark_result = self.process_query(query, task_type_hint)

        if not use_external_tools or self._mcp_manager is None:
            return stark_result

        try:
            # Use MCP agent to enhance with external tools
            import asyncio

            mcp_result = await self._mcp_manager.agent.execute_with_external_tools(
                query, {"stark_result": stark_result}
            )

            # Combine results
            combined_result = stark_result.copy()
            combined_result.update(
                {
                    "mcp_enhanced": True,
                    "external_tools_used": mcp_result.get("external_tools_used", []),
                    "combined_output": mcp_result.get(
                        "combined_output", stark_result.get("response", "")
                    ),
                    "mcp_success": mcp_result.get("success", False),
                }
            )

            return combined_result

        except Exception as e:
            logger.warning(f"MCP enhancement failed: {e}")
            # Return original STARK result if MCP fails
            stark_result["mcp_enhanced"] = False
            stark_result["mcp_error"] = str(e)
            return stark_result

    def process_query(
        self, query: str, task_type_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a query and return a dict result. Delegates to predict().

        Args:
            query: Natural language query
            task_type_hint: Optional task type hint

        Returns:
            Result dict with response, task, confidence, etc.
        """
        result = self.predict(query)
        return result.to_dict()

    def get_mcp_status(self) -> Dict[str, Any]:
        """
        Get MCP system status and available servers.

        Returns:
            MCP status information
        """
        if self._mcp_manager is None:
            return {"enabled": False, "status": "not_initialized"}

        try:
            client = self._mcp_manager.client
            return {
                "enabled": True,
                "servers_connected": len(client.available_servers),
                "available_servers": {
                    server_id: client.get_server_info(server_id)
                    for server_id in client.available_servers
                },
                "available_tools": client.list_available_tools(),
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}

    async def connect_mcp_server(
        self,
        server_id: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Connect to an external MCP server.

        Args:
            server_id: Unique server identifier
            command: Command to start server
            args: Command arguments
            env: Environment variables

        Returns:
            True if connection successful
        """
        if self._mcp_manager is None:
            logger.error("MCP Manager not initialized")
            return False

        return await self._mcp_manager.client.connect_server(
            server_id, command, args, env
        )

    async def disconnect_mcp_server(self, server_id: str) -> bool:
        """
        Disconnect from an external MCP server.

        Args:
            server_id: Server identifier

        Returns:
            True if disconnection successful
        """
        if self._mcp_manager is None:
            logger.error("MCP Manager not initialized")
            return False

        return await self._mcp_manager.client.disconnect_server(server_id)

    # =========================================================================
    # MEDIA MEMORY
    # =========================================================================

    def log_media(
        self,
        file_path: str,
        source: str = "user",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Ingest a media file into the Gemini Embedding 2 / ChromaDB store.

        Args:
            file_path: Absolute path to the file.
            source: Origin label — 'user', 'generated', 'web', or agent name.
            description: Optional description; auto-generated by Gemini if omitted.
            tags: Optional tag list; auto-extracted if omitted.

        Returns:
            Metadata dict, or {"error": ...} if media memory is unavailable.
        """
        if self._media_store is None:
            self._load_modules()
        if self._media_store is None:
            return {"error": "MediaMemory unavailable — set GEMINI_API_KEY"}
        try:
            return self._media_store.ingest(
                file_path, source=source, description=description, tags=tags
            )
        except Exception as e:
            logger.error(f"MediaMemory ingest failed: {e}")
            return {"error": str(e)}

    def search_media(
        self,
        query: str,
        n_results: int = 5,
        media_type: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic + structured search over stored media assets.

        Args:
            query: Natural language query.
            n_results: Max results to return.
            media_type: Optional filter — 'image', 'video', 'audio', 'document', 'other'.
            source: Optional source filter.
            tags: Optional tag list (ANY-match).
            since: ISO 8601 lower-bound timestamp filter.

        Returns:
            List of metadata dicts sorted by similarity score, or [] on error.
        """
        if self._media_store is None:
            self._load_modules()
        if self._media_store is None:
            return []
        try:
            return self._media_store.search(
                query,
                n_results=n_results,
                media_type=media_type,
                source=source,
                tags=tags,
                since=since,
            )
        except Exception as e:
            logger.error(f"MediaMemory search failed: {e}")
            return []

    def __repr__(self) -> str:
        return f"STARK(v{STARK_VERSION}, running={self._running}, queries={self._queries_processed})"


# =============================================================================
# SINGLETON
# =============================================================================

_stark_instance: Optional[STARK] = None


def get_stark(lazy_load: bool = True) -> STARK:
    """
    Get or create the global STARK instance.

    Args:
        lazy_load: If True, defer module loading until first use

    Returns:
        STARK instance
    """
    global _stark_instance

    if _stark_instance is None:
        _stark_instance = STARK(lazy_load=lazy_load)

    return _stark_instance


def reset_stark() -> None:
    """Reset the global STARK instance (for testing)."""
    global _stark_instance

    if _stark_instance is not None:
        if _stark_instance._running:
            _stark_instance.stop()
        _stark_instance = None
