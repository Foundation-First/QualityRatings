"""Make a one-page report for a locality, school district, single site or hand-picked group of sites.

Internal use only. Reads internal/data/sites.json (built by build_data.py, never published) and the aggregate
files in site/data. Writes a self-contained HTML page to internal/reports/ (open it, then Print -> Save as PDF).

  python scripts/make_report.py --locality "Spotsylvania County"
  python scripts/make_report.py --district "Spotsylvania County"       (public-school sites only)
  python scripts/make_report.py --site "Little Learners"                (name fragment or site ID)
  python scripts/make_report.py --sites 13700,13701 --label "ABC Child Care (2 sites)"
  python scripts/make_report.py --list "Spot"                           (find place or site names)

The region and state comparison uses the same program type whenever the group is a single type.
Sharing a report outside the team needs approval; the page says so.
"""
import argparse, datetime, html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YRS = ['2023-24', '2024-25', '2025-26']
TL = {'Center': 'Child care centers', 'Public School': 'Public schools', 'Family Day Home': 'Home-based child care'}
LEVELS = [('Needs Support', 100, 399), ('Meets Expectations', 400, 699), ('Exceeds Expectations', 700, 800)]
LCOL = ['#F7941D', '#9CC3DB', '#11689B']
GREEN, GREY, INK, NAVY = '#6FA82B', '#85888B', '#23323f', '#0E3F66'
esc = html.escape


def load(p):
    return json.load(open(ROOT / p, encoding='utf-8'))


def lv(tp):
    return 0 if tp <= 399 else 1 if tp <= 699 else 2


def pts(s, y):
    return s['tp'] if y == '2025-26' else (s['hist'].get(y) or {}).get('tp')


def chart(ser, lo, hi):
    W, H, L, R, TP, B = 640, 250, 60, 30, 20, 40
    X = lambda i: L + i * (W - L - R) / 2
    Y = lambda v: TP + (hi - v) / (hi - lo) * (H - TP - B)
    o = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Average total points by year" style="width:100%%">' % (W, H + 40)]
    for t in range(int(lo // 20 + 1) * 20, int(hi), 20):
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#e9eef2"/><text x="%d" y="%.1f" text-anchor="end" font-size="15" fill="%s">%d</text>' % (L, W - R, Y(t), Y(t), L - 8, Y(t) + 5, INK, t))
    for i, y in enumerate(YRS):
        o.append('<text x="%.1f" y="%d" text-anchor="middle" font-size="16" fill="%s">%s</text>' % (X(i), H - 8, INK, y))
    for k, (nm, vs, c, dash) in enumerate(ser):
        d = ' stroke-dasharray="%s"' % dash if dash else ''
        pp = [(i, X(i), Y(v), v) for i, v in enumerate(vs) if v is not None]
        o.append('<polyline fill="none" stroke="%s" stroke-width="3.5"%s points="%s"/>' % (c, d, ' '.join('%.1f,%.1f' % (x, y) for _, x, y, _ in pp)))
        for i, x, y, v in pp:
            others = [s[1][i] for s in ser if s is not ser[k] and s[1][i] is not None]
            below = bool(others) and v < min(others)      # lowest line: label underneath, others above
            o.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s"/><text x="%.1f" y="%.1f" text-anchor="middle" font-size="15" font-weight="700" fill="%s">%.0f</text>' % (x, y, c, x, y + (24 if below else -11), '#5d6064' if c == GREY else c, v))
    lx = L
    for nm, _, c, dash in ser:
        d = ' stroke-dasharray="%s"' % dash if dash else ''
        o.append('<line x1="%d" x2="%d" y1="%d" y2="%d" stroke="%s" stroke-width="3.5"%s/><text x="%d" y="%d" font-size="15" fill="%s">%s</text>' % (lx, lx + 26, H + 22, H + 22, c, d, lx + 32, H + 27, INK, esc(nm)))
        lx += 52 + len(nm) * 7.5
    o.append('</svg>')
    return ''.join(o)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--locality')
    g.add_argument('--district')
    g.add_argument('--site')
    g.add_argument('--sites')
    g.add_argument('--list')
    ap.add_argument('--label', help='title for a hand-picked group')
    ap.add_argument('--asof', help='override the "data as of" text')
    a = ap.parse_args()
    D = load('internal/data/sites.json')
    S = load('site/data/summary.json')
    META = load('site/data/meta.json')
    sites = D['sites']
    if a.list:
        q = a.list.lower()
        for p in sorted({s['county'] for s in sites if q in s['county'].lower()}):
            print('place:', p)
        for s in sites:
            if q in s['name'].lower():
                print('site %s: %s (%s, %s)' % (s['id'], s['name'], s['county'], TL[s['type']]))
        return
    if a.locality or a.district:
        name = a.locality or a.district
        m = [s for s in sites if s['county'].lower() == name.lower()]
        if not m:
            sys.exit('No place called "%s". Try --list.' % name)
        name = m[0]['county']
        if a.district:
            m = [s for s in m if s['type'] == 'Public School']
            if not m:
                sys.exit('%s has no public-school sites in RRNC.' % name)
            title, sub = name + ' Public Schools', 'School district: public-school sites that take part in VQB5'
        else:
            title, sub = name, 'Locality: all VQB5 sites'
    elif a.site:
        m = [s for s in sites if str(s['id']) == a.site] or [s for s in sites if a.site.lower() in s['name'].lower()]
        if len(m) != 1:
            sys.exit('Matches: ' + (', '.join('%s %s' % (s['id'], s['name']) for s in m) or 'none') + '. Use the site ID to pick one.')
        title, sub = m[0]['name'], '%s in %s' % (TL[m[0]['type']], m[0]['county'])
    else:
        ids = {x.strip() for x in a.sites.split(',')}
        m = [s for s in sites if str(s['id']) in ids]
        if len(m) != len(ids):
            sys.exit('Some site IDs were not found.')
        title, sub = a.label or '%d selected sites' % len(m), 'Selected group of sites'

    types = {s['type'] for s in m}
    T = next(iter(types)) if len(types) == 1 else None
    scope = TL[T] if T else 'all site types'
    reg = {y: (S['years'][y] if T is None else S['years'][y]['byType'][T]) for y in YRS}
    st = {y: (S['statewide'][y] if T is None else S['statewide'][y]['byType'][T]) for y in YRS}
    n = len(m)
    avg = sum(s['tp'] for s in m) / n
    cnt = [0, 0, 0]
    for s in m:
        cnt[lv(s['tp'])] += 1
    byyr = {y: [pts(s, y) for s in m if pts(s, y) is not None] for y in YRS}
    who = 'This group' if n > 1 else 'This site'
    ser = [(who, [sum(byyr[y]) / len(byyr[y]) if byyr[y] else None for y in YRS], INK, ''),
           ('RRNC, ' + scope.lower(), [reg[y]['avg'] for y in YRS], GREEN, ''),
           ('Virginia, ' + scope.lower(), [st[y]['avg'] for y in YRS], GREY, '6 4')]
    vals = [v for _, vs, _, _ in ser for v in vs if v is not None]
    svg = chart(ser, min(vals) - 14, max(vals) + 14)

    def pcell(c, tot):
        return '%d (%.0f%%)' % (c, 100 * c / tot) if tot else '-'
    rb, sb = reg['2025-26']['bins'], st['2025-26']['bins']
    rl, sl = [rb[0], sum(rb[1:4]), rb[4]], [sb[0], sum(sb[1:4]), sb[4]]
    rows = ''.join('<tr><td><i class="dot" style="background:%s"></i>%s (%d-%d)</td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td></tr>' % (
        LCOL[i], LEVELS[i][0], LEVELS[i][1], LEVELS[i][2], pcell(cnt[i], n), pcell(rl[i], reg['2025-26']['n']), pcell(sl[i], st['2025-26']['n'])) for i in (2, 1, 0))
    nrow = ''.join('<td class="n">%d</td>' % len(byyr[y]) for y in YRS)
    listing = ''
    if n <= 30:
        srt = sorted(m, key=lambda s: -s['tp'])
        listing = '<h2>%s</h2><table><thead><tr><th>Site</th><th>Type</th><th class="n">2023-24</th><th class="n">2024-25</th><th class="n">2025-26</th><th>Rating</th></tr></thead><tbody>' % ('Sites' if n > 1 else 'Site detail') + ''.join(
            '<tr><td>%s</td><td>%s</td>' % (esc(s['name']), TL[s['type']]) + ''.join('<td class="n">%s</td>' % (pts(s, y) if pts(s, y) is not None else '-') for y in YRS) + '<td>%s</td></tr>' % esc(s['rating']) for s in srt) + '</tbody></table>'
    else:
        listing = '<p class="small">%d sites; the site list is left off to keep this to one page.</p>' % n
    asof = a.asof or META['vdoeWorkbook']
    d1, d2 = avg - reg['2025-26']['avg'], avg - st['2025-26']['avg']
    css = ("@page{size:letter;margin:.5in}body{margin:0;font:16px/1.4 'Nunito Sans',system-ui,sans-serif;color:%s;background:#fff}.pg{max-width:8in;margin:0 auto;padding:0 8px 20px}"
           ".top{background:%s;color:#fff;padding:18px 22px;border-bottom:5px solid %s}.top h1{margin:0;font-size:28px;line-height:1.15}.top p{margin:4px 0 0}"
           ".asof{margin:10px 0 0;color:#4f5f6b}.draft{display:inline-block;background:#fff4e0;border:1px solid #f3d29a;color:#6a3b00;padding:3px 10px;border-radius:6px;font-weight:700;margin-top:8px}"
           ".k{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}.k div{border:1px solid #e1e8ed;border-radius:10px;padding:10px 12px}.k b{display:block;font-size:28px;color:%s;line-height:1.1}.k span{color:#4f5f6b}"
           "h2{font-size:20px;color:%s;margin:16px 0 4px}table{width:100%%;border-collapse:collapse}th,td{padding:6px 8px;border-bottom:1px solid #d5dde3;text-align:left}th{background:#eef4f8;color:%s}"
           ".n{text-align:right;white-space:nowrap}.dot{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:8px}.small{color:#4f5f6b}footer{margin-top:14px;color:#4f5f6b;border-top:1px solid #d5dde3;padding-top:8px}") % (INK, NAVY, GREEN, NAVY, NAVY, NAVY)
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%(t)s - VQB5 one-pager</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700;800&display=swap"><style>%(css)s</style></head><body><div class="pg">'
            '<div class="top"><h1>%(t)s</h1><p>%(sub)s &middot; Ready Region North Central &middot; VQB5 quality ratings, 2025-26</p></div>'
            '<div class="asof"><b>Data as of:</b> %(asof)s. Prepared %(today)s.</div>'
            '<span class="draft">Internal use. Approval is needed before sharing outside Foundation First / RRNC.</span>'
            '<div class="k"><div><b>%(n)d</b><span>%(sw)s rated</span></div><div><b>%(avg).0f</b><span>%(av)s points</span></div>'
            '<div><b>%(d1)+.0f</b><span>vs. RRNC (%(ra).0f)</span></div><div><b>%(d2)+.0f</b><span>vs. Virginia (%(sa).0f)</span></div></div>'
            '<h2>Ratings in 2025-26</h2><table><thead><tr><th>Quality rating</th><th class="n">%(who)s</th><th class="n">RRNC</th><th class="n">Virginia</th></tr></thead><tbody>%(rows)s</tbody></table>'
            '<p class="small">RRNC and Virginia figures are for %(scope)s.</p>'
            '<h2>Average points over time</h2>%(svg)s'
            '<table><thead><tr><th>Sites with a score</th>%(yh)s</tr></thead><tbody><tr><td>%(who)s</td>%(nrow)s</tr></tbody></table>'
            '<p class="small">Prior-year points are those VDOE lists for sites still participating in 2025-26.</p>%(listing)s'
            '<footer>Source: VDOE VQB5 Quality Rating Data (public). Scores run from 100 to 800. No Provider 360 or other internal data is included.</footer></div></body></html>') % dict(
        t=esc(title), css=css, sub=esc(sub), asof=esc(asof), today=datetime.date.today().strftime('%B %d, %Y').replace(' 0', ' '), n=n, sw='sites' if n != 1 else 'site',
        avg=avg, av='Average' if n > 1 else 'Total', d1=d1, d2=d2, ra=reg['2025-26']['avg'], sa=st['2025-26']['avg'], who=who, rows=rows, scope=scope.lower(), svg=svg,
        yh=''.join('<th class="n">%s</th>' % y for y in YRS), nrow=nrow, listing=listing)
    out = ROOT / 'internal' / 'reports'
    out.mkdir(parents=True, exist_ok=True)
    f = out / (re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') + '.html')
    f.write_text(page, encoding='utf-8')
    print('Wrote', f)


main()
