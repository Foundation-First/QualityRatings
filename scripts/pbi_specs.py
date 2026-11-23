"""Vega-Lite specs for the Deneb visuals of the Power BI dashboard (build_dashboard.py imports this).

Each builder returns a spec whose data is the Deneb dataset named "dataset". PREVIEW holds sample rows so
scripts/preview_specs.py can draw every chart in a browser before it goes into the report.
Forms follow the data: tiles for counts, bullet bars for scores against a maximum, rings for a share,
dots for comparing groups on one scale.
"""
import copy, json

NAVY, GREEN, GREY, ORANGE = '#0E3F66', '#6FA82B', '#85888B', '#F7941D'
EXC, MEET, NEEDS = '#11689B', '#9CC3DB', '#F7941D'          # rating colours, as on the site
INK, MUTED = '#23323F', '#4F5F6B'
WHO = ['This group', 'RRNC', 'Virginia']
BASE = {'$schema': 'https://vega.github.io/schema/vega-lite/v5.json', 'data': {'name': 'dataset'},
        'width': 'container', 'height': 'container', 'autosize': {'type': 'fit', 'contains': 'padding'},
        'config': {'view': {'stroke': None}, 'font': 'Segoe UI', 'axis': {'labelColor': INK, 'labelFontSize': 12}}}


def _who(keys, who=WHO):
    return [{'fold': list(keys), 'as': ['key', 'value']},
            {'filter': 'isValid(datum.value)'},
            {'calculate': json.dumps(list(who)) + '[indexof(' + json.dumps(list(keys)) + ', datum.key)]', 'as': 'Who'}]


def tiles(order, colors, calc, rows=('big', 'label', 'sub1', 'sub2'), ys=(46, 70, 90, 108), sizes=(36, 13, 12, 12)):
    """Row of tiles: a colour strip on top, a big number, a label and two small lines. `calc` makes the fields."""
    spec = copy.deepcopy(BASE)
    spec['transform'] = calc
    x = {'field': 'Item', 'type': 'ordinal', 'sort': order, 'axis': None, 'scale': {'paddingInner': 0.1, 'paddingOuter': 0.02}}
    spec['encoding'] = {'x': x}
    layers = [{'mark': {'type': 'bar', 'cornerRadius': 2},
               'encoding': {'y': {'value': 0}, 'y2': {'value': 7}, 'color': {'field': 'Item', 'type': 'nominal', 'scale': {'domain': order, 'range': colors}, 'legend': None}}}]
    for r, y, sz in zip(rows, ys, sizes):
        layers.append({'mark': {'type': 'text', 'fontSize': sz, 'fontWeight': 'bold' if r == 'big' else 'normal', 'color': NAVY if r == 'big' else (INK if r == 'label' else MUTED)},
                       'encoding': {'y': {'value': y}, 'text': {'field': r, 'type': 'nominal'}}})
    spec['layer'] = layers
    return spec


def rating_tiles():
    order = ['Exceeds Expectations', 'Meets Expectations', 'Needs Support']
    calc = [{'calculate': 'datum.Level', 'as': 'Item'},
            {'calculate': 'format(round(datum["Group level share"] * datum["Sites rated"]), ",")', 'as': 'big'},
            {'calculate': 'datum.Level', 'as': 'label'},
            {'calculate': 'format(datum["Group level share"], ".0%") + " of sites"', 'as': 'sub1'},
            {'calculate': '"RRNC " + format(datum["RRNC level share"], ".0%") + "  ·  Virginia " + format(datum["Virginia level share"], ".0%")', 'as': 'sub2'}]
    return tiles(order, [EXC, MEET, NEEDS], calc)


def detail_tiles(order, colors, label_map=None):
    """Honor Roll and years in VQB5: group count and share, with RRNC and Virginia shares (Virginia only when present)."""
    calc = [{'calculate': 'datum.Item', 'as': 'Item'},
            {'calculate': 'format(round(datum["Group detail share"] * datum["Sites rated"]), ",")', 'as': 'big'},
            {'calculate': 'datum.Item', 'as': 'label'},
            {'calculate': 'format(datum["Group detail share"], ".0%") + " of sites"', 'as': 'sub1'},
            {'calculate': '"RRNC " + format(datum["RRNC detail share"], ".0%") + (isValid(datum["Virginia detail share"]) ? "  ·  VA " + format(datum["Virginia detail share"], ".0%") : "")', 'as': 'sub2'}]
    return tiles(order, colors, calc, ys=(48, 72, 92, 110), sizes=(34, 13, 12, 12))


def bullet(maxes, order):
    """Score against the maximum possible: track, group bar, RRNC and Virginia ticks."""
    keys = ['Group detail points', 'RRNC detail points', 'Virginia detail points']
    spec = copy.deepcopy(BASE)
    spec['transform'] = _who(keys) + [
        {'calculate': "datum.Item", 'as': 'Item'},
        {'pivot': 'Who', 'value': 'value', 'groupby': ['Item']},
        {'calculate': json.dumps(maxes) + '[datum.Item]', 'as': 'mx'},
        {'calculate': '0', 'as': 'zero'}, {'calculate': '1', 'as': 'one'},
        {'calculate': 'datum["This group"] / datum.mx', 'as': 'g'},
        {'calculate': 'datum["RRNC"] / datum.mx', 'as': 'r'},
        {'calculate': 'datum["Virginia"] / datum.mx', 'as': 'v'},
        {'calculate': 'format(datum["This group"], ".0f") + "   RRNC " + format(datum["RRNC"], ".0f") + "   Virginia " + format(datum["Virginia"], ".0f") + "   (of " + datum.mx + ")"', 'as': 'text'}]
    x = lambda f: {'field': f, 'type': 'quantitative', 'scale': {'domain': [0, 1]}, 'axis': None}
    spec['encoding'] = {'y': {'field': 'Item', 'type': 'nominal', 'sort': order, 'axis': {'title': None, 'ticks': False, 'domain': False, 'labelFontSize': 13, 'labelLimit': 130}, 'scale': {'paddingInner': 0.55}}}
    spec['layer'] = [
        {'mark': {'type': 'bar', 'height': 26, 'color': '#EAF0F5', 'cornerRadius': 3}, 'encoding': {'x': x('zero'), 'x2': {'field': 'one'}}},
        {'mark': {'type': 'bar', 'height': 12, 'color': NAVY, 'cornerRadius': 2}, 'encoding': {'x': x('zero'), 'x2': {'field': 'g'}}},
        {'mark': {'type': 'tick', 'height': 26, 'thickness': 4, 'color': GREEN}, 'encoding': {'x': x('r')}},
        {'mark': {'type': 'tick', 'height': 26, 'thickness': 4, 'color': GREY}, 'encoding': {'x': x('v')}},
        {'mark': {'type': 'text', 'align': 'left', 'dy': -22, 'fontSize': 12, 'color': INK, 'fontWeight': 'bold'}, 'encoding': {'x': x('zero'), 'text': {'field': 'text', 'type': 'nominal'}}}]
    return spec


def rings(pct_field_keys, who=WHO):
    """One ring per group showing a share."""
    keys = list(pct_field_keys)
    colors = [NAVY, GREEN, GREY]
    spec = copy.deepcopy(BASE)
    spec['hconcat'] = []
    for w, c in zip(who, colors):
        child = {
            'transform': _who(keys, who) + [
                {'filter': "datum.Who === '" + w + "'"},
                {'calculate': 'format(datum.value, ".0%")', 'as': 'pct'},
                {'calculate': '[datum.value, 1 - datum.value]', 'as': 'arr'},
                {'calculate': "['yes', 'no']", 'as': 'lab'},
                {'flatten': ['arr', 'lab']}],
            'title': {'text': w, 'fontSize': 13, 'color': INK, 'anchor': 'middle'},
            'width': 100, 'height': 100,
            'layer': [
                {'mark': {'type': 'arc', 'innerRadius': 34, 'outerRadius': 50},
                 'encoding': {'theta': {'field': 'arr', 'type': 'quantitative', 'stack': True},
                              'color': {'field': 'lab', 'type': 'nominal', 'scale': {'domain': ['yes', 'no'], 'range': [c, '#E9EEF2']}, 'legend': None},
                              'order': {'field': 'lab', 'type': 'nominal', 'sort': 'descending'}}},
                {'transform': [{'filter': "datum.lab === 'yes'"}],
                 'mark': {'type': 'text', 'fontSize': 18, 'fontWeight': 'bold', 'color': NAVY, 'align': 'center', 'baseline': 'middle'},
                 'encoding': {'x': {'value': 50}, 'y': {'value': 50}, 'text': {'field': 'pct', 'type': 'nominal'}}}]}
        spec['hconcat'].append(child)
    for k in ('autosize', 'width', 'height'):
        spec.pop(k, None)
    return spec


def dot_plot(keys, item_field, fmt, who=WHO):
    """One row per item, one dot per group on a shared score axis."""
    keys = list(keys)
    spec = copy.deepcopy(BASE)
    spec['transform'] = [{'calculate': "datum['" + item_field + "'] ? datum['" + item_field + "'] : '(Blank)'", 'as': 'Item'}] + _who(keys, who) + [
        {'calculate': "datum.Who === 'This group' ? datum.value : null", 'as': 'gv'},
        {'joinaggregate': [{'op': 'max', 'field': 'gv', 'as': 'groupVal'}], 'groupby': ['Item']}]
    color = {'field': 'Who', 'type': 'nominal', 'sort': who, 'scale': {'domain': who, 'range': [NAVY, GREEN, GREY][:len(who)]},
             'legend': {'orient': 'top', 'title': None, 'labelFontSize': 12, 'symbolType': 'circle'}}
    x = {'field': 'value', 'type': 'quantitative', 'scale': {'zero': False, 'nice': True}, 'axis': {'title': None, 'grid': False, 'labelFontSize': 12}}
    spec['encoding'] = {'y': {'field': 'Item', 'type': 'nominal', 'axis': {'title': None, 'ticks': False, 'domain': False, 'labelFontSize': 13, 'labelLimit': 150}, 'scale': {'paddingInner': 0.3}}}
    lab = lambda who_, dy, col_, flt: {'transform': [{'filter': flt}], 'mark': {'type': 'text', 'dy': dy, 'fontSize': 12, 'fontWeight': 'bold', 'color': col_},
                                       'encoding': {'x': {'field': 'value', 'type': 'quantitative'}, 'text': {'field': 'value', 'type': 'quantitative', 'format': fmt}}}
    spec['layer'] = [
        {'transform': [{'aggregate': [{'op': 'min', 'field': 'value', 'as': 'lo'}, {'op': 'max', 'field': 'value', 'as': 'hi'}], 'groupby': ['Item']}],
         'mark': {'type': 'rule', 'color': '#D5DDE3', 'strokeWidth': 2}, 'encoding': {'x': {'field': 'lo', 'type': 'quantitative'}, 'x2': {'field': 'hi'}}},
        {'transform': [{'calculate': "datum.Who === 'Virginia' ? 0 : datum.Who === 'RRNC' ? 1 : 2", 'as': 'z'}],
         'mark': {'type': 'circle', 'size': 170, 'opacity': 1}, 'encoding': {'x': x, 'color': color, 'order': {'field': 'z', 'type': 'quantitative'}}},
        lab('g', -14, NAVY, "datum.Who === 'This group'"),
        lab('r', -28, '#4C7A12', "datum.Who === 'RRNC' && datum.value !== datum.groupVal"),
        lab('v', 16, '#5F6368', "datum.Who === 'Virginia'")]
    return spec


# ---- sample rows for the browser preview (field names as Deneb receives them)
PREVIEW = {
    'rating_tiles': [{'Level': 'Exceeds Expectations', 'Group level share': .021, 'RRNC level share': .021, 'Virginia level share': .017, 'Sites rated': 514},
                     {'Level': 'Meets Expectations', 'Group level share': .977, 'RRNC level share': .977, 'Virginia level share': .981, 'Sites rated': 514},
                     {'Level': 'Needs Support', 'Group level share': .002, 'RRNC level share': .002, 'Virginia level share': .002, 'Sites rated': 514}],
    'honor': [{'Item': 'Excellence', 'Group detail share': .021, 'RRNC detail share': .021, 'Virginia detail share': .017, 'Sites rated': 514},
              {'Item': 'Improvement', 'Group detail share': .086, 'RRNC detail share': .086, 'Virginia detail share': .095, 'Sites rated': 514},
              {'Item': 'Infant/Toddler', 'Group detail share': .046, 'RRNC detail share': .046, 'Virginia detail share': .066, 'Sites rated': 514}],
    'years': [{'Item': 'First year', 'Group detail share': .11, 'RRNC detail share': .11, 'Virginia detail share': None, 'Sites rated': 514},
              {'Item': 'Second year', 'Group detail share': .11, 'RRNC detail share': .11, 'Virginia detail share': None, 'Sites rated': 514},
              {'Item': 'Third year or more', 'Group detail share': .78, 'RRNC detail share': .78, 'Virginia detail share': None, 'Sites rated': 514}],
    'points': [{'Item': 'Interaction points', 'Group detail points': 503, 'RRNC detail points': 503, 'Virginia detail points': 507},
               {'Item': 'Total points', 'Group detail points': 600, 'RRNC detail points': 600, 'Virginia detail points': 594}],
    'curriculum': [{'Item': 'Curriculum points', 'Group detail share': .97, 'RRNC detail share': .97, 'Virginia detail share': .87}],
    'types': [{'cr720_providertypename': 'Public School', 'Average points': 626, 'RRNC average points': 626, 'Virginia average points': 628},
              {'cr720_providertypename': 'Home-Based Child Care', 'Average points': 591, 'RRNC average points': 591, 'Virginia average points': 578},
              {'cr720_providertypename': 'Center', 'Average points': 589, 'RRNC average points': 589, 'Virginia average points': 584},
              {'cr720_providertypename': None, 'Average points': 582, 'RRNC average points': 582, 'Virginia average points': 594}],
}
