"""回测指标测试。"""

from __future__ import annotations

import pandas as pd

from backtest.metrics import (
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_total_return,
)


def build_result_df() -> pd.DataFrame:
    """构造测试用资金曲线。"""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "total_value": [100000, 110000, 99000, 120000],
            "strategy_return": [0.0, 0.1, -0.1, 0.212121],
        }
    )


def test_calculate_max_drawdown() -> None:
    """测试最大回撤。"""
    result_df = build_result_df()
    max_drawdown = calculate_max_drawdown(result_df)
    assert round(max_drawdown, 2) == -0.10


def test_calculate_total_return() -> None:
    """测试总收益率。"""
    result_df = build_result_df()
    total_return = calculate_total_return(result_df)
    assert round(total_return, 2) == 0.20


def test_calculate_sharpe_ratio_no_error() -> None:
    """测试夏普比率函数可正常执行。"""
    result_df = build_result_df()
    sharpe_ratio = calculate_sharpe_ratio(result_df)
    assert isinstance(sharpe_ratio, float)
