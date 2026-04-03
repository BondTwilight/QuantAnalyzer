---
title: QuantBrain AI量化策略自学习系统
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# 🧠 QuantBrain — AI量化策略自学习系统

> 全自动量化策略分析平台 — Streamlit + Backtrader + BaoStock + GLM AI

## 功能

- 📊 **信号仪表盘** — 持仓盈亏 + 最新信号 + AI学习进度
- 📡 **每日扫描** — 多股扫描生成买卖信号，可一键买入
- 💼 **持仓跟踪** — 实时盈亏 + 手动卖出 + 全部交易记录
- 📈 **K线分析** — K线+均线+MACD+RSI+BOLL + AI诊断
- 🤖 **AI策略学习** — GitHub搜索 + AI生成新策略 + AI优化现有策略 + 策略库
- 🔄 **策略回测** — 代码回测 + 内置策略
- ⚙️ **设置** — 资金设置 + 数据源 + 公网访问

## 云存储

本应用使用 **GitHub Contents API** 实现跨会话状态持久化（信号、持仓、策略知识库）。

需要设置以下 Secrets：
- `GITHUB_TOKEN` — GitHub Personal Access Token (需要 `repo` 权限)
- `GITHUB_STORAGE_REPO` — 存储数据的仓库名称 (如 `BondTwilight/QuantAnalyzer`)
