# MorningStar Fund Scraper

Scrapes fund data (quotes, performance, and holdings) from Morningstar using Playwright and exports the results to an Excel workbook.

## Project Structure

```
MorningStar/
├── run.py              # Entry point — run this from the project root
├── output/             # Generated Excel files go here
│   └── morningstar_scraped.xlsx
└── src/
    ├── __init__.py
    ├── main.py         # Configuration (ISIN list, logging, output path)
    ├── scraper.py      # Browser orchestration and concurrency control
    ├── extractors.py   # Page-level data extraction (quote, performance, holdings)
    └── export.py       # DataFrame construction and Excel export
```

## Requirements

- Python 3.10+
- [Playwright](https://playwright.dev/python/) (Chromium)
- pandas
- openpyxl

### Install

```bash
pip install playwright pandas openpyxl
playwright install chromium
```

## Usage

```bash
python run.py
```

The scraper will:

1. Launch a Chromium browser
2. Scrape all configured ISINs concurrently (default: 8 workers, 3 pages per fund)
3. Save results to `output/morningstar_scraped.xlsx`

### Configure

Edit the `ISINS` list in `src/main.py` to change which funds are scraped. Adjust `max_concurrent` in `scrape_all()` to control parallelism.

## Output

The Excel file contains four sheets:

| Sheet | Contents |
|---|---|
| Quote | Key fund metrics (NAV, expense ratio, etc.) |
| Performance Annual | Year-by-year returns |
| Performance Trailing | Trailing period returns (1M, 3M, YTD, etc.) |
| Holdings | Individual fund holdings with weights |
