"""LME copper stocks parser tests against frozen two-era fixtures.

The LME monthly workbook has changed layout over time: the new era uses the
'Closing Stock' sheet with a 'BusinessDate' header and tightly packed
columns; the old era uses 'ClosingStock' with 'Stock Date' and columns
spaced one apart. The dynamic-scan parser must handle both."""

from __future__ import annotations

from pathlib import Path

import pytest

from arkwatch.fetchers.flows_extra import fetch_lme_stocks

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "lme"


class _FakeResp:
    def __init__(self, content, status=200):
        self.content = content
        self.status_code = status


def _patch(monkeypatch, path):
    """Patch the HTTP session so requests serve a local fixture file."""
    data = path.read_bytes()

    class _Sess:
        def get(self, url, timeout=None):
            return _FakeResp(data)

    monkeypatch.setattr("curl_cffi.requests.Session", lambda impersonate=None: _Sess())


def test_parse_new_format_2026(monkeypatch):
    _patch(monkeypatch, FIX / "stocks-july-2026.xlsx")
    rows = fetch_lme_stocks(2026, 7)
    assert len(rows) == 23  # 23 trading days in July 2026
    assert rows[0]["ts"] == "2026-07-01"
    assert rows[0]["copper_tonnes"] == pytest.approx(322350)
    # dates ascending
    assert rows[-1]["ts"] == "2026-07-31"


def test_parse_old_format_2024(monkeypatch):
    _patch(monkeypatch, FIX / "stocks-january-2024.xlsx")
    rows = fetch_lme_stocks(2024, 1)
    assert len(rows) >= 20  # a full month has roughly 22 trading days
    assert rows[0]["ts"].startswith("2024-01")
    # 2024 copper levels should be the same order of magnitude (~100-200K tonnes)
    assert 50000 < rows[0]["copper_tonnes"] < 300000


def test_soft_404_html_returns_empty(monkeypatch):
    """A not-yet-published month returns HTTP 200 with an HTML body: parse to [], never raise."""

    class _Sess:
        def get(self, url, timeout=None):
            return _FakeResp(b"\r\n\r\n<!DOCTYPE html><html>challenge</html>")

    monkeypatch.setattr("curl_cffi.requests.Session", lambda impersonate=None: _Sess())
    assert fetch_lme_stocks(2099, 12) == []
