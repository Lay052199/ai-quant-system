"""FastAPI 后端服务。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException

from api_models import BacktestRequest, BacktestResponse, HealthResponse, StrategyItem, StrategyListResponse
from backtest.engine import run_backtest
from backtest.metrics import calculate_metrics
from config import BENCHMARK, COMMISSION_RATE, INITIAL_CASH, SLIPPAGE_RATE
from data.akshare_loader import get_a_stock_daily, get_index_daily
from data.data_cleaner import clean_price_data
from report.report_generator import generate_text_report
from risk.risk_manager import generate_risk_report
from strategy.ma_strategy import generate_ma_signal
from strategy.momentum_strategy import generate_momentum_signal
from strategy.rsi_strategy import generate_rsi_signal

app = FastAPI(
    title="AI Quant System API",
    description="基于 Python + AKShare 的量化研究与历史回测 API，仅用于学习、研究和模拟分析。",
    version="1.0.0",
)


def get_strategy_registry() -> Dict[str, Dict[str, Any]]:
    """返回策略注册表。"""
    return {
        "双均线策略": {
            "description": "基于短期均线与长期均线金叉/死叉的趋势跟踪策略。",
            "default_params": {"short_window": 5, "long_window": 20},
            "handler": lambda df, params: generate_ma_signal(
                df,
                short_window=int(params.get("short_window", 5)),
                long_window=int(params.get("long_window", 20)),
            ),
        },
        "动量策略": {
            "description": "基于过去一段时间价格涨跌幅的简单动量策略。",
            "default_params": {"window": 20, "threshold": 0},
            "handler": lambda df, params: generate_momentum_signal(
                df,
                window=int(params.get("window", 20)),
                threshold=float(params.get("threshold", 0)),
            ),
        },
        "RSI 策略": {
            "description": "基于 RSI 超买超卖区间的反转型策略。",
            "default_params": {"window": 14, "lower": 30, "upper": 70},
            "handler": lambda df, params: generate_rsi_signal(
                df,
                window=int(params.get("window", 14)),
                lower=float(params.get("lower", 30)),
                upper=float(params.get("upper", 70)),
            ),
        },
    }


def safe_date_to_str(value: Any) -> str | None:
    """安全转换日期字段，避免对 NaT 或空值直接调用 strftime。"""
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (pd.Timestamp, datetime, date)):
        if pd.isna(value):
            return None
        return value.strftime("%Y-%m-%d")
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return None


def to_json_compatible(value: Any) -> Any:
    """将 pandas、numpy、日期等对象递归转换为可 JSON 序列化的原生类型。"""
    if isinstance(value, str):
        return value
    if isinstance(value, (pd.Timestamp, datetime, date)) or value is pd.NaT:
        return safe_date_to_str(value)
    if isinstance(value, np.generic):
        return to_json_compatible(value.item())
    if isinstance(value, dict):
        return {str(key): to_json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_compatible(item) for item in value]
    if isinstance(value, pd.Series):
        return [to_json_compatible(item) for item in value.tolist()]
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return value


def dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """将 DataFrame 转换为可 JSON 序列化的记录列表。"""
    records = df.to_dict(orient="records")
    return [{key: to_json_compatible(value) for key, value in record.items()} for record in records]


def metrics_to_python(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """将指标字典转换为原生类型。"""
    return {key: to_json_compatible(value) for key, value in metrics.items()}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """健康检查接口。"""
    return HealthResponse(status="ok", service="ai_quant_system_api")


@app.get("/api/strategies", response_model=StrategyListResponse)
def get_strategies() -> StrategyListResponse:
    """返回支持的策略列表。"""
    registry = get_strategy_registry()
    strategies = [
        StrategyItem(
            name=name,
            description=config["description"],
            default_params=config["default_params"],
        )
        for name, config in registry.items()
    ]
    return StrategyListResponse(strategies=strategies)


@app.post("/api/backtest", response_model=BacktestResponse)
def backtest(payload: BacktestRequest) -> BacktestResponse:
    """执行历史回测并返回 JSON 结果。"""
    registry = get_strategy_registry()
    if payload.strategy not in registry:
        raise HTTPException(status_code=400, detail=f"不支持的策略名称: {payload.strategy}")

    try:
        adjust = "" if payload.adjust in {"", "不复权"} else payload.adjust
        price_df = get_a_stock_daily(
            symbol=payload.symbol,
            start_date=payload.start_date,
            end_date=payload.end_date,
            adjust=adjust,
            use_cache=True,
        )
        benchmark_df = get_index_daily(
            symbol=payload.benchmark_symbol or BENCHMARK,
            start_date=payload.start_date,
            end_date=payload.end_date,
            use_cache=True,
        )
        clean_df = clean_price_data(price_df)
        strategy_df = registry[payload.strategy]["handler"](clean_df, payload.strategy_params or {})
        result_df, trades_df = run_backtest(
            strategy_df,
            initial_cash=payload.initial_cash,
            commission_rate=payload.commission_rate,
            slippage_rate=payload.slippage_rate,
            benchmark_df=benchmark_df,
        )
        metrics = calculate_metrics(result_df, trades_df)
        risk_report = generate_risk_report(result_df, trades_df)
        report = generate_text_report(
            metrics=metrics,
            risk_report=risk_report,
            strategy_name=payload.strategy,
            symbol=payload.symbol,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )

        equity_curve_columns = [
            column
            for column in [
                "date",
                "close",
                "strategy_nav",
                "benchmark_nav",
                "excess_nav",
                "drawdown",
                "position",
                "trade_flag",
            ]
            if column in result_df.columns
        ]
        equity_curve = dataframe_to_records(result_df[equity_curve_columns].copy())
        trades = dataframe_to_records(trades_df.copy())

        return BacktestResponse(
            metrics=metrics_to_python(metrics),
            risk_report=[str(item) for item in risk_report],
            report=str(report),
            equity_curve=equity_curve,
            trades=trades,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"回测执行失败: {exc}") from exc
