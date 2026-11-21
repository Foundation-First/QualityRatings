// Shared data loading, filter bar, brand palette and chart helpers for all pages.
const P = {blue: '#11689B', navy: '#0E3F66', green: '#99CA3C', greenD: '#6FA82B', orange: '#F7941D', grey: '#98999B', lightBlue: '#9CC3DB', ink: '#23323f', grid: '#e9eef2'};
// ---- Rating scale -------------------------------------------------------------------------------------------
// Total scores fall in five 100-point bands (the building block for every scale). A rating scale is a set of
// levels, each a group of bands, ordered low -> high.
//   three = VQB5 today: Needs Support 100-399 | Meets Expectations 400-699 | Exceeds Expectations 700-800
//   five  = the coming 5-level system, built on the 100-point bands. VDOE's official level names are not yet
//           confirmed, so levels are labelled by their point band (add names here once confirmed).
// The 3-level scale is the default. Add ?scale=5 to any page URL to preview the 5-level scale.
const BANDS = ['399 or less', '400-499', '500-599', '600-699', '700-800'];
const bandIdx = v => v == null ? -1 : v <= 399 ? 0 : v <= 499 ? 1 : v <= 599 ? 2 : v <= 699 ? 3 : 4;
const bandCounts = list => { const c = BANDS.map(() => 0); list.forEach(s => { const i = bandIdx(s.tp); if (i >= 0) c[i]++; }); return c; };
const SCHEMES = {
  three: {key: 'three', title: '3-level', groups: [[0], [1, 2, 3], [4]], levels: [
    {name: 'Needs Support', short: 'Needs Support', pts: '100-399', color: P.orange, text: '#23323f'},
    {name: 'Meets Expectations', short: 'Meets', pts: '400-699', color: P.lightBlue, text: '#23323f'},
    {name: 'Exceeds Expectations', short: 'Exceeds', pts: '700-800', color: P.greenD, text: '#fff'}]},
  five: {key: 'five', title: '5-level (preview)', groups: [[0], [1], [2], [3], [4]], levels: [
    {name: '399 or less', short: '399 or less', pts: '100-399', color: P.orange, text: '#23323f'},
    {name: '400-499', short: '400-499', pts: '400-499', color: '#FBC77A', text: '#23323f'},
    {name: '500-599', short: '500-599', pts: '500-599', color: P.lightBlue, text: '#23323f'},
    {name: '600-699', short: '600-699', pts: '600-699', color: P.blue, text: '#fff'},
    {name: '700-800', short: '700-800', pts: '700-800', color: P.greenD, text: '#fff'}]},
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
const TYPES = ['Center', 'Public School', 'Family Day Home'];
const TLABEL = {Center: 'Child care centers', 'Public School': 'Public schools', 'Family Day Home': 'Home-based child care'};
const TSHORT = {Center: 'Centers', 'Public School': 'Public schools', 'Family Day Home': 'Home-based'};   // compact labels for tables
const distName = n => `${n} Public Schools`;   // a locality's school district, e.g. "Prince William County Public Schools"
const TCOLOR = {Center: P.blue, 'Public School': '#6B7F91', 'Family Day Home': P.green};
const AGE_COLOR = {Infant: P.green, Toddler: P.orange, 'Pre-K': P.blue};
const css = n => ({'--accent': P.blue, '--meets': P.lightBlue, '--grid': P.grid, '--ink': P.ink, '--exceeds': P.greenD, '--needs': P.orange, '--mute': '#5b6b78'}[n]);
const $ = s => document.querySelector(s);
const sum = a => a.reduce((x, y) => x + y, 0);
const mean = a => a.length ? sum(a) / a.length : null;
const fmt = n => n == null ? '–' : n.toLocaleString();
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const pc = (v, n) => { if (!n) return '–'; const p = 100 * v / n; return p > 0 && p < 1 ? '<1%' : Math.round(p) + '%'; };
// groups (optional): [[label, colspan], ...] draws a spanning header row above the column headings
const table = (head, rows, numFrom = 1, groups) => `<table><thead>${groups ? `<tr class="grp">${groups.map(([l, n]) => `<th colspan="${n}">${l}</th>`).join('')}</tr>` : ''}<tr>${head.map((h, i) => `<th class="${i >= numFrom ? 'n' : ''}">${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map((c, i) => `<td class="${i >= numFrom ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
const kpis = items => items.map(([b, s]) => `<div class="kpi"><b>${b}</b><span>${s}</span></div>`).join('');
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
  $('#count').textContent = `Showing ${FILTERED.length.toLocaleString()} of ${ALL.length.toLocaleString()} sites`;
  onChange();
}

function plot(id, traces, layout = {}) {
  const base = {
    margin: {t: 10, r: 12, b: 70, l: 50}, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {family: "'Nunito Sans',system-ui,sans-serif", color: P.ink, size: 13}, legend: {orientation: 'h', y: -0.3},
    xaxis: {gridcolor: P.grid, automargin: true, zeroline: false}, yaxis: {gridcolor: P.grid, automargin: true, zeroline: false},
    hoverlabel: {font: {family: "'Nunito Sans',system-ui,sans-serif"}},
  };
  const lay = {...base, ...layout, xaxis: {...base.xaxis, ...(layout.xaxis || {})}, yaxis: {...base.yaxis, ...(layout.yaxis || {})}};
  Plotly.react(id, traces, lay, {displayModeBar: false, responsive: true});
}

// page: nav key; cb: draw function; opts.data = names of extra JSON files to load (as SUMMARY / CLASS); opts.filters=false hides filter bar
async function init(page, cb, opts = {}) {
  onChange = cb;
  document.querySelectorAll('nav a').forEach(a => a.classList.toggle('on', a.dataset.p === page));
  if (opts.summary) SUMMARY = await loadJSON('summary');
  if (opts.class) CLASS = await loadJSON('class');
  if (opts.bench) BENCH = await loadJSON('benchmarks');
  if (opts.filters === false) {
    $('#filters').remove();
    if (opts.sites) { DATA = await loadJSON('sites'); ALL = DATA.sites; }
    cb(); return;
  }
  buildFilters();
  DATA = await loadJSON('sites');
  ALL = DATA.sites;
  update();
}

const NAV = `<div class="stripe"></div><header><div class="wrap">
<div class="brand"><img src="img/ff-logo.png" alt="Foundation First – Building Early Childhood Success"><h1>VQB5 Quality Ratings Dashboard<small>Ready Region North Central · 2025-26 program year</small></h1>
<div class="logos"><img class="rr" src="img/rrnc-logo.png" alt="Ready Region North Central" style="height:52px"></div></div>
<nav><a data-p="summary" href="index.html">Summary</a><a data-p="compare" href="compare.html">Compare levels</a><a data-p="class" href="class.html">CLASS observations</a><a data-p="overview" href="ratings.html">Explore ratings</a>
<a data-p="trends" href="trends.html">Trends</a><a data-p="programs" href="programs.html">Curriculum &amp; funding</a></nav></div></header>
<div id="filters"><div class="wrap"><div class="bar"><b>Filter these charts</b><span id="count"></span></div><div class="grid-f"></div></div></div>`;
const FOOT = `<footer class="wrap">Source: <a href="https://earlychildhoodquality.doe.virginia.gov/quality-ratings/">Virginia Department of Education VQB5 Quality Rating Data</a> (2023-24 to 2025-26) and Ready Region North Central CLASS and coaching summaries. Statewide figures are aggregates shown for comparison. This is an independent visualization; VDOE's published data is the official record.</footer>`;
document.head.insertAdjacentHTML('beforeend', '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700;800&display=swap">');
document.body.insertAdjacentHTML('afterbegin', NAV);
if (scaleKey === 'five') document.querySelector('header').insertAdjacentHTML('afterend', '<div class="preview-banner"><div class="wrap">Preview: the coming 5-level rating scale, shown as 100-point bands. the official level names from VDOE are pending. <a href="?scale=3">Back to the current 3-level view</a></div></div>');
document.body.insertAdjacentHTML('beforeend', FOOT);
