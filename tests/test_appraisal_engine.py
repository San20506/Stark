from memory.appraisal_engine import AppraisalEngine


def test_appraisal_returns_all_dimensions():
    engine = AppraisalEngine()
    result = engine.compute("I fixed the bug and now it works great")

    assert set(result.keys()) == {
        "novelty",
        "valence",
        "agency",
        "coping",
        "certainty",
        "goal_relevance",
    }
    assert all(0.0 <= value <= 1.0 for value in result.values())


def test_appraisal_smoothing_changes_with_history():
    engine = AppraisalEngine(smoothing_window=3)

    first = engine.compute("error error failed")
    second = engine.compute("great success fixed")
    third = engine.compute("great success fixed")

    assert third["valence"] >= first["valence"]
    assert second != first


def test_appraisal_uses_session_state_signals():
    engine = AppraisalEngine()
    result = engine.compute(
        "please help me",
        session_state={
            "task_complexity": 0.9,
            "rolling_success_rate": 0.4,
            "task_scores": {"error_debugging": 0.8, "conversation": 0.2},
            "goal_texts": ["debug code quickly"],
        },
    )

    assert result["coping"] <= 0.2
    assert result["certainty"] > 0.0
    assert result["goal_relevance"] >= 0.0


def test_appraisal_is_novel_threshold_helper():
    engine = AppraisalEngine()
    result = engine.compute("completely unseen phrase alpha beta gamma")

    assert isinstance(engine.is_novel(result), bool)
