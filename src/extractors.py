"""Page-level data extractors for Morningstar fund pages."""

import logging

log = logging.getLogger(__name__)

QUOTE_SELECTOR = "ul.quote__data__mdc li.quote__item__mdc"
PERF_TABLE_SELECTOR = "table.mds-table__sal"
HOLDINGS_TABLE_SELECTOR = "table.mds-table--fixed-column__sal"


async def extract_quote(page, url):
    await page.goto(f"{url}/quote", wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_selector(QUOTE_SELECTOR, timeout=50_000)

    return await page.evaluate("""() => {
        const result = {};
        document.querySelectorAll('ul.quote__data__mdc li.quote__item__mdc').forEach(item => {
            const labelEl = item.querySelector('.quote__label__mdc');
            if (!labelEl) return;
            const label = labelEl.innerText.trim().split('\\n')[0];
            const values = Array.from(item.querySelectorAll('.quote__value__mdc, .mdc-locked-text__mdc'))
                .filter(el => !el.querySelector('.quote__value__mdc, .mdc-locked-text__mdc'))
                .map(el => el.innerText.trim().replace(/\\u00a0/g, ' ').replace(/\\u2212/g, '-'))
                .filter(v => v);
            if (!values.length) return;
            result[label] = values.join(' / ');
        });
        return result;
    }""")


async def extract_performance(page, url):
    await page.goto(f"{url}/performance", wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_load_state("networkidle", timeout=50_000)

    tables = await page.locator(PERF_TABLE_SELECTOR).all()
    annual = await _parse_table(tables[0])
    trailing = await _parse_table(tables[1]) if len(tables) >= 2 else {}

    return {"annual": annual, "trailing": trailing}


async def extract_holdings(page, url):
    await page.goto(f"{url}/portfolio", wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_selector(HOLDINGS_TABLE_SELECTOR, timeout=50_000)

    table = page.locator(HOLDINGS_TABLE_SELECTOR).first
    headers = await _extract_headers(table)
    all_holdings = []

    while True:
        rows = await _extract_holding_rows(table, headers)
        all_holdings.extend(rows)

        next_btn = page.locator("button[aria-label='Next']").first
        if await next_btn.count() == 0 or await next_btn.get_attribute("disabled") is not None:
            break

        await next_btn.evaluate("el => el.click()")
        try:
            await page.wait_for_load_state("networkidle", timeout=3_000)
        except Exception:
            await page.wait_for_timeout(500)

    return all_holdings


async def _parse_table(table):
    return await table.evaluate("""table => {
        const headers = [];
        table.querySelectorAll('thead th.mds-th__sal').forEach(th => {
            const text = th.innerText.trim();
            if (text) headers.push(text);
        });

        const result = {};
        table.querySelectorAll('tbody tr.mds-tr__sal').forEach(row => {
            const rowHeaderTd = row.querySelector('td.row-header');
            const rowKey = rowHeaderTd
                ? rowHeaderTd.innerText.trim()
                : (row.querySelector('th')?.innerText.trim() ?? '');

            const cells = rowHeaderTd
                ? row.querySelectorAll('td.mds-td__sal:not(.row-header)')
                : row.querySelectorAll('td.mds-td__sal');

            const rowValues = {};
            Array.from(cells).forEach((cell, i) => {
                if (i >= headers.length) return;
                const srOnly = cell.querySelector('.sr-only');
                rowValues[headers[i]] = srOnly
                    ? srOnly.innerText.replace('Quartile Rank is', '').trim()
                    : cell.innerText.trim();
            });

            if (rowKey) result[rowKey] = rowValues;
        });

        return result;
    }""")


async def _extract_headers(table):
    return await table.evaluate("""table => {
        return Array.from(table.querySelectorAll('thead th.mds-th__sal')).map(th => {
            const span = th.querySelector('.mds-th__text__sal');
            if (!span) return th.innerText.trim();
            const clone = span.cloneNode(true);
            clone.querySelectorAll('.sal-tooltiptext, .sal-component-chiclet').forEach(n => n.remove());
            return clone.innerText.trim().split('\\n')[0].trim();
        });
    }""")


async def _extract_holding_rows(table, headers):
    return await table.evaluate("""(table, headers) => {
        const rows = [];
        table.querySelectorAll('tbody tr.mds-tr__sal').forEach(row => {
            const rowData = {};

            const nameTh = row.querySelector("th[scope='row']");
            if (nameTh) {
                const nameLink = nameTh.querySelector('a');
                rowData[headers[0]] = (nameLink ?? nameTh).innerText.trim();
            }

            Array.from(row.querySelectorAll('td.mds-td__sal')).forEach((cell, i) => {
                const colIdx = i + 1;
                if (colIdx >= headers.length) return;

                const esg = cell.querySelector('.ip-sustainability[rating]');
                if (esg) {
                    const rating = esg.getAttribute('rating');
                    rowData[headers[colIdx]] = rating ? rating + '/5' : '\u2014';
                } else {
                    const lines = cell.innerText.trim().split('\\n').map(l => l.trim()).filter(l => l);
                    const isDecrease = lines.includes('% Decrease');
                    const filtered = lines.filter(l => l !== '% Increase' && l !== '% Decrease');
                    rowData[headers[colIdx]] = filtered.length ? (isDecrease ? '-' + filtered.join(' ') : filtered.join(' ')) : '\u2014';
                }
            });

            if (Object.keys(rowData).length > 0) rows.push(rowData);
        });
        return rows;
    }""", headers)
