# -*- coding: utf-8 -*-
"""Adversarial re-test of 'estrBasis' findings. Fresh curl_cffi sessions everywhere."""
import json, re, html as H, os, sys, time

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from curl_cffi import requests

OUT = r'D:\remote\ark-watch\tmp\verify_out'
os.makedirs(OUT, exist_ok=True)

def log(*a):
    print(*a, flush=True)

def fresh():
    return requests.Session(impersonate='chrome')

def get(url, headers=None, s=None, timeout=(10, 60)):
    ss = s or fresh()
    return ss.get(url, headers=headers or {}, timeout=timeout)

REF_CME = {'Referer': 'https://www.cmegroup.com/'}
QS_BASE = 'https://cmegroup-tools.quikstrike.net/User/QuikStrikeView.aspx'
URL_ESTRWATCH = QS_BASE + '?viewitemid=ESTRWatch&userId=lwolf&jobRole=&company=&companyType='

def ascii_safe(s, n=300):
    return re.sub(r'\s+', ' ', s)[:n].encode('ascii', 'replace').decode()

# ================= CLAIM 1: anonymous access =================
log('=' * 25, 'CLAIM 1: QuikStrikeView anonymous access')

# 1a fresh session + bare cmegroup Referer
r = get(URL_ESTRWATCH, REF_CME)
estr_html = r.text if r.status_code == 200 else ''
log('1a ESTRWatch + Referer=cmegroup.com/:', r.status_code, 'len', len(r.text), 'final', r.url)
log('   markers:', {m: (m in estr_html) for m in ['ESRM6', 'ESTR Fixings', '9/10/2026', 'JSONSettings', 'Meeting Date']})

# 1b no Referer at all
r2 = get(URL_ESTRWATCH)
log('1b NO Referer:', r2.status_code, 'len', len(r2.text), 'final', r2.url)
log('   body:', ascii_safe(r2.text, 220))

# 1c Referer = quikstrike.net
r3 = get(URL_ESTRWATCH, {'Referer': 'https://www.quikstrike.net/'})
log('1c Referer=quikstrike.net:', r3.status_code, 'len', len(r3.text))

# 1d Referer = unrelated site
r4 = get(URL_ESTRWATCH, {'Referer': 'https://example.com/'})
log('1d Referer=example.com:', r4.status_code, 'len', len(r4.text), 'final', r4.url)

# 1e reproducibility: third fresh session
r5 = get(URL_ESTRWATCH, REF_CME)
log('1e fresh session repeat:', r5.status_code, 'len', len(r5.text), 'ESRM6 present:', 'ESRM6' in r5.text)

# wrapper pages: which quikstrike URLs do they reference?
WRAPPERS = {
    'estrwatch': 'https://www.cmegroup.com/markets/interest-rates/cme-estrwatch.html',
    'xccy': 'https://www.cmegroup.com/markets/interest-rates/cme-group-cross-currency-basis-watch.html',
}
qs_urls = {}
for k, u in WRAPPERS.items():
    try:
        rw = get(u)
        hits = sorted(set(H.unescape(m) for m in re.findall(r'cmegroup-tools\.quikstrike\.net[^"\'\s<>\\]+', rw.text)))
        qs_urls[k] = hits
        log('wrapper', k, rw.status_code, 'len', len(rw.text), 'qs-refs:', len(hits))
        for h in hits:
            log('   ', h[:220])
    except Exception as e:
        log('wrapper', k, 'FAILED:', repr(e))

# save html for offline parsing
open(os.path.join(OUT, 'estrwatch.html'), 'w', encoding='utf-8', errors='replace').write(estr_html)

# ================= CLAIM 2 (data content of ESTRWatch, cross-check) =================
log('=' * 25, 'ESTRWatch content markers')
mm = re.search(r'lvMeetings1.*?</table>', estr_html, re.S)
if mm:
    cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', mm.group(0), re.S)
    clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
    clean = [c for c in clean if c != '']
    log('meeting-table cells (first 60):', clean[:60])
for sym in ['ESRM6', 'ESRZ6', 'ESRH7']:
    i = estr_html.find(sym)
    if i >= 0:
        seg = re.sub(r'<[^>]+>', '|', estr_html[i:i + 500])
        seg = re.sub(r'\|+', '|', seg)
        log(sym, 'ctx:', seg[:220])
n_js = len(re.findall(r'JSONSettings', estr_html))
log('JSONSettings occurrences:', n_js)

# try decoding chart settings
charts = []
for m in re.finditer(r'"JSONSettings":"((?:[^"\\]|\\.)*)"', estr_html):
    raw = m.group(1)
    try:
        dec = raw.encode('latin-1', 'backslashreplace').decode('unicode_escape')
        charts.append(dec)
    except Exception as e:
        log('chart decode fail:', repr(e))
log('decoded chart settings:', len(charts))
for c in charts:
    pts = len(re.findall(r'\{"X"?[:\s]', c)) or len(re.findall(r'\d{4}-\d{2}-\d{2}', c))
    log('  chart: len', len(c), 'date-like tokens:', len(re.findall(r'\d{4}-\d{2}-\d{2}', c)),
        'has 2025-09-01:', '2025-09-01' in c, 'has 2.191/1.916:', ('2.191' in c or '1.916' in c))
    open(os.path.join(OUT, 'chart_%d.json' % charts.index(c)), 'w', encoding='utf-8', errors='replace').write(c)

# ================= CLAIM 3: settlements id 10247 =================
log('=' * 25, 'CLAIM 3: CmeWS settlements 10247')

def settles(pid, date, s=None):
    u = ('https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/%s/FUT'
         '?strategy=DEFAULT&tradeDate=%s&pageSize=500' % (pid, date))
    rr = get(u, s=s)
    try:
        return rr.status_code, rr.json()
    except Exception as e:
        return rr.status_code, {'_parse_error': repr(e), '_head': ascii_safe(rr.text, 200)}

st, d = settles(10247, '08/28/2026')
log('10247 @08/28/2026:', st, 'empty:', d.get('empty'), 'rows:', len(d.get('settlements') or []),
    'tradeDate:', d.get('tradeDate'), 'updateTime:', d.get('updateTime'))
esr_rows = {}
for row in (d.get('settlements') or []):
    log('   ', row.get('month'), '| settle', row.get('settle'), '| OI', row.get('openInterest'),
        '| vol', row.get('volume'), '| chg', row.get('change'))
    esr_rows[row.get('month')] = row

for dt in ['08/27/2026', '08/21/2026', '08/14/2026']:
    st2, d2 = settles(10247, dt)
    log('10247 @%s:' % dt, st2, 'empty:', d2.get('empty'), 'rows:', len(d2.get('settlements') or []))

# ProductSlate
try:
    rps = get('https://www.cmegroup.com/CmeWS/mvc/ProductSlate/V2/List?searchString=ESTR&pageSize=8')
    log('ProductSlate ESTR:', rps.status_code, ascii_safe(rps.text, 500))
except Exception as e:
    log('ProductSlate ESTR FAILED:', repr(e))

# ================= CLAIM 5: reproduce xccy basis from settlements =================
log('=' * 25, 'CLAIM 5: xccy basis reproduction')

# 5a fetch the xccy tool page
xccy_url = None
cand = [u for u in qs_urls.get('xccy', []) if 'viewitemid' in u]
if cand:
    xccy_url = cand[0]
else:
    xccy_url = QS_BASE + '?viewitemid=XCCYCalculator&userId=lwolf&jobRole=&company=&companyType='
log('xccy tool url:', xccy_url[:200])
rx = get(xccy_url, REF_CME)
xccy_html = rx.text if rx.status_code == 200 else ''
log('xccy fetch:', rx.status_code, 'len', len(rx.text))
open(os.path.join(OUT, 'xccy.html'), 'w', encoding='utf-8', errors='replace').write(xccy_html)
log('   title EUR/USD:', ('EUR/USD' in xccy_html), '| Implied Basis:', ('Implied Basis' in xccy_html),
    '| FX Link:', ('FX Link' in xccy_html))

# header stats
for pat in [r'Spot FX[^<]*', r'FX Link[^<]*', r'Fixing Date[^<]*']:
    m = re.search(pat, xccy_html)
    log('   header:', ascii_safe(m.group(0), 80) if m else None)

# parse main grid
rows_parsed = []
tbls = re.findall(r'<table[^>]*>(.*?)</table>', xccy_html, re.S)
log('tables on xccy page:', len(tbls))
for t in tbls:
    txt = re.sub(r'<[^>]+>', ' ', t)
    if 'Implied Basis' in txt or ('Period Start' in txt):
        trs = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)
        for tr in trs:
            cells = [re.sub(r'&nbsp;', ' ', re.sub(r'<[^>]+>', '', c)).strip()
                     for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
            cells = [c for c in cells if c != '']
            if cells:
                rows_parsed.append(cells)
for rp_ in rows_parsed:
    log('   ROW:', rp_)

# 5b settlements for SR3 (8462) and 6E (58)
def settle_map(pid, date='08/28/2026'):
    stx, dx = settles(pid, date)
    out = {}
    for row in (dx.get('settlements') or []):
        out[row.get('month')] = row
    log('settles', pid, stx, 'rows', len(out))
    for k, v in list(out.items())[:14]:
        log('   ', k, v.get('settle'), 'OI', v.get('openInterest'))
    return out

sr3 = settle_map(8462)
e6 = settle_map(58)

def fnum(x):
    try:
        return float(str(x).replace(',', ''))
    except Exception:
        return None

# claimed tool table (from finding, dated 08-28) as fallback/anchor:
CLAIMED = [
    # period, start, end, days, SR3feed, ESRfeed, 6Efeed(F), basis_tool
    ('Jun26', '2026-09-01', '2026-09-16', 15, 96.3525, 97.8075, 1.1587500, 2.50),
    ('Sep26', '2026-09-16', '2026-12-16', 91, 96.14, 97.54, 1.1628500, -0.84),
    ('Dec26', '2026-12-16', '2027-03-16', 91, 95.91, 97.36, 1.1672000, -3.96),
    ('Mar27', '2027-03-16', '2027-06-16', 91, 95.775, 97.23, 1.1714000, 2.14),
    ('Jun27', '2027-06-16', '2027-09-16', 91, 95.72, 97.1575, 1.1756000, 0.89),
    ('Sep27', '2027-09-16', '2027-12-16', 91, 95.73, 97.1375, 1.1796500, 3.46),
]

MONTH = {'F': 'JAN', 'G': 'FEB', 'H': 'MAR', 'J': 'APR', 'K': 'MAY', 'M': 'JUN',
         'N': 'JUL', 'Q': 'AUG', 'U': 'SEP', 'V': 'OCT', 'X': 'NOV', 'Z': 'DEC'}

def code_to_month(code):
    # e.g. ESRZ6 -> 'DEC 26'
    return '%s %s' % (MONTH.get(code[3], '??'), code[4:].lstrip('0').zfill(2) if False else ('20' + code[4:]))

log('--- reproduction (formula from finding; inputs = live settlement strings) ---')
for per, d0, d1, days, sr3f, esrf, ef, basis_claim in CLAIMED:
    t = days / 360.0
    # find matching contract settles by value
    def find(pid_map, val, tol=6e-05):
        for k, v in pid_map.items():
            sv = fnum(v.get('settle'))
            if sv is not None and abs(sv - val) <= tol:
                return k, v.get('settle'), sv
        # looser pass (4dp rounding)
        for k, v in pid_map.items():
            sv = fnum(v.get('settle'))
            if sv is not None and abs(sv - round(val, 4)) <= 1e-09:
                return k, v.get('settle'), sv
        return None, None, None
    sr_k, sr_s, sr_v = find(sr3, sr3f)
    es_k, es_s, es_v = find(esr_rows, esrf)
    e6_k, e6_s, e6_v = find(e6, ef)
    # S = 6E settle at period start: front stub -> use tool spot (1.15806 per finding); forward rows -> previous quarterly 6E
    if per == 'Jun26':
        S, s_note = 1.15806, 'tool-spot(1.15875-0.00069)'
    else:
        prev = {'Sep26': 'SEP 26', 'Dec26': 'DEC 26', 'Mar27': 'MAR 27', 'Jun27': 'JUN 27', 'Sep27': 'SEP 27'}[per]
        S, s_note = fnum(e6.get(prev, {}).get('settle')), '6E ' + prev
    F = e6_v
    r_usd, r_eur = 100 - sr_v, 100 - es_v
    basis = ((S * (1 + r_usd / 100.0 * t) / F - 1) / t - r_eur / 100.0) * 10000.0
    log('%s days=%d | SR3 %s(%s)=%s ESR %s(%s)=%s 6E_F %s=%s | S=%.5f(%s) | calc=%+.3f tool=%+.2f diff=%+.3f' % (
        per, days, sr_k, sr_s, sr_v, es_k, es_s, es_v, e6_k, e6_s, S, s_note, basis, basis_claim, basis - basis_claim))

log('DONE')
