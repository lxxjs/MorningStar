"""Export scraped fund data to Excel."""

import logging

import pandas as pd

log = logging.getLogger(__name__)


def save_to_excel(results: dict, path: str = "morningstar_scraped.xlsx"):
    sheets = {
        "Quote": _build_quote_df(results),
        "Performance Annual": _build_perf_df(results, "annual"),
        "Performance Trailing": _build_perf_df(results, "trailing"),
        "Holdings": _build_holdings_df(results),
    }

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            _coerce_numeric(df).to_excel(writer, sheet_name=name, index=False)

    log.info("Saved to %s", path)


def _build_quote_df(results: dict) -> pd.DataFrame:
    return pd.DataFrame([
        {"ISIN": isin, **data["quote"]}
        for isin, data in results.items() if data is not None
    ])


def _build_perf_df(results: dict, key: str) -> pd.DataFrame:
    rows = []
    for isin, data in results.items():
        if data is None:
            continue
        for label, cols in data["performance"][key].items():
            rows.append({"ISIN": isin, "": label, **cols})
    return pd.DataFrame(rows)


def _build_holdings_df(results: dict) -> pd.DataFrame:
    return pd.DataFrame([
        {"ISIN": isin, **holding}
        for isin, data in results.items() if data is not None
        for holding in data["holdings"]
    ])


def _coerce_numeric(df: pd.DataFrame, skip_cols: tuple = ("ISIN", "")) -> pd.DataFrame:
    for col in df.columns:
        if col in skip_cols:
            continue
        cleaned = (
            df[col].astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("\u2212", "-", regex=False)
            .str.strip()
        )
        numeric = pd.to_numeric(cleaned, errors="coerce")
        df[col] = numeric.where(numeric.notna(), df[col])
    return df
