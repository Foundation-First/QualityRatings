"""Build the 16:9 "Dashboard" page of the Power BI report: KPI cards plus six native charts on one screen.

Run with Power BI Desktop closed:  python scripts/build_dashboard.py internal/powerbi-work
Needs page 1 (the one-pager) and the numeric measures (build_powerbi.py --measures-only).
Re-running rebuilds the page from scratch; any older pages after page 1 are removed.
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

TEMPLATE = PROJECT / 'deneb-template.json'      # a Deneb visual Desktop wrote (add one on the Dashboard page, then run this)
for f in RP.glob('pages/*/visuals/*/visual.json'):
    if 'deneb' in f.read_text(encoding='utf-8-sig')[:2000].lower() and '"visualType": "deneb' in f.read_text(encoding='utf-8-sig'):
        shutil.copy(f, TEMPLATE)
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
pg = load(P1 / 'page.json')
pg.update(name=P3.name, displayName='Dashboard', width=1280, height=720)
dump(pg, P3 / 'page.json')
(P3 / 'visuals').mkdir(exist_ok=True)

src = {}
for f in (P1 / 'visuals').glob('*/visual.json'):
    j = load(f)
    if 'visual' not in j:      # a visual group the user made in Desktop
        continue
    src.setdefault(j['visual']['visualType'], []).append(j)
FIELDS = None
fields = lambda j: [p['queryRef'] for d in (j['visual'].get('query', {}).get('queryState', {}) or {}).values() for p in d.get('projections', [])]
title_card = next(j for j in src['cardVisual'] if any('Report title' in r for r in fields(j)))
slicers = sorted(src['slicer'], key=lambda j: j['position']['x'])
chart = src['lineChart'][0]
boxes = sorted(src['textbox'], key=lambda j: 'Internal use' in json.dumps(j))     # the "Data as of" box first, the footer last
asof_card = boxes[0]      # the "Data as of" line (a text box or a card, whichever page 1 uses)
kpis = [next(j for j in src['cardVisual'] if any('Published Scores.' + m in r for r in fields(j))) for m in ('Sites rated', 'Average points', 'Gap vs RRNC', 'Gap vs Virginia')]
footer = boxes[-1]
L = lambda v: {'expr': {'Literal': {'Value': v}}}


def col(ent, prop, name): return {'field': {'Column': {'Expression': {'SourceRef': {'Entity': ent}}, 'Property': prop}}, 'queryRef': ent + '.' + prop, 'nativeQueryRef': prop, 'active': True, 'displayName': name}
def mea(prop, name): return {'field': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Published Scores'}}, 'Property': prop}}, 'queryRef': 'Published Scores.' + prop, 'nativeQueryRef': prop, 'displayName': name}


z = [0]


def add(template, x, y, w, h):
    j = copy.deepcopy(template)
    j['name'] = uuid.uuid4().hex[:20]
    j.pop('parentGroupName', None)
    if template['visual']['visualType'] != 'slicer':
        j.pop('filterConfig', None)
    j['position'].update(x=x, y=y, width=w, height=h, z=z[0], tabOrder=z[0])
    z[0] += 1
    d = P3 / 'visuals' / j['name']
    d.mkdir()
    return j, d


def section_filter(section):
    ent = {'Name': 'd', 'Entity': 'Detail', 'Type': 0}
    fld = {'Column': {'Expression': {'SourceRef': {'Entity': 'Detail'}}, 'Property': 'Section'}}
    cond = {'Column': {'Expression': {'SourceRef': {'Source': 'd'}}, 'Property': 'Section'}}
    return {'filters': [{'name': uuid.uuid4().hex[:20], 'field': fld, 'type': 'Categorical', 'filter': {'Version': 2, 'From': [ent], 'Where': [{'Condition': {'In': {'Expressions': [cond], 'Values': [[{'Literal': {'Value': "'" + section + "'"}}]]}}}]}, 'howCreated': 'User'}]}


def make_chart(kind, x, y, w, h, title, category, series, section=None):
    j, d = add(chart, x, y, w, h)
    v = j['visual']
    v['visualType'] = kind
    v['query'] = {'queryState': {'Category': {'projections': [category]}, 'Y': {'projections': series}}}
    v['visualContainerObjects']['title'][0]['properties']['text'] = L("'" + title + "'")
    v['visualContainerObjects']['subTitle'] = [{'properties': {'show': L('false')}}]
    v['objects'] = {'labels': [{'properties': {'show': L('true'), 'fontSize': L('12D'), 'labelPosition': L("'OutsideEnd'")}}],
                    'valueAxis': [{'properties': {'show': L('false')}}],
                    'legend': [{'properties': {'show': L('true'), 'position': L("'Bottom'"), 'fontSize': L('12D')}}]}
    if section:
        j['filterConfig'] = section_filter(section)
    dump(j, d / 'visual.json')


def deneb(x, y, w, h, title, category, series, spec):
    j, d = add(json.load(open(TEMPLATE, encoding='utf-8')), x, y, w, h)
    j['visual']['query'] = {'queryState': {'dataset': {'projections': [category] + series}}}
    j.pop('filterConfig', None)
    lit = lambda t: L("'" + t.replace("'", "''") + "'")
    j['visual']['objects'] = {'vega': [{'properties': {'provider': lit('vegaLite'), 'renderMode': lit('svg'), 'jsonSpec': lit(json.dumps(spec)), 'jsonConfig': lit('{}'), 'isNewDialogOpen': L('false')}}]}
    j['visual']['visualContainerObjects'] = {'title': [{'properties': {'show': L('true'), 'text': L("'" + title + "'")}}]}
    dump(j, d / 'visual.json')


LEVELS = ['Exceeds Expectations', 'Meets Expectations', 'Needs Support']
RATINGS_SPEC = {
    '$schema': 'https://vega.github.io/schema/vega-lite/v5.json',
    'data': {'name': 'dataset'},
    'autosize': {'type': 'fit', 'contains': 'padding'},
    'config': {'view': {'stroke': None}, 'font': 'Segoe UI'},
    'transform': [
        {'fold': ['Group level share', 'RRNC level share', 'Virginia level share'], 'as': ['key', 'share']},
        {'calculate': "datum.key === 'Group level share' ? 'This group' : datum.key === 'RRNC level share' ? 'RRNC' : 'Virginia'", 'as': 'Who'},
        {'calculate': 'indexof(' + json.dumps(LEVELS) + ', datum.Level)', 'as': 'ord'},
        {'window': [{'op': 'sum', 'field': 'share', 'as': 'cum'}], 'groupby': ['Who'], 'sort': [{'field': 'ord'}], 'frame': [None, 0]},
        {'calculate': 'datum.cum - datum.share', 'as': 'start'},
        {'calculate': 'datum.cum - datum.share / 2', 'as': 'mid'}],
    'encoding': {'y': {'field': 'Who', 'type': 'nominal', 'sort': ['This group', 'RRNC', 'Virginia'], 'axis': {'title': None, 'labelFontSize': 13, 'labelColor': '#23323F', 'ticks': False, 'domain': False}}},
    'layer': [
        {'mark': {'type': 'bar', 'height': 38, 'cornerRadius': 3},
         'encoding': {'x': {'field': 'start', 'type': 'quantitative', 'scale': {'domain': [0, 1]}, 'axis': None}, 'x2': {'field': 'cum'},
                      'color': {'field': 'Level', 'type': 'nominal', 'sort': LEVELS, 'scale': {'domain': LEVELS, 'range': ['#6FA82B', '#11689B', '#F7941D']},
                                'legend': {'orient': 'bottom', 'title': None, 'labelFontSize': 12, 'symbolType': 'square'}}}},
        {'transform': [{'filter': 'datum.share >= 0.05'}],
         'mark': {'type': 'text', 'fontSize': 13, 'fontWeight': 'bold', 'color': 'white'},
         'encoding': {'x': {'field': 'mid', 'type': 'quantitative', 'scale': {'domain': [0, 1]}}, 'text': {'field': 'share', 'type': 'quantitative', 'format': '.0%'}}}]}

# title band, dropdowns, as-of line
j, d = add(title_card, 0, 0, 1280, 64); dump(j, d / 'visual.json')
for n, s_ in enumerate(slicers):
    j, d = add(s_, 16 + n * 262, 70, 250, 52)
    j['filterConfig'] = copy.deepcopy(s_.get('filterConfig', {}))
    if not j['filterConfig']: j.pop('filterConfig')
    dump(j, d / 'visual.json')
j, d = add(asof_card, 812, 72, 452, 48); dump(j, d / 'visual.json')
# four number cards
for n, k in enumerate(kpis):
    j, d = add(k, 16 + n * 316, 126, 300, 76); dump(j, d / 'visual.json')

G, R, V = 'This group', 'RRNC', 'Virginia'
W, X = 408, [16, 436, 856]
Y1, Y2, H = 210, 456, 238
j, d = add(chart, X[0], Y1, W, H)
j['visual']['visualContainerObjects']['subTitle'] = [{'properties': {'show': L('false')}}]
dump(j, d / 'visual.json')     # average points by program year (copied from page 1)
deneb(X[1], Y1, W, H, 'Quality ratings: share of sites', col('Rating Levels', 'Level', 'Level'),
      [mea('Group level share', 'Group level share'), mea('RRNC level share', 'RRNC level share'), mea('Virginia level share', 'Virginia level share')], RATINGS_SPEC)
make_chart('clusteredColumnChart', X[2], Y1, W, H, 'Average points by program type',
           col('Sites-Orgs', 'cr720_providertypename', 'Program type'),
           [mea('Average points', G), mea('RRNC average points', R), mea('Virginia average points', V)])
make_chart('clusteredColumnChart', X[0], Y2, W, H, 'Average points by component',
           col('Detail', 'Item', 'Component'),
           [mea('Group detail points', G), mea('RRNC detail points', R), mea('Virginia detail points', V)], 'Points')
make_chart('clusteredColumnChart', X[1], Y2, W, H, 'Honor Roll: share of sites',
           col('Detail', 'Item', 'Honor Roll'),
           [mea('Group detail share', G), mea('RRNC detail share', R), mea('Virginia detail share', V)], 'Honor Roll')
make_chart('clusteredColumnChart', X[2], Y2, W, H, 'Years in VQB5: share of sites',
           col('Detail', 'Item', 'Years in VQB5'),
           [mea('Group detail share', G), mea('RRNC detail share', R)], 'Years in VQB5')

j, d = add(footer, 16, 700, 1248, 20)
j['visual']['objects']['general'][0]['properties']['paragraphs'] = [{'textRuns': [{'value': 'Internal use. Approval is needed before sharing outside Foundation First / RRNC. Source: VDOE VQB5 public data. No Provider 360 data.', 'textStyle': {'fontSize': '10pt', 'color': '#4f5f6b'}}]}]
dump(j, d / 'visual.json')
print('Dashboard built:', P3.name, '-', len(list((P3 / 'visuals').glob('*'))), 'visuals')
