"""Tests for memory/tool_schema_store.py — ToolSchemaStore."""
import time
import uuid

import pytest

from memory.tool_schema_store import ToolSchema, ToolSchemaStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_schema(
    *,
    schema_id: str = None,
    name: str = "test_tool",
    description: str = "A test tool",
    tool_type: str = "function",
    confidence: float = 0.9,
    last_used: float = None,
    use_count: int = 1,
    staleness_days: int = 30,
    parameters: dict = None,
    metadata: dict = None,
) -> ToolSchema:
    return ToolSchema(
        schema_id=schema_id or str(uuid.uuid4()),
        name=name,
        description=description,
        parameters=parameters or {"arg1": "str"},
        tool_type=tool_type,
        confidence=confidence,
        last_used=last_used if last_used is not None else time.time(),
        use_count=use_count,
        staleness_days=staleness_days,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# register / get
# ---------------------------------------------------------------------------

def test_register_and_get(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    schema = _make_schema(name="my_tool")
    sid = store.register(schema)
    assert sid == schema.schema_id

    fetched = store.get(sid)
    assert fetched is not None
    assert fetched.schema_id == sid
    assert fetched.name == "my_tool"


def test_get_nonexistent_returns_none(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    assert store.get("no-such-id") is None


def test_register_increments_use_count(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    schema = _make_schema()
    store.register(schema)
    store.register(schema)  # second registration of same id

    fetched = store.get(schema.schema_id)
    assert fetched is not None
    # First insert sets use_count to 1; second increments by 1 → 2
    assert fetched.use_count == 2


# ---------------------------------------------------------------------------
# query_by_name
# ---------------------------------------------------------------------------

def test_query_by_name(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    store.register(_make_schema(name="alpha_search"))
    store.register(_make_schema(name="beta_compute"))

    results = store.query_by_name("alpha")
    assert len(results) == 1
    assert results[0].name == "alpha_search"

    # Partial match — both have letters in common but only one matches "beta"
    results_beta = store.query_by_name("beta")
    assert len(results_beta) == 1
    assert results_beta[0].name == "beta_compute"


def test_query_by_name_case_insensitive(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    store.register(_make_schema(name="CoolTool"))
    results = store.query_by_name("cooltool")
    assert len(results) == 1


# ---------------------------------------------------------------------------
# query_by_type
# ---------------------------------------------------------------------------

def test_query_by_type(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    store.register(_make_schema(name="fn_tool", tool_type="function"))
    store.register(_make_schema(name="api_tool", tool_type="api"))

    fn_results = store.query_by_type("function")
    assert len(fn_results) == 1
    assert fn_results[0].name == "fn_tool"

    api_results = store.query_by_type("api")
    assert len(api_results) == 1
    assert api_results[0].name == "api_tool"

    none_results = store.query_by_type("nonexistent")
    assert none_results == []


# ---------------------------------------------------------------------------
# query_weighted
# ---------------------------------------------------------------------------

def test_query_weighted_returns_matching(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    store.register(_make_schema(name="weather_fetcher", description="Fetches weather data"))
    store.register(_make_schema(name="calendar_tool", description="Manages calendar events"))

    results = store.query_weighted("weather", top_k=5)
    assert len(results) >= 1
    names = [r.name for r in results]
    assert "weather_fetcher" in names
    assert "calendar_tool" not in names


def test_query_weighted_no_match_returns_empty(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    store.register(_make_schema(name="some_tool", description="Does something"))
    results = store.query_weighted("zzz_no_match")
    assert results == []


# ---------------------------------------------------------------------------
# record_use
# ---------------------------------------------------------------------------

def test_record_use_updates_last_used(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    old_time = time.time() - 1000.0
    schema = _make_schema(last_used=old_time)
    store.register(schema)

    before = store.get(schema.schema_id)
    assert before is not None

    time.sleep(0.05)  # ensure time.time() advances slightly
    store.record_use(schema.schema_id)

    after = store.get(schema.schema_id)
    assert after is not None
    assert after.last_used > before.last_used


def test_record_use_increments_use_count(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    schema = _make_schema()
    store.register(schema)

    before = store.get(schema.schema_id)
    store.record_use(schema.schema_id)
    after = store.get(schema.schema_id)

    assert after.use_count == before.use_count + 1


# ---------------------------------------------------------------------------
# evict_stale
# ---------------------------------------------------------------------------

def test_evict_stale(tmp_path):
    import sqlite3

    store = ToolSchemaStore(db_path=tmp_path / "tools.db", staleness_days=1)
    old_schema = _make_schema(name="stale_tool")
    recent_schema = _make_schema(name="fresh_tool")
    store.register(old_schema)
    store.register(recent_schema)

    # Backdating last_used directly in the DB because register() always uses now
    ancient_time = time.time() - 3 * 86400  # 3 days ago, past the 1-day staleness
    with sqlite3.connect(tmp_path / "tools.db") as conn:
        conn.execute(
            "UPDATE tool_schemas SET last_used = ? WHERE schema_id = ?",
            (ancient_time, old_schema.schema_id),
        )
        conn.commit()

    evicted = store.evict_stale()
    assert evicted == 1
    assert store.get(old_schema.schema_id) is None
    assert store.get(recent_schema.schema_id) is not None


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------

def test_count(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "tools.db")
    assert store.count() == 0

    for i in range(3):
        store.register(_make_schema(name=f"tool_{i}"))

    assert store.count() == 3
