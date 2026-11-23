// Shared data loading, filter bar, brand palette and chart helpers for all pages.
// One meaning per colour (so a colour never changes meaning between charts):
//   green  = RRNC (our region / our sites)      grey   = Virginia (state benchmark)
//   orange -> light blue -> blue = rating levels, low -> high (a blue/orange ramp stays distinguishable for red-green colour blindness)
//   tan / slate / brown = site types             dark / light green = emphasis within RRNC data (e.g. new vs returning, fall vs spring)
const P = {blue: '#11689B', navy: '#0E3F66', green: '#99CA3C', rrnc: '#6FA82B', greenD: '#6FA82B', greenDD: '#3E6B0F', greenL: '#B7D98A', orange: '#F7941D', grey: '#85888B', lightBlue: '#9CC3DB', ink: '#23323f', grid: '#e9eef2', tan: '#D9B98A', slate: '#6B7F91', brown: '#8A5A2B', absent: '#CFD4D9'};
// ---- Rating scale -------------------------------------------------------------------------------------------
// Total scores fall in five 100-point bands (the building block for every scale). A rating scale is a set of
// levels, each a group of bands, ordered low -> high.
//   three = VQB5 through 2025-26: Needs Support 100-399 | Meets Expectations 400-699 | Exceeds Expectations 700-800
//   five  = VQB5's new levels (official names from VDOE's Fall 2026 Data Deep Dive): beginning with the 2026-27
//           program year, with ratings issued in fall 2027.
// The 3-level scale is the default. Add ?scale=5 to any page URL to preview the 5-level scale.
const BANDS = ['399 or less', '400-499', '500-599', '600-699', '700-800'];
const bandIdx = v => v == null ? -1 : v <= 399 ? 0 : v <= 499 ? 1 : v <= 599 ? 2 : v <= 699 ? 3 : 4;
const bandCounts = list => { const c = BANDS.map(() => 0); list.forEach(s => { const i = bandIdx(s.tp); if (i >= 0) c[i]++; }); return c; };
const SCHEMES = {
  three: {key: 'three', title: '3-level', groups: [[0], [1, 2, 3], [4]], levels: [
    {name: 'Needs Support', short: 'Needs Support', pts: '100-399', color: P.orange, text: '#23323f'},
    {name: 'Meets Expectations', short: 'Meets Expectations', pts: '400-699', color: P.lightBlue, text: '#23323f'},
    {name: 'Exceeds Expectations', short: 'Exceeds Expectations', pts: '700-800', color: P.blue, text: '#fff'}]},
  five: {key: 'five', title: '5-level', groups: [[0], [1], [2], [3], [4]], levels: [
    {name: 'Needs Support', short: 'Needs Support', pts: '100-399', color: '#F7941D', text: '#23323f'},
    {name: 'Approaching Expectations', short: 'Approaching Expectations', pts: '400-499', color: '#FBC77A', text: '#23323f'},
    {name: 'Meets Expectations', short: 'Meets Expectations', pts: '500-599', color: '#BCD6E8', text: '#23323f'},
    {name: 'Exceeds Expectations', short: 'Exceeds Expectations', pts: '600-699', color: '#6FA3C7', text: '#23323f'},
    {name: 'Distinguished', short: 'Distinguished', pts: '700-800', color: '#11689B', text: '#fff'}]},
};
let scaleKey = 'three';
try {
  const q = new URLSearchParams(location.search).get('scale');
  if (q) sessionStorage.setItem('vqb5scale', q === '5' || q === 'five' ? 'five' : 'three');
  scaleKey = sessionStorage.getItem('vqb5scale') === 'five' ? 'five' : 'three';
} catch (e) {}
const SCHEME = SCHEMES[scaleKey], LEVELS = SCHEME.levels;
const levelsFromBins = bins => SCHEME.groups.map(g => sum(g.map(i => bins[i])));   // counts per level, low -> high
const levelIdx = tp => tp == null ? -1 : SCHEME.groups.findIndex(g => g.includes(bandIdx(tp)));
const levelOf = tp => LEVELS[levelIdx(tp)]?.name ?? null;
const levelCounts = list => levelsFromBins(bandCounts(list));
const DESC = LEVELS.map((_, i) => LEVELS.length - 1 - i);   // display order high -> low, like VDOE's own tables
const lvShort = i => LEVELS[i].short;
// table column header for a level: two short lines so the full name (always with "Expectations") fits a narrow card
const lvHead = i => LEVELS[i].name.replace(/ (Expectations|Support)$/, '<br>$1');
// "502 (98%)": a count with its share in parentheses
const np = (v, t) => `${fmt(v)} (${pc(v, t)})`;
const TYPES = ['Center', 'Public School', 'Family Day Home'];
const TLABEL = {Center: 'Child care centers', 'Public School': 'Public schools', 'Family Day Home': 'Home-based child care'};
const TSHORT = {Center: 'Centers', 'Public School': 'Public schools', 'Family Day Home': 'Home-based'};   // compact labels for tables
// A locality's school division. Counties are "<County> Public Schools"; these independent cities use their official division names.
const DIST_OVERRIDE = {'Manassas': 'Manassas City Public Schools', 'Manassas Park': 'Manassas Park City Schools', 'Fredericksburg': 'Fredericksburg City Public Schools'};
const distName = n => DIST_OVERRIDE[n] || `${n} Public Schools`;
const TCOLOR = {Center: P.tan, 'Public School': P.slate, 'Family Day Home': P.brown};
const TTEXT = {Center: '#23323f', 'Public School': '#fff', 'Family Day Home': '#fff'};
const $ = s => document.querySelector(s);
const sum = a => a.reduce((x, y) => x + y, 0);
const mean = a => a.length ? sum(a) / a.length : null;
const fmt = n => n == null ? '–' : n.toLocaleString();
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const pc = (v, n) => { if (!n) return '–'; const p = 100 * v / n; return p > 0 && p < 1 ? '<1%' : Math.round(p) + '%'; };
// groups (optional): [[label, colspan], ...] draws a spanning header row above the column headings
const table = (head, rows, numFrom = 1, groups) => {
  const cls = h => typeof h === 'object' ? h.cls : '';
  const hc = i => head[i] && typeof head[i] === 'object' ? head[i].cls : '';
  return `<table><thead>${groups ? `<tr class="grp">${groups.map(([l, n]) => `<th colspan="${n}">${l}</th>`).join('')}</tr>` : ''}<tr>${head.map((h, i) => `<th class="${i >= numFrom ? 'n' : ''} ${cls(h)}">${typeof h === 'object' ? h.t : h}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map((c, i) => `<td class="${i >= numFrom ? 'n' : ''} ${hc(i) === 'hl' ? 'hl' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
};
const kpis = items => items.map(([b, s, c]) => `<div class="kpi"><b>${b}</b><span>${c ? `<i class="dot" style="background:${c}"></i>` : ''}${s}</span></div>`).join('');
async function loadJSON(name) { return (await fetch('data/' + name + '.json')).json(); }

let state = {};
try { state = JSON.parse(sessionStorage.getItem('vqb5f') || '{}'); } catch (e) {}
let DATA, SUMMARY, CLASS, BENCH, ALL, FILTERED = [], onChange = () => {};

const FILTERS = [
  ['county', 'Locality', s => [s.county]],
  ['type', 'Site type', s => [s.type]],
  ['level', 'Quality rating', s => [levelOf(s.tp)]],
  ['rooms', 'Age group served', s => s.rooms],
  ['fund', 'Public funding', s => s.fund],
  ['honor', 'Honor roll', s => s.honor],
  ['curr', 'Curriculum', s => s.curr],
];

function match(s, skip) {
  for (const [k, , get] of FILTERS) {
    if (k === skip || !state[k]) continue;
    if (!get(s).includes(state[k])) return false;
  }
  const q = (state.q || '').toLowerCase();
  if (q && !(s.name + ' ' + s.addr + ' ' + s.county).toLowerCase().includes(q)) return false;
  return true;
}

function buildFilters() {
  const box = $('#filters .grid-f');
  box.innerHTML = '<label>Search name or address<input type="search" id="f-q" placeholder="e.g. Little Stars, 22030"></label>';
  for (const [k, label] of FILTERS) box.insertAdjacentHTML('beforeend', `<label>${label}<select id="f-${k}"></select></label>`);
  box.insertAdjacentHTML('beforeend', '<button id="reset">Reset filters</button>');
  $('#f-q').value = state.q || '';
  $('#f-q').addEventListener('input', e => { state.q = e.target.value; update(); });
  for (const [k] of FILTERS) $('#f-' + k).addEventListener('change', e => { state[k] = e.target.value; update(); });
  $('#reset').onclick = () => { for (const k in state) delete state[k]; $('#f-q').value = ''; update(); };
}

function refreshOptions() {
  // Faceted options: each list reflects the counts under all the *other* active filters.
  for (const [k, , get] of FILTERS) {
    const counts = {};
    for (const s of ALL) if (match(s, k)) for (const v of get(s)) if (v) counts[v] = (counts[v] || 0) + 1;
    if (state[k] && !(state[k] in counts)) delete state[k];
    let keys = Object.keys(counts).sort();
    if (k === 'level') keys = LEVELS.map(l => l.name).filter(r => counts[r]);
    const sel = $('#f-' + k);
    sel.innerHTML = '<option value="">All</option>' + keys.map(v => `<option value="${esc(v)}">${esc(v)} (${counts[v]})</option>`).join('');
    sel.value = state[k] || '';
  }
}

function update() {
  refreshOptions();
  FILTERED = ALL.filter(s => match(s));
  try { sessionStorage.setItem('vqb5f', JSON.stringify(state)); } catch (e) {}
  // Filters are tucked away by default, so say plainly when the data has been narrowed.
  const active = FILTERS.filter(f => state[f[0]]).map(f => `${f[1]}: ${state[f[0]]}`).concat(state.q ? [`Search: “${state.q}”`] : []);
  $('#count').innerHTML = `Showing ${FILTERED.length.toLocaleString()} of ${ALL.length.toLocaleString()} sites` + (active.length ? ` <span class="note" style="font-weight:600">· narrowed by ${active.map(esc).join('; ')}</span> <a href="#" id="clear-f">Clear</a>` : '');
  const cf = $('#clear-f'); if (cf) cf.onclick = ev => { ev.preventDefault(); $('#reset').click(); };
  const sn = $('#smalln');
  if (sn) { sn.style.display = FILTERED.length < 20 ? '' : 'none'; sn.textContent = FILTERED.length ? `Based on ${FILTERED.length} ${FILTERED.length === 1 ? 'site' : 'sites'}.` : 'No sites match these filters.'; }
  onChange();
}

function plot(id, traces, layout = {}) {
  const base = {
    margin: {t: 10, r: 12, b: 70, l: 50}, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {family: "'Nunito Sans',system-ui,sans-serif", color: P.ink, size: 15}, legend: {orientation: 'h', y: -0.3},
    xaxis: {gridcolor: P.grid, automargin: true, zeroline: false}, yaxis: {gridcolor: P.grid, automargin: true, zeroline: false},
    hoverlabel: {font: {family: "'Nunito Sans',system-ui,sans-serif"}},
  };
  const lay = {...base, ...layout, xaxis: {...base.xaxis, ...(layout.xaxis || {})}, yaxis: {...base.yaxis, ...(layout.yaxis || {})}};
  Plotly.react(id, traces, lay, {displayModeBar: false, responsive: true});
}

// Sankey (flow) diagram: rating levels by year, ribbons = sites moving between levels. `sites` need hist + tp.
// Only sites still in the program in 2025-26 are in the source data, so earlier-year bars show those sites;
// "Not yet rated" holds sites that joined later.
function sankeyLevels(id, sites, years = ['2023-24', '2024-25', '2025-26']) {
  const K = LEVELS.length, NR = K, NCOL = years.length, GREY = '#CFD4D9';
  const tpOf = (s, y) => y === '2025-26' ? s.tp : s.hist?.[y]?.tp;
  const lvl = (s, y) => { const tp = tpOf(s, y); return tp == null ? NR : levelIdx(tp); };
  const cnt = years.map(() => Array(K + 1).fill(0)), flow = {};
  sites.forEach(s => years.forEach((y, c) => {
    const a = lvl(s, y); cnt[c][a]++;
    if (c < NCOL - 1) { const b = lvl(s, years[c + 1]); if (a === NR && b === NR) return; const k = `${c}|${a}|${b}`; flow[k] = (flow[k] || 0) + 1; }
  }));
  const order = [...DESC, NR];                                   // top -> bottom: highest level first
  const nid = (c, l) => c * (K + 1) + l;
  const nodes = [], colorOf = l => l === NR ? GREY : LEVELS[l].color;
  const xs = [0.02, 0.5, 0.98].slice(0, NCOL);
  const label = [], color = [], x = [], y = [];
  for (let c = 0; c < NCOL; c++) {
    const shown = order.filter(l => cnt[c][l] > 0 || l !== NR);
    const tot = sum(cnt[c]) || 1, share = l => Math.max(cnt[c][l] / tot, 0.06), allocTot = sum(shown.map(share));
    let cum = 0;
    for (const l of order) {                                      // every node must exist so link indices stay valid; stacked top -> bottom in `order`
      const v = cnt[c][l], inShown = shown.includes(l);
      const sh = inShown ? share(l) / allocTot : 0, center = cum + sh / 2; if (inShown) cum += sh;
      label[nid(c, l)] = v ? `${l === NR ? 'Not yet rated' : LEVELS[l].name} (${v})` : '';
      color[nid(c, l)] = colorOf(l); x[nid(c, l)] = xs[c]; y[nid(c, l)] = Math.min(0.97, Math.max(0.03, center));
    }
  }
  const src = [], tgt = [], val = [], lcol = [], ltxt = [], moved = {total: 0, changed: 0};
  Object.entries(flow).forEach(([k, v]) => {
    const [c, a, b] = k.split('|').map(Number);
    src.push(nid(c, a)); tgt.push(nid(c + 1, b)); val.push(v);
    const rgb = colorOf(a).replace('#', ''), r = parseInt(rgb.slice(0, 2), 16), g = parseInt(rgb.slice(2, 4), 16), bl = parseInt(rgb.slice(4, 6), 16);
    lcol.push(`rgba(${r},${g},${bl},${a === NR ? 0.5 : 0.7})`);
    if (a !== NR && b !== NR) { moved.total += v; if (a !== b) moved.changed += v; }
    ltxt.push(`${years[c]} ${a === NR ? 'Not yet rated' : LEVELS[a].name} to ${years[c + 1]} ${b === NR ? 'Not yet rated' : LEVELS[b].name}`);
  });
  const lay = {margin: {t: 30, r: 10, b: 10, l: 10}, paper_bgcolor: 'rgba(0,0,0,0)', font: {family: "'Nunito Sans',system-ui,sans-serif", color: P.ink, size: 15},
    annotations: years.map((yy, c) => ({text: `<b>${yy}</b>`, x: [0, 0.5, 1][c] ?? c / (NCOL - 1), xanchor: ['left', 'center', 'right'][c] ?? 'center', y: 1.06, yref: 'paper', showarrow: false, font: {size: 15}}))};
  sankeyLevels.lastMoved = moved;
  Plotly.react(id, [{type: 'sankey', arrangement: 'fixed', node: {pad: 14, thickness: 18, line: {width: 0}, label, color, x, y, hovertemplate: '%{label}<extra></extra>'},
    link: {source: src, target: tgt, value: val, color: lcol, customdata: ltxt, hovertemplate: '%{customdata}: %{value} sites<extra></extra>'}}], lay, {displayModeBar: false, responsive: true});
}

// page: nav key; cb: draw function; opts.data = names of extra JSON files to load (as SUMMARY / CLASS); opts.filters=false hides filter bar
// Give every chart a text description (card title + subtitle + key takeaway) for screen readers.
function labelCharts() {
  document.querySelectorAll('.chart').forEach(el => {
    const card = el.closest('.card'); if (!card) return;
    const t = [card.querySelector('h3')?.textContent, card.querySelector(':scope > p')?.textContent, card.querySelector('.insight')?.textContent].filter(Boolean).map(x => x.trim().replace(/\.$/, '')).join('. ');
    el.setAttribute('role', 'img'); el.setAttribute('aria-label', `Chart: ${t}. Hover or tap the chart for exact values.`);
  });
}

// Ranking as a dot plot (dots need no zero baseline, unlike bars). rows: [{name, label, v, n}], refs: [{x, label, color, dash}]
function dotRank(id, rows, refs, highlight) {
  const sorted = [...rows].sort((a, b) => a.v - b.v), vals = [...rows.map(r => r.v), ...refs.map(r => r.x)];
  const lo = Math.min(...vals), hi = Math.max(...vals);
  plot(id, [{type: 'scatter', mode: 'markers+text', x: sorted.map(r => r.v), y: sorted.map(r => `${r.label} (${r.n} ${r.n === 1 ? 'site' : 'sites'})`), text: sorted.map(r => Math.round(r.v)), textposition: 'middle right', cliponaxis: false,
    marker: {size: sorted.map(r => r.n < 5 ? 9 : 13), color: sorted.map(r => r.name === highlight ? P.ink : P.rrnc), opacity: sorted.map(r => r.n < 5 ? 0.45 : 1), line: {width: 1.5, color: '#fff'}},
    hovertemplate: '%{y}<br>Average: %{x:.0f} points<extra></extra>'}],
    {shapes: refs.map(r => ({type: 'line', x0: r.x, x1: r.x, y0: 0, y1: 1, yref: 'paper', line: {color: r.color, dash: r.dash || 'dash', width: 2}})),
     annotations: refs.map((r, i) => ({x: r.x, y: 1.04, yref: 'paper', text: `${r.label} ${Math.round(r.x)}`, showarrow: false, xanchor: i ? 'left' : 'right', font: {color: r.text || r.color}})),
     xaxis: {title: 'Average total points', range: [lo - 20, hi + 30]}, yaxis: {automargin: true}, showlegend: false, margin: {t: 30, r: 40, b: 50, l: 200}});
  $('#' + id).style.height = Math.max(300, rows.length * 30 + 100) + 'px';
  Plotly.Plots.resize(id);
}

async function init(page, cb, opts = {}) {
  onChange = () => { cb(); labelCharts(); };
  document.querySelectorAll('nav a').forEach(a => a.classList.toggle('on', a.dataset.p === page));
  if (opts.summary) SUMMARY = await loadJSON('summary');
  if (opts.class) CLASS = await loadJSON('class');
  if (opts.bench) BENCH = await loadJSON('benchmarks');
  if (opts.filters === false) {
    $('#filters').remove();
    if (opts.sites) { DATA = await loadJSON('sites'); ALL = DATA.sites; }
    onChange(); return;
  }
  buildFilters();
  $('#ftoggle').addEventListener('click', e => { const o = $('#filters').classList.toggle('open'); e.target.textContent = o ? 'Hide filters' : 'Narrow down (optional)'; e.target.setAttribute('aria-expanded', o); });
  DATA = await loadJSON('sites');
  ALL = DATA.sites;
  update();
}

const NAV = `<header><div class="wrap">
<div class="brand"><img src="img/ff-logo.png" alt="Foundation First – Building Early Childhood Success"><h1>Ready Region North Central - VQB5 Quality Ratings Explorer<small>2025-26 program year</small></h1>
<div class="logos"><img class="rr" src="img/rrnc-logo.png" alt="Ready Region North Central" style="height:52px"></div></div>
<nav><a data-p="summary" href="index.html">Home</a><a data-p="locality" href="locality.html">My locality</a><a data-p="time" href="over-time.html">Over time</a><a data-p="types" href="types.html">Program types</a><a data-p="class" href="class.html">CLASS</a><a data-p="five" href="five-level.html">Five-level ratings</a><a data-p="about" href="about.html">About</a></nav></div></header>
<div id="filters"><div class="wrap"><div class="bar"><span id="count"></span><button id="ftoggle" type="button" aria-expanded="false">Narrow down (optional)</button></div><div class="grid-f"></div><div id="smalln" class="smalln" role="status" style="display:none"></div></div></div>`;
const FOOT = `<footer class="wrap"><p><b>Source:</b> <a href="https://earlychildhoodquality.doe.virginia.gov/quality-ratings/">Virginia Department of Education VQB5 Quality Rating Data</a> and RRNC CLASS summaries. <span id="asof"></span> Independent visualization; VDOE's data is the official record. <a href="about.html">About &amp; definitions</a></p></footer>`;
document.head.insertAdjacentHTML('beforeend', '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700;800&display=swap">');
document.body.insertAdjacentHTML('afterbegin', NAV);
if (scaleKey === 'five') document.querySelector('header').insertAdjacentHTML('afterend', '<div class="preview-banner"><div class="wrap">Preview: the five-level ratings VDOE will use beginning with the 2026-27 program year (ratings issued fall 2027), applied to 2025-26 scores. <a href="?scale=3">Back to the current 3-level view</a></div></div>');
document.body.insertAdjacentHTML('beforeend', FOOT);
fetch('data/meta.json').then(r => r.json()).then(m => { const el = $('#asof'); if (el) el.textContent = `Updated ${new Date(m.built + 'T12:00:00').toLocaleDateString('en-US', {month: 'long', day: 'numeric', year: 'numeric'})}.`; }).catch(() => {});
