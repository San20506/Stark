"""
Proactive Message Templates
============================
Formats outbound proactive messages so STARK sounds like an assistant,
not a log dump. Keeps messages short — these are chat notifications, not essays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ProactivePayload:
    trigger: str          # "new_insight" | "conflict" | "daily_summary" | "goal_alert"
    title: str
    body: str
    action_hint: str = ""  # e.g. "/recall memory to review"


def render_new_insight(insight: str, tags: list[str] | None = None) -> ProactivePayload:
    tag_line = f" [{', '.join(tags)}]" if tags else ""
    return ProactivePayload(
        trigger="new_insight",
        title="New insight",
        body=f"I noticed something while reviewing today{tag_line}:\n{insight}",
        action_hint="/recall insights to review all",
    )


def render_conflict(topic: str, note_a: str, note_b: str) -> ProactivePayload:
    return ProactivePayload(
        trigger="conflict",
        title="Potential conflict",
        body=(
            f"Heads up — your notes about '{topic}' may conflict:\n"
            f"• {note_a}\n"
            f"• {note_b}"
        ),
        action_hint="/recall conflict to review",
    )


def render_daily_summary(
    promoted: int, conflicts: int, top_insight: str = ""
) -> ProactivePayload:
    lines = [f"Daily digest — {promoted} pattern(s) promoted to memory."]
    if conflicts:
        lines.append(f"⚠ {conflicts} conflict(s) awaiting review.")
    if top_insight:
        lines.append(f"Top insight: {top_insight}")
    return ProactivePayload(
        trigger="daily_summary",
        title="Daily summary",
        body="\n".join(lines),
        action_hint="/recall summary for full report",
    )


def render_goal_alert(goal: str, relevance: float) -> ProactivePayload:
    return ProactivePayload(
        trigger="goal_alert",
        title="Goal relevance spike",
        body=f"Something you're working on ties strongly to your goal: '{goal}' (relevance {relevance:.0%})",
        action_hint="/recall goals to review",
    )


def format_for_chat(payload: ProactivePayload, include_hint: bool = True) -> str:
    """Render a ProactivePayload as a plain-text chat message."""
    parts = [f"[{payload.title}]", "", payload.body]
    if include_hint and payload.action_hint:
        parts += ["", f"→ {payload.action_hint}"]
    return "\n".join(parts)


def from_diary_entry(entry: dict[str, Any]) -> ProactivePayload | None:
    """
    Best-effort conversion of a diary entry dict to a ProactivePayload.
    Returns None if the entry doesn't contain enough content to push.
    """
    insights: list[str] = entry.get("insights") or []
    tags: list[str] = entry.get("tags") or []
    summary: str = entry.get("summary") or ""

    if insights:
        return render_new_insight(insights[0], tags or None)
    if summary:
        return ProactivePayload(
            trigger="new_insight",
            title="Reflection",
            body=summary,
        )
    return None
