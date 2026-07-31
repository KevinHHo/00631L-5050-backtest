import pandas as pd
import pytest

from src import stress_test


def _nav() -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=6, freq="D")
    # peaks at day 2 (120), troughs at day 4 (84) -> -30% drawdown within the window
    return pd.Series([100, 110, 120, 100, 84, 90], index=idx)


def test_slice_and_rebase_starts_at_one():
    nav = _nav()
    rebased = stress_test.slice_and_rebase(nav, "2020-01-03", "2020-01-06")
    assert rebased.iloc[0] == pytest.approx(1.0)


def test_window_summary_computes_return_and_mdd():
    nav = _nav()
    summary = stress_test.window_summary(nav, "2020-01-01", "2020-01-06")
    assert summary["區間報酬"] == pytest.approx(90 / 100 - 1)
    assert summary["區間MDD"] == pytest.approx(84 / 120 - 1)


def test_slice_and_rebase_raises_when_no_overlap():
    nav = _nav()
    with pytest.raises(RuntimeError):
        stress_test.slice_and_rebase(nav, "2021-01-01", "2021-02-01")


def test_build_window_table_has_one_column_pair_per_window():
    navs = {"A": _nav(), "B": _nav() * 2}
    windows = [{"name": "測試區間", "start": "2020-01-01", "end": "2020-01-06"}]
    table = stress_test.build_window_table(navs, windows)
    assert list(table.columns) == ["測試區間｜區間報酬", "測試區間｜區間MDD"]
    assert set(table.index) == {"A", "B"}
