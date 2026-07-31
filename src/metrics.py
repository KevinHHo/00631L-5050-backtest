"""Performance metrics computed from a portfolio NAV (net asset value) series."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def cagr(nav: pd.Series) -> float:
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return (nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1


def drawdown_series(nav: pd.Series) -> pd.Series:
    running_max = nav.cummax()
    return nav / running_max - 1


def max_drawdown(nav: pd.Series) -> float:
    return drawdown_series(nav).min()


def annualized_vol(nav: pd.Series) -> float:
    daily_returns = nav.pct_change().dropna()
    return daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def sharpe_ratio(nav: pd.Series, risk_free_annual: float = 0.0) -> float:
    vol = annualized_vol(nav)
    if vol == 0:
        return float("nan")
    return (cagr(nav) - risk_free_annual) / vol


def calmar_ratio(nav: pd.Series) -> float:
    mdd = max_drawdown(nav)
    if mdd == 0:
        return float("nan")
    return cagr(nav) / abs(mdd)


def summarize(nav: pd.Series, risk_free_annual: float = 0.0) -> dict:
    return {
        "CAGR": cagr(nav),
        "MDD": max_drawdown(nav),
        "年化波動度": annualized_vol(nav),
        "Sharpe": sharpe_ratio(nav, risk_free_annual),
        "Calmar": calmar_ratio(nav),
        "期末淨值(起始=1)": nav.iloc[-1],
    }
