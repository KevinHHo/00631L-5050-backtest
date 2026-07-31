"""Slice a NAV series into named historical stress windows and summarize each.

Used to check whether a strategy's behavior (e.g. "50:50 lowers MDD") still
holds inside specific historical crashes, not just over a full backtest period
that happens to be dominated by a bull market.
"""
from __future__ import annotations

import pandas as pd

from . import metrics


def slice_and_rebase(nav: pd.Series, start: str, end: str) -> pd.Series:
    """Slice `nav` to [start, end] and rebase it so the window's first value is 1.0."""
    window = nav.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    if window.empty:
        raise RuntimeError(f"NAV 序列在 {start}~{end} 沒有資料，請確認回測區間有涵蓋這個窗口。")
    return window / window.iloc[0]


def window_summary(nav: pd.Series, start: str, end: str) -> dict:
    rebased = slice_and_rebase(nav, start, end)
    return {
        "區間報酬": rebased.iloc[-1] - 1,
        "區間MDD": metrics.max_drawdown(rebased),
    }


def build_window_table(navs: dict[str, pd.Series], windows: list[dict]) -> pd.DataFrame:
    """One row per strategy, one 報酬/MDD column pair per stress window."""
    rows = {}
    for name, nav in navs.items():
        row = {}
        for w in windows:
            summary = window_summary(nav, w["start"], w["end"])
            row[f"{w['name']}｜區間報酬"] = summary["區間報酬"]
            row[f"{w['name']}｜區間MDD"] = summary["區間MDD"]
        rows[name] = row
    return pd.DataFrame(rows).T
