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
NAVY, GREEN, GREY = '#0E3F66', '#6FA82B', '#85888B'
WHO = ['This group', 'RRNC', 'Virginia']
BASE = {'$schema': 'https://vega.github.io/schema/vega-lite/v5.json', 'data': {'name': 'dataset'},
        'autosize': {'type': 'fit', 'contains': 'padding'},
        'config': {'view': {'stroke': None}, 'font': 'Segoe UI', 'axis': {'labelColor': '#23323F', 'labelFontSize': 12}}}


def deneb(x, y, w, h, title, category, series, spec, only=None):
    j, d = add(deneb_tpl, x, y, w, h)
    j['visual']['query'] = {'queryState': {'dataset': {'projections': [category] + series}}}
    lit = lambda t: L("'" + t.replace("'", "''") + "'")
    j['visual']['objects'] = {'vega': [{'properties': {'provider': lit('vegaLite'), 'renderMode': lit('svg'), 'jsonSpec': lit(json.dumps(spec)), 'jsonConfig': lit('{}'), 'isNewDialogOpen': L('false')}}]}
    j['visual']['visualContainerObjects'] = {'title': [{'properties': {'show': L('true'), 'text': L("'" + title + "'")}}]}
    if only:
        j['filterConfig'] = detail_filter(*only)
    dump(j, d / 'visual.json')


def grouped_bars(measure_names, item_field, fmt, items_sort=None, who=WHO):
    """Horizontal grouped bars: one row per item, one bar per group (This group / RRNC / Virginia)."""
    keys = [m for m in measure_names]
    spec = copy.deepcopy(BASE)
    spec['transform'] = [
        {'calculate': "datum['" + item_field + "'] === 'Curriculum points' ? 'VDOE-approved curriculum' : datum['" + item_field + "'] ? datum['" + item_field + "'] : '(Blank)'", 'as': 'Item'},
        {'fold': keys, 'as': ['key', 'value']},
        {'filter': 'isValid(datum.value)'},
        {'calculate': json.dumps(who) + '[indexof(' + json.dumps(keys) + ', datum.key)]', 'as': 'Who'}]
    y = {'field': 'Item', 'type': 'nominal', 'axis': {'title': None, 'ticks': False, 'domain': False, 'labelFontSize': 13, 'labelLimit': 150}, 'scale': {'paddingInner': 0.3}}
    if items_sort:
        y['sort'] = items_sort
    spec['encoding'] = {'y': y}
    spec['layer'] = [
        {'mark': {'type': 'bar', 'cornerRadiusEnd': 3},
         'encoding': {'yOffset': {'field': 'Who', 'type': 'nominal', 'sort': who, 'scale': {'paddingInner': 0.08}},
                      'x': {'field': 'value', 'type': 'quantitative', 'axis': None, 'scale': {'zero': True, 'nice': False}},
                      'color': {'field': 'Who', 'type': 'nominal', 'sort': who, 'scale': {'domain': who, 'range': [NAVY, GREEN, GREY][:len(who)]}, 'legend': None}}},
        {'mark': {'type': 'text', 'align': 'left', 'dx': 4, 'fontSize': 12, 'color': '#23323F'},
         'encoding': {'yOffset': {'field': 'Who', 'type': 'nominal', 'sort': who, 'scale': {'paddingInner': 0.08}},
                      'x': {'field': 'value', 'type': 'quantitative'},
                      'text': {'field': 'value', 'type': 'quantitative', 'format': fmt}}}]
    return spec


LEVELS = ['Exceeds Expectations', 'Meets Expectations', 'Needs Support']
RATINGS_SPEC = copy.deepcopy(BASE)
RATINGS_SPEC.update({
    'transform': [
        {'fold': ['Group level share', 'RRNC level share', 'Virginia level share'], 'as': ['key', 'share']},
        {'calculate': "datum.key === 'Group level share' ? 'This group' : datum.key === 'RRNC level share' ? 'RRNC' : 'Virginia'", 'as': 'Who'},
        {'calculate': 'indexof(' + json.dumps(LEVELS) + ', datum.Level)', 'as': 'ord'},
        {'window': [{'op': 'sum', 'field': 'share', 'as': 'cum'}], 'groupby': ['Who'], 'sort': [{'field': 'ord'}], 'frame': [None, 0]},
        {'calculate': 'datum.cum - datum.share', 'as': 'start'},
        {'calculate': 'datum.cum - datum.share / 2', 'as': 'mid'}],
    'encoding': {'y': {'field': 'Who', 'type': 'nominal', 'sort': WHO, 'axis': {'title': None, 'labelFontSize': 13, 'ticks': False, 'domain': False}}},
    'layer': [
        {'mark': {'type': 'bar', 'height': 34, 'cornerRadius': 3},
         'encoding': {'x': {'field': 'start', 'type': 'quantitative', 'scale': {'domain': [0, 1]}, 'axis': None}, 'x2': {'field': 'cum'},
                      'color': {'field': 'Level', 'type': 'nominal', 'sort': LEVELS, 'scale': {'domain': LEVELS, 'range': ['#11689B', '#9CC3DB', '#F7941D']},
                                'legend': {'orient': 'bottom', 'direction': 'vertical', 'title': None, 'labelFontSize': 12, 'symbolType': 'square'}}}},
        {'transform': [{'filter': 'datum.share >= 0.05'}],
         'mark': {'type': 'text', 'fontSize': 13, 'fontWeight': 'bold'},
         'encoding': {'x': {'field': 'mid', 'type': 'quantitative', 'scale': {'domain': [0, 1]}}, 'text': {'field': 'share', 'type': 'quantitative', 'format': '.0%'},
                      'color': {'condition': {'test': "datum.Level === 'Meets Expectations'", 'value': '#23323F'}, 'value': 'white'}}}]})

# ---- layout: Letter portrait, 816 x 1056
j, d = add(title_card, 0, 0, 816, 64); dump(j, d / 'visual.json')
j, d = add(asof_box, 20, 70, 776, 46); dump(j, d / 'visual.json')
for n, k in enumerate(kpis):
    j, d = add(k, 20 + n * 196, 122, 184, 78); dump(j, d / 'visual.json')

W, X = 384, [20, 412]
YS, H = [210, 444, 678], 226
j, d = add(chart, X[0], YS[0], W, H)
j['visual']['visualContainerObjects']['subTitle'] = [{'properties': {'show': L('false')}}]
dump(j, d / 'visual.json')

deneb(X[1], YS[0], W, H, 'Quality ratings: share of sites', col('Rating Levels', 'Level'),
      [mea('Group level share'), mea('RRNC level share'), mea('Virginia level share')], RATINGS_SPEC)
deneb(X[0], YS[1], W, H, 'Average points by program type', col('Sites-Orgs', 'cr720_providertypename'),
      [mea('Average points'), mea('RRNC average points'), mea('Virginia average points')],
      grouped_bars(['Average points', 'RRNC average points', 'Virginia average points'], 'cr720_providertypename', 'd'))
deneb(X[1], YS[1], W, H, 'Honor Roll: share of sites', col('Detail', 'Item'),
      [mea('Group detail share'), mea('RRNC detail share'), mea('Virginia detail share')],
      grouped_bars(['Group detail share', 'RRNC detail share', 'Virginia detail share'], 'Item', '.0%', ['Excellence', 'Improvement', 'Infant/Toddler']), ('Section', ['Honor Roll']))
deneb(X[0], YS[2], W, H, 'Average points: interaction and total', col('Detail', 'Item'),
      [mea('Group detail points'), mea('RRNC detail points'), mea('Virginia detail points')],
      grouped_bars(['Group detail points', 'RRNC detail points', 'Virginia detail points'], 'Item', 'd', ['Interaction points', 'Total points']), ('Item', ['Interaction points', 'Total points']))
deneb(X[1], YS[2], W, H, 'Years in VQB5: share of sites', col('Detail', 'Item'),
      [mea('Group detail share'), mea('RRNC detail share')],
      grouped_bars(['Group detail share', 'RRNC detail share'], 'Item', '.0%', ['First year', 'Second year', 'Third year or more'], WHO[:2]), ('Section', ['Years in VQB5']))
deneb(20, 912, 776, 100, 'Sites using a VDOE-approved curriculum', col('Detail', 'Item'),
      [mea('Group detail share'), mea('RRNC detail share'), mea('Virginia detail share')],
      grouped_bars(['Group detail share', 'RRNC detail share', 'Virginia detail share'], 'Item', '.0%'), ('Item', ['Curriculum points']))

j, d = add(footer, 20, 1016, 776, 36)
j['visual']['objects']['general'][0]['properties']['paragraphs'] = [{'textRuns': [{'value': 'Internal use. Approval is needed before sharing outside Foundation First / RRNC. Source: VDOE VQB5 Quality Rating Data (public); Virginia figures from VDOE statewide files. Scores run from 100 to 800. No Provider 360 or other internal data is included.', 'textStyle': {'fontSize': '10pt', 'color': '#4f5f6b'}}]}]
dump(j, d / 'visual.json')
print('Dashboard built:', P3.name, '-', len(list((P3 / 'visuals').glob('*'))), 'visuals')
