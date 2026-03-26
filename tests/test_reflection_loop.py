"""Tests for memory/reflection_loop.py — ReflectionLoop."""
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest

from memory.reflection_loop import ReflectionLoop, ReflectionResult
from memory.thread_state import SessionState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(messages: list = None) -> SessionState:
    return SessionState(
        session_id=str(uuid.uuid4()),
        messages=messages or [],
    )


def _make_loop(**kwargs) -> ReflectionLoop:
    """Return a ReflectionLoop with a very long delay so auto-timer never fires."""
    kwargs.setdefault("trigger_delay_sec", 9999)
    kwargs.setdefault("model_name", "test-model")
    return ReflectionLoop(**kwargs)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

def test_init():
    loop = ReflectionLoop(trigger_delay_sec=60, model_name="qwen2.5:3b")
    assert loop._trigger_delay_sec == 60
    assert loop._model_name == "qwen2.5:3b"
    assert loop._last_result is None
    assert loop._timer is None


# ---------------------------------------------------------------------------
# get_last_result
# ---------------------------------------------------------------------------

def test_get_last_result_initially_none():
    loop = _make_loop()
    assert loop.get_last_result() is None


# ---------------------------------------------------------------------------
# _build_conversation_text
# ---------------------------------------------------------------------------

def test_build_conversation_text_with_messages():
    loop = _make_loop()
    session = _make_session(messages=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ])
    text = loop._build_conversation_text(session)
    assert "user: Hello" in text
    assert "assistant: Hi there" in text


def test_build_conversation_text_empty_messages():
    loop = _make_loop()
    session = _make_session(messages=[])
    text = loop._build_conversation_text(session)
    assert text == ""


def test_build_conversation_text_skips_empty_content():
    loop = _make_loop()
    session = _make_session(messages=[
        {"role": "user", "content": ""},
        {"role": "assistant", "content": "Response"},
    ])
    text = loop._build_conversation_text(session)
    assert "user:" not in text
    assert "assistant: Response" in text


# ---------------------------------------------------------------------------
# _extract_insights
# ---------------------------------------------------------------------------

def test_extract_insights_bullet_list():
    loop = _make_loop()
    text = "Summary: blah\nInsights:\n- First insight here\n- Second insight here\n"
    insights = loop._extract_insights(text)
    assert len(insights) == 2
    assert "First insight here" in insights
    assert "Second insight here" in insights


def test_extract_insights_fallback_sentences():
    """When no bullet lines exist, sentences of appropriate length are returned."""
    loop = _make_loop()
    # No bullets — the fallback splits on sentence terminators
    text = (
        "The user asked about Python. "
        "The assistant provided a detailed explanation of list comprehensions. "
        "No further topics were discussed in this session."
    )
    insights = loop._extract_insights(text)
    # Should return at least some sentences (length 15-150 chars, >3 words)
    assert isinstance(insights, list)
    assert len(insights) >= 1


def test_extract_insights_empty_text():
    loop = _make_loop()
    result = loop._extract_insights("")
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# _summarize_via_llm — mocked HTTP
# ---------------------------------------------------------------------------

def test_summarize_via_llm_failure():
    """When requests.post raises, a fallback ReflectionResult is returned."""
    loop = _make_loop()
    with patch("memory.reflection_loop.requests.post", side_effect=ConnectionError("no conn")):
        result = loop._summarize_via_llm("some conversation text")

    assert isinstance(result, ReflectionResult)
    assert result.summary == "[Reflection unavailable]"
    assert result.insights == []


def test_summarize_via_llm_success(monkeypatch):
    """A well-formed LLM response is parsed into summary and insights."""
    loop = _make_loop()
    fake_response_text = (
        "Summary: The user discussed Python list comprehensions.\n"
        "Insights:\n"
        "- List comprehensions are concise\n"
        "- They can replace simple for-loops\n"
    )

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"response": fake_response_text}

    monkeypatch.setattr("memory.reflection_loop.requests.post", lambda *a, **kw: mock_resp)

    result = loop._summarize_via_llm("user: tell me about Python")

    assert isinstance(result, ReflectionResult)
    assert "Python" in result.summary or len(result.summary) > 0
    assert len(result.insights) == 2
    assert "List comprehensions are concise" in result.insights


def test_summarize_via_llm_http_error(monkeypatch):
    """An HTTP error (raise_for_status raises) → fallback ReflectionResult."""
    import requests as req

    loop = _make_loop()

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = req.HTTPError("500 Server Error")

    monkeypatch.setattr("memory.reflection_loop.requests.post", lambda *a, **kw: mock_resp)

    result = loop._summarize_via_llm("conversation")
    assert result.summary == "[Reflection unavailable]"


# ---------------------------------------------------------------------------
# trigger() — timer creation
# ---------------------------------------------------------------------------

def test_trigger_schedules_timer():
    """trigger() with a long delay creates an active timer."""
    loop = ReflectionLoop(trigger_delay_sec=9999, model_name="test-model")
    session = _make_session(messages=[{"role": "user", "content": "hello"}])

    loop.trigger(session)

    assert loop._timer is not None
    assert loop._timer.is_alive()

    # Cleanup: cancel the timer to avoid background threads in test suite
    loop._timer.cancel()


def test_trigger_cancels_previous_timer():
    """A second trigger() cancels the first timer and creates a new one."""
    loop = ReflectionLoop(trigger_delay_sec=9999, model_name="test-model")
    session = _make_session(messages=[{"role": "user", "content": "first"}])

    loop.trigger(session)
    first_timer = loop._timer

    loop.trigger(session)
    second_timer = loop._timer

    assert second_timer is not first_timer
    assert not first_timer.is_alive()  # was cancelled
    assert second_timer.is_alive()

    second_timer.cancel()


# ---------------------------------------------------------------------------
# Integration: trigger → _run_reflection stores result
# ---------------------------------------------------------------------------

def test_run_reflection_stores_result(monkeypatch):
    """_run_reflection (called synchronously) updates _last_result."""
    loop = _make_loop()
    session = _make_session(messages=[{"role": "user", "content": "Tell me about TDD"}])

    fake_text = (
        "Summary: Discussion about TDD practices.\n"
        "Insights:\n"
        "- TDD reduces bugs\n"
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"response": fake_text}

    monkeypatch.setattr("memory.reflection_loop.requests.post", lambda *a, **kw: mock_resp)

    loop._run_reflection(session)

    result = loop.get_last_result()
    assert result is not None
    assert isinstance(result, ReflectionResult)
    assert len(result.insights) >= 1
