"""Add the one-pager pieces to the Power BI project in internal/powerbi/ (never published).

Writes, idempotently:
  - tables/Virginia.tmdl        Virginia averages and rating counts by year and program type (from site/data/summary.json)
  - tables/Rating Levels.tmdl   the three rating levels, in order
  - measures on 'Published Scores' (current year, RRNC, Virginia, ratings text, title, as-of)
  - ref table lines in model.tmdl
  - the one-page report layout (Letter portrait) on the report's first page

Run it with Power BI Desktop closed, then open "Quality Ratings.pbip".
Re-run after build_data.py when new years are published, to refresh the Virginia numbers.
"""
import json, re, sys, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = int(next((a.split('=')[1] for a in sys.argv if a.startswith('--stage=')), 3))   # 0 = remove everything added; 1 = + tables; 2 = + measures; 3 = + report page (default canvas size); 4 = + Letter-size page
KEEP_TABLES = '--keep-tables' in sys.argv   # tables were added in Desktop; do not write or remove them
PBI = Path(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--project=')), ROOT / 'internal' / 'powerbi'))   # folder that holds the .pbip
SM = next(PBI.glob('*.SemanticModel')) / 'definition'
RP = next(PBI.glob('*.Report')) / 'definition'
T = '\t'
guid = lambda s: str(uuid.uuid5(uuid.NAMESPACE_URL, 'ff-vqb5/' + s))

# ---------------------------------------------------------------- Virginia benchmark table
S = json.load(open(ROOT / 'site' / 'data' / 'summary.json', encoding='utf-8'))
rows = []
for y, d in sorted(S['statewide'].items()):
    sy = int(y[:4])
    groups = [('All', d)] + [(t, d['byType'][t]) for t in ('Center', 'Public School', 'Family Day Home')]
    for t, g in groups:
        b = g['bins']
        rows.append((sy, t, g['n'], round(g['avg'], 1), b[0], b[1] + b[2] + b[3], b[4]))
data = ', '.join('{%d, "%s", %d, %s, %d, %d, %d}' % r for r in rows)
cols = [('StartYear', 'int64', '0'), ('Type', 'string', None), ('Sites', 'int64', '0'), ('AvgPoints', 'double', None),
        ('Needs', 'int64', '0'), ('Meets', 'int64', '0'), ('Exceeds', 'int64', '0')]
out = ['table Virginia', T + 'lineageTag: ' + guid('Virginia'), '']
for c, dt, fmt in cols:
    out += [T + 'column ' + c, T * 2 + 'dataType: ' + dt]
    if fmt: out.append(T * 2 + 'formatString: ' + fmt)
    out += [T * 2 + 'lineageTag: ' + guid('Virginia.' + c), T * 2 + 'summarizeBy: none', T * 2 + 'sourceColumn: ' + c, '']
out += [T + 'partition Virginia = m', T * 2 + 'mode: import', T * 2 + 'source =', T * 4 + 'let',
        T * 4 + '  Source = #table(type table [StartYear = Int64.Type, Type = text, Sites = Int64.Type, AvgPoints = number, Needs = Int64.Type, Meets = Int64.Type, Exceeds = Int64.Type], {' + ('{' + data + '}' if False else data) + '})',
        T * 4 + 'in', T * 4 + '  Source', '']
if not KEEP_TABLES:
    (SM / 'tables' / 'Virginia.tmdl').write_text('\n'.join(out), encoding='utf-8')
    if STAGE < 1:
        (SM / 'tables' / 'Virginia.tmdl').unlink()

# ---------------------------------------------------------------- rating levels
lv = ['table \'Rating Levels\'', T + 'lineageTag: ' + guid('Levels'), '',
      T + 'column Level', T * 2 + 'dataType: string', T * 2 + 'lineageTag: ' + guid('Levels.Level'), T * 2 + 'summarizeBy: none', T * 2 + 'sourceColumn: [Level]', T * 2 + 'sortByColumn: Order', '',
      T + 'column Order', T * 2 + 'dataType: int64', T * 2 + 'formatString: 0', T * 2 + 'lineageTag: ' + guid('Levels.Order'), T * 2 + 'summarizeBy: none', T * 2 + 'sourceColumn: [Order]', '',
      T + "partition 'Rating Levels' = calculated", T * 2 + 'mode: import',
      T * 2 + 'source = DATATABLE("Level", STRING, "Order", INTEGER, {{"Exceeds Expectations", 1}, {"Meets Expectations", 2}, {"Needs Support", 3}})', '']
if not KEEP_TABLES:
    (SM / 'tables' / 'Rating Levels.tmdl').write_text('\n'.join(lv), encoding='utf-8')
    if STAGE < 1:
        (SM / 'tables' / 'Rating Levels.tmdl').unlink()

# ---------------------------------------------------------------- model refs
if not KEEP_TABLES:
    mp = SM / 'model.tmdl'
    m = mp.read_text(encoding='utf-8')
    for t in ('Virginia', "'Rating Levels'"):
        m = m.replace('ref table ' + t + '\n', '').rstrip('\n') + '\n'
        if STAGE >= 1:
            m += 'ref table ' + t + '\n'
    mp.write_text(m, encoding='utf-8')

# ---------------------------------------------------------------- measures
PS, SO, PY = "'Published Scores'", "'Sites-Orgs'", "'Program Year'"
MEAS = [
 ('Latest Year', None, f"""MAXX(FILTER(ALL({PY}), CALCULATE(COUNTROWS({PS}), REMOVEFILTERS({PS})) > 0), {PY}[cr720_name])"""),
 ('Sites rated', '0', f"""VAR ly = [Latest Year]
RETURN CALCULATE(DISTINCTCOUNT({PS}[cr720_vacsiteid]), {PY}[cr720_name] = ly)"""),
 ('Average points', '0', f"""VAR ly = [Latest Year]
RETURN CALCULATE(AVERAGE({PS}[cr720_totalpoints]), {PY}[cr720_name] = ly)"""),
 ('RRNC average points', '0', f"""VAR ly = [Latest Year]
RETURN CALCULATE(AVERAGE({PS}[cr720_totalpoints]), REMOVEFILTERS({PS}), {PY}[cr720_name] = ly)"""),
 ('Virginia type', None, f"""VAR t = SELECTEDVALUE({SO}[cr720_providertypename])
RETURN IF(ISBLANK(t), "All", SWITCH(TRUE(),
    CONTAINSSTRING(t, "Public"), "Public School",
    CONTAINSSTRING(t, "Home") || CONTAINSSTRING(t, "Family"), "Family Day Home",
    CONTAINSSTRING(t, "Center"), "Center", "All"))"""),
 ('Virginia average points', '0', """VAR yr = MAX(Virginia[StartYear])
VAR vt = [Virginia type]
RETURN CALCULATE(MAX(Virginia[AvgPoints]), Virginia[StartYear] = yr, Virginia[Type] = vt)"""),
 ('Gap vs RRNC', '+0;-0;0', """[Average points] - [RRNC average points]"""),
 ('Gap vs Virginia', '+0;-0;0', """[Average points] - [Virginia average points]"""),
 ('Group average by year', '0', f"""AVERAGE({PS}[cr720_totalpoints])"""),
 ('RRNC average by year', '0', f"""CALCULATE(AVERAGE({PS}[cr720_totalpoints]), REMOVEFILTERS({PS}))"""),
 ('Virginia average by year', '0', """VAR sy = VALUE(LEFT(SELECTEDVALUE('Program Year'[cr720_name]), 4))
VAR vt = [Virginia type]
RETURN CALCULATE(MAX(Virginia[AvgPoints]), Virginia[StartYear] = sy, Virginia[Type] = vt)"""),
 ('Total points', '0', f"""MAX({PS}[cr720_totalpoints])"""),
 ('Group rating level', None, f"""VAR lvl = SELECTEDVALUE('Rating Levels'[Level])
VAR ly = [Latest Year]
VAR n = COALESCE(CALCULATE(DISTINCTCOUNT({PS}[cr720_vacsiteid]), {PY}[cr720_name] = ly, {PS}[cr720_qualityrating] = lvl), 0)
RETURN n & " (" & FORMAT(DIVIDE(n, [Sites rated], 0), "0%") & ")\""""),
 ('RRNC rating level', None, f"""VAR lvl = SELECTEDVALUE('Rating Levels'[Level])
VAR ly = [Latest Year]
VAR tot = CALCULATE(DISTINCTCOUNT({PS}[cr720_vacsiteid]), REMOVEFILTERS({PS}), {PY}[cr720_name] = ly)
VAR n = COALESCE(CALCULATE(DISTINCTCOUNT({PS}[cr720_vacsiteid]), REMOVEFILTERS({PS}), {PY}[cr720_name] = ly, {PS}[cr720_qualityrating] = lvl), 0)
RETURN n & " (" & FORMAT(DIVIDE(n, tot, 0), "0%") & ")\""""),
 ('Virginia rating level', None, """VAR lvl = SELECTEDVALUE('Rating Levels'[Level])
VAR yr = MAX(Virginia[StartYear])
VAR vt = [Virginia type]
VAR tot = CALCULATE(MAX(Virginia[Sites]), Virginia[StartYear] = yr, Virginia[Type] = vt)
VAR n = SWITCH(lvl,
    "Needs Support", CALCULATE(MAX(Virginia[Needs]), Virginia[StartYear] = yr, Virginia[Type] = vt),
    "Meets Expectations", CALCULATE(MAX(Virginia[Meets]), Virginia[StartYear] = yr, Virginia[Type] = vt),
    "Exceeds Expectations", CALCULATE(MAX(Virginia[Exceeds]), Virginia[StartYear] = yr, Virginia[Type] = vt))
RETURN n & " (" & FORMAT(DIVIDE(n, tot, 0), "0%") & ")\""""),
 ('Report title', None, f"""IF(ISFILTERED({PS}[cr720_sitename]), SELECTEDVALUE({PS}[cr720_sitename], "Selected sites"),
    IF(ISFILTERED({PS}[cr720_county]), SELECTEDVALUE({PS}[cr720_county], "Selected localities"), "Ready Region North Central"))
    & IF(SELECTEDVALUE({SO}[cr720_providertypename]) <> BLANK(), " - " & SELECTEDVALUE({SO}[cr720_providertypename]), "")"""),
 ('As of', None, f"""\"Data as of \" & FORMAT(CALCULATE(MAX({PS}[modifiedon]), REMOVEFILTERS()), "mmmm d, yyyy") & ". Prepared " & FORMAT(TODAY(), "mmmm d, yyyy") & ".\""""),
]
blk = []
for name, fmt, dax in MEAS:
    blk.append(f"{T}measure '{name}' =")
    blk += [T * 3 + ln for ln in dax.split('\n')]
    if fmt: blk.append(f"{T*2}formatString: {fmt}")
    blk += [f"{T*2}lineageTag: {guid('m.' + name)}", '']
pp = SM / 'tables' / 'Published Scores.tmdl'
t = pp.read_text(encoding='utf-8')
t = re.sub(r"(?m)^\tmeasure '(?:" + '|'.join(re.escape(n) for n in [m[0] for m in MEAS] + ['Latest Start']) + r")' =.*\n(?:(?:\t\t.*)?\n)*", '', t)   # remove only our own measure blocks
i = t.index("\n\tpartition 'Published Scores'")
t = t[:i].rstrip('\n') + '\n\n' + ('\n'.join(blk) if STAGE >= 2 else '') + t[i:]
pp.write_text(t, encoding='utf-8')
if '--measures-only' in sys.argv:
    print('Measures updated in', pp)
    raise SystemExit

# ---------------------------------------------------------------- report page
NAVY, GREEN, INK = '#0E3F66', '#6FA82B', '#23323f'
PLAIN = '--plain' in sys.argv     # python scripts/build_powerbi.py --plain  (data bindings only; use to isolate a load error)
PAGE = json.load(open(RP / 'pages' / 'pages.json', encoding='utf-8-sig'))['pageOrder'][0]   # the report's first page
SCHEMA = 'https://developer.microsoft.com/json-schema/fabric/item/report/definition/'
L = lambda v: {'expr': {'Literal': {'Value': v}}}
Q = lambda s: L("'" + s + "'")
col = lambda e, p: {'Column': {'Expression': {'SourceRef': {'Entity': e}}, 'Property': p}}
mea = lambda e, p: {'Measure': {'Expression': {'SourceRef': {'Entity': e}}, 'Property': p}}
proj = (lambda f, e, p, active=None: dict(field=f, queryRef=e + '.' + p, nativeQueryRef=p, **({'active': True} if active else {})))
C = lambda e, p: proj(col(e, p), e, p)
M = lambda p: proj(mea(PS.strip("'"), p), PS.strip("'"), p)
solid = lambda c: {'solid': {'color': L("'" + c + "'")}}
vis_dir = RP / 'pages' / PAGE / 'visuals'


def container(name, x, y, w, h, visual, container_objects=None):
    v = {'$schema': SCHEMA + 'visualContainer/2.0.0/schema.json', 'name': name,
         'position': {'x': x, 'y': y, 'z': 0, 'height': h, 'width': w, 'tabOrder': len(list(vis_dir.glob('*')))},
         'visual': visual}
    if PLAIN and visual['visualType'] != 'textbox':      # --plain: no formatting at all, only data bindings
        visual.pop('objects', None)
        container_objects = None
    if container_objects: v['visual']['visualContainerObjects'] = container_objects
    if PLAIN and visual['visualType'] == 'slicer': visual['objects'] = {'data': [{'properties': {'mode': Q('Dropdown')}}]}
    d = vis_dir / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'visual.json').write_text(json.dumps(v, indent=2), encoding='utf-8')


def title(text, size=12):
    return {'title': [{'properties': {'show': L('true'), 'text': Q(text), 'fontSize': L('%dD' % size), 'fontColor': solid(NAVY), 'bold': L('true')}}]}


def background(c):
    return {'background': [{'properties': {'show': L('true'), 'color': solid(c), 'transparency': L('0D')}}]}


import shutil
if vis_dir.exists():
    shutil.rmtree(vis_dir)
vis_dir.mkdir(parents=True)

if STAGE >= 4:     # Letter-size page; earlier stages leave the page exactly as Desktop saved it
    pj = RP / 'pages' / PAGE / 'page.json'
    pg = json.load(open(pj, encoding='utf-8-sig'))
    pg.update(displayName='One-pager', displayOption='FitToPage', height=1056, width=816)
    pj.write_text(json.dumps(pg, indent=2), encoding='utf-8')

if STAGE < 3:
    shutil.rmtree(vis_dir)
    print('Stage', STAGE, 'built; report page left blank.')
    raise SystemExit
# title band
container('title', 0, 0, 816, 70, {'visualType': 'card', 'query': {'queryState': {'Values': {'projections': [M('Report title')]}}},
    'objects': {'labels': [{'properties': {'fontSize': L('26D'), 'bold': L('true'), 'color': solid('#FFFFFF')}}], 'categoryLabels': [{'properties': {'show': L('false')}}]},
    'drillFilterOtherVisuals': True}, background(NAVY))
# slicers: place (county/city), site type, site
for nm, x, w, e, p, tt in [('s_place', 20, 250, PS.strip("'"), 'cr720_county', 'County or city'), ('s_type', 285, 220, SO.strip("'"), 'cr720_providertypename', 'Program type'), ('s_site', 520, 276, PS.strip("'"), 'cr720_sitename', 'Site (optional)')]:
    container(nm, x, 82, w, 62, {'visualType': 'slicer', 'query': {'queryState': {'Values': {'projections': [C(e, p)]}}},
        'objects': {'data': [{'properties': {'mode': Q('Dropdown')}}]}, 'drillFilterOtherVisuals': True}, title(tt))
# as-of
container('asof', 20, 152, 776, 28, {'visualType': 'card', 'query': {'queryState': {'Values': {'projections': [M('As of')]}}},
    'objects': {'labels': [{'properties': {'fontSize': L('12D'), 'color': solid('#4f5f6b')}}], 'categoryLabels': [{'properties': {'show': L('false')}}]}, 'drillFilterOtherVisuals': True})
# KPI cards
for i, (nm, label) in enumerate([('Sites rated', 'Sites rated'), ('Average points', 'Average points'), ('Gap vs RRNC', 'Points vs. RRNC'), ('Gap vs Virginia', 'Points vs. Virginia')]):
    container('k%d' % i, 20 + i * 196, 188, 184, 84, {'visualType': 'card', 'query': {'queryState': {'Values': {'projections': [M(nm)]}}},
        'objects': {'labels': [{'properties': {'fontSize': L('30D'), 'bold': L('true'), 'color': solid(NAVY)}}], 'categoryLabels': [{'properties': {'fontSize': L('12D'), 'color': solid('#4f5f6b')}}]},
        'drillFilterOtherVisuals': True}, {**background('#FFFFFF'), **{'border': [{'properties': {'show': L('true'), 'color': solid('#d5dde3'), 'radius': L('8D')}}]}})
# ratings table
container('levels', 20, 284, 776, 136, {'visualType': 'tableEx', 'query': {'queryState': {'Values': {'projections': [C('Rating Levels', 'Level'), M('Group rating level'), M('RRNC rating level'), M('Virginia rating level')]}}},
    'objects': {'columnHeaders': [{'properties': {'fontSize': L('12D'), 'bold': L('true'), 'fontColor': solid(NAVY), 'backColor': solid('#eef4f8')}}], 'values': [{'properties': {'fontSize': L('12D')}}]},
    'drillFilterOtherVisuals': True}, title('Ratings in the latest program year: sites (share)'))
# over time
container('trend', 20, 432, 776, 270, {'visualType': 'lineChart', 'query': {'queryState': {'Category': {'projections': [C(PY.strip("'"), 'cr720_name')]}, 'Y': {'projections': [M('Group average by year'), M('RRNC average by year'), M('Virginia average by year')]}}},
    'objects': {'legend': [{'properties': {'show': L('true'), 'position': Q('Bottom'), 'fontSize': L('12D')}}], 'labels': [{'properties': {'show': L('true'), 'fontSize': L('12D')}}],
                'valueAxis': [{'properties': {'showAxisTitle': L('false'), 'fontSize': L('12D')}}], 'categoryAxis': [{'properties': {'fontSize': L('12D')}}]},
    'drillFilterOtherVisuals': True}, title('Average total points by program year'))
# site detail: sites by year
container('sites', 20, 714, 776, 292, {'visualType': 'pivotTable', 'query': {'queryState': {'Rows': {'projections': [C(PS.strip("'"), 'cr720_sitename')]}, 'Columns': {'projections': [C(PY.strip("'"), 'cr720_name')]}, 'Values': {'projections': [M('Total points')]}}},
    'objects': {'columnHeaders': [{'properties': {'fontSize': L('12D'), 'bold': L('true'), 'fontColor': solid(NAVY)}}], 'rowHeaders': [{'properties': {'fontSize': L('12D')}}], 'values': [{'properties': {'fontSize': L('12D')}}]},
    'drillFilterOtherVisuals': True}, title('Total points by site and program year'))
# footer
container('foot', 20, 1014, 776, 34, {'visualType': 'textbox', 'objects': {'general': [{'properties': {'paragraphs': [{'textRuns': [{'value': 'Internal use. Approval is needed before sharing outside Foundation First / RRNC. Source: VDOE VQB5 Quality Rating Data (public); Virginia figures from VDOE statewide files. Scores run from 100 to 800. No Provider 360 or other internal data is included.', 'textStyle': {'fontSize': '10pt', 'color': '#4f5f6b'}}]}]}}]}})
print('Built Virginia table, rating levels, measures and report page in', PBI)
