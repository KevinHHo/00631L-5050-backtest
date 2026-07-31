"""Fetch and cache historical ETF prices from Yahoo Finance."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import yfinance as yf


def _cache_path(cache_dir: Path, ticker: str) -> Path:
    return cache_dir / f"{ticker.replace('.', '_')}.csv"


def fetch(
    ticker: str,
    start: str,
    end: str | None,
    cache_dir: Path,
    refresh: bool = False,
) -> pd.Series:
    """Return a daily adjusted-close price series for `ticker`, indexed by date.

    Uses a local CSV cache under `cache_dir` to avoid re-downloading on every run.
    If the ticker's real listing date is later than `start`, the returned series
    simply begins at whatever date data is actually available.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, ticker)

    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) if end else pd.Timestamp(dt.date.today())

    if not refresh and path.exists():
        cached = pd.read_csv(path, index_col=0, parse_dates=True)["close"]
        if (
            not cached.empty
            and cached.index.min() <= start_ts
            and cached.index.max() >= end_ts - pd.Timedelta(days=5)
        ):
            return cached.loc[start_ts:end_ts]

    data = yf.download(
        ticker,
        start=start_ts.strftime("%Y-%m-%d"),
        end=(end_ts + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
    )
    if data.empty:
        raise RuntimeError(
            f"抓不到 {ticker} 的資料，請確認 ticker 代號與日期區間是否正確。"
        )
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    series = data["Close"].rename("close")
    series.to_frame().to_csv(path)
    return series.loc[start_ts:end_ts]


def synthetic_cash(index: pd.DatetimeIndex, annual_rate: float) -> pd.Series:
    """Build a synthetic 'cash' price series compounding daily at `annual_rate`."""
    days_elapsed = (index - index[0]).days
    values = (1.0 + annual_rate) ** (days_elapsed / 365.25)
    return pd.Series(values, index=index, name="cash")


def aligned_prices(price_series: dict[str, pd.Series]) -> pd.DataFrame:
    """Inner-join a set of price series onto their common trading dates."""
    df = pd.concat(price_series, axis=1, join="inner").sort_index()
    if df.empty:
        raise RuntimeError("所有標的沒有共同的交易日區間，請檢查 ticker 或日期設定。")
    return df
