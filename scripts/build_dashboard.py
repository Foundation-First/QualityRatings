"""Build the printable "Dashboard" page (Letter, portrait) of the Power BI report: title, KPI cards and six charts.

Charts are Deneb (Vega-Lite) visuals, except the line chart, which is copied from page 1.
Locality, program type and site are not on the page: they are in the Filters pane, which PDF export and printing leave out.

Run with Power BI Desktop closed:  python scripts/build_dashboard.py internal/powerbi-work
Needs page 1 (the one-pager), the numeric measures (build_powerbi.py --measures-only) and one Deneb visual
saved anywhere in the report once (a copy is kept in <project>/deneb-template.json).
Re-running rebuilds the page from scratch; any pages after the second are removed.
"""
import copy, json, os, shutil, sys, uuid
from pathlib import Path

PROJECT = Path(sys.argv[1] if len(sys.argv) > 1 else 'internal/powerbi-work')
RP = next(PROJECT.glob('*.Report')) / 'definition'
pages_json = RP / 'pages' / 'pages.json'
load = lambda p: json.load(open(p, encoding='utf-8-sig'))
dump = lambda j, p: p.write_text(json.dumps(j, indent=2), encoding='utf-8')
order = load(pages_json)
P1 = RP / 'pages' / order['pageOrder'][0]
L = lambda v: {'expr': {'Literal': {'Value': v}}}

# ---- keep a Deneb visual Desktop wrote, as the template for the charts
TEMPLATE = PROJECT / 'deneb-template.json'
for f in RP.glob('pages/*/visuals/*/visual.json'):
    t = f.read_text(encoding='utf-8-sig')
    if '"visualType": "deneb' in t:
        shutil.copy(f, TEMPLATE)
if not TEMPLATE.exists():
    sys.exit('Add a Deneb visual to the report in Power BI Desktop, save, close, and run this again.')
deneb_tpl = json.load(open(TEMPLATE, encoding='utf-8'))

# ---- page folder
for old in order['pageOrder'][2:]:
    shutil.rmtree(RP / 'pages' / old, ignore_errors=True)
order['pageOrder'] = order['pageOrder'][:2]
if len(order['pageOrder']) > 1:
    P3 = RP / 'pages' / order['pageOrder'][1]
    shutil.rmtree(P3 / 'visuals', onerror=lambda f, p_, e: (os.chmod(p_, 0o777), f(p_)))
else:
    pid = uuid.uuid4().hex[:20]
    P3 = RP / 'pages' / pid
    P3.mkdir()
    order['pageOrder'].append(pid)
order['activePageName'] = P3.name
dump(order, pages_json)
(P3 / 'visuals').mkdir(exist_ok=True)


def col(ent, prop, name=None):
    return {'field': {'Column': {'Expression': {'SourceRef': {'Entity': ent}}, 'Property': prop}}, 'queryRef': ent + '.' + prop, 'nativeQueryRef': prop, 'active': True}


def mea(prop):
    return {'field': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Published Scores'}}, 'Property': prop}}, 'queryRef': 'Published Scores.' + prop, 'nativeQueryRef': prop}


# ---- Filters pane: locality, program type, site (not printed)
pg = load(P1 / 'page.json')
pg.update(name=P3.name, displayName='Dashboard', width=816, height=1056)
pg['filterConfig'] = {'filters': [
    {'name': uuid.uuid4().hex[:20], 'field': col(ent, prop)['field'], 'type': 'Categorical'}
    for ent, prop in (('Published Scores', 'cr720_county'), ('Sites-Orgs', 'cr720_providertypename'), ('Published Scores', 'cr720_sitename'))]}
dump(pg, P3 / 'page.json')

# ---- source visuals from page 1
src = {}
for f in (P1 / 'visuals').glob('*/visual.json'):
    j = load(f)
    if 'visual' in j:      # skip visual groups
        src.setdefault(j['visual']['visualType'], []).append(j)
fields = lambda j: [p['queryRef'] for d in (j['visual'].get('query', {}).get('queryState', {}) or {}).values() for p in d.get('projections', [])]
title_card = next(j for j in src['cardVisual'] if any('Report title' in r for r in fields(j)))
kpis = [next(j for j in src['cardVisual'] if any('Published Scores.' + m in r for r in fields(j))) for m in ('Sites rated', 'Average points', 'Gap vs RRNC', 'Gap vs Virginia')]
chart = src['lineChart'][0]
boxes = sorted(src['textbox'], key=lambda j: 'Internal use' in json.dumps(j))     # the "Data as of" box first, the footer last
asof_box, footer = boxes[0], boxes[-1]

z = [0]


def add(template, x, y, w, h):
    j = copy.deepcopy(template)
    j['name'] = uuid.uuid4().hex[:20]
    j.pop('parentGroupName', None)
    j.pop('filterConfig', None)
    j['position'].update(x=x, y=y, width=w, height=h, z=z[0], tabOrder=z[0])
    z[0] += 1
    d = P3 / 'visuals' / j['name']
    d.mkdir()
    return j, d


def detail_filter(prop, values):
    """Visual-level filter: Detail[prop] is one of values."""
    ent = {'Name': 'd', 'Entity': 'Detail', 'Type': 0}
    fld = {'Column': {'Expression': {'SourceRef': {'Entity': 'Detail'}}, 'Property': prop}}
    cond = {'Column': {'Expression': {'SourceRef': {'Source': 'd'}}, 'Property': prop}}
    vals = [[{'Literal': {'Value': "'" + v + "'"}}] for v in values]
    return {'filters': [{'name': uuid.uuid4().hex[:20], 'field': fld, 'type': 'Categorical', 'filter': {'Version': 2, 'From': [ent], 'Where': [{'Condition': {'In': {'Expressions': [cond], 'Values': vals}}}]}, 'howCreated': 'User'}]}


# ---- Deneb charts
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pbi_specs as S


def deneb(x, y, w, h, title, category, series, spec, only=None):
    j, d = add(deneb_tpl, x, y, w, h)
    j['visual']['query'] = {'queryState': {'dataset': {'projections': [category] + series}}}
    lit = lambda t: L("'" + t.replace("'", "''") + "'")
    j['visual']['objects'] = {'vega': [{'properties': {'provider': lit('vegaLite'), 'renderMode': lit('svg'), 'jsonSpec': lit(json.dumps(spec)), 'jsonConfig': lit('{}'), 'isNewDialogOpen': L('false')}}]}
    j['visual']['visualContainerObjects'] = {'title': [{'properties': {'show': L('true'), 'text': L("'" + title + "'")}}]}
    if only:
        j['filterConfig'] = detail_filter(*only)
    dump(j, d / 'visual.json')


# ---- layout: Letter portrait, 816 x 1056
j, d = add(title_card, 0, 0, 816, 64); dump(j, d / 'visual.json')
j, d = add(asof_box, 20, 70, 776, 46); dump(j, d / 'visual.json')
for n, k in enumerate(kpis):
    j, d = add(k, 20 + n * 196, 122, 184, 78); dump(j, d / 'visual.json')

W, X = 384, [20, 412]
S_ = lambda *names: [mea(n) for n in names]
SH = ('Group detail share', 'RRNC detail share', 'Virginia detail share')

# row 1: ratings as tiles
deneb(20, 210, 776, 165, 'Quality ratings, latest program year', col('Rating Levels', 'Level'),
      S_('Group level share', 'RRNC level share', 'Virginia level share', 'Sites rated'), S.rating_tiles())
# row 2: trend (native line chart from page 1) and program type dots
j, d = add(chart, X[0], 383, W, 230)
j['visual']['visualContainerObjects']['subTitle'] = [{'properties': {'show': L('false')}}]
dump(j, d / 'visual.json')
deneb(X[1], 383, W, 230, 'Average score by program type', col('Sites-Orgs', 'cr720_providertypename'),
      S_('Average points', 'RRNC average points', 'Virginia average points'),
      S.dot_plot(['Average points', 'RRNC average points', 'Virginia average points'], 'cr720_providertypename', 'd'))
# row 3: points against the maximum, and years in VQB5
deneb(X[0], 621, W, 175, 'Points against the maximum possible', col('Detail', 'Item'),
      S_('Group detail points', 'RRNC detail points', 'Virginia detail points'),
      S.bullet({'Interaction points': 700, 'Total points': 800}, ['Interaction points', 'Total points']), ('Item', ['Interaction points', 'Total points']))
deneb(X[1], 621, W, 175, 'Years in VQB5', col('Detail', 'Item'), S_(*SH, 'Sites rated'),
      S.detail_tiles(['First year', 'Second year', 'Third year or more'], ['#C9DCEA', '#7FA9C9', '#0E3F66']), ('Section', ['Years in VQB5']))
# row 4: Honor Roll tiles and curriculum rings
deneb(X[0], 804, W, 175, 'Honor Roll', col('Detail', 'Item'), S_(*SH, 'Sites rated'),
      S.detail_tiles(['Excellence', 'Improvement', 'Infant/Toddler'], ['#BFDC8C', '#8DBF4A', '#4C7A12']), ('Section', ['Honor Roll']))
deneb(X[1], 804, W, 175, 'Sites using a VDOE-approved curriculum', col('Detail', 'Item'), S_(*SH),
      S.rings(SH), ('Item', ['Curriculum points']))

j, d = add(footer, 20, 988, 776, 44)
j['visual']['objects']['general'][0]['properties']['paragraphs'] = [{'textRuns': [{'value': 'Internal use. Approval is needed before sharing outside Foundation First / RRNC. Source: VDOE VQB5 Quality Rating Data (public); Virginia figures from VDOE statewide files. Scores run from 100 to 800. No Provider 360 or other internal data is included.', 'textStyle': {'fontSize': '10pt', 'color': '#4f5f6b'}}]}]
dump(j, d / 'visual.json')
print('Dashboard built:', P3.name, '-', len(list((P3 / 'visuals').glob('*'))), 'visuals')
