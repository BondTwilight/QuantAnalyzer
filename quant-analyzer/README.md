# QuantAnalyzer v3.3 🧠

> 全自动量化策略分析平台 — Python 3.14 + Streamlit + Backtrader + AKShare

[English](#) | [中文](#)

---

## 🚀 快速开始

```bash
cd quant-analyzer

# 安装依赖
pip install -r requirements.txt

# 运行主应用（推荐 v3.3）
streamlit run enhanced_app.py

# 或运行经典版本
streamlit run app.py
```

## ✨ v3.3 新功能

| 模块 | 功能 | 状态 |
|------|------|------|
| 🆕 财务分析 | 杜邦分析、风险评分、财务报表可视化 | ✅ |
| 🆕 策略编辑器 | 7种策略模板、可视化参数配置、一键回测 | ✅ |
| 🆕 因子研究 | 30+因子、IC分析、因子绩效评估 | ✅ |
| 🆕 风控中心 | 仓位管理、止损计算、回撤监控、模拟交易 | ✅ |
| 🆕 自动运行 | 全自动回测调度、数据更新、AI学习、GitHub同步 | ✅ |
| 🆕 AKShare | 新增AKShare数据源，替代BaoStock更丰富 | ✅ |
| 🆕 GitHub资源 | 自动追踪热门量化开源项目 | ✅ |
| 🆕 AI学习 | 自进化策略优化引擎 | ✅ |

## 📂 项目结构

```
quant-analyzer/
├── app.py                 # 主应用 v3.2
├── enhanced_app.py        # 主应用 v3.3 ⭐推荐
├── config.py              # 全局配置
├── auto_runner.py         # 全自动运行引擎
├── github_monitor.py      # GitHub资源监控
├── core/
│   ├── engine.py          # Backtrader回测引擎
│   ├── ai_analyzer.py     # AI多模型分析
│   ├── scheduler.py        # 定时调度
│   └── ...
├── data/
│   ├── fetcher.py         # 数据获取（BaoStock + AKShare）
│   └── ...
├── strategy_library/       # 27个内置策略
│   ├── ma_cross.py        # 双均线
│   ├── macd.py            # MACD
│   ├── bollinger.py        # 布林带
│   ├── rsi_strategy.py     # RSI
│   └── ...
└── cache/                 # 运行时缓存
    ├── runner_state.json   # 运行状态
    └── github_sync.json    # GitHub同步数据
```

## 📊 功能总览

### 10大页面

1. **🏠 首页看板** — 策略表现总览、净值曲线、快捷操作
2. **📊 回测中心** — 策略回测、参数配置、AI分析
3. **✏️ 策略编辑器** — 可视化模板、代码解析、批量回测
4. **💰 财务分析** — 杜邦分析、风险评分、投资建议
5. **📈 市场数据** — K线图、技术指标（RSI/MACD）
6. **🔬 因子研究** — 因子池、IC分析、绩效评估
7. **🛡️ 风控中心** — 仓位管理、止损、回撤监控、模拟交易
8. **🤖 AI分析** — 策略审查、市场研判、自学习进化
9. **🔄 自动运行** — 全自动调度、日志监控
10. **📚 GitHub资源** — 量化开源项目追踪

## 🤖 AI多模型支持

| 模型 | 费用 | 特点 |
|------|------|------|
| Cerebras | 免费 | 70B大模型，无限制 |
| 智谱 GLM-4 | 免费注册 | 中文理解强 |
| Groq | 免费注册 | 超快推理 |
| DeepSeek V3 | 新用户免费500万token | 推理能力强 |
| SiliconFlow | 免费14元/天 | 多模型可选 |
| Google Gemini 2.0 | 免费 | 最强免费模型之一 |

## ⚡ 全自动运行

```bash
# 完整自动循环（所有任务）
python auto_runner.py --once

# 仅回测
python auto_runner.py --backtest

# 仅更新数据
python auto_runner.py --data

# 启动守护进程
python auto_runner.py --daemon

# 强制执行（忽略时间检查）
python auto_runner.py --backtest --force
```

### 调度计划
- **每日回测**: 工作日 15:30（收盘后）
- **数据更新**: 每日 16:00
- **AI学习**: 每3天
- **GitHub同步**: 每周

## 📦 数据源

| 数据源 | 说明 | 安装 |
|--------|------|------|
| BaoStock | A股历史数据 | 内置 |
| AKShare | 财经数据（推荐） | `pip install akshare` |

## 🔧 环境要求

- Python 3.10+
- Streamlit 1.30+
- Backtrader 1.9+
- Pandas, NumPy, Plotly

## 📝 策略库（27个策略）

**趋势跟踪**: 双均线、MACD、DualThrust、海龟、Donchian、布林带突破

**均值回归**: 布林带、RSI均值回归、配对交易

**动量因子**: 动量、行业轮动、因子择时

**多因子**: 多因子选股、小市值、价值投资

**技术指标**: VWAP、OBV、一目均衡表、超级趋势

**事件驱动**: 财报、分红、再平衡

## 📈 参考的开源项目

- [AKShare](https://github.com/akfamily/akshare) — 免费财经数据
- [Qlib](https://github.com/AI4Finance-Foundation/Qlib) — 微软AI量化
- [vn.py](https://github.com/vnpy/vnpy) — 量化交易平台
- [TradingAgents-CN](https://github.com/wjb-johnny/TradingAgents-CN) — 多智能体AI
- [SmartQuant-Trading-System](https://github.com/jiangfei-maker/SmartQuant-Trading-System) — 财务分析参考

## ⚠️ 注意事项

1. **.env 文件**: 不要泄露 API Key
2. **回测不等于实盘**: 历史回测不代表未来收益
3. **风险控制**: 建议在「风控中心」配置止损
4. **TA-Lib**: 可选安装，用于加速技术指标计算

## 📄 License

MIT License

---

*Powered by QuantAnalyzer v3.3 — 全自动量化策略分析平台*
