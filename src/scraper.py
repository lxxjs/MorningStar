"""Browser orchestration: launches Playwright, manages concurrency, scrapes funds."""

import asyncio
import logging
import time

from playwright.async_api import async_playwright

from src.extractors import extract_quote, extract_performance, extract_holdings

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
HIDE_WEBDRIVER_SCRIPT = (
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
)
BASE_URL = "https://www.morningstar.com/funds/_"


async def scrape_all(isins: list[str], max_concurrent: int = 8) -> dict:
    results: dict[str, dict | None] = {}
    total = len(isins)
    sem = asyncio.Semaphore(max_concurrent)
    done_count = 0
    wall_start = time.perf_counter()

    async def worker(isin):
        nonlocal done_count
        async with sem:
            log.info("Scraping %s ...", isin)
            try:
                t0 = time.perf_counter()
                data = await _scrape_one(context, isin)
                elapsed = time.perf_counter() - t0
                results[isin] = data
                done_count += 1
                log.info(
                    "[%d/%d] Done %s — %d holdings (%.1fs)",
                    done_count, total, isin, len(data["holdings"]), elapsed,
                )
            except Exception as e:
                done_count += 1
                log.error("[%d/%d] Failed %s: %s", done_count, total, isin, e)
                results[isin] = None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        await context.add_init_script(HIDE_WEBDRIVER_SCRIPT)

        log.info("Launching %d concurrent workers", max_concurrent)

        await asyncio.gather(*(worker(isin) for isin in isins))
        await browser.close()

    wall_elapsed = time.perf_counter() - wall_start
    succeeded = sum(1 for v in results.values() if v is not None)
    avg = wall_elapsed / succeeded if succeeded else 0
    log.info(
        "Total wall time: %.1fs | %d/%d funds succeeded | avg %.1fs/fund",
        wall_elapsed, succeeded, total, avg,
    )

    return results


async def _scrape_one(context, isin: str) -> dict:
    url = f"{BASE_URL}/{isin}"
    pages = [await context.new_page() for _ in range(3)]
    try:
        quote, performance, holdings = await asyncio.gather(
            extract_quote(pages[0], url),
            extract_performance(pages[1], url),
            extract_holdings(pages[2], url),
        )
    finally:
        for pg in pages:
            await pg.close()

    return {"quote": quote, "performance": performance, "holdings": holdings}

