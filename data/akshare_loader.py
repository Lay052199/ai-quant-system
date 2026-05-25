"""AKShare 数据加载模块。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import akshare as ak
import pandas as pd

from config import CACHE_PATH


RAW_TO_STANDARD_COLUMNS = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_change",
    "涨跌额": "change_amount",
    "换手率": "turnover",
}


def _build_cache_path(symbol: str, start_date: str, end_date: str, adjust: str) -> Path:
    """构建缓存文件路径。"""
    adjust_tag = adjust if adjust else "bfq"
    return CACHE_PATH / f"{symbol}_{start_date}_{end_date}_{adjust_tag}.csv"


def _normalize_price_df(df: pd.DataFrame) -> pd.DataFrame:
    """统一 AKShare 返回字段并完成基础清洗。"""
    renamed = df.rename(columns=RAW_TO_STANDARD_COLUMNS)
    required_columns = list(RAW_TO_STANDARD_COLUMNS.values())
    missing_columns = [column for column in required_columns if column not in renamed.columns]
    if missing_columns:
        raise ValueError(f"行情数据字段缺失: {missing_columns}")

    normalized = renamed[required_columns].copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
    normalized = normalized.dropna(subset=["date"])
    normalized = normalized.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

    numeric_columns = [column for column in required_columns if column != "date"]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    if normalized[["open", "close", "high", "low"]].isnull().any().any():
        raise ValueError("行情数据存在关键价格字段空值，请检查数据源返回结果。")

    return normalized


def get_a_stock_daily(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
    use_cache: bool = True,
) -> pd.DataFrame:
    """获取 A 股日线历史行情。

    参数:
        symbol: 股票代码，例如 "000001"。
        start_date: 开始日期，格式 YYYYMMDD。
        end_date: 结束日期，格式 YYYYMMDD。
        adjust: 复权方式，可选 qfq、hfq 或空字符串。
        use_cache: 是否优先使用本地缓存。

    返回:
        pandas.DataFrame: 标准化后的历史行情数据。
    """
    cache_path = _build_cache_path(symbol, start_date, end_date, adjust)

    try:
        if use_cache and cache_path.exists():
            cached_df = pd.read_csv(cache_path)
            return _normalize_price_df(cached_df)

        raw_df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

        if raw_df is None or raw_df.empty:
            raise ValueError(
                f"未获取到股票 {symbol} 在 {start_date} 至 {end_date} 区间的历史行情，请检查代码或日期范围。"
            )

        normalized_df = _normalize_price_df(raw_df)
        normalized_df.to_csv(cache_path, index=False, encoding="utf-8-sig")
        return normalized_df
    except Exception as exc:
        message = (
            f"AKShare 历史行情获取失败，股票代码={symbol}，区间={start_date}-{end_date}。"
            f"详细原因: {exc}"
        )
        raise RuntimeError(message) from exc
