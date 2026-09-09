"""Parser tests against frozen QuikStrike HTML fixtures.

The fixtures are raw captures of the live pages: parsers must keep matching
them verbatim. If a fixture stops parsing, the upstream structure changed —
re-capture the fixture deliberately instead of loosening the parser."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from arkwatch.fetchers.quikstrike import (
    _cells,
    _fedwatch_eventtarget,
    _form_action,
    compare_diy_vs_official,
)

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "quikstrike"


@pytest.fixture(scope="module")
def menu_post() -> str:
    return (FIX / "menu_post_FedWatch.html").read_text(encoding="utf-8", errors="ignore")


class TestQuikStrikeParsers:
    def test_cells_strips_tags(self):
        assert _cells("<tr><td>a</td><td> b </td></tr>") == ["a", "b"]

    def test_form_action_has_session(self, menu_post):
        """The form action must carry insid/qsid — without them the server ignores the POST."""
        action = _form_action(menu_post)
        assert "insid=" in action and "qsid=" in action
        assert action.startswith("https://cmegroup-tools.quikstrike.net")

    def test_parse_meeting_and_probs(self, menu_post):
        """A meeting row 'DD Mon YYYY|CONTRACT|...' is followed by a probability row 'E%|H%|X%'."""
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", menu_post, re.S)
        meeting = probs = None
        for tr in rows:
            cells = _cells(tr)
            if (
                re.match(
                    r"\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}", cells[0]
                )
                and len(cells) >= 2
            ):
                meeting = cells
                continue
            if meeting and len(cells) == 3 and all(c.endswith("%") for c in cells):
                probs = cells
                break
        assert meeting, "meeting row not found in fixture"
        assert probs, "probability row not found in fixture"
        e, h, x = (float(p[:-1]) for p in probs)
        assert e + h + x == pytest.approx(100.0, abs=0.5)

    def test_eventtarget_fixture_format(self):
        """HTML entities (&#39;) inside the __doPostBack href must be decoded."""
        html = '<a href="javascript:__doPostBack(&#39;ctl00$x&#39;,&#39;&#39;)">FedWatch Tool</a>'
        assert _fedwatch_eventtarget(html) == "ctl00$x"

    def test_compare_diy_vs_official_gate(self):
        diy = [{"meeting": "SEP 26", "hike": 0.66}]
        off = [{"meeting": "Sep 2026", "hike": 66.3}]
        cmp_ = compare_diy_vs_official(diy, off)
        assert len(cmp_) == 1
        assert cmp_[0]["pass"] is True  # 0.3pp difference is within the 3pp tolerance
        off2 = [{"meeting": "Sep 2026", "hike": 80.0}]
        assert compare_diy_vs_official(diy, off2)[0]["pass"] is False
