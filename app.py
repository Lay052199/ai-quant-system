"""Streamlit 应用入口。"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Iterable

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from backtest.batch_runner import parse_symbols, run_batch_backtest
from backtest.exporter import (
    export_batch_backtest_result,
    export_backtest_result,
    export_sensitivity_result,
    export_trades_detail,
)
from backtest.sensitivity import analyze_ma_parameter_sensitivity
from config import BENCHMARK, COMMISSION_RATE, INITIAL_CASH, SLIPPAGE_RATE
from data.akshare_loader import get_index_daily
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


def format_metrics(metrics: Dict[str, float]) -> pd.DataFrame:
    """格式化核心指标表。"""
    ratio_keys = {"总收益率", "基准收益率", "超额收益率", "年化收益率", "最大回撤", "胜率", "年化波动率"}
    number_keys = {"最终资产", "初始资金"}
    formatted_values = []

    for key, value in metrics.items():
        if key in ratio_keys:
            formatted_values.append(f"{value:.2%}")
        elif key == "夏普比率":
            formatted_values.append(f"{value:.4f}")
        elif key in number_keys:
            formatted_values.append(f"{value:,.2f}")
        else:
            formatted_values.append(value)

    return pd.DataFrame({"指标": list(metrics.keys()), "数值": formatted_values})


def format_leaderboard(leaderboard_df: pd.DataFrame) -> pd.DataFrame:
    """格式化排行榜表格。"""
    display_df = leaderboard_df.copy()
    for column in ["总收益率", "年化收益率", "最大回撤", "胜率"]:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "")
    if "夏普比率" in display_df.columns:
        display_df["夏普比率"] = display_df["夏普比率"].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "")
    return display_df


def sort_leaderboard(leaderboard_df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
    """按指定指标排序排行榜。"""
    if leaderboard_df.empty or sort_by not in leaderboard_df.columns:
        return leaderboard_df

    sorted_df = leaderboard_df.copy()
    if sort_by == "最大回撤":
        sorted_df["_sort_value"] = sorted_df[sort_by].abs()
        sorted_df = sorted_df.sort_values(by="_sort_value", ascending=True, na_position="last").drop(columns="_sort_value")
    else:
        sorted_df = sorted_df.sort_values(by=sort_by, ascending=False, na_position="last")
    sorted_df = sorted_df.reset_index(drop=True)
    return sorted_df


def plot_nav_chart(result_df: pd.DataFrame) -> plt.Figure:
    """绘制策略、基准和超额净值曲线。"""
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(result_df["date"], result_df["strategy_nav"], label="策略净值", linewidth=2, color="#1f77b4")
    ax.plot(result_df["date"], result_df["benchmark_nav"], label="基准净值", linewidth=2, color="#ff7f0e")
    ax.plot(result_df["date"], result_df["excess_nav"], label="超额净值", linewidth=1.6, color="#2ca02c")
    ax.set_title("策略、基准与超额净值曲线")
    ax.set_xlabel("日期")
    ax.set_ylabel("净值")
    ax.legend()
    ax.grid(alpha=0.3)
    return fig


def plot_drawdown_chart(result_df: pd.DataFrame) -> plt.Figure:
    """绘制回撤曲线。"""
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.fill_between(result_df["date"], result_df["drawdown"], 0, color="#d62728", alpha=0.3, label="回撤")
    ax.plot(result_df["date"], result_df["drawdown"], color="#d62728", linewidth=1.5)
    ax.set_title("策略回撤曲线")
    ax.set_xlabel("日期")
    ax.set_ylabel("回撤")
    ax.legend()
    ax.grid(alpha=0.3)
    return fig


def plot_trade_points_chart(result_df: pd.DataFrame, symbol: str, strategy_name: str) -> plt.Figure:
    """绘制买卖点标记图。"""
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(result_df["date"], result_df["close"], label="收盘价", linewidth=1.8, color="#1f77b4")
    buy_df = result_df[result_df["trade_flag"] == 1]
    sell_df = result_df[result_df["trade_flag"] == -1]
    if not buy_df.empty:
        ax.scatter(buy_df["date"], buy_df["close"], marker="^", color="#d62728", s=80, label="买点")
    if not sell_df.empty:
        ax.scatter(sell_df["date"], sell_df["close"], marker="v", color="#2ca02c", s=80, label="卖点")
    ax.set_title(f"{symbol} {strategy_name} 买卖点标记图")
    ax.set_xlabel("日期")
    ax.set_ylabel("价格")
    ax.legend()
    ax.grid(alpha=0.3)
    return fig


def build_sensitivity_ranges() -> tuple[Iterable[int], Iterable[int]]:
    """生成默认双均线敏感性分析参数范围。"""
    short_windows = [3, 5, 8, 10]
    long_windows = [15, 20, 30, 60]
    return short_windows, long_windows


def render_single_stock_detail(
    symbol: str,
    strategy_name: str,
    clean_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    signal_df: pd.DataFrame,
    result_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    metrics: Dict[str, float],
    risk_report: list[str],
    report_text: str,
    backtest_excel: Path,
    trades_excel: Path,
    sensitivity_df: pd.DataFrame,
    sensitivity_path: Path | None,
) -> None:
    """渲染单股票详细回测页面。"""
    st.subheader(f"单股票详细结果：{symbol}")
    st.subheader("原始行情数据预览")
    st.dataframe(clean_df.head(20), use_container_width=True)

    st.subheader("基准行情数据预览")
    st.dataframe(benchmark_df.head(20), use_container_width=True)

    preview_df = signal_df.copy()
    if "executed_signal" in result_df.columns:
        preview_df["executed_signal"] = result_df["executed_signal"]
    if "position" in result_df.columns:
        preview_df["position"] = result_df["position"]

    preview_columns = [
        column
        for column in ["date", "close", "signal", "executed_signal", "position", "ma_short", "ma_long", "momentum", "rsi"]
        if column in preview_df.columns
    ]
    st.subheader("策略信号数据预览")
    st.dataframe(preview_df[preview_columns].head(30), use_container_width=True)

    st.subheader("策略、基准与超额净值曲线")
    st.pyplot(plot_nav_chart(result_df), clear_figure=True)

    st.subheader("回撤曲线")
    st.pyplot(plot_drawdown_chart(result_df), clear_figure=True)

    st.subheader("买卖点标记图")
    st.pyplot(plot_trade_points_chart(result_df, symbol, strategy_name), clear_figure=True)

    st.subheader("核心指标表")
    st.table(format_metrics(metrics))

    st.subheader("交易记录表")
    if trades_df.empty:
        st.warning("当前策略在该区间内没有产生完整交易记录。")
    else:
        st.dataframe(trades_df, use_container_width=True)

    st.subheader("导出文件")
    st.write(f"- 回测结果 Excel：`{backtest_excel}`")
    st.write(f"- 交易明细 Excel：`{trades_excel}`")
    if sensitivity_path is not None:
        st.write(f"- 参数敏感性分析 Excel：`{sensitivity_path}`")

    st.subheader("风险提示")
    for item in risk_report:
        st.write(f"- {item}")

    if not sensitivity_df.empty:
        st.subheader("双均线参数敏感性分析")
        st.dataframe(sensitivity_df, use_container_width=True)

    st.subheader("自动生成的中文分析报告")
    st.text(report_text)


def main() -> None:
    """运行 Streamlit 页面。"""
    configure_matplotlib()
    st.set_page_config(page_title="AI 量化策略研究与回测系统", layout="wide")
    st.title("AI 量化策略研究与回测系统")
    st.caption("当前版本仅支持历史回测与模拟分析，不包含真实交易或真实下单功能。")

    strategy_map = build_strategy_map()

    with st.sidebar:
        st.header("参数设置")
        symbols_text = st.text_input("股票代码（支持多个，英文逗号分隔）", value="000001").strip()
        benchmark_symbol = st.text_input("基准指数代码", value=BENCHMARK).strip()
        start_date = st.text_input("开始日期", value="20200101").strip()
        end_date = st.text_input("结束日期", value="20241231").strip()
        adjust_option = st.selectbox("复权方式", options=["qfq", "hfq", "不复权"], index=0)
        strategy_name = st.selectbox("策略选择", options=list(strategy_map.keys()), index=0)
        sort_by = st.selectbox("排行榜排序字段", options=["总收益率", "夏普比率", "最大回撤"], index=0)
        initial_cash = st.number_input("初始资金", min_value=1000.0, value=float(INITIAL_CASH), step=1000.0)
        commission_rate = st.number_input("手续费", min_value=0.0, value=float(COMMISSION_RATE), step=0.0001, format="%.4f")
        slippage_rate = st.number_input("滑点", min_value=0.0, value=float(SLIPPAGE_RATE), step=0.0001, format="%.4f")
        enable_sensitivity = st.checkbox("启用双均线参数敏感性分析", value=True)
        run_button = st.button("运行回测", type="primary")

    if not run_button:
        st.info("请在左侧设置参数后点击“运行回测”。")
        return

    symbols = parse_symbols(symbols_text)
    if not symbols:
        st.error("请至少输入一个股票代码。")
        return

    adjust = "" if adjust_option == "不复权" else adjust_option

    try:
        benchmark_df = get_index_daily(symbol=benchmark_symbol, start_date=start_date, end_date=end_date, use_cache=True)
        leaderboard_df, batch_details = run_batch_backtest(
            symbols=symbols,
            strategy_func=strategy_map[strategy_name],
            benchmark_df=benchmark_df,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
            initial_cash=initial_cash,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )
        sorted_leaderboard_df = sort_leaderboard(leaderboard_df, sort_by=sort_by)
        batch_excel = export_batch_backtest_result(sorted_leaderboard_df, strategy_name, start_date, end_date)
    except Exception as exc:
        st.error(f"运行失败：{exc}")
        return

    st.subheader("批量回测排行榜")
    st.dataframe(format_leaderboard(sorted_leaderboard_df), use_container_width=True)
    st.write(f"- 批量回测结果 Excel：`{batch_excel}`")

    failed_symbols = sorted_leaderboard_df[sorted_leaderboard_df.get("错误信息", pd.Series(dtype=object)).notna()] if "错误信息" in sorted_leaderboard_df.columns else pd.DataFrame()
    if not failed_symbols.empty:
        st.subheader("失败股票提示")
        st.dataframe(failed_symbols[["股票代码", "错误信息"]], use_container_width=True)

    primary_symbol = next((symbol for symbol in symbols if not batch_details.get(symbol, {}).get("error")), None)
    if primary_symbol is None:
        st.warning("所有股票均回测失败，无法展示单股票详情。")
        return
    primary_detail = batch_details.get(primary_symbol, {})

    clean_df = primary_detail["clean_df"]
    signal_df = primary_detail["signal_df"]
    result_df = primary_detail["result_df"]
    trades_df = primary_detail["trades_df"]
    metrics = primary_detail["metrics"]
    risk_report = generate_risk_report(result_df, trades_df)
    report_text = generate_text_report(metrics, risk_report, strategy_name, primary_symbol, start_date, end_date)
    backtest_excel = export_backtest_result(result_df, trades_df, metrics, primary_symbol, strategy_name)
    trades_excel = export_trades_detail(trades_df, primary_symbol, strategy_name)

    sensitivity_df = pd.DataFrame()
    sensitivity_path: Path | None = None
    if enable_sensitivity and strategy_name == "双均线策略":
        try:
            short_windows, long_windows = build_sensitivity_ranges()
            sensitivity_df = analyze_ma_parameter_sensitivity(
                clean_df,
                short_windows=short_windows,
                long_windows=long_windows,
                benchmark_df=benchmark_df,
                initial_cash=initial_cash,
                commission_rate=commission_rate,
                slippage_rate=slippage_rate,
            )
            sensitivity_path = export_sensitivity_result(sensitivity_df, primary_symbol, strategy_name)
        except Exception as exc:
            st.warning(f"参数敏感性分析执行失败：{exc}")

    render_single_stock_detail(
        symbol=primary_symbol,
        strategy_name=strategy_name,
        clean_df=clean_df,
        benchmark_df=benchmark_df,
        signal_df=signal_df,
        result_df=result_df,
        trades_df=trades_df,
        metrics=metrics,
        risk_report=risk_report,
        report_text=report_text,
        backtest_excel=backtest_excel,
        trades_excel=trades_excel,
        sensitivity_df=sensitivity_df,
        sensitivity_path=sensitivity_path,
    )


if __name__ == "__main__":
    main()
