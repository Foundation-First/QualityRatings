# VQB5 Quality Ratings Explorer – Ready Region 8 North Central

Filterable charts built from the Virginia Department of Education's public
[VQB5 Quality Rating Data](https://earlychildhoodquality.doe.virginia.gov/quality-ratings/).

- `site/` – the static website (publish this folder). Pages (answer-first, for busy readers): Home (headline numbers + question menu), My locality (pick a place, read one sentence), Over time (same sites across years, with a program-type switch), Program types (+ Honor Roll), CLASS (essentials first, detail collapsed), and Compare (site → district → region → state lookup, linked from My locality). About & definitions holds the glossary. Old URLs (`ratings`, `trends`, `programs`, `explore`) redirect to the nearest new page.
  Only Ready Region 8 site records are published; statewide data appears only as aggregates (`summary.json`) for comparison.
- `scripts/class_data.py` – CLASS/coaching figures transcribed from the regional handouts and VDOE's external CLASS report (not in the workbooks). Edit and re-run when new handouts come out.
- `scripts/build_data.py` – cleans `raw/*.xlsx` into `site/data/sites.json`.
- `raw/` – downloaded VDOE workbooks (git-ignored; re-download from the VDOE page).

## Refresh the data
1. Download the new workbook(s) from the VDOE page into `raw/` and update the file names in `scripts/build_data.py`.
2. `pip install pandas openpyxl` then `python scripts/build_data.py`.
3. Check `site/data/sites.json` changed, then commit and push.

## Preview locally
`cd site && python -m http.server 8000` and open http://localhost:8000 (needed because the pages fetch the JSON).

## Publish on GitHub Pages
A workflow in `.github/workflows/pages.yml` deploys `site/` on every push to `main`.
One-time setup: repo Settings → Pages → Source: **GitHub Actions**.

## Rating scales
Every chart reads from one rating scale defined in `site/common.js` (`SCHEMES`). The current 3-level scale (Needs Support / Meets / Exceeds) is the default.
The coming 5-level scale is built on 100-point bands, so it is already available as a preview: add `?scale=5` to any page URL
(`?scale=3` switches back). Its levels are labelled by point band until VDOE's official level names are confirmed; update the names in `SCHEMES.five`.

## Colour rules (keep these when adding charts)
One meaning per colour, defined in `site/common.js`: green = RRNC, grey = Virginia, orange -> light blue -> blue = rating levels (low -> high),
tan / slate / brown = site types, dark / light green = emphasis within RRNC data. Chart colours come from `P`, `LEVELS` and `TCOLOR`; the colour key on
`about.html` is built from the same objects. Rankings use dot plots (no truncated bars).

## Refreshing
`python scripts/build_data.py` rebuilds `site/data/*.json` (including `meta.json`, which drives the "data last refreshed" line in the footer).

## Look
The visual system follows VDOE's Fall 2026 Data Deep Dive deck (kept in `raw/inspo/deepdive`, git-ignored): navy title band with a light-weight white title, a bold grey takeaway sentence, one exhibit on white, navy-header tables with an orange RRNC header and a sky-blue Average column, peach stat cells, thick-line charts with bold direct labels, dumbbell charts with round markers, and the dark-blue Foundation First banner with the four-colour top stripe.
Palette and rating-level colours are defined once in `site/common.js` (`P`, `SCHEMES`): RRNC orange, Virginia navy/dark grey, Needs Support amber, Approaching orange, Meets teal, Exceeds blue, Distinguished navy.
Text is 16px or larger everywhere (charts included). Calibri is used where installed, with Carlito (metric-compatible) as the web fallback.

## Rating levels
`?scale=5` on any page shows 2025-26 scores in VDOE's new five levels (official names from the deck); `?scale=3` returns to the three-level view.
