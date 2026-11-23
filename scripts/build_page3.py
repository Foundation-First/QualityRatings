"""Build page 3 ("Charts") of the Power BI one-pager: native column/bar charts, same fields as pages 1-2.

Run with Power BI Desktop closed:  python scripts/build_page3.py internal/powerbi-work
Needs pages 1 and 2 (build_page2.py) and the numeric measures (build_powerbi.py --measures-only).
Re-running rebuilds page 3 from scratch.
"""
import copy, json, shutil, sys, uuid
from pathlib import Path

PROJECT = Path(sys.argv[1] if len(sys.argv) > 1 else 'internal/powerbi-work')
RP = next(PROJECT.glob('*.Report')) / 'definition'
pages_json = RP / 'pages' / 'pages.json'
load = lambda p: json.load(open(p, encoding='utf-8-sig'))
dump = lambda j, p: p.write_text(json.dumps(j, indent=2), encoding='utf-8')
order = load(pages_json)
P1 = RP / 'pages' / order['pageOrder'][0]

if len(order['pageOrder']) > 2:
    P3 = RP / 'pages' / order['pageOrder'][2]
    shutil.rmtree(P3 / 'visuals', ignore_errors=True)
else:
    pid = uuid.uuid4().hex[:20]
    P3 = RP / 'pages' / pid
    P3.mkdir()
    order['pageOrder'].append(pid)
    dump(order, pages_json)
pg = load(P1 / 'page.json')
pg.update(name=P3.name, displayName='Charts')
dump(pg, P3 / 'page.json')
(P3 / 'visuals').mkdir()

src = {}
for f in (P1 / 'visuals').glob('*/visual.json'):
    j = load(f)
    src.setdefault(j['visual']['visualType'], []).append(j)
fields = lambda j: [p['queryRef'] for d in (j['visual'].get('query', {}).get('queryState', {}) or {}).values() for p in d.get('projections', [])]
title_card = next(j for j in src['cardVisual'] if any('Report title' in r for r in fields(j)))
slicers = sorted(src['slicer'], key=lambda j: j['position']['x'])
chart = src['lineChart'][0]
footer = src['textbox'][0]
L = lambda v: {'expr': {'Literal': {'Value': v}}}


def col(ent, prop, name): return {'field': {'Column': {'Expression': {'SourceRef': {'Entity': ent}}, 'Property': prop}}, 'queryRef': ent + '.' + prop, 'nativeQueryRef': prop, 'active': True, 'displayName': name}
def mea(prop, name): return {'field': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Published Scores'}}, 'Property': prop}}, 'queryRef': 'Published Scores.' + prop, 'nativeQueryRef': prop, 'displayName': name}


z = [0]


def add(template, x, y, w, h):
    j = copy.deepcopy(template)
    j['name'] = uuid.uuid4().hex[:20]
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
    v['objects'] = {'labels': [{'properties': {'show': L('true'), 'fontSize': L('12D')}}],
                    'legend': [{'properties': {'show': L('true'), 'position': L("'Bottom'"), 'fontSize': L('12D')}}]}
    if section:
        j['filterConfig'] = section_filter(section)
    dump(j, d / 'visual.json')


# title band and the three dropdowns (same fields as page 1)
j, d = add(title_card, 0, 0, 816, 76); dump(j, d / 'visual.json')
for n, s in enumerate(slicers):
    j, d = add(s, 20 + n * 262, 86, 250, 60)
    j['filterConfig'] = copy.deepcopy(s.get('filterConfig', {}))
    if not j['filterConfig']: j.pop('filterConfig')
    dump(j, d / 'visual.json')

G, R, V = 'This group', 'RRNC', 'Virginia'
make_chart('clusteredColumnChart', 20, 160, 380, 270, 'Quality ratings, latest year: share of sites',
           col('Rating Levels', 'Level', 'Quality rating'),
           [mea('Group level share', G), mea('RRNC level share', R), mea('Virginia level share', V)])
make_chart('clusteredBarChart', 416, 160, 380, 270, 'Average points by program type',
           col('Sites-Orgs', 'cr720_providertypename', 'Program type'),
           [mea('Average points', G), mea('RRNC average points', R), mea('Virginia average points', V)])
make_chart('clusteredColumnChart', 20, 442, 380, 270, 'Average points by component',
           col('Detail', 'Item', 'Component'),
           [mea('Group detail points', G), mea('RRNC detail points', R), mea('Virginia detail points', V)], 'Points')
make_chart('clusteredColumnChart', 416, 442, 380, 270, 'Honor Roll: share of sites',
           col('Detail', 'Item', 'Honor Roll'),
           [mea('Group detail share', G), mea('RRNC detail share', R), mea('Virginia detail share', V)], 'Honor Roll')
make_chart('clusteredColumnChart', 20, 724, 776, 240, 'Years in VQB5: share of sites',
           col('Detail', 'Item', 'Years in VQB5'),
           [mea('Group detail share', G), mea('RRNC detail share', R)], 'Years in VQB5')

j, d = add(footer, 20, 976, 776, 40)
dump(j, d / 'visual.json')
print('Page 3 built:', P3.name, '-', len(list((P3 / 'visuals').glob('*'))), 'visuals')
