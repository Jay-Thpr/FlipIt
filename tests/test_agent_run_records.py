from backend.run_records import build_agent_run_event_row, build_agent_run_row


def test_build_agent_run_row_defaults_and_overrides() -> None:
    row = build_agent_run_row(
        session_id="session-1",
        user_id="user-1",
        pipeline="sell",
        item_id="item-1",
        request_payload={"foo": "bar"},
        result_payload={"ok": True},
        next_action_payload={"type": "wait"},
        error="boom",
        created_at="2026-04-05T00:00:00+00:00",
    )

    assert row["session_id"] == "session-1"
    assert row["user_id"] == "user-1"
    assert row["pipeline"] == "sell"
    assert row["item_id"] == "item-1"
    assert row["status"] == "queued"
    assert row["phase"] == "queued"
    assert row["next_action_type"] == "wait"
    assert row["next_action_payload"] == {"type": "wait"}
    assert row["request_payload"] == {"foo": "bar"}
    assert row["result_payload"] == {"ok": True}
    assert row["error"] == "boom"
    assert row["created_at"] == "2026-04-05T00:00:00+00:00"
    assert row["updated_at"] == "2026-04-05T00:00:00+00:00"


def test_build_agent_run_event_row_defaults() -> None:
    row = build_agent_run_event_row(
        run_id="run-1",
        session_id="session-1",
        event_type="pipeline_started",
        step="vision_analysis",
    )

    assert row["run_id"] == "run-1"
    assert row["session_id"] == "session-1"
    assert row["event_type"] == "pipeline_started"
    assert row["step"] == "vision_analysis"
    assert row["payload"] == {}
    assert "created_at" in row
