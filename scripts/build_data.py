"""Clean the VDOE VQB5 quality-rating workbooks into site/data/sites.json."""
import json, re, pandas as pd

a = pd.read_excel('raw/r2526.xlsx')
cur = {}
for sh in ('Sites', 'Classrooms'):
    d = pd.read_excel('raw/cur2526.xlsx', sheet_name=sh, header=3).dropna(subset=['Curriculum'])
    cur[sh.lower()] = [[c, int(n)] for c, n in zip(d['Curriculum'], d.iloc[:, 1]) if pd.notna(n)]

def num(v):
    return None if pd.isna(v) else int(v)
def txt(v):
    return None if pd.isna(v) else str(v).strip()
def lst(v, sep):
    if pd.isna(v) or str(v).strip() in ('None', 'NA', ''): return []
    return [x.strip() for x in re.split(sep, str(v)) if x.strip()]

rows = []
for r in a.to_dict('records'):
    z = re.search(r'\b(\d{5})(?:-\d{4})?\s*$', str(r['Address']))
    rows.append(dict(
        id=int(r['VACSiteId']), name=txt(r['SiteName']),
        region=re.sub(r'Ready Region (\d) - ', r'R\1 ', r['RegionName']),
        county=txt(r['County']), type=txt(r['SiteType']), addr=txt(r['Address']),
        zip=z.group(1) if z else None, web=txt(r['Website']),
        rating=txt(r['QualityRating']), ip=num(r['InteractionPts']), cp=num(r['CurriculumPts']), tp=num(r['TotalPts']),
        honor=lst(r['Honor Roll'], r',\s*'),
        rooms=lst(r['ClassroomsServed'], r';\s*'),
        fund=lst(r['PublicFundingSources'], r',\s*'),
        curr=lst(r['CurriculumNamesUnique'], r';\s*'),
        days=len(lst(r['OperatingDays'], r',')),
        hist={
            '2024-25': dict(rating=txt(r['Quality Rating: 2024-2025']), ip=num(r['Interaction Points: 2024-2025']), cp=num(r['Curriculum Points: 2024-2025']), tp=num(r['Total Points: 2024-2025'])),
            '2023-24': dict(rating=txt(r['Quality Rating: 2023-2024']), ip=num(r['Interaction Points: 2023-2024']), cp=num(r['Curriculum Points: 2023-2024']), tp=num(r['Total Points: 2023-2024'])),
        },
    ))
# drop empty history entries to shrink the file
for s in rows:
    s['hist'] = {y: h for y, h in s['hist'].items() if h['rating']}
out = dict(year='2025-26', sites=rows, curriculum=cur,
           source='https://earlychildhoodquality.doe.virginia.gov/quality-ratings/')
json.dump(out, open('site/data/sites.json', 'w'), separators=(',', ':'))
print(len(rows), 'sites written')
