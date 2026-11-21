# VQB5 Quality Ratings Explorer

Filterable charts built from the Virginia Department of Education's public
[VQB5 Quality Rating Data](https://earlychildhoodquality.doe.virginia.gov/quality-ratings/).

- `site/` – the static website (publish this folder). Pages: Overview, Trends, Curriculum & funding, Site finder.
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
