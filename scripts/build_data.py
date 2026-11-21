"""Clean the VDOE VQB5 workbooks into site/data/sites.json (North Central sites only)
and site/data/summary.json (North Central summary + statewide benchmark aggregates).

Only Ready Region 8 site-level records are published. Statewide figures are
aggregates only (counts / averages), used as a benchmark like VDOE's own summary PDF.
"""
import json, re, pandas as pd

REGION = 'Ready Region 8 - North Central'
TYPES = ['Center', 'Public School', 'Family Day Home']
RATINGS = ['Exceeds Expectations', 'Meets Expectations', 'Needs Support']

a = pd.read_excel('raw/r2526.xlsx')
b = pd.read_excel('raw/r2425.xlsx')
c = pd.read_excel('raw/r2324.xlsx')

def pts(v):
    if pd.isna(v): return None
    m = re.search(r'\d+', str(v))
    return int(m.group()) if m else None

# Normalise each year's full file (all regions) to a common shape for the summary aggregates.
years = {
    '2023-24': pd.DataFrame(dict(region=c['Ready Region Name'], type=c['Site Type'], rating=c['Quality Rating'], tp=c['Total Points'].map(pts), honor=None)),
    '2024-25': pd.DataFrame(dict(region=b['RegionName'], type=b['SiteType'], rating=b['QualityRating'], tp=b['TotalPts'].map(pts), honor=b['Honor Roll'])),
    '2025-26': pd.DataFrame(dict(region=a['RegionName'], type=a['SiteType'], rating=a['QualityRating'], tp=a['TotalPts'].map(pts), honor=a['Honor Roll'])),
}

def aggregate(df):
    out = dict(n=int(df.rating.notna().sum()), ratings={r: int((df.rating == r).sum()) for r in RATINGS},
               avg=round(float(df.tp.mean()), 1) if len(df) else None, byType={})
    for t in TYPES:
        d = df[df.type == t]
        out['byType'][t] = dict(n=int(len(d)), avg=round(float(d.tp.mean()), 1) if len(d) else None)
    return out

def honor(df):
    """Honor roll counts by category x site type, plus unique sites on any honor roll."""
    cats = {'Excellence': 'Excellence', 'Improvement': 'Top Improvement in Interactions', 'Infant/Toddler': 'Top Infant and Toddler Quality'}
    h = df.honor.fillna('')
    res = {label: {t: int(((h.str.contains(k)) & (df.type == t)).sum()) for t in TYPES} for k, label in cats.items()}
    res['_unique'] = int((h != '').sum())
    return res

summary = dict(region='Ready Region 8 - North Central', years={}, statewide={}, honor={}, honorStatewide={})
for y, df in years.items():
    summary['years'][y] = aggregate(df[df.region == REGION])
    summary['statewide'][y] = aggregate(df)
for y in ('2024-25', '2025-26'):
    summary['honor'][y] = honor(years[y][years[y].region == REGION])
    summary['honorStatewide'][y] = honor(years[y])
json.dump(summary, open('site/data/summary.json', 'w'), separators=(',', ':'))

# ---- site-level records: North Central only ----
a = a[a['RegionName'] == REGION]

def num(v): return None if pd.isna(v) else int(v)
def txt(v): return None if pd.isna(v) else str(v).strip()
def lst(v, sep):
    if pd.isna(v) or str(v).strip() in ('None', 'NA', ''): return []
    return [x.strip() for x in re.split(sep, str(v)) if x.strip()]

rows = []
for r in a.to_dict('records'):
    rooms = lst(r['ClassroomsServed'], r';\s*')
    hist = {
        '2024-25': dict(rating=txt(r['Quality Rating: 2024-2025']), ip=num(r['Interaction Points: 2024-2025']), cp=num(r['Curriculum Points: 2024-2025']), tp=num(r['Total Points: 2024-2025'])),
        '2023-24': dict(rating=txt(r['Quality Rating: 2023-2024']), ip=num(r['Interaction Points: 2023-2024']), cp=num(r['Curriculum Points: 2023-2024']), tp=num(r['Total Points: 2023-2024'])),
    }
    rows.append(dict(
        id=int(r['VACSiteId']), name=txt(r['SiteName']), county=txt(r['County']), type=txt(r['SiteType']),
        addr=txt(r['Address']), web=txt(r['Website']),
        rating=txt(r['QualityRating']), ip=num(r['InteractionPts']), cp=num(r['CurriculumPts']), tp=num(r['TotalPts']),
        honor=lst(r['Honor Roll'], r',\s*'), rooms=rooms, ages=', '.join(rooms) or 'Not reported',
        fund=lst(r['PublicFundingSources'], r',\s*'), curr=lst(r['CurriculumNamesUnique'], r';\s*'),
        hist={y: h for y, h in hist.items() if h['rating']},
    ))

json.dump(dict(year='2025-26', region=REGION, sites=rows), open('site/data/sites.json', 'w'), separators=(',', ':'))
print(len(rows), 'North Central sites written')
for y in summary['statewide']:
    s = summary['statewide'][y]
    print(y, 'statewide n =', s['n'], 'avg =', s['avg'], '| NC n =', summary['years'][y]['n'], 'avg =', summary['years'][y]['avg'])
print('honor statewide 25-26', summary['honorStatewide']['2025-26'])
