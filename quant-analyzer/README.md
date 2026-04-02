---
title: QuantAnalyzer 量化策略分析平台
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# 📊 QuantAnalyzer 量化策略分析平台

基于 Backtrader + BaoStock + Streamlit 的 A股量化策略回测分析平台。

## 功能特性

- 🧠 **8大量化策略**：双均线交叉、RSI均值回归、动量策略、多因子选股、行业轮动、布林带策略、聚宽小市值、聚宽DualThrust
- 📈 **10+专业指标**：年化收益、夏普比率、Sortino比率、最大回撤、胜率、盈亏比、Calmar比率、Beta、Alpha等
- 🤖 **AI智能分析**：接入智谱GLM-4-Flash（免费）、DeepSeek、OpenAI，无API Key也有规则分析兜底
- 📊 **专业可视化**：Plotly交互式图表，净值曲线、收益分布、风险散点图
- 🔄 **自动调度**：工作日15:30自动回测，每周日AI自学习
- 📋 **报告导出**：HTML/Excel格式报告

## 技术栈

- Python 3.11 + Streamlit
- Backtrader (回测引擎)
- BaoStock (A股数据源)
- Plotly (可视化)
- SQLite (数据存储)

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```
