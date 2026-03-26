import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from core.constants import (
    OLLAMA_BASE_URL,
    REFLECTION_MODEL_NAME,
    REFLECTION_TRIGGER_DELAY_SEC,
)
from memory.thread_state import SessionState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReflectionResult:
    insights: List[str] = field(default_factory=list)
    summary: str = ""
    triggered_at: float = field(default_factory=time.time)


class ReflectionLoop:
    def __init__(
        self,
        trigger_delay_sec: int = REFLECTION_TRIGGER_DELAY_SEC,
        model_name: str = REFLECTION_MODEL_NAME,
    ):
        self._trigger_delay_sec = trigger_delay_sec
        self._model_name = model_name
        self._lock = threading.RLock()
        self._last_result: Optional[ReflectionResult] = None
        self._timer: Optional[threading.Timer] = None

    def trigger(self, session_state: SessionState) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(
                self._trigger_delay_sec,
                self._run_reflection,
                args=(session_state,),
            )
            self._timer.start()

    def _run_reflection(self, session_state: SessionState) -> ReflectionResult:
        conversation_text = self._build_conversation_text(session_state)
        result = self._summarize_via_llm(conversation_text)
        with self._lock:
            self._last_result = result
        return result

    def _build_conversation_text(self, session_state: SessionState) -> str:
        lines: List[str] = []
        for msg in session_state.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "").strip()
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _summarize_via_llm(self, conversation_text: str) -> ReflectionResult:
        prompt = (
            "You are analyzing a conversation to extract key insights and create a summary.\n\n"
            "Provide your analysis in this format:\n"
            "Summary: [2-3 sentence summary of the conversation]\n"
            "Insights:\n"
            "- [Key insight 1]\n"
            "- [Key insight 2]\n"
            "- [Key insight 3]\n\n"
            "Conversation:\n"
            f"{conversation_text}"
        )
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": self._model_name, "prompt": prompt, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
            text = response.json().get("response", "")
        except Exception as exc:
            logger.warning("Reflection LLM call failed: %s", exc)
            return ReflectionResult(
                insights=[],
                summary="[Reflection unavailable]",
                triggered_at=time.time(),
            )

        summary = ""
        if text.startswith("Summary:"):
            parts = text.split("Summary:", 1)
            remaining = parts[1] if len(parts) > 1 else ""
            summary_match = re.match(
                r"(.+?)(?:^Insights:|$)", remaining, re.DOTALL | re.MULTILINE
            )
            if summary_match:
                summary = summary_match.group(1).strip()
            else:
                summary = remaining.strip().split("Insights:")[0].strip()
        else:
            summary = text.strip().split("Insights:")[0].strip()

        insights = self._extract_insights(text)

        return ReflectionResult(
            insights=insights, summary=summary, triggered_at=time.time()
        )

    def _extract_insights(self, text: str) -> List[str]:
        bullet_pattern = re.compile(r"^-\s+(.+)$", re.MULTILINE)
        matches = bullet_pattern.findall(text)
        if matches:
            return [m.strip() for m in matches if m.strip()]
        fallback = re.findall(r" insight \d+[:\s]+(.+?)(?=\n|$)", text, re.IGNORECASE)
        if fallback:
            return [s.strip() for s in fallback if s.strip()]
        sentences = re.split(r"[.!?]+", text)
        insights = [
            s.strip()
            for s in sentences
            if 15 < len(s.strip()) < 150 and len(s.split()) > 3
        ]
        return insights[:5]

    def get_last_result(self) -> Optional[ReflectionResult]:
        with self._lock:
            return self._last_result
