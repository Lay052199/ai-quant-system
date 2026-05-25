# ai_quant_system

## 项目简介

`ai_quant_system` 是一个基于 Python + AKShare + Streamlit 的 A 股量化研究系统。当前版本聚焦历史行情获取、技术策略回测、风险指标计算和可视化展示，不包含真实交易、真实下单或券商实盘接入。

## 项目功能

- 获取 A 股历史日线行情，并支持本地缓存
- 支持双均线、动量、RSI 三种基础策略
- 提供考虑手续费和滑点的单标的历史回测
- 计算总收益率、年化收益率、最大回撤、夏普比率、年化波动率、胜率等指标
- 生成基础风险提示和中文策略分析报告
- 通过 Streamlit 页面进行参数配置、图表展示和结果查看

## 项目结构

```text
ai_quant_system/
├── AGENTS.md
├── README.md
├── requirements.txt
├── config.py
├── app.py
├── data/
│   ├── __init__.py
│   ├── akshare_loader.py
│   └── data_cleaner.py
├── strategy/
│   ├── __init__.py
│   ├── ma_strategy.py
│   ├── momentum_strategy.py
│   └── rsi_strategy.py
├── backtest/
│   ├── __init__.py
│   ├── engine.py
│   └── metrics.py
├── risk/
│   ├── __init__.py
│   └── risk_manager.py
├── report/
│   ├── __init__.py
│   └── report_generator.py
├── cache/
├── outputs/
└── tests/
    └── test_metrics.py
```

## 安装依赖命令

```powershell
cd ai_quant_system
pip install -r requirements.txt
```

## 运行命令

```powershell
cd ai_quant_system
streamlit run app.py
```

如果 Windows 环境下 `streamlit` 命令未加入 PATH，可使用：

```powershell
cd ai_quant_system
py -m streamlit run app.py
```

## 示例股票代码

- `000001` 平安银行
- `600519` 贵州茅台
- `601318` 中国平安
- `000333` 美的集团

## 当前版本功能

- 历史行情获取与缓存
- 单标的技术策略回测
- 风险评估与文本报告生成
- Streamlit 可视化展示
- Windows + VS Code + PowerShell 环境运行支持

## 后续计划

- 接入 Tushare
- 接入 OpenAI API 生成智能报告
- 增加多因子选股
- 增加组合回测
- 增加模拟交易
- 后续再考虑实盘接口

## 风险声明

本项目仅用于学习、研究和模拟分析，不构成任何投资建议，不保证盈利，不应直接用于实盘交易。
