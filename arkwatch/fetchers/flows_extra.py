"""flows_extra.py — flow fetchers: Farside BTC/ETH ETF flows, TIC China
holdings, PBoC gold reserves, LME copper stocks, and LBMA silver vault data.

The targets are bot-gated or ship unusual formats (Farside HTML tables with
'DD MMM YYYY' dates, Treasury TIC HTML, SAFE/LME/LBMA XLSX archives), so each
parser is tailored to a verified response shape.
"""

from __future__ import annotations

import io
import re
from datetime import UTC, datetime

import requests
from curl_cffi import requests as creq

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
}


def _fetch_farside(path: str) -> dict:
    """Fetch the latest net-flow row from a Farside table.

    Dates appear as 'DD MMM YYYY' inside span.tabletext in the tbody;
    negative values are parenthesized '(5.7)' inside a redFont span.
    """
    r = requests.get(f"https://farside.co.uk/{path}/", headers=UA, timeout=(10, 30))
    if r.status_code != 200:
        raise RuntimeError(f"Farside {path}: HTTP {r.status_code}")
    # rows are keyed by a leading date cell
    trs = re.findall(
        r'<tr[^>]*>\s*<td><span class="tabletext">(\d{1,2}\s+\w{3}\s+\d{4})</span></td>.*?</tr>',
        r.text,
        re.S,
    )
    if not trs:
        raise RuntimeError(f"Farside {path}: no date rows in tbody")
    date = trs[0]  # latest
    # normalize 'DD MMM YYYY' -> ISO for flows_daily
    try:
        iso = datetime.strptime(date, "%d %b %Y").date().isoformat()
    except ValueError:
        iso = date
    # locate the full row for that date and slice to its </tr>
    idx = r.text.find(f">{date}<")
    if idx < 0:
        raise RuntimeError(f"Farside {path}: date could not be located")
    tr_end = r.text.find("</tr>", idx)
    tr_text = r.text[idx:tr_end]
    # Capture parentheses in the RAW match: detecting them after stripping
    # commas would search for "(1234.5)" and never match "(1,234.5)", so
    # thousand-separated outflows would lose their negative sign.
    nums = re.findall(
        r'<span class="(?:tabletext|redFont|greenFont)">(\(?)([\d.,]+)(\))?</span>', tr_text
    )
    if not nums:
        raise RuntimeError(f"Farside {path}: no numbers in row")
    open_p, total_raw, close_p = nums[-1]
    val = float(total_raw.replace(",", "").rstrip("."))
    if open_p and close_p:  # both parentheses captured raw = negative value
        val = -val
    return {"ts": date, "date_iso": iso, "net_flow_musd": val}


def fetch_farside_btc() -> dict:
    return _fetch_farside("btc")


def fetch_farside_eth() -> dict:
    return _fetch_farside("eth")


def fetch_tic_china() -> dict:
    """China long-term Treasury holdings from the official MFH table (slt_table5).

    Columns run newest-first, so the LEFTMOST column is the latest period.
    The legacy ticdata mfh.txt endpoint is a stale snapshot frozen in
    Feb-2023 and must not be used; this HTML table is the maintained source.
    """
    s = creq.Session(impersonate="chrome")
    r = s.get(
        "https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.html",
        timeout=(10, 30),
    )
    if r.status_code != 200:
        raise RuntimeError(f"TIC: HTTP {r.status_code}")
    text = r.text
    cells = [c.strip() for c in re.sub(r"<[^>]+>", "|", text).split("|")]
    # Read periods only from the table header: a run of >= 3 consecutive
    # 'YYYY-mm' cells. Empty split artifacts between <td>s are skipped so
    # they do not break the run.
    periods = []
    run = []
    for c in cells:
        if not c:
            continue
        if re.fullmatch(r"20\d\d-\d\d", c):
            run.append(c)
        else:
            if len(run) >= 3:
                periods.extend(run)
            run = []
    if len(run) >= 3:
        periods.extend(run)
    try:
        i = cells.index("China, Mainland")
    except ValueError as exc:
        raise RuntimeError("TIC: China, Mainland row not found") from exc
    nums = []
    for c in cells[i + 1 :]:
        if re.fullmatch(r"[\d,.]+", c or ""):
            nums.append(float(c.replace(",", "")))
        elif nums:
            break
    if not nums:
        raise RuntimeError("TIC: no numbers in the China row")
    return {
        "ts": periods[0] if periods else "latest",
        "china_usd_b": nums[0],
    }  # first column = latest period


def fetch_pboc_gold() -> dict:
    """PBoC gold reserves from the SAFE monthly XLSX."""
    from openpyxl import load_workbook

    s = creq.Session(impersonate="chrome")
    r = s.get("https://www.safe.gov.cn/en/2021/0203/2045.html", timeout=(10, 30))
    if r.status_code != 200:
        raise RuntimeError(f"SAFE: HTTP {r.status_code}")
    links = re.findall(r'href="(/en/file/file/[^"]+\.xlsx)"', r.text)
    if not links:
        raise RuntimeError("SAFE: XLSX link not found")
    r2 = s.get(f"https://www.safe.gov.cn{links[0]}", timeout=(10, 60))
    if r2.status_code != 200 or r2.content[:2] != b"PK":
        raise RuntimeError(f"SAFE XLSX: HTTP {r2.status_code}")
    wb = load_workbook(io.BytesIO(r2.content), read_only=True, data_only=True)
    # Sheet1 layout: row 3 holds 'YYYY.MM' date headers, rows 4-5 are unit
    # rows (100M USD / 100M SDR), and the gold volume row embeds values in
    # Chinese text like '7419万盎司' (wan-oz), one column per month. Volume
    # is parsed from that text; conversion is centralized in units.
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    # build column index -> 'YYYY-MM' from the row-3 date headers
    date_cols: dict[int, str] = {}
    if len(rows) > 3:
        for i, c in enumerate(rows[3]):
            m = re.match(r"(\d{4})\.(\d{2})", str(c).strip() if c else "")
            if m:
                date_cols[i] = f"{m.group(1)}-{m.group(2)}"
    for row in rows:
        vals = [str(c).strip() if c is not None else "" for c in row]
        if not any("万盎司" in v for v in vals):
            continue
        # the LAST cell containing 'N万盎司' is the latest month
        for i in range(len(vals) - 1, -1, -1):
            m = re.search(r"([\d.,]+)\s*万盎司", vals[i])
            if not m:
                continue
            wan_oz = float(m.group(1).replace(",", ""))
            from ..units import wan_oz_to_tonnes

            tonnes = wan_oz_to_tonnes(wan_oz)
            ts = date_cols.get(i) or datetime.now(UTC).strftime("%Y-%m")
            return {"ts": ts, "wan_oz": wan_oz, "tonnes": round(tonnes, 1)}
    raise RuntimeError("SAFE: Gold volume row (万盎司) not found")


_LME_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


def fetch_lme_stocks(year: int, month: int, session=None) -> list[dict]:
    """LME daily closing stocks (CA = copper column), unit tonnes.

    Monthly XLSX archives follow a predictable filename pattern,
    stocks-{month}-{year}.xlsx (archive reaches back to 2018). Two header
    eras exist ('Stock Date' vs 'BusinessDate'), so the header row is
    located dynamically. Cloudflare requires curl_cffi chrome impersonation,
    and the session must be SHARED across months: a fresh session per file
    fires many consecutive distinct TLS fingerprints and gets blocked.
    Returns [{'ts': 'YYYY-MM-DD', 'copper_tonnes': float}] daily rows; []
    when the file is not published yet or the format is unrecognized.
    """
    from openpyxl import load_workbook

    url = (
        "https://www.lme.com/-/media/files/data/reports-and-data/"
        f"warehouse-and-stock-reports/stocks-summary/"
        f"stocks-{_LME_MONTHS[month - 1]}-{year}.xlsx"
    )
    s = session if session is not None else creq.Session(impersonate="chrome")
    r = s.get(url, timeout=(10, 60))
    # Unpublished months are a soft-404: HTTP 200 with an HTML body.
    # Genuine XLSX starts with the PK magic bytes.
    if r.status_code != 200 or r.content[:2] != b"PK":
        return []
    wb = load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    # locate the header row dynamically: 'BusinessDate'/'Stock Date' plus 'CA'
    hdr_i = date_col = ca_col = None
    for i, row in enumerate(rows[:20]):
        cells = [str(c).strip() if c is not None else "" for c in row]
        if "BusinessDate" in cells:
            hdr_i, date_col = i, cells.index("BusinessDate")
        elif "Stock Date" in cells:
            hdr_i, date_col = i, cells.index("Stock Date")
        if hdr_i is not None:
            if "CA" in cells:
                ca_col = cells.index("CA")
                break
            hdr_i = None  # header row without a CA column -> keep looking
    if hdr_i is None or ca_col is None:
        return []
    out = []
    for row in rows[hdr_i + 1 :]:
        if len(row) <= ca_col:
            continue
        d, v = row[date_col], row[ca_col]
        if d is None or v is None:
            continue
        ts = d.date().isoformat() if hasattr(d, "date") else str(d)[:10]
        try:
            out.append({"ts": ts, "copper_tonnes": float(v)})
        except (TypeError, ValueError):
            continue
    return out


def fetch_lbma_silver() -> dict:
    """LBMA silver vault holdings from the CDN XLSX."""
    from openpyxl import load_workbook

    s = creq.Session(impersonate="chrome")
    r = s.get("https://www.lbma.org.uk/prices-and-data/london-vault-data", timeout=(10, 30))
    links = (
        re.findall(r'href="(https://cdn\.lbma\.org\.uk/[^"]+\.xlsx)"', r.text)
        if r.status_code == 200
        else []
    )
    if not links:
        now = datetime.now(UTC)
        prev = f"{now.year}-{now.month - 1:02d}" if now.month > 1 else f"{now.year - 1}-12"
        links = [f"https://cdn.lbma.org.uk/media/london-vault-data/lbv-{prev}.xlsx"]
    r2 = s.get(links[0], timeout=(10, 60))
    if r2.status_code != 200 or r2.content[:2] != b"PK":
        raise RuntimeError(f"LBMA: HTTP {r2.status_code}")
    wb = load_workbook(io.BytesIO(r2.content), read_only=True, data_only=True)
    # Layout: row 1 headers ('Month End|Gold|Silver'), row 2 units
    # ("Troy Ounces ('000s)" = thousand oz), row 3 = newest month with an
    # EMPTY 'Month End' label, rows 4+ = 'YYYY-MM' descending. The
    # koz -> tonnes conversion is centralized in units.koz_to_tonnes.
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    silver_col = None
    for row in rows[:3]:
        for i, c in enumerate(row):
            if c and str(c).strip().lower() == "silver":
                silver_col = i
                break
        if silver_col is not None:
            break
    if silver_col is None:
        raise RuntimeError("LBMA: Silver column not found in header")
    for row in rows:
        if row is None or len(row) <= silver_col:
            continue
        v = row[silver_col]
        if isinstance(v, (int, float)) and v > 0:
            koz = float(v)
            # ts from the row label; when empty (newest row), derive it from
            # the filename pattern 'July-2026.xlsx'
            ts = str(row[0]).strip() if row and row[0] else ""
            if not re.match(r"\d{4}-\d{2}", ts):
                m = re.search(r"([A-Za-z]+)-(\d{4})", links[0])
                if m:
                    mo = {
                        "january": "01",
                        "february": "02",
                        "march": "03",
                        "april": "04",
                        "may": "05",
                        "june": "06",
                        "july": "07",
                        "august": "08",
                        "september": "09",
                        "october": "10",
                        "november": "11",
                        "december": "12",
                    }.get(m.group(1).lower())
                    if mo:
                        ts = f"{m.group(2)}-{mo}"
            from ..units import koz_to_tonnes

            return {
                "ts": ts or datetime.now(UTC).strftime("%Y-%m"),
                "koz": round(koz, 1),
                "tonnes": round(koz_to_tonnes(koz), 1),
            }
    raise RuntimeError("LBMA: no Silver data rows")
