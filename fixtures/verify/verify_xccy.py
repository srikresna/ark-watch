# -*- coding: utf-8 -*-
import re, sys, os, json
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from curl_cffi import requests

OUT = r'D:\remote\ark-watch\tmp\verify_out'

def log(*a): print(*a, flush=True)

s = requests.Session(impersonate='chrome')
u = ('https://cmegroup-tools.quikstrike.net/User/QuikStrikeView.aspx'
     '?viewitemid=XCCYCalculator&userId=lwolf&jobRole=&company=&companyType=')
r = s.get(u, headers={'Referer': 'https://www.cmegroup.com/'}, timeout=(10, 60))
log('XCCY QuikStrikeView:', r.status_code, 'len', len(r.text), 'final', r.url[:160])
h = r.text
open(os.path.join(OUT, 'xccy_view.html'), 'w', encoding='utf-8', errors='replace').write(h)
log('markers:', {m: (m in h) for m in ['Cross Currency Basis Watch', 'Implied Basis', 'FX Link',
                                       'EUR/USD', 'Period Start', 'Maintenance']})

# header stats
for pat in [r'Spot FX.{0,120}', r'FX Link.{0,120}', r'Fixing Date.{0,160}', r'Front Quarterly.{0,120}']:
    m = re.search(pat, h)
    if m:
        log('HDR:', re.sub(r'<[^>]+>', ' ', m.group(0))[:120].strip())

# parse all tables, keep the one w/ Implied Basis header or IMM rows
best = []
for t in re.findall(r'<table[^>]*>(.*?)</table>', h, re.S):
    plain = re.sub(r'<[^>]+>', ' ', t)
    if 'Implied Basis' in plain or ('Period Start' in plain) or re.search(r'\bJun\s?26\b|\bSep\s?26\b', plain):
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
            cells = [re.sub(r'&nbsp;?', ' ', re.sub(r'<[^>]+>', '', c)).strip()
                     for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
            cells = [c for c in cells if c != '']
            if cells:
                best.append(cells)
for row in best:
    log('ROW:', row)

# fixings chart points count from saved ESTRWatch chart json
try:
    c = open(os.path.join(OUT, 'chart_0.json'), encoding='utf-8', errors='replace').read()
    log('--- chart_0 structure probe ---')
    log('len', len(c))
    # find array-looking point patterns
    pts = re.findall(r'\[\s*"?([\d.\-\/: ]{4,25})"?\s*,\s*([\d.]+)\s*\]', c)
    log('pair-tuples found:', len(pts))
    if pts:
        ys = [float(p[1]) for p in pts]
        log('first5', pts[:5], 'last5', pts[-5:])
        log('n=%d min=%.3f max=%.3f' % (len(ys), min(ys), max(ys)))
        flat = [p for p in pts if abs(float(p[1]) - ys[-1]) < 1e-9]
        log('points equal to last value:', len(flat))
except Exception as e:
    log('chart probe fail:', repr(e))
log('DONE2')
