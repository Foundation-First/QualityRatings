# VQB5 Quality Ratings Explorer – Ready Region 8 North Central

Filterable charts built from the Virginia Department of Education's public
[VQB5 Quality Rating Data](https://earlychildhoodquality.doe.virginia.gov/quality-ratings/).

- `site/` – the static website (publish this folder). Pages: Summary, Compare levels (site → district → region → state), CLASS observations, Explore ratings, Trends, Curriculum & funding, Find a site.
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
