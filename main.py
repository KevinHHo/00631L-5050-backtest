"""CLI entry point: run the 00631L 50:50 backtest and produce charts + tables."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src import backtest, leverage_analysis, report

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="00631L 與正2 ETF 50:50 回測")
    parser.add_argument("--config", default="config.yaml", help="設定檔路徑")
    parser.add_argument("--output", default="output", help="輸出資料夾")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = backtest.load_config(args.config)
    navs, results, groups = backtest.run(cfg)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_sorted = results.sort_values("Calmar", ascending=False)
    results_sorted.to_csv(output_dir / "results.csv", encoding="utf-8-sig")

    formatted = report.format_results_table(results_sorted)
    (output_dir / "results.md").write_text(formatted.to_markdown(), encoding="utf-8")
    print(formatted.to_string())

    baseline_navs = {name: navs[name] for name in groups["baselines"]}

    # 總覽圖：每個 baseline + 每組配對表現最好（Calmar 最高）的再平衡規則
    best_per_pair = {}
    for pair_name, labels in groups["pairs"].items():
        best_label = results.loc[labels, "Calmar"].idxmax()
        best_per_pair[best_label] = navs[best_label]

    overview_navs = {**baseline_navs, **best_per_pair}
    report.plot_equity_curves(
        overview_navs, "總覽：基準 vs 各配對最佳再平衡組合", output_dir / "overview_equity.png"
    )
    report.plot_drawdowns(
        overview_navs, "總覽：回撤比較", output_dir / "overview_drawdown.png"
    )

    # 每組配對各自一張圖：附上 00631L / 0050 基準，比較該配對的所有再平衡規則
    core_baselines = {
        name: nav for name, nav in baseline_navs.items() if "00631L" in name or "0050" in name
    }
    for pair_name, labels in groups["pairs"].items():
        pair_navs = {**core_baselines, **{label: navs[label] for label in labels}}
        safe_name = pair_name.replace(" ", "_").replace("+", "plus")
        report.plot_equity_curves(
            pair_navs, f"{pair_name}：各再平衡規則比較", output_dir / f"{safe_name}_equity.png"
        )
        report.plot_drawdowns(
            pair_navs, f"{pair_name}：各再平衡規則回撤比較", output_dir / f"{safe_name}_drawdown.png"
        )

    # 拆解「00631L 實際表現」有多少是波動耗損、多少是費用/其他因素造成的落差
    lev_cfg = cfg.get("leverage_analysis", {})
    if lev_cfg:
        leverage = float(lev_cfg.get("leverage", 2.0))
        annual_cost = float(lev_cfg.get("annual_cost", 0.0))
        base_label = lev_cfg["base_baseline"]
        leveraged_label = lev_cfg["leveraged_baseline"]

        risk_free = float(cfg.get("risk_free_annual_rate", 0.0))
        tracking_table = leverage_analysis.tracking_difference_table(
            navs[base_label], navs[leveraged_label], leverage, annual_cost, risk_free
        )
        tracking_formatted = report.format_results_table(tracking_table)
        (output_dir / "leverage_tracking.md").write_text(
            tracking_formatted.to_markdown(), encoding="utf-8"
        )
        tracking_table.to_csv(output_dir / "leverage_tracking.csv", encoding="utf-8-sig")
        print("\n=== 正2實際表現拆解：波動耗損 vs 費用/其他因素 ===")
        print(tracking_formatted.to_string())

        clean_synthetic = leverage_analysis.simulate_leveraged_from_returns(
            navs[base_label], leverage, annual_cost=0.0
        )
        cost_synthetic = leverage_analysis.simulate_leveraged_from_returns(
            navs[base_label], leverage, annual_cost=annual_cost
        )
        tracking_navs = {
            base_label: navs[base_label],
            leveraged_label: navs[leveraged_label],
            f"合成{leverage:g}倍（無費用）": clean_synthetic,
            f"合成{leverage:g}倍（含{annual_cost * 100:.2f}%年費）": cost_synthetic,
        }
        report.plot_equity_curves(
            tracking_navs,
            f"{leveraged_label} vs 合成每日複利倍數：拆解波動耗損與費用",
            output_dir / "leverage_tracking_equity.png",
        )

    print(f"\n圖表與報表已輸出至：{output_dir.resolve()}")


if __name__ == "__main__":
    main()
