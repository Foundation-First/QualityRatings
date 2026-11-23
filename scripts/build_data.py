"""Clean the VDOE VQB5 workbooks into internal/data/sites.json (site-level records, never published)
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
    '2024-25': pd.DataFrame(dict(region=b['RegionName'], type=b['SiteType'], rating=b['QualityRating'], tp=b['TotalPts'].map(pts), honor=b['Honor Roll'], prev=pd.to_numeric(b['Total Points: 2023-2024'], errors='coerce'))),
    '2025-26': pd.DataFrame(dict(region=a['RegionName'], type=a['SiteType'], rating=a['QualityRating'], tp=a['TotalPts'].map(pts), honor=a['Honor Roll'], prev=pd.to_numeric(a['Total Points: 2024-2025'], errors='coerce'))),
}

def aggregate(df):
    cutb = pd.cut(df.tp, [0, 399, 499, 599, 699, 800], labels=['399 or less', '400-499', '500-599', '600-699', '700-800'])
    out = dict(n=int(df.rating.notna().sum()), ratings={r: int((df.rating == r).sum()) for r in RATINGS},
               bins=[int((cutb == b).sum()) for b in cutb.cat.categories],
               avg=round(float(df.tp.mean()), 1) if len(df) else None, byType={})
    for t in TYPES:
        d = df[df.type == t]
        cb = pd.cut(d.tp, [0, 399, 499, 599, 699, 800], labels=['399 or less', '400-499', '500-599', '600-699', '700-800'])
        out['byType'][t] = dict(n=int(len(d)), avg=round(float(d.tp.mean()), 1) if len(d) else None, bins=[int((cb == bn).sum()) for bn in cb.cat.categories])
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
def roster(prev_df, cur_df):
    # Sites are followed with the earlier-year points VDOE lists beside each site (site ID numbers change between years):
    # a site with earlier-year points is "returning", one without is "new".
    out = {}
    for key in ['all'] + TYPES:
        cu = cur_df if key == 'all' else cur_df[cur_df.type == key]
        cont, new = cu[cu.prev.notna()], cu[cu.prev.isna()]
        r1 = lambda v: None if v is None or pd.isna(v) else round(float(v), 1)
        out[key] = dict(n=int(len(cu)), cont=dict(n=int(len(cont)), avg=r1(cont.tp.mean())), new=dict(n=int(len(new)), avg=r1(new.tp.mean())))
    return out
def rr(y): return years[y][years[y].region == REGION]
summary['roster'] = {'2024-25': roster(rr('2023-24'), rr('2024-25')), '2025-26': roster(rr('2024-25'), rr('2025-26'))}
for y in ('2024-25', '2025-26'):
    summary['honor'][y] = honor(years[y][years[y].region == REGION])
    summary['honorStatewide'][y] = honor(years[y])

# ---- site-level records: North Central only ----
a_all = a.copy()
a = a[a['RegionName'] == REGION]

# ---- extra North Central breakdowns for the Summary page ----
BINS = ['399 or less', '400-499', '500-599', '600-699', '700-800']
cut = pd.cut(a.TotalPts, [0, 399, 499, 599, 699, 800], labels=BINS)
summary['bins'] = dict(labels=BINS, byType={t: [int(((a.SiteType == t) & (cut == b)).sum()) for b in BINS] for t in TYPES})
summary['typeRatings'] = {t: {r: int(((a.SiteType == t) & (a.QualityRating == r)).sum()) for r in RATINGS} for t in TYPES}
is_new = a['Quality Rating: 2024-2025'].isna()
summary['newSites'] = dict(
    n=int(is_new.sum()), byType={t: int(((a.SiteType == t) & is_new).sum()) for t in TYPES},
    avgNew=round(float(a[is_new].TotalPts.mean()), 1), avgReturning=round(float(a[~is_new].TotalPts.mean()), 1),
    returningPrev=round(float(a[~is_new]['Total Points: 2024-2025'].mean()), 1), nReturning=int((~is_new).sum()),
    newBins=[int(((cut == b) & is_new).sum()) for b in BINS])
using = ~a.CurriculumUse.fillna('').str.contains('did not report')
summary['curriculumUse'] = {t: dict(using=int(((a.SiteType == t) & using).sum()), total=int((a.SiteType == t).sum())) for t in TYPES}

# ---- years in VQB5 (as of 2025-26): first year, second year (joined 2024-25), three years (participating since 2023-24)
def tenure(df):
    t24, t23 = df['Total Points: 2024-2025'], df['Total Points: 2023-2024']
    first, second, third = df[t24.isna()], df[t24.notna() & t23.isna()], df[t24.notna() & t23.notna()]
    r = lambda v: None if pd.isna(v) else round(float(v), 1)
    return dict(first=dict(n=int(len(first)), avg=r(first.TotalPts.mean())),
                second=dict(n=int(len(second)), avg=r(second.TotalPts.mean()), avgFirstYear=r(second['Total Points: 2024-2025'].mean())),
                third=dict(n=int(len(third)), avg=r(third.TotalPts.mean())))
summary['tenure'] = {k: tenure(a if k == 'all' else a[a.SiteType == k]) for k in ['all'] + TYPES}

# ---- sites rated in all three years: average points each year (aggregate only, no site identifiers) ----
def same_sites(df):
    d = df[df['Total Points: 2024-2025'].notna() & df['Total Points: 2023-2024'].notna()]
    return dict(n=int(len(d)), avg={'2023-24': round(float(d['Total Points: 2023-2024'].mean()), 1), '2024-25': round(float(d['Total Points: 2024-2025'].mean()), 1), '2025-26': round(float(d.TotalPts.mean()), 1)} if len(d) else {})
summary['sameSites'] = {k: same_sites(a if k == 'all' else a[a.SiteType == k]) for k in ['all'] + TYPES}
json.dump(summary, open('site/data/summary.json', 'w'), separators=(',', ':'))

# ---- statewide benchmark aggregates for the Compare page (no site identifiers) ----
HSTART, HSTEP = 340, 5
def bench(df):
    hist = [0] * 90
    for v in df.TotalPts.dropna():
        hist[min(89, max(0, int((v - HSTART) // HSTEP)))] += 1
    cutb = pd.cut(df.TotalPts, [0, 399, 499, 599, 699, 800], labels=BINS)
    return dict(n=int(len(df)), tp=round(float(df.TotalPts.mean()), 1), ip=round(float(df.InteractionPts.mean()), 1), cp=round(float(df.CurriculumPts.mean()), 1),
                ratings={r: int((df.QualityRating == r).sum()) for r in RATINGS}, bins=[int((cutb == b).sum()) for b in BINS],
                start=HSTART, step=HSTEP, hist=hist)
json.dump(dict(state={'all': bench(a_all), **{t: bench(a_all[a_all.SiteType == t]) for t in TYPES}}), open('site/data/benchmarks.json', 'w'), separators=(',', ':'))

def num(v): return None if pd.isna(v) else int(v)
def txt(v): return None if pd.isna(v) else str(v).strip()
def lst(v, sep):
    if pd.isna(v) or str(v).strip() in ('None', 'NA', ''): return []
    return [x.strip() for x in re.split(sep, str(v)) if x.strip()]

import os
os.makedirs('internal/data', exist_ok=True)   # site-level records stay out of the published site/ folder
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
        cu='did not report' not in str(r['CurriculumUse']),
        hist={y: h for y, h in hist.items() if h['rating']},
    ))

json.dump(dict(year='2025-26', region=REGION, sites=rows), open('internal/data/sites.json', 'w'), separators=(',', ':'))
import datetime
json.dump(dict(built=datetime.date.today().isoformat(), vdoeWorkbook='2025-26 VQB5 Quality Rating Data for Website (VDOE file dated 2026-09-29)'), open('site/data/meta.json', 'w'))
print(len(rows), 'North Central sites written')
for y in summary['statewide']:
    s = summary['statewide'][y]
    print(y, 'statewide n =', s['n'], 'avg =', s['avg'], '| NC n =', summary['years'][y]['n'], 'avg =', summary['years'][y]['avg'])
print('honor statewide 25-26', summary['honorStatewide']['2025-26'])
