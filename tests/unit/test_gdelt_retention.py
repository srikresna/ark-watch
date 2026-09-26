from datetime import UTC, datetime, timedelta

from arkwatch import db
from arkwatch.gdelt_storage import backup_database
from arkwatch.qa.gdelt_retention import _cutoff, clean


def test_cutoff_is_start_of_current_utc_week():
    saturday = datetime(2026, 9, 26, 7, 12, tzinfo=UTC)
    sunday = datetime(2026, 9, 27, 7, 12, tzinfo=UTC)

    assert _cutoff(saturday) == "2026-09-20T00:00:00+00:00"
    assert _cutoff(sunday) == "2026-09-27T00:00:00+00:00"


def _seed(path, fetched_at):
    conn = db.get_conn(path, allow_init=True)
    conn.executemany(
        "INSERT INTO gdelt_events "
        "(event_id,event_date,added_at_utc,fetched_at,raw_record_json) VALUES (?,?,?,?,?)",
        [
            ("old", "20260901", fetched_at[0], fetched_at[0], "{}"),
            ("old-unlinked", "20260901", fetched_at[0], fetched_at[0], "{}"),
            ("recent", "20260920", fetched_at[1], fetched_at[1], "{}"),
        ],
    )
    conn.executemany(
        "INSERT INTO gdelt_mentions "
        "(observation_id,event_id,fetched_at,raw_record_json) VALUES (?,?,?,?)",
        [
            ("old-mention", "old", fetched_at[0], "{}"),
            ("recent-mention", "old", fetched_at[1], "{}"),
        ],
    )
    conn.executemany(
        "INSERT INTO gdelt_gkg "
        "(record_id,record_time,themes_json,entities_json,locations_json,tone_json,"
        "fetched_at,raw_record_json) VALUES (?,?,?,?,?,?,?,?)",
        [
            ("old-gkg", fetched_at[0], "[]", "{}", "[]", "[]", fetched_at[0], "{}"),
            ("new-gkg", fetched_at[1], "[]", "{}", "[]", "[]", fetched_at[1], "{}"),
        ],
    )
    conn.commit()
    conn.close()


def test_gdelt_retention_preview_is_read_only_and_protects_referenced_events(tmp_path):
    path = tmp_path / "arkwatch.db"
    now = datetime(2026, 9, 27, 7, tzinfo=UTC)
    _seed(path, ["2026-09-26T23:59:59+00:00", "2026-09-27T00:00:00+00:00"])

    result = clean(path, now=now)

    assert result["applied"] is False
    assert result["cutoff_utc"] == "2026-09-27T00:00:00+00:00"
    assert result["tables"]["gdelt_mentions"]["rows"] == 1
    assert result["tables"]["gdelt_gkg"]["rows"] == 1
    assert result["tables"]["gdelt_events"]["rows"] == 1
    assert result["protected_events"] == 1
    conn = db.get_conn(path)
    assert conn.execute("SELECT COUNT(*) FROM gdelt_events").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM gdelt_mentions").fetchone()[0] == 2
    conn.close()


def test_gdelt_retention_apply_requires_matching_backup_and_deletes_old_rows(tmp_path):
    path = tmp_path / "arkwatch.db"
    backup = tmp_path / "pre-cleanup.db"
    now = datetime.now(UTC) + timedelta(seconds=2)
    cutoff = _cutoff(now)
    old = (datetime.fromisoformat(cutoff) - timedelta(seconds=1)).isoformat()
    recent = cutoff
    _seed(path, [old, recent])
    backup_database(path, backup)

    result = clean(path, now=now, apply=True, backup_path=backup)

    assert result["deleted"] == {
        "gdelt_mentions": 1,
        "gdelt_gkg": 1,
        "gdelt_events": 1,
    }
    conn = db.get_conn(path)
    assert conn.execute("SELECT event_id FROM gdelt_events ORDER BY event_id").fetchall() == [
        ("old",),
        ("recent",),
    ]
    assert conn.execute("SELECT observation_id FROM gdelt_mentions").fetchall() == [
        ("recent-mention",)
    ]
    assert conn.execute("SELECT record_id FROM gdelt_gkg").fetchall() == [("new-gkg",)]
    conn.close()


def test_gdelt_retention_apply_refuses_missing_backup(tmp_path):
    path = tmp_path / "arkwatch.db"
    now = datetime.now(UTC)
    _seed(path, ["2000-01-01T00:00:00+00:00", "2000-01-02T00:00:00+00:00"])

    try:
        clean(path, now=now, apply=True, backup_path=tmp_path / "missing.db")
    except FileNotFoundError as exc:
        assert "pre-cleanup backup required" in str(exc)
    else:
        raise AssertionError("missing backup must abort deletion")

    conn = db.get_conn(path)
    assert conn.execute("SELECT COUNT(*) FROM gdelt_events").fetchone()[0] == 3
    conn.close()
