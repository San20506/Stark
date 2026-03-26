import time
from memory.episode_manager import EpisodeManager
from memory.thread_state import SessionState


def test_episode_segmentation_trigger():
    manager = EpisodeManager(surprise_threshold=0.5)

    # High confidence -> no segment
    assert manager.should_segment(confidence=0.9) is False
    # Low confidence (high surprise) -> segment
    assert manager.should_segment(confidence=0.1) is True


def test_create_episode_from_session():
    manager = EpisodeManager()
    session = SessionState(
        session_id="session-123",
        messages=[
            {"role": "user", "content": "Need to debug python code"},
            {"role": "assistant", "content": "I can help with debugging."},
        ],
        active_tool_schemas=["python_repl"],
    )

    episode = manager.create_episode_from_session(
        session, insights="Learned about index errors"
    )

    assert episode.session_id == "session-123"
    assert "user: need to debug python code" in episode.content.lower()
    assert "debug" in episode.tags or "python" in episode.tags
    assert episode.insights == "Learned about index errors"
    assert episode.tool_schemas_used == ["python_repl"]
