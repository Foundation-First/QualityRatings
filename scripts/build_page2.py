"""Build page 2 ("Deeper dive") of the Power BI one-pager by cloning the visuals Desktop wrote for page 1.

Run with Power BI Desktop closed:  python scripts/build_page2.py internal/powerbi-work
Needs page 1 to exist with: the title card, three slicers, a table and a footer text box (see finish_pbi_report.py),
and the Detail table plus the Detail measures (build_powerbi.py --measures-only).
Re-running rebuilds page 2 from scratch.
"""
import copy, json, shutil, sys, uuid
from pathlib import Path

PROJECT = Path(sys.argv[1] if len(sys.argv) > 1 else 'internal/powerbi-work')
RP = next(PROJECT.glob('*.Report')) / 'definition'
pages_json = RP / 'pages' / 'pages.json'
order = json.load(open(pages_json, encoding='utf-8-sig'))
P1 = RP / 'pages' / order['pageOrder'][0]
load = lambda p: json.load(open(p, encoding='utf-8-sig'))
dump = lambda j, p: p.write_text(json.dumps(j, indent=2), encoding='utf-8')

# --- page 2 folder (reuse the second page if it already exists)
if len(order['pageOrder']) > 1:
    P2 = RP / 'pages' / order['pageOrder'][1]
    shutil.rmtree(P2 / 'visuals', ignore_errors=True)
else:
    pid = uuid.uuid4().hex[:20]
    P2 = RP / 'pages' / pid
    P2.mkdir()
    order['pageOrder'].append(pid)
    dump(order, pages_json)
pg = load(P1 / 'page.json')
pg.update(name=P2.name, displayName='Deeper dive')
dump(pg, P2 / 'page.json')
(P2 / 'visuals').mkdir()

src = {}
for f in (P1 / 'visuals').glob('*/visual.json'):
    j = load(f)
    src.setdefault(j['visual']['visualType'], []).append(j)
fields = lambda j: [p['queryRef'] for d in (j['visual'].get('query', {}).get('queryState', {}) or {}).values() for p in d.get('projections', [])]
title_card = next(j for j in src['cardVisual'] if any('Report title' in r for r in fields(j)))
slicers = sorted(src['slicer'], key=lambda j: j['position']['x'])
table = src['tableEx'][0]
footer = src['textbox'][0]
L = lambda v: {'expr': {'Literal': {'Value': v}}}


def col(ent, prop, name): return {'field': {'Column': {'Expression': {'SourceRef': {'Entity': ent}}, 'Property': prop}}, 'queryRef': ent + '.' + prop, 'nativeQueryRef': prop, 'displayName': name}
def mea(prop, name): return {'field': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Published Scores'}}, 'Property': prop}}, 'queryRef': 'Published Scores.' + prop, 'nativeQueryRef': prop, 'displayName': name}


z = [0]


def add(template, x, y, w, h):
    j = copy.deepcopy(template)
    j['name'] = uuid.uuid4().hex[:20]
    j.pop('filterConfig', None) if template['visual']['visualType'] != 'slicer' else None
    j['position'].update(x=x, y=y, width=w, height=h, z=z[0], tabOrder=z[0])
    z[0] += 1
    d = P2 / 'visuals' / j['name']
    d.mkdir()
    return j, d


def save(j, d): dump(j, d / 'visual.json')


def titled(j, text):
    j['visual'].setdefault('visualContainerObjects', {})['title'] = [{'properties': {'show': L('true'), 'text': L("'" + text + "'")}}]


# title band and the three dropdowns (same fields as page 1)
j, d = add(title_card, 0, 0, 816, 76); save(j, d)
for n, s in enumerate(slicers):
    j, d = add(s, 20 + n * 262, 86, 250, 60)
    j['filterConfig'] = copy.deepcopy(s.get('filterConfig', {})) or j.get('filterConfig')
    if not j['filterConfig']: j.pop('filterConfig')
    save(j, d)


def section_filter(section):
    ent = {'Name': 'd', 'Entity': 'Detail', 'Type': 0}
    fld = {'Column': {'Expression': {'SourceRef': {'Entity': 'Detail'}}, 'Property': 'Section'}}
    cond = {'Column': {'Expression': {'SourceRef': {'Source': 'd'}}, 'Property': 'Section'}}
    return {'filters': [{'name': uuid.uuid4().hex[:20], 'field': fld, 'type': 'Categorical', 'filter': {'Version': 2, 'From': [ent], 'Where': [{'Condition': {'In': {'Expressions': [cond], 'Values': [[{'Literal': {'Value': "'" + section + "'"}}]]}}}]}, 'howCreated': 'User'}]}


def detail_table(y, h, label, text, section):
    j, d = add(table, 20, y, 776, h)
    j['filterConfig'] = section_filter(section)
    j['visual']['query'] = {'queryState': {'Values': {'projections': [col('Detail', 'Item', label), mea('Detail group', 'This group'), mea('Detail RRNC', 'RRNC'), mea('Detail Virginia', 'Virginia')]}}}
    titled(j, text)
    save(j, d)


detail_table(160, 150, 'Points (average)', 'Points breakdown, latest program year', 'Points')
detail_table(322, 150, 'Honor Roll', 'Honor Roll: sites (share)', 'Honor Roll')

# by program type
j, d = add(table, 20, 484, 776, 214)
j['visual']['query'] = {'queryState': {'Values': {'projections': [col('Sites-Orgs', 'cr720_providertypename', 'Program type'), mea('Sites rated', 'Sites'), mea('Average points', 'This group, average points'), mea('RRNC average points', 'RRNC'), mea('Virginia average points', 'Virginia')]}}}
titled(j, 'By program type, latest program year')
save(j, d)

detail_table(710, 150, 'Years in VQB5', 'Years in VQB5: sites and average points', 'Years in VQB5')

j, d = add(footer, 20, 872, 776, 40)
save(j, d)
print('Page 2 built:', P2.name, '-', len(list((P2 / 'visuals').glob('*'))), 'visuals')
