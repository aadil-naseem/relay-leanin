"""Phase 1: trace builder produces JSON-safe calculation-log entries."""

from app.core.trace import TraceBuilder


def test_entries_are_appended_in_order():
    builder = TraceBuilder()
    builder.add("rain_hazard", "rolling 24h rain 148 mm -> 0.86", inputs={"max24_mm": 148.2}, output={"hazard": 0.86})
    builder.add("vulnerability", "site facts -> 0.62", inputs={"elevation_m": 9.4}, output={"v": 0.62})
    entries = builder.to_list()
    assert [entry["step"] for entry in entries] == ["rain_hazard", "vulnerability"]


def test_unserializable_values_are_stringified_not_dropped():
    builder = TraceBuilder()
    builder.add("step", "detail", inputs={"obj": object()}, output={"ok": 1})
    entry = builder.to_list()[0]
    assert isinstance(entry["inputs"]["obj"], str)
    assert entry["output"] == {"ok": 1}


def test_to_list_returns_a_copy():
    builder = TraceBuilder()
    builder.add("a", "b")
    snapshot = builder.to_list()
    snapshot.clear()
    assert len(builder) == 1


def test_len_tracks_entries():
    builder = TraceBuilder()
    assert len(builder) == 0
    builder.add("x", "y")
    assert len(builder) == 1