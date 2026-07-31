import numpy as np
import pandas as pd
import pytest

from src import leverage_analysis, metrics


def test_simulate_leveraged_from_returns_no_cost():
    idx = pd.date_range("2020-01-01", periods=3, freq="D")
    base_nav = pd.Series([1.0, 1.1, 0.99], index=idx)  # +10% then -10%
    leveraged = leverage_analysis.simulate_leveraged_from_returns(base_nav, leverage=2.0)
    assert leveraged.iloc[0] == pytest.approx(1.0)
    assert leveraged.iloc[1] == pytest.approx(1.2)   # 1 + 2*0.10
    assert leveraged.iloc[2] == pytest.approx(0.96)  # 1.2 * (1 + 2*-0.10)


def test_annual_cost_drags_down_nav():
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    base_nav = pd.Series([1.0, 1.01, 1.02, 1.01, 1.03], index=idx)
    no_cost = leverage_analysis.simulate_leveraged_from_returns(base_nav, 2.0, annual_cost=0.0)
    with_cost = leverage_analysis.simulate_leveraged_from_returns(base_nav, 2.0, annual_cost=0.05)
    assert with_cost.iloc[-1] < no_cost.iloc[-1]


def test_naive_leveraged_cagr_matches_hand_calc():
    idx = pd.DatetimeIndex(["2020-01-01", "2022-01-01"])
    base_nav = pd.Series([1.0, 2.0], index=idx)
    expected = (1 + metrics.cagr(base_nav)) ** 2 - 1
    assert leverage_analysis.naive_leveraged_cagr(base_nav, leverage=2.0) == pytest.approx(expected)


def test_tracking_difference_table_has_expected_rows():
    idx = pd.date_range("2020-01-01", periods=200, freq="D")
    base_nav = pd.Series(1.0 + 0.0005 * np.arange(200), index=idx)
    actual_leveraged = leverage_analysis.simulate_leveraged_from_returns(base_nav, 2.0, annual_cost=0.02)

    table = leverage_analysis.tracking_difference_table(base_nav, actual_leveraged, 2.0, annual_cost=0.011)

    assert "正2 ETF 實際表現" in table.index
    assert table.loc["正2 ETF 實際表現", "CAGR"] == pytest.approx(metrics.cagr(actual_leveraged))
