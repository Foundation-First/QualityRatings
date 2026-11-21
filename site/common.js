// Shared data loading, filter bar and chart helpers for all pages.
const RATINGS = ['Needs Support', 'Meets Expectations', 'Exceeds Expectations'];
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const rcolor = r => css({'Needs Support': '--needs', 'Meets Expectations': '--meets', 'Exceeds Expectations': '--exceeds'}[r]);
const $ = s => document.querySelector(s);
const sum = a => a.reduce((x, y) => x + y, 0);
const mean = a => a.length ? sum(a) / a.length : null;
const fmt = n => n == null ? '–' : n.toLocaleString();
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
let state = {};
try { state = JSON.parse(sessionStorage.getItem('vqb5f') || '{}'); } catch (e) {}
let DATA, ALL, FILTERED = [], onChange = () => {};

const FILTERS = [
  ['region', 'Ready Region', s => [s.region]],
  ['county', 'Locality', s => [s.county]],
  ['type', 'Site type', s => [s.type]],
  ['rating', 'Quality rating', s => [s.rating]],
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
  const box = $('#filters .wrap');
  box.innerHTML = '<label>Search name / address<input type="search" id="f-q" placeholder="e.g. Little Stars, 23219"></label>';
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
    if (k === 'rating') keys = RATINGS.filter(r => counts[r]);
    const sel = $('#f-' + k);
    sel.innerHTML = '<option value="">All</option>' + keys.map(v => `<option value="${esc(v)}">${esc(v)} (${counts[v]})</option>`).join('');
    sel.value = state[k] || '';
  }
}

function update() {
  refreshOptions();
  FILTERED = ALL.filter(s => match(s));
  try { sessionStorage.setItem('vqb5f', JSON.stringify(state)); } catch (e) {}
  $('#count').textContent = `${FILTERED.length.toLocaleString()} of ${ALL.length.toLocaleString()} sites`;
  onChange();
}

function plot(id, traces, layout = {}) {
  const base = {
    margin: {t: 10, r: 10, b: 40, l: 50}, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {color: css('--ink'), size: 12}, legend: {orientation: 'h', y: -0.2},
    xaxis: {gridcolor: css('--grid'), automargin: true}, yaxis: {gridcolor: css('--grid'), automargin: true},
  };
  const lay = {...base, ...layout, xaxis: {...base.xaxis, ...(layout.xaxis || {})}, yaxis: {...base.yaxis, ...(layout.yaxis || {})}};
  Plotly.react(id, traces, lay, {displayModeBar: false, responsive: true});
}

async function init(page, cb) {
  onChange = cb;
  document.querySelectorAll('nav a').forEach(a => a.classList.toggle('on', a.dataset.p === page));
  buildFilters();
  DATA = await (await fetch('data/sites.json')).json();
  ALL = DATA.sites;
  update();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', update);
}

const NAV = `<header><div class="wrap"><h1>Virginia VQB5 Quality Ratings Explorer</h1><nav>
<a data-p="overview" href="index.html">Overview</a><a data-p="trends" href="trends.html">Trends</a>
<a data-p="programs" href="programs.html">Curriculum &amp; funding</a><a data-p="sites" href="sites.html">Site finder</a></nav>
<span id="count" class="note"></span></div></header><div id="filters"><div class="wrap"></div></div>`;
const FOOT = `<footer class="wrap">Data: <a href="https://earlychildhoodquality.doe.virginia.gov/quality-ratings/">Virginia Department of Education, VQB5 Quality Rating Data 2025-2026</a>
(includes 2024-25 and 2023-24 results for continuing sites). This is an independent visualization, not affiliated with VDOE; check the VDOE site for official data.</footer>`;
document.body.insertAdjacentHTML('afterbegin', NAV);
document.body.insertAdjacentHTML('beforeend', FOOT);
