"""Morningstar fund scraper — entry point."""

import asyncio
import logging
from pathlib import Path

from src.scraper import scrape_all
from src.export import save_to_excel

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

ISINS = [
    "IE0004896431",
    "LU0346389348",
    "LU0053666078",
    "LU0028119013",
    "LU0224105477",
    "LU0370789561",
    "LU0114722902",
    "LU0346392995",
]


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    results = asyncio.run(scrape_all(ISINS))
    save_to_excel(results, path=str(OUTPUT_DIR / "morningstar_scraped.xlsx"))


if __name__ == "__main__":
    main()
