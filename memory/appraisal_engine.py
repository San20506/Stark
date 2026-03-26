import math
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from core.constants import (
    APPRAISAL_NOVELTY_THRESHOLD,
    APPRAISAL_SMOOTHING_WINDOW,
)


POSITIVE_WORDS = {
    "good",
    "great",
    "excellent",
    "happy",
    "thanks",
    "love",
    "success",
    "improved",
    "fixed",
}

NEGATIVE_WORDS = {
    "bad",
    "terrible",
    "sad",
    "error",
    "bug",
    "failed",
    "broken",
    "issue",
    "problem",
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def _hash_embedding(text: str, dim: int = 128) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for token in tokens:
        idx = hash(token) % dim
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


@dataclass(frozen=True)
class AppraisalVector:
    novelty: float
    valence: float
    agency: float
    coping: float
    certainty: float
    goal_relevance: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "novelty": self.novelty,
            "valence": self.valence,
            "agency": self.agency,
            "coping": self.coping,
            "certainty": self.certainty,
            "goal_relevance": self.goal_relevance,
        }


class AppraisalEngine:
    def __init__(self, smoothing_window: int = APPRAISAL_SMOOTHING_WINDOW):
        self.smoothing_window = max(1, smoothing_window)
        self._recent_embeddings: deque[np.ndarray] = deque(maxlen=20)
        self._recent_vectors: deque[AppraisalVector] = deque(
            maxlen=self.smoothing_window
        )
        self._last_latency_ms = 0.0

    def compute(
        self,
        text: str,
        recent_messages: Optional[Iterable[Dict[str, str]]] = None,
        session_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        started = time.perf_counter()
        try:
            state = session_state or {}
            embed = _hash_embedding(text)

            novelty = self._compute_novelty(embed)
            goal_relevance = self._compute_goal_relevance(embed, state)
            valence = self._compute_valence(text, goal_relevance)
            agency = self._compute_agency(text)
            coping = self._compute_coping(state)
            certainty = self._compute_certainty(state)

            vector = AppraisalVector(
                novelty=_clamp(novelty),
                valence=_clamp(valence),
                agency=_clamp(agency),
                coping=_clamp(coping),
                certainty=_clamp(certainty),
                goal_relevance=_clamp(goal_relevance),
            )

            self._recent_embeddings.append(embed)
            self._recent_vectors.append(vector)
            smoothed = self._smooth(vector)
            self._last_latency_ms = (time.perf_counter() - started) * 1000.0
            return smoothed.as_dict()
        except Exception:
            self._last_latency_ms = (time.perf_counter() - started) * 1000.0
            return {
                "novelty": 0.5,
                "valence": 0.5,
                "agency": 0.5,
                "coping": 0.5,
                "certainty": 0.5,
                "goal_relevance": 0.5,
            }

    def is_novel(self, appraisal: Dict[str, float]) -> bool:
        return appraisal.get("novelty", 0.0) >= APPRAISAL_NOVELTY_THRESHOLD

    @property
    def last_latency_ms(self) -> float:
        return self._last_latency_ms

    def _compute_novelty(self, embed: np.ndarray) -> float:
        if not self._recent_embeddings:
            return 1.0
        mean = np.mean(np.stack(list(self._recent_embeddings), axis=0), axis=0)
        similarity = _cosine(embed, mean)
        return 1.0 - ((similarity + 1.0) / 2.0)

    def _compute_goal_relevance(
        self, embed: np.ndarray, state: Dict[str, Any]
    ) -> float:
        goal_texts = state.get("goal_texts", [])
        goal_embeddings = state.get("goal_embeddings", [])

        sims: List[float] = []
        for item in goal_embeddings:
            target = np.array(item, dtype=np.float32)
            sims.append((_cosine(embed, target) + 1.0) / 2.0)

        if not sims:
            for text in goal_texts:
                target = _hash_embedding(str(text))
                sims.append((_cosine(embed, target) + 1.0) / 2.0)

        if not sims:
            return 0.5
        return float(max(sims))

    def _compute_valence(self, text: str, goal_relevance: float) -> float:
        tokens = _tokenize(text)
        if not tokens:
            return 0.5
        pos = sum(1 for t in tokens if t in POSITIVE_WORDS)
        neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)
        raw = (pos - neg) / max(1, len(tokens))
        sentiment = (raw + 1.0) / 2.0
        return _clamp(0.7 * sentiment + 0.3 * goal_relevance)

    def _compute_agency(self, text: str) -> float:
        tokens = _tokenize(text)
        if not tokens:
            return 0.5
        self_refs = {"i", "me", "my", "mine", "myself"}
        external_refs = {"you", "your", "he", "she", "they", "them", "it"}
        self_count = sum(1 for t in tokens if t in self_refs)
        external_count = sum(1 for t in tokens if t in external_refs)
        total = self_count + external_count
        if total == 0:
            return 0.5
        return self_count / total

    def _compute_coping(self, state: Dict[str, Any]) -> float:
        complexity = float(state.get("task_complexity", 0.5))
        success_rate = float(state.get("rolling_success_rate", 0.7))
        success_rate = max(0.1, success_rate)
        ratio = complexity / success_rate
        return _clamp(1.0 - ratio)

    def _compute_certainty(self, state: Dict[str, Any]) -> float:
        scores = state.get("task_scores")
        if isinstance(scores, dict) and scores:
            probs = np.array(list(scores.values()), dtype=np.float32)
            total = float(probs.sum())
            if total <= 0:
                return 0.5
            probs = probs / total
            entropy = -float(np.sum([p * math.log(max(p, 1e-10)) for p in probs]))
            max_entropy = math.log(max(len(probs), 2))
            certainty = 1.0 - (entropy / max_entropy)
            return _clamp(certainty)
        return float(_clamp(state.get("task_confidence", 0.5)))

    def _smooth(self, current: AppraisalVector) -> AppraisalVector:
        vectors = list(self._recent_vectors)
        if len(vectors) <= 1:
            return current
        novelty = float(np.mean([v.novelty for v in vectors]))
        valence = float(np.mean([v.valence for v in vectors]))
        agency = float(np.mean([v.agency for v in vectors]))
        coping = float(np.mean([v.coping for v in vectors]))
        certainty = float(np.mean([v.certainty for v in vectors]))
        goal_relevance = float(np.mean([v.goal_relevance for v in vectors]))
        return AppraisalVector(
            novelty, valence, agency, coping, certainty, goal_relevance
        )
