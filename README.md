# ai_quant_system

## 项目简介

`ai_quant_system` 是一个基于 Python + AKShare + Streamlit 的 A 股量化研究系统。当前版本聚焦历史行情获取、技术策略回测、风险指标计算和可视化展示，不包含真实交易、真实下单或券商实盘接入。

## 项目功能

- 获取 A 股历史日线行情，并支持本地缓存
- 获取基准指数历史行情，默认使用沪深 300
- 支持双均线、动量、RSI 三种基础策略
- 提供考虑手续费和滑点的单标的历史回测
- 支持多股票批量回测与排行榜展示
- 计算总收益率、基准收益率、超额收益率、年化收益率、最大回撤、夏普比率、年化波动率、胜率等指标
- 生成基础风险提示和中文策略分析报告
- 生成更专业的规则模板中文策略研究报告，并预留未来 AI 报告接口
- 支持回测结果、交易明细、参数敏感性分析导出 Excel
- 支持批量回测结果导出 Excel
- 提供净值曲线、回撤曲线和买卖点标记图
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
│   ├── batch_runner.py
│   ├── engine.py
│   ├── exporter.py
│   ├── metrics.py
│   └── sensitivity.py
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
- 多股票批量回测与排行榜
- 基准收益比较与超额收益分析
- 参数敏感性分析（当前支持双均线策略）
- 回测结果与交易明细 Excel 导出
- 中文策略分析报告 txt 导出
- 风险评估与文本报告生成
- Streamlit 可视化展示
- Windows + VS Code + PowerShell 环境运行支持

## 导出说明

- 回测结果导出到 `outputs/backtest_股票代码_策略名.xlsx`
- 交易明细导出到 `outputs/trades_股票代码_策略名.xlsx`
- 双均线敏感性分析导出到 `outputs/sensitivity_股票代码_策略名.xlsx`
- 批量回测排行榜导出到 `outputs/batch_backtest_策略名_开始日期_结束日期.xlsx`
- 中文策略分析报告导出到 `outputs/report_股票代码_策略名.txt`

## 回测说明

- 默认基准指数为沪深 300，代码为 `000300`
- 指数数据优先使用 AKShare 的 `index_zh_a_hist` 接口，并带本地缓存与异常回退机制
- 为防止未来函数，所有策略信号均在下一交易日执行
- 多股票输入格式为英文逗号分隔，例如 `000001,600519,300750`
- 当前报告模块默认使用规则模板生成，不依赖 OpenAI API
- 当前版本只支持历史研究与模拟分析，不包含实盘交易

## 云端部署说明

- `app.py` 依赖 `data.akshare_loader.get_index_daily` 获取基准指数历史行情
- `get_index_daily` 当前已内置，优先使用 `AKShare.index_zh_a_hist`
- 若云端环境 AKShare 某个指数接口临时不可用，程序会自动尝试备用指数接口，并给出清晰错误信息
- 为降低 Streamlit Cloud 环境差异带来的问题，`requirements.txt` 已显式约束 `akshare>=1.18.63`

## 后续计划

- 接入 Tushare
- 接入 OpenAI API 生成智能报告
- 增加多因子选股
- 增加组合回测
- 增加模拟交易
- 后续再考虑实盘接口

## 风险声明

本项目仅用于学习、研究和模拟分析，不构成任何投资建议，不保证盈利，不应直接用于实盘交易。
