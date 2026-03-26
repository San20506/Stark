from memory.diary_store import DiaryEntry, DiaryStore


def test_write_and_semantic_query(tmp_path):
    db_path = tmp_path / "episodic.db"
    store = DiaryStore(db_path=db_path, soft_cap=100)

    store.write(
        DiaryEntry(content="fixed index error in python list", tags=["debug", "python"])
    )
    store.write(
        DiaryEntry(content="planned weekly roadmap for project", tags=["planning"])
    )

    results = store.query_semantic("python index error fix", top_k=2)
    assert len(results) >= 1
    assert "index error" in results[0].content


def test_timerange_and_tag_queries(tmp_path):
    db_path = tmp_path / "episodic.db"
    store = DiaryStore(db_path=db_path, soft_cap=100)

    id1 = store.write(DiaryEntry(content="entry one", timestamp=1000.0, tags=["a"]))
    id2 = store.write(DiaryEntry(content="entry two", timestamp=2000.0, tags=["b"]))

    timerange = store.query_timerange(900.0, 1500.0)
    tags = store.query_tags(["b"])

    assert len(timerange) == 1
    assert timerange[0].id == id1
    assert len(tags) == 1
    assert tags[0].id == id2


def test_emotion_query_and_soft_cap_archive(tmp_path):
    db_path = tmp_path / "episodic.db"
    archive_path = tmp_path / "archive.jsonl"
    store = DiaryStore(db_path=db_path, soft_cap=2, archive_path=archive_path)

    store.write(DiaryEntry(content="e1", timestamp=1000.0, emotion_vector=[0.1, 0.2]))
    store.write(DiaryEntry(content="e2", timestamp=1001.0, emotion_vector=[0.4, 0.5]))
    store.write(DiaryEntry(content="e3", timestamp=1002.0, emotion_vector=[0.9, 0.9]))

    matches = store.query_emotion({0: (0.85, 1.0), 1: (0.85, 1.0)})

    assert store.count() == 2
    assert archive_path.exists()
    assert len(matches) == 1
    assert matches[0].content == "e3"
