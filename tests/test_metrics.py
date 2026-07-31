import pandas as pd
import pytest

from src import metrics


def test_max_drawdown_known_path():
    idx = pd.date_range("2020-01-01", periods=4, freq="D")
    nav = pd.Series([100, 120, 90, 108], index=idx)
    assert metrics.max_drawdown(nav) == pytest.approx(-0.25)


def test_drawdown_series_zero_at_new_highs():
    idx = pd.date_range("2020-01-01", periods=3, freq="D")
    nav = pd.Series([1.0, 1.1, 1.2], index=idx)
    dd = metrics.drawdown_series(nav)
    assert (dd == 0).all()


def test_cagr_two_year_double():
    idx = pd.DatetimeIndex(["2020-01-01", "2022-01-01"])
    nav = pd.Series([1.0, 2.0], index=idx)
    years = (idx[-1] - idx[0]).days / 365.25
    expected = 2.0 ** (1 / years) - 1
    assert metrics.cagr(nav) == pytest.approx(expected)


def test_calmar_ratio_matches_cagr_over_mdd():
    idx = pd.date_range("2020-01-01", periods=4, freq="D")
    nav = pd.Series([100, 120, 90, 108], index=idx)
    assert metrics.calmar_ratio(nav) == pytest.approx(metrics.cagr(nav) / 0.25)


def test_sharpe_ratio_zero_vol_returns_nan():
    idx = pd.date_range("2020-01-01", periods=3, freq="D")
    nav = pd.Series([1.0, 1.0, 1.0], index=idx)
    assert metrics.sharpe_ratio(nav) != metrics.sharpe_ratio(nav)  # NaN != NaN
