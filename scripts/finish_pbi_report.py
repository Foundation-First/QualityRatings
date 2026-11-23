"""Fill in the one-pager visuals that were created in Power BI Desktop (internal use).

Edits the visual.json files Desktop wrote, so the format is exactly Desktop's own:
  - positions every visual on the Letter page
  - adds fields to the empty ratings table, matrix and line chart
  - adds the four number cards (copied from the title card)
  - writes the footer text
Run with Power BI Desktop closed:  python scripts/finish_pbi_report.py "internal/powerbi-work"
A copy of the visuals folder is saved first as visuals-backup next to the project.
"""
import copy, json, shutil, sys, uuid
from pathlib import Path

PROJECT = Path(sys.argv[1] if len(sys.argv) > 1 else 'internal/powerbi-work')
RP = next(PROJECT.glob('*.Report')) / 'definition'
PAGE = RP / 'pages' / json.load(open(RP / 'pages' / 'pages.json', encoding='utf-8-sig'))['pageOrder'][0]
VIS = PAGE / 'visuals'
shutil.copytree(VIS, PROJECT / 'visuals-backup', dirs_exist_ok=True)

PS, SO, PY, RL = 'Published Scores', 'Sites-Orgs', 'Program Year', 'Rating Levels'
load = lambda p: json.load(open(p, encoding='utf-8-sig'))
vis = {}
for f in VIS.glob('*/visual.json'):
    j = load(f)
    vis[j['visual']['visualType'] + ':' + f.parent.name] = (f, j)


def pick(vtype, predicate=lambda j: True):
    return [(f, j) for k, (f, j) in vis.items() if k.startswith(vtype + ':') and predicate(j)]


def fields_of(j):
    return [p['queryRef'] for d in (j['visual'].get('query', {}).get('queryState', {}) or {}).values() for p in d.get('projections', [])]


def col(ent, prop): return {'field': {'Column': {'Expression': {'SourceRef': {'Entity': ent}}, 'Property': prop}}, 'queryRef': ent + '.' + prop, 'nativeQueryRef': prop}
def mea(prop, ent=PS): return {'field': {'Measure': {'Expression': {'SourceRef': {'Entity': ent}}, 'Property': prop}}, 'queryRef': ent + '.' + prop, 'nativeQueryRef': prop}


def named(pr, name):
    pr['displayName'] = name
    return pr


def titled(j, text):
    L = lambda v: {'expr': {'Literal': {'Value': v}}}
    j['visual'].setdefault('visualContainerObjects', {})['title'] = [{'properties': {'show': L('true'), 'text': L("'" + text + "'")}}]


def place(j, x, y, w, h, z=None):
    return _place(j, x, y, w, h, z)


def _place(j, x, y, w, h, z=None):
    p = j['position']
    p.update(x=x, y=y, width=w, height=h)
    if z is not None: p.update(z=z, tabOrder=z)


def has(j, ref): return any(ref in r for r in fields_of(j))


# --- existing visuals, found by their fields
title = next(j for _, j in (pick('cardVisual', lambda j: has(j, 'Report title'))))
asof = next(j for _, j in (pick('cardVisual', lambda j: has(j, 'As of'))))
place(title, 0, 0, 816, 76, 0)
for n, (_, j) in enumerate(sorted(pick('slicer'), key=lambda t: t[1]['position']['x'])):
    place(j, 20 + n * 262, 86, 250, 60, 1 + n)
place(asof, 20, 150, 776, 30, 4)

# --- four number cards, copied from the title card
for n, (prop, label) in enumerate([('Sites rated', 'Sites rated'), ('Average points', 'Average points'), ('Gap vs RRNC', 'Points vs. RRNC'), ('Gap vs Virginia', 'Points vs. Virginia')]):
    if any(has(j, 'Published Scores.' + prop) for _, j in pick('cardVisual')): continue
    c = copy.deepcopy(title)
    name = uuid.uuid4().hex[:20]
    c['name'] = name
    c.pop('filterConfig', None)
    c['visual']['query']['queryState']['Data']['projections'] = [mea(prop)]
    o = c['visual']['objects']
    o['label'] = [{'properties': {'show': {'expr': {'Literal': {'Value': 'true'}}}}, 'selector': {'id': 'default'}}]
    o['value'][0]['properties']['fontSize'] = {'expr': {'Literal': {'Value': '30D'}}}
    o['value'][0]['properties']['fontColor'] = {'solid': {'color': {'expr': {'Literal': {'Value': "'#0E3F66'"}}}}}
    c['visual']['visualContainerObjects']['background'][0]['properties']['color']['solid']['color']['expr']['Literal']['Value'] = "'#FFFFFF'"
    place(c, 20 + n * 196, 190, 184, 84, 5 + n)
    d = VIS / name
    d.mkdir()
    json.dump(c, open(d / 'visual.json', 'w', encoding='utf-8'), indent=2)

# --- ratings table
_, t = pick('tableEx')[0]
t['visual']['query'] = {'queryState': {'Values': {'projections': [named(col(RL, 'Level'), 'Quality rating'), named(mea('Group rating level'), 'This group'), named(mea('RRNC rating level'), 'RRNC'), named(mea('Virginia rating level'), 'Virginia')]}}}
titled(t, 'Ratings in the latest program year: sites (share)')
place(t, 20, 286, 776, 176, 9)
# --- line chart
_, l = pick('lineChart')[0]
l['visual']['query'] = {'queryState': {'Category': {'projections': [named(col(PY, 'cr720_name'), 'Program year')]},
                                       'Y': {'projections': [named(mea('Group average by year'), 'This group'), named(mea('RRNC average by year'), 'RRNC'), named(mea('Virginia average by year'), 'Virginia')]}}}
titled(l, 'Average total points by program year')
place(l, 20, 474, 776, 450, 10)
# --- no site-by-site matrix: sites are a filter only, never a list that compares them
for f, j in pick('pivotTable'):
    shutil.rmtree(f.parent)
    vis.pop('pivotTable:' + f.parent.name)

# --- footer
_, tb = pick('textbox')[0]
tb['visual']['objects']['general'][0]['properties']['paragraphs'] = [{'textRuns': [{'value': 'Internal use. Approval is needed before sharing outside Foundation First / RRNC. Source: VDOE VQB5 Quality Rating Data (public); Virginia figures from VDOE statewide files. Scores run from 100 to 800. No Provider 360 or other internal data is included.', 'textStyle': {'fontSize': '10pt', 'color': '#4f5f6b'}}]}]
place(tb, 20, 940, 776, 40, 12)

for f, j in vis.values():
    json.dump(j, open(f, 'w', encoding='utf-8'), indent=2)
print('Updated', len(vis), 'existing visuals; cards present:', len(pick('cardVisual')) + 0)
