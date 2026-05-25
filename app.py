"""Streamlit 应用入口。"""

from __future__ import annotations

from typing import Callable, Dict, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from backtest.engine import run_backtest
from backtest.metrics import calculate_metrics
from config import ADJUST, COMMISSION_RATE, INITIAL_CASH, SLIPPAGE_RATE
from data.akshare_loader import get_a_stock_daily
from data.data_cleaner import clean_price_data
from report.report_generator import generate_text_report
from risk.risk_manager import generate_risk_report
from strategy.ma_strategy import generate_ma_signal
from strategy.momentum_strategy import generate_momentum_signal
from strategy.rsi_strategy import generate_rsi_signal


def configure_matplotlib() -> None:
    """设置 matplotlib 中文字体兼容。"""
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def build_strategy_map() -> Dict[str, Callable[[pd.DataFrame], pd.DataFrame]]:
    """构建策略名称与函数映射。"""
    return {
        "双均线策略": lambda df: generate_ma_signal(df, short_window=5, long_window=20),
        "动量策略": lambda df: generate_momentum_signal(df, window=20, threshold=0),
        "RSI 策略": lambda df: generate_rsi_signal(df, window=14, lower=30, upper=70),
    }


def plot_backtest_charts(result_df: pd.DataFrame) -> Tuple[plt.Figure, plt.Figure, plt.Figure]:
    """绘制策略净值、基准净值和回撤图表。"""
    chart_df = result_df.copy()
    chart_df["strategy_nav"] = chart_df["total_value"] / chart_df["total_value"].iloc[0]
    chart_df["benchmark_nav"] = (1 + chart_df["benchmark_return"].fillna(0)).cumprod()
    chart_df["drawdown"] = chart_df["strategy_nav"] / chart_df["strategy_nav"].cummax() - 1

    fig_strategy, ax_strategy = plt.subplots(figsize=(10, 5))
    ax_strategy.plot(chart_df["date"], chart_df["strategy_nav"], label="策略净值", linewidth=2, color="#1f77b4")
    ax_strategy.set_title("策略净值曲线")
    ax_strategy.set_xlabel("日期")
    ax_strategy.set_ylabel("净值")
    ax_strategy.legend()
    ax_strategy.grid(alpha=0.3)

    fig_benchmark, ax_benchmark = plt.subplots(figsize=(10, 5))
    ax_benchmark.plot(chart_df["date"], chart_df["benchmark_nav"], label="基准净值", linewidth=2, color="#ff7f0e")
    ax_benchmark.set_title("基准净值曲线")
    ax_benchmark.set_xlabel("日期")
    ax_benchmark.set_ylabel("净值")
    ax_benchmark.legend()
    ax_benchmark.grid(alpha=0.3)

    fig_dd, ax_dd = plt.subplots(figsize=(10, 4))
    ax_dd.fill_between(chart_df["date"], chart_df["drawdown"], 0, color="#d62728", alpha=0.3, label="回撤")
    ax_dd.plot(chart_df["date"], chart_df["drawdown"], color="#d62728", linewidth=1.5)
    ax_dd.set_title("策略回撤曲线")
    ax_dd.set_xlabel("日期")
    ax_dd.set_ylabel("回撤")
    ax_dd.legend()
    ax_dd.grid(alpha=0.3)

    return fig_strategy, fig_benchmark, fig_dd


def main() -> None:
    """运行 Streamlit 页面。"""
    configure_matplotlib()
    st.set_page_config(page_title="AI 量化策略研究与回测系统", layout="wide")
    st.title("AI 量化策略研究与回测系统")
    st.caption("当前版本仅支持历史回测与模拟分析，不包含真实交易或真实下单功能。")

    strategy_map = build_strategy_map()

    with st.sidebar:
        st.header("参数设置")
        symbol = st.text_input("股票代码", value="000001").strip()
        start_date = st.text_input("开始日期", value="20200101").strip()
        end_date = st.text_input("结束日期", value="20241231").strip()
        adjust_option = st.selectbox("复权方式", options=["qfq", "hfq", "不复权"], index=0)
        strategy_name = st.selectbox("策略选择", options=list(strategy_map.keys()), index=0)
        initial_cash = st.number_input("初始资金", min_value=1000.0, value=float(INITIAL_CASH), step=1000.0)
        commission_rate = st.number_input("手续费", min_value=0.0, value=float(COMMISSION_RATE), step=0.0001, format="%.4f")
        slippage_rate = st.number_input("滑点", min_value=0.0, value=float(SLIPPAGE_RATE), step=0.0001, format="%.4f")
        run_button = st.button("运行回测", type="primary")

    if not run_button:
        st.info("请在左侧设置参数后点击“运行回测”。")
        return

    adjust = "" if adjust_option == "不复权" else adjust_option

    try:
        raw_df = get_a_stock_daily(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
            use_cache=True,
        )
        clean_df = clean_price_data(raw_df)
        signal_df = strategy_map[strategy_name](clean_df)
        result_df, trades_df = run_backtest(
            signal_df,
            initial_cash=initial_cash,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )
        metrics = calculate_metrics(result_df, trades_df)
        risk_report = generate_risk_report(result_df, trades_df)
        report_text = generate_text_report(metrics, risk_report, strategy_name, symbol, start_date, end_date)
    except Exception as exc:
        st.error(f"运行失败：{exc}")
        return

    metric_display_df = pd.DataFrame(
        {
            "指标": list(metrics.keys()),
            "数值": [
                f"{value:.2%}" if key in {"总收益率", "年化收益率", "最大回撤", "胜率", "年化波动率"} else f"{value:.4f}" if key == "夏普比率" else f"{value:,.2f}" if key in {"最终资产", "初始资金"} else value
                for key, value in metrics.items()
            ],
        }
    )

    st.subheader("原始行情数据预览")
    st.dataframe(clean_df.head(20), use_container_width=True)

    st.subheader("策略信号数据预览")
    preview_columns = [column for column in ["date", "close", "signal", "position", "ma_short", "ma_long", "momentum", "rsi"] if column in signal_df.columns]
    st.dataframe(signal_df[preview_columns].head(30), use_container_width=True)

    fig_strategy, fig_benchmark, fig_dd = plot_backtest_charts(result_df)
    st.subheader("策略净值曲线")
    st.pyplot(fig_strategy, clear_figure=True)

    st.subheader("基准净值曲线")
    st.pyplot(fig_benchmark, clear_figure=True)

    st.subheader("回撤曲线")
    st.pyplot(fig_dd, clear_figure=True)

    st.subheader("核心指标表")
    st.table(metric_display_df)

    st.subheader("交易记录表")
    if trades_df.empty:
        st.warning("当前策略在该区间内没有产生完整交易记录。")
    else:
        st.dataframe(trades_df, use_container_width=True)

    st.subheader("风险提示")
    for item in risk_report:
        st.write(f"- {item}")

    st.subheader("自动生成的中文分析报告")
    st.text(report_text)


if __name__ == "__main__":
    main()
