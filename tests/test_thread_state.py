import time

from memory.thread_state import ThreadStateManager


def test_new_session_and_reload(tmp_path):
    manager = ThreadStateManager(sessions_dir=tmp_path)
    state = manager.new_session()

    manager.update(
        session_id=state.session_id,
        query="hello",
        response="hi",
        emotion_vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    )

    reloaded = manager.load_session(state.session_id)
    assert reloaded.session_id == state.session_id
    assert len(reloaded.messages) == 2
    assert reloaded.emotion_vector == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]


def test_missing_session_file_starts_fresh(tmp_path):
    manager = ThreadStateManager(sessions_dir=tmp_path)
    state = manager.load_session("missing-session")

    assert state.session_id == "missing-session"
    assert state.messages == []


def test_conversation_end_detection(tmp_path):
    manager = ThreadStateManager(sessions_dir=tmp_path)
    state = manager.new_session()

    assert manager.is_conversation_ended(state.session_id, idle_seconds=300) is False
    time.sleep(0.01)
    assert manager.is_conversation_ended(state.session_id, idle_seconds=0) is True


def test_compresses_large_state(tmp_path):
    manager = ThreadStateManager(sessions_dir=tmp_path, max_state_size_mb=1)
    state = manager.new_session()

    large_chunk = "x" * 200_000
    for idx in range(8):
        manager.update(
            session_id=state.session_id,
            query=f"q-{idx}-{large_chunk}",
            response=f"r-{idx}-{large_chunk}",
        )

    reloaded = manager.load_session(state.session_id)
    assert len(reloaded.messages) < 16
    assert reloaded.messages[0]["role"] == "system"
