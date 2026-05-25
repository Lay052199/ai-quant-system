"""策略报告生成模块。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from config import OUTPUT_PATH


def generate_text_report(
    metrics: Dict[str, float],
    risk_report: List[str],
    strategy_name: str,
    symbol: str,
    start_date: str,
    end_date: str,
) -> str:
    """生成中文策略分析报告并保存到输出目录。"""
    total_return = metrics.get("总收益率", 0.0)
    annual_return = metrics.get("年化收益率", 0.0)
    max_drawdown = metrics.get("最大回撤", 0.0)
    sharpe_ratio = metrics.get("夏普比率", 0.0)
    volatility = metrics.get("年化波动率", 0.0)
    win_rate = metrics.get("胜率", 0.0)
    trade_count = metrics.get("交易次数", 0)

    advantages = []
    if sharpe_ratio > 1:
        advantages.append("风险调整后收益表现较好，策略稳定性相对较强。")
    if abs(max_drawdown) < 0.15:
        advantages.append("最大回撤控制较温和。")
    if not advantages:
        advantages.append("策略结构简单，便于解释、调参与迭代。")

    limitations = []
    if total_return <= 0:
        limitations.append("当前参数下策略整体收益表现偏弱。")
    if abs(max_drawdown) > 0.2:
        limitations.append("回撤较大，资金曲线承压明显。")
    if trade_count <= 1:
        limitations.append("样本交易次数较少，统计稳定性有限。")
    if not limitations:
        limitations.append("策略仍基于单一技术指标，适应不同市场环境的能力有限。")

    report_text = f"""策略分析报告

策略名称：{strategy_name}
回测标的：{symbol}
回测区间：{start_date} - {end_date}

一、收益表现
策略总收益率为 {total_return:.2%}，年化收益率为 {annual_return:.2%}，最终资产为 {metrics.get('最终资产', 0):,.2f} 元。
策略夏普比率为 {sharpe_ratio:.2f}，年化波动率为 {volatility:.2%}，交易胜率为 {win_rate:.2%}，共发生 {trade_count} 笔交易。

二、风险表现
最大回撤为 {max_drawdown:.2%}。
风险提示如下：
{chr(10).join(f"- {item}" for item in risk_report)}

三、策略优点
{chr(10).join(f"- {item}" for item in advantages)}

四、策略局限
{chr(10).join(f"- {item}" for item in limitations)}

五、后续优化方向
- 可引入多因子过滤条件，降低单一指标失效风险。
- 可加入仓位管理、止盈止损和波动率约束，优化回撤表现。
- 后续可接入 Tushare、OpenAI API 和模拟交易模块，扩展研究能力。
"""

    report_path = OUTPUT_PATH / f"report_{symbol}_{strategy_name}.txt"
    report_path.write_text(report_text, encoding="utf-8")
    return report_text
