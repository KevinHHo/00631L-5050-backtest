"""Portfolio construction with configurable target weights and rebalancing."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RebalanceRule:
    name: str
    kind: str  # "none" | "calendar" | "threshold"
    freq: str | None = None   # "M" / "Q" / "Y" when kind == "calendar"
    band: float | None = None  # e.g. 0.10 when kind == "threshold"


def _calendar_rebalance_dates(index: pd.DatetimeIndex, freq: str) -> set:
    periods = index.to_series().dt.to_period(freq)
    period_changed = periods.ne(periods.shift(1))
    dates = index[period_changed]
    return set(dates[1:])  # skip day 0, it's already at target weights


def simulate(
    prices: pd.DataFrame,
    weights: dict[str, float],
    rule: RebalanceRule,
    cost_bps: float = 0.0,
) -> pd.Series:
    """Simulate a portfolio's NAV series given asset prices, target weights, and a rebalance rule.

    `prices` columns must be a superset of `weights` keys, aligned on a common date index.
    Returns a NAV series starting at 1.0.
    """
    assets = list(weights.keys())
    px = prices[assets]
    idx = px.index

    calendar_dates: set = set()
    if rule.kind == "calendar" and rule.freq:
        calendar_dates = _calendar_rebalance_dates(idx, rule.freq)

    nav = pd.Series(index=idx, dtype=float)
    nav.iloc[0] = 1.0
    shares = {a: weights[a] / px[a].iloc[0] for a in assets}

    for i in range(1, len(idx)):
        date = idx[i]
        values = {a: shares[a] * px[a].iloc[i] for a in assets}
        total = sum(values.values())

        triggered = False
        if rule.kind == "calendar":
            triggered = date in calendar_dates
        elif rule.kind == "threshold" and rule.band is not None:
            drift = max(abs(values[a] / total - weights[a]) for a in assets)
            triggered = drift > rule.band

        if triggered:
            target_values = {a: total * weights[a] for a in assets}
            turnover = sum(abs(target_values[a] - values[a]) for a in assets) / 2
            total -= turnover * (cost_bps / 10_000)
            shares = {a: (total * weights[a]) / px[a].iloc[i] for a in assets}

        nav.iloc[i] = total

    return nav
