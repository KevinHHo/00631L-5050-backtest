"""CLI: stress-test a synthetic 2x-leveraged Taiwan-index product across
historical bear markets that 00631L itself never lived through.

00631L only started trading on 2014-10-31, so there's no real price history
for it during the 2000 dot-com bust or the 2008 financial crisis. This script
builds a synthetic leveraged product from ^TWII (台灣加權指數) daily returns
instead -- going back to 1997 -- and runs it through the same 50:50
rebalancing engine as main.py, to check whether the "50:50 lowers MDD"
finding from main.py's bull-market backtest still holds in real crashes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src import backtest, data_fetcher, leverage_analysis, metrics, portfolio, report, stress_test

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="模擬正2在歷史空頭市場的表現")
    parser.add_argument("--config", default="bear_market_config.yaml", help="設定檔路徑")
    parser.add_argument("--output", default="output/bear_market", help="輸出資料夾")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = backtest.load_config(args.config)

    data_cfg = cfg["data"]
    cache_dir = Path(data_cfg.get("cache_dir", "data/cache"))
    index_prices = data_fetcher.fetch(
        data_cfg["index_ticker"],
        data_cfg["start"],
        data_cfg.get("end"),
        cache_dir,
        bool(data_cfg.get("refresh", False)),
    )
    index_nav = (index_prices / index_prices.iloc[0]).rename("index")

    leverage = float(cfg.get("leverage", 2.0))
    annual_cost = float(cfg.get("annual_cost", 0.0))
    leveraged_nav = leverage_analysis.simulate_leveraged_from_returns(index_nav, leverage, annual_cost)

    prices = pd.concat({"index": index_nav, "leveraged": leveraged_nav}, axis=1).dropna()

    rules = backtest.build_rebalance_rules(cfg)
    none_rule = portfolio.RebalanceRule(name="single_asset", kind="none")

    navs: dict[str, pd.Series] = {}
    navs[f"模擬正{leverage:g} 單押"] = portfolio.simulate(prices, {"leveraged": 1.0}, none_rule)
    navs["指數本身 單押"] = portfolio.simulate(prices, {"index": 1.0}, none_rule)

    pair_labels = []
    for rule_name, rule in rules.items():
        label = f"模擬正{leverage:g} + 指數｜{rule_name}"
        navs[label] = portfolio.simulate(prices, {"leveraged": 0.5, "index": 0.5}, rule)
        pair_labels.append(label)

    results = pd.DataFrame({name: metrics.summarize(nav) for name, nav in navs.items()}).T
    results_sorted = results.sort_values("Calmar", ascending=False)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_sorted.to_csv(output_dir / "results.csv", encoding="utf-8-sig")
    formatted = report.format_results_table(results_sorted)
    (output_dir / "results.md").write_text(formatted.to_markdown(), encoding="utf-8")
    print(f"=== 全期間（{index_nav.index[0].date()} ~ {index_nav.index[-1].date()}）===")
    print(formatted.to_string())

    report.plot_equity_curves(navs, "全期間：模擬正2 vs 50:50（含歷史空頭）", output_dir / "full_period_equity.png")
    report.plot_drawdowns(navs, "全期間：回撤比較", output_dir / "full_period_drawdown.png")

    windows = cfg["stress_windows"]
    window_table = stress_test.build_window_table(navs, windows)
    window_table.to_csv(output_dir / "stress_windows.csv", encoding="utf-8-sig")
    window_formatted = report.format_percent_table(window_table)
    (output_dir / "stress_windows.md").write_text(window_formatted.to_markdown(), encoding="utf-8")
    print("\n=== 各歷史空頭區間表現 ===")
    print(window_formatted.to_string())

    for w in windows:
        window_navs = {name: stress_test.slice_and_rebase(nav, w["start"], w["end"]) for name, nav in navs.items()}
        safe_name = w["name"].replace(" ", "_")
        report.plot_equity_curves(
            window_navs, f"{w['name']}：模擬正2 vs 50:50", output_dir / f"window_{safe_name}_equity.png"
        )
        report.plot_drawdowns(
            window_navs, f"{w['name']}：回撤比較", output_dir / f"window_{safe_name}_drawdown.png"
        )

    print(f"\n圖表與報表已輸出至：{output_dir.resolve()}")


if __name__ == "__main__":
    main()
