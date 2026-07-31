import pandas as pd
import pytest

from src import portfolio


def _prices() -> pd.DataFrame:
    # Asset A doubles on day 2, then drops back to its original price on day 3.
    # Asset B stays flat throughout. This makes rebalance-vs-no-rebalance diverge.
    idx = pd.date_range("2020-01-01", periods=4, freq="D")
    return pd.DataFrame(
        {"A": [1.0, 1.0, 2.0, 1.0], "B": [1.0, 1.0, 1.0, 1.0]},
        index=idx,
    )


def test_no_rebalance_lets_weights_drift():
    rule = portfolio.RebalanceRule(name="none", kind="none")
    nav = portfolio.simulate(_prices(), {"A": 0.5, "B": 0.5}, rule)
    assert nav.iloc[-1] == pytest.approx(1.0)


def test_threshold_rebalance_resets_exposure():
    rule = portfolio.RebalanceRule(name="threshold_10", kind="threshold", band=0.10)
    nav = portfolio.simulate(_prices(), {"A": 0.5, "B": 0.5}, rule)
    # A's spike on day 2 triggers a rebalance; giving up some upside before the
    # day-3 drop leaves the rebalanced portfolio ahead of the no-rebalance case.
    assert nav.iloc[-1] == pytest.approx(1.125)


def test_threshold_below_band_does_not_trigger():
    rule = portfolio.RebalanceRule(name="threshold_50", kind="threshold", band=0.50)
    nav = portfolio.simulate(_prices(), {"A": 0.5, "B": 0.5}, rule)
    assert nav.iloc[-1] == pytest.approx(1.0)


def test_calendar_rebalance_dates_trigger_on_period_change():
    idx = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-01", "2020-02-15"])
    dates = portfolio._calendar_rebalance_dates(idx, "M")
    assert dates == {pd.Timestamp("2020-02-01")}


def test_transaction_cost_reduces_nav_on_rebalance_day():
    rule = portfolio.RebalanceRule(name="threshold_10", kind="threshold", band=0.10)
    nav_no_cost = portfolio.simulate(_prices(), {"A": 0.5, "B": 0.5}, rule, cost_bps=0)
    nav_with_cost = portfolio.simulate(_prices(), {"A": 0.5, "B": 0.5}, rule, cost_bps=100)
    assert nav_with_cost.iloc[-1] < nav_no_cost.iloc[-1]
