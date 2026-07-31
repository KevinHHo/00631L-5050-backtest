"""Render comparison charts and tables from backtest results."""
from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
# Benign log noise: matplotlib probes a mathtext fallback glyph for the unicode
# minus sign even though axes.unicode_minus=False below means it's never used.
logging.getLogger("matplotlib.mathtext").setLevel(logging.ERROR)
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from . import metrics

# Register a CJK-capable font so Chinese labels render instead of showing as
# missing-glyph boxes. Falls back to matplotlib's default if none is found.
_CJK_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msjh.ttc",   # Microsoft JhengHei (Traditional Chinese, Windows)
    r"C:\Windows\Fonts\msyh.ttc",   # Microsoft YaHei (Simplified Chinese, Windows)
    "/System/Library/Fonts/PingFang.ttc",  # macOS
]
for _font_path in _CJK_FONT_CANDIDATES:
    if Path(_font_path).exists():
        fm.fontManager.addfont(_font_path)
        plt.rcParams["font.family"] = fm.FontProperties(fname=_font_path).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

# Validated categorical palette (fixed order — do not reshuffle; see dataviz skill).
PALETTE = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE_INK = "#c3c2b7"


def _style_axes(ax, title: str, ylabel: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.set_title(title, color=INK_PRIMARY, fontsize=13, loc="left", pad=12)
    ax.set_ylabel(ylabel, color=INK_SECONDARY, fontsize=10)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    ax.grid(True, color=GRIDLINE, linewidth=0.8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(BASELINE_INK)


def _legend_outside(ax) -> None:
    # With up to ~8 series, any inside-plot corner collides with some line
    # somewhere over a multi-decade series, so the legend lives outside the axes.
    ax.legend(
        frameon=False,
        fontsize=9,
        labelcolor=INK_SECONDARY,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
    )


def plot_equity_curves(navs: dict[str, pd.Series], title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=SURFACE)
    for i, (name, nav) in enumerate(navs.items()):
        ax.plot(nav.index, nav.values, label=name, color=PALETTE[i % len(PALETTE)], linewidth=2)
    ax.set_yscale("log")
    _style_axes(ax, title, "淨值（起始 = 1，log scale）")
    _legend_outside(ax)
    fig.savefig(path, dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def plot_drawdowns(navs: dict[str, pd.Series], title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=SURFACE)
    for i, (name, nav) in enumerate(navs.items()):
        dd = metrics.drawdown_series(nav) * 100
        ax.plot(dd.index, dd.values, label=name, color=PALETTE[i % len(PALETTE)], linewidth=2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    _style_axes(ax, title, "回撤")
    _legend_outside(ax)
    fig.savefig(path, dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def format_results_table(results: pd.DataFrame) -> pd.DataFrame:
    formatted = results.copy()
    for col in ("CAGR", "MDD", "年化波動度"):
        formatted[col] = (formatted[col] * 100).map(lambda v: f"{v:.1f}%")
    for col in ("Sharpe", "Calmar"):
        formatted[col] = formatted[col].map(lambda v: f"{v:.2f}")
    formatted["期末淨值(起始=1)"] = formatted["期末淨值(起始=1)"].map(lambda v: f"{v:.2f}")
    return formatted


def format_percent_table(table: pd.DataFrame) -> pd.DataFrame:
    """Format every column of `table` as a percentage (used for stress-window
    report/MDD tables, where every column is already a fraction like 0.12)."""
    return table.map(lambda v: f"{v * 100:.1f}%" if pd.notna(v) else "-")
