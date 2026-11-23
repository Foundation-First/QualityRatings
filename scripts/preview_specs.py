"""Draw the dashboard's Deneb specs in a browser with sample data, so they can be checked before they go into Power BI.

python scripts/preview_specs.py   ->  internal/spec-preview.html
"""
import json
from pathlib import Path
import pbi_specs as S

CHARTS = [  # title, spec, sample rows, width, plot height
    ('Quality ratings', S.rating_tiles(), 'rating_tiles', 776, 120),
    ('Average score by program type', S.dot_plot(['Average points', 'RRNC average points', 'Virginia average points'], 'cr720_providertypename', 'd'), 'types', 384, 185),
    ('Points against the maximum', S.bullet({'Interaction points': 700, 'Total points': 800}, ['Interaction points', 'Total points']), 'points', 384, 145),
    ('Years in VQB5', S.detail_tiles(['First year', 'Second year', 'Third year or more'], ['#C9DCEA', '#7FA9C9', '#0E3F66']), 'years', 384, 122),
    ('Honor Roll', S.detail_tiles(['Excellence', 'Improvement', 'Infant/Toddler'], ['#BFDC8C', '#8DBF4A', '#4C7A12']), 'honor', 384, 122),
    ('Approved curriculum', S.rings(['Group detail share', 'RRNC detail share', 'Virginia detail share']), 'curriculum', 384, 145),
]
cards = []
for i, (title, spec, key, w, h) in enumerate(CHARTS):
    cards.append(f'<div class="card" style="width:{w}px"><h3>{title}</h3><div id="c{i}" style="width:{w - 40}px;height:{h}px"></div></div>')
js = ''.join(f"vegaEmbed('#c{i}', Object.assign({json.dumps(spec)}, {{data: {{values: {json.dumps(S.PREVIEW[key])}}}}}), {{actions: false}}).catch(e => document.getElementById('c{i}').textContent = 'ERROR: ' + e.message);\n"
             for i, (t, spec, key, w, h) in enumerate(CHARTS))
html = f'''<!doctype html><meta charset=utf-8><style>body{{font-family:Segoe UI,sans-serif;background:#F6F8FA;margin:16px}}.card{{background:#fff;border-radius:10px;box-shadow:0 1px 6px #0E3F6633;padding:12px 20px;margin:0 12px 12px 0;display:inline-block;vertical-align:top;box-sizing:border-box}}h3{{margin:0 0 6px;color:#0E3F66;font-size:16px}}</style>
{''.join(cards)}
<script src="https://cdn.jsdelivr.net/npm/vega@5.30.0"></script><script src="https://cdn.jsdelivr.net/npm/vega-lite@5.19.0"></script><script src="https://cdn.jsdelivr.net/npm/vega-embed@6.25.0"></script>
<script>{js}</script>'''
out = Path('internal/spec-preview.html')
out.write_text(html, encoding='utf-8')
print('wrote', out.resolve())
