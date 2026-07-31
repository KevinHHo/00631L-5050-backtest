"""Decompose a real leveraged ETF's return into decay, fees, and everything else.

A 2x leveraged ETF's realized return differs from "2x the underlying's return"
for two independent reasons:
  1. Volatility decay: daily rebalancing to a constant leverage ratio means the
     fund compounds leveraged DAILY returns, which is mathematically worse than
     doubling the total-period return whenever the underlying is volatile. This
     happens even with zero fees and a perfectly efficient futures market.
  2. Fees and real-world tracking effects: management/custody fees, financing
     cost, and how well the fund's futures/swap rolling captures (or fails to
     capture) any dividend-driven futures backwardation.

This module isolates (1) from (2) by building synthetic, daily-compounded
leveraged NAV series from the underlying's actual daily returns, so they can be
compared against the real fund's actual NAV series.
"""
from __future__ import annotations

import pandas as pd

from . import metrics


def simulate_leveraged_from_returns(
    base_nav: pd.Series, leverage: float, annual_cost: float = 0.0
) -> pd.Series:
    """Compound `leverage`x the daily returns of `base_nav`, minus a constant
    daily cost drag. Starts at 1.0 on `base_nav`'s first date.

    Volatility decay isn't modeled separately -- it falls out naturally from
    compounding leveraged daily returns, the same way a real leveraged ETF's
    daily rebalancing does.
    """
    daily_returns = base_nav.pct_change().dropna()
    daily_cost = annual_cost / 252
    leveraged_returns = leverage * daily_returns - daily_cost
    compounded = (1 + leveraged_returns).cumprod()
    day_zero = pd.Series([1.0], index=[base_nav.index[0]])
    return pd.concat([day_zero, compounded])


def naive_leveraged_cagr(base_nav: pd.Series, leverage: float) -> float:
    """The (intuitive but wrong) shortcut of raising total return to the power
    of the leverage factor -- ignores path dependency / volatility decay
    entirely. Kept only as a reference point for how much decay actually costs.
    """
    base_cagr = metrics.cagr(base_nav)
    return (1 + base_cagr) ** leverage - 1


def tracking_difference_table(
    base_nav: pd.Series,
    actual_leveraged_nav: pd.Series,
    leverage: float,
    annual_cost: float,
    risk_free_annual: float = 0.0,
) -> pd.DataFrame:
    """Compare four views of "N-times leveraged" performance over the same
    period, to isolate how much of the gap between naive expectations and
    reality is decay vs fees vs other real-world tracking effects:

    1. Naive one-shot N-times CAGR (ignores decay entirely)
    2. Synthetic daily-compounded N-times, no fees (decay only)
    3. Synthetic daily-compounded N-times, with `annual_cost` (decay + fees)
    4. The real fund's actual NAV (decay + fees + real-world tracking effects,
       e.g. futures basis/backwardation capture)
    """
    clean_synthetic = simulate_leveraged_from_returns(base_nav, leverage, annual_cost=0.0)
    cost_synthetic = simulate_leveraged_from_returns(base_nav, leverage, annual_cost=annual_cost)

    blank_row = {
        "CAGR": naive_leveraged_cagr(base_nav, leverage),
        "MDD": float("nan"),
        "年化波動度": float("nan"),
        "Sharpe": float("nan"),
        "Calmar": float("nan"),
        "期末淨值(起始=1)": float("nan"),
    }

    rows = {
        f"理論上一次性{leverage:g}倍（忽略波動耗損，僅供對照）": blank_row,
        f"合成每日複利{leverage:g}倍（含波動耗損，無費用）": metrics.summarize(clean_synthetic, risk_free_annual),
        f"合成每日複利{leverage:g}倍（含波動耗損+{annual_cost * 100:.2f}%年費）": metrics.summarize(
            cost_synthetic, risk_free_annual
        ),
        "正2 ETF 實際表現": metrics.summarize(actual_leveraged_nav, risk_free_annual),
    }
    return pd.DataFrame(rows).T
