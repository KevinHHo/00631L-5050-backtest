"""Load config.yaml, run every baseline / 50:50 x rebalance-rule combination."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from . import data_fetcher, metrics, portfolio


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_rebalance_rules(cfg: dict) -> dict[str, portfolio.RebalanceRule]:
    rules = {}
    for r in cfg["rebalance_rules"]:
        rules[r["name"]] = portfolio.RebalanceRule(
            name=r["name"],
            kind=r["type"],
            freq=r.get("freq"),
            band=r.get("band"),
        )
    return rules


def run(cfg: dict) -> tuple[dict[str, pd.Series], pd.DataFrame, dict]:
    """Run every strategy in `cfg` and return (nav_series_by_label, results_table, groups).

    `groups` maps back to the config structure so callers (e.g. the CLI) can decide
    how to group strategies into charts without re-parsing label strings:
        groups = {"baselines": [...names...], "pairs": {pair_name: [combo_label, ...]}}
    """
    data_cfg = cfg["data"]
    cache_dir = Path(data_cfg.get("cache_dir", "data/cache"))
    refresh = bool(data_cfg.get("refresh", False))
    start = data_cfg["start"]
    end = data_cfg.get("end")

    assets_cfg = cfg["assets"]
    raw_prices = {
        key: data_fetcher.fetch(ticker, start, end, cache_dir, refresh)
        for key, ticker in assets_cfg.items()
    }
    prices = data_fetcher.aligned_prices(raw_prices)

    risk_free = float(cfg.get("risk_free_annual_rate", 0.0))
    prices["cash"] = data_fetcher.synthetic_cash(prices.index, risk_free)

    rules = build_rebalance_rules(cfg)
    cost_bps = float(cfg.get("transaction_cost_bps", 0.0))
    none_rule = portfolio.RebalanceRule(name="single_asset", kind="none")

    navs: dict[str, pd.Series] = {}
    groups: dict = {"baselines": [], "pairs": {}}

    for b in cfg["strategies"]["baselines"]:
        navs[b["name"]] = portfolio.simulate(prices, b["weights"], none_rule, cost_bps)
        groups["baselines"].append(b["name"])

    for pair in cfg["strategies"]["pairs"]:
        leg_a, leg_b = pair["legs"]
        weights = {leg_a: 0.5, leg_b: 0.5}
        labels = []
        for rule_name, rule in rules.items():
            label = f"{pair['name']}｜{rule_name}"
            navs[label] = portfolio.simulate(prices, weights, rule, cost_bps)
            labels.append(label)
        groups["pairs"][pair["name"]] = labels

    results = pd.DataFrame(
        {name: metrics.summarize(nav, risk_free) for name, nav in navs.items()}
    ).T

    return navs, results, groups
