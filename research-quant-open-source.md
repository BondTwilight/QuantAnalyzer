# GitHub Trending 量化交易开源项目调研

> 调研时间：2026-04-02  
> 调研方式：GitHub Topics / LibHunt / Web Search  
> 搜索关键词：quant, trading bot, backtrader, algorithmic trading, A股量化

---

## 一、综合排名（按 Stars 降序）

### 1. Freqtrade ⭐ 48,100
- **URL**: https://github.com/freqtrade/freqtrade
- **语言**: Python
- **描述**: 免费开源的加密货币交易机器人，支持多种交易策略（网格、DCA、AI策略等），可在 Binance、Hyperliquid 等 15+ 交易所自动运行。
- **A股相关**: ❌ 仅支持加密货币
- **Backtrader集成**: ❌ 独立框架，有自己的回测引擎

### 2. OpenBB ⭐ 64,300
- **URL**: https://github.com/OpenBB-finance/OpenBB
- **语言**: Python
- **描述**: 开源金融数据平台，服务分析师、量化交易员和AI代理。提供多市场数据获取、可视化分析及策略回测。
- **A股相关**: ✅ 支持A股等多市场
- **Backtrader集成**: ❌ 数据平台，非策略框架，但可为其提供数据

### 3. Qlib (微软) ⭐ 40,000
- **URL**: https://github.com/microsoft/qlib
- **语言**: Python (99.2%)
- **描述**: 微软开源的AI量化投资平台，支持监督学习、市场动态建模和强化学习。内置A股因子库（cn_data，2007-2020年800只股票日线+分钟线数据）。
- **A股相关**: ✅ 完全支持，内置中国A股数据包和示例
- **Backtrader集成**: ❌ 独立ML框架，策略范式与Backtrader不同，但可提取Alpha因子用于Backtrader策略

### 4. vn.py (VeighNa) ⭐ 38,800
- **URL**: https://github.com/vnpy/vnpy
- **语言**: Python (99.4%)
- **描述**: 国产Python开源量化交易平台框架，广泛应用于私募基金、证券公司。自带回测引擎(cta_backtester)，支持参数优化。
- **A股相关**: ✅ 支持A股（中泰XTP、华鑫奇点、东证OST、东方财富EMT接口）
- **Backtrader集成**: ❌ 自带回测引擎，与Backtrader独立

### 5. daily_stock_analysis ⭐ 27,700
- **URL**: https://github.com/zhulinsen/daily_stock_analysis
- **语言**: Python (78.9%), TypeScript (18.0%)
- **描述**: LLM驱动的A/H/美股智能分析器，AI决策仪表盘 + 多数据源行情 + 实时新闻 + 多渠道推送（企业微信/飞书/Telegram等）。支持GitHub Actions零成本定时运行。
- **A股相关**: ✅ 完全支持A股、港股、美股
- **Backtrader集成**: ❌ AI分析工具，非策略回测框架

### 6. awesome-quant ⭐ 25,300
- **URL**: https://github.com/wilsonfreitas/awesome-quant
- **语言**: HTML
- **描述**: 量化金融领域顶级开源库和资源汇总，涵盖交易机器人、算法交易、金融数据、回测框架等。
- **A股相关**: ⚠️ 资源列表，包含部分A股相关项目
- **Backtrader集成**: N/A 资源列表

### 7. LEAN (QuantConnect) ⭐ 18,100
- **URL**: https://github.com/QuantConnect/Lean
- **语言**: C#
- **描述**: QuantConnect的开源算法交易引擎，支持Python和C#，涵盖研究、回测和实时交易。
- **A股相关**: ❌ 主要面向美股
- **Backtrader集成**: ❌ 独立引擎

### 8. NautilusTrader ⭐ 21,600
- **URL**: https://github.com/nautechsystems/nautilus_trader
- **语言**: Rust (64.2%), Python (27.6%)
- **描述**: 生产级Rust原生多资产交易引擎，事件驱动架构，高性能回测和实时执行。足够快用于训练AI交易代理。
- **A股相关**: ❌ 主要面向数字资产和传统金融（非A股专向）
- **Backtrader集成**: ❌ 独立引擎，架构与Backtrader不同

### 9. AKShare ⭐ 12,000+
- **URL**: https://github.com/akfamily/akshare
- **语言**: Python
- **描述**: 开源金融数据接口库，专门获取A股、港股、美股等市场行情数据。数据源覆盖极广。
- **A股相关**: ✅ 核心功能即为A股数据
- **Backtrader集成**: ✅ 可作为Backtrader的数据源（Feed），提供A股日线/分钟线数据

### 10. FinRL ⭐ 14,600
- **URL**: https://github.com/AI4Finance-Foundation/FinRL
- **语言**: Jupyter Notebook (83.1%), Python (16.9%)
- **描述**: 首个开源金融强化学习框架，支持A2C/DDPG/PPO/TD3/SAC等DRL算法。14种数据源含Akshare/Baostock/Tushare等A股源。
- **A股相关**: ✅ 支持A股（通过AkShare/Baostock/Tushare）
- **Backtrader集成**: ❌ 独立RL框架，策略范式不同。但其DRL策略思路可借鉴移植到Backtrader

### 11. QBot ⭐ 16,800
- **URL**: https://github.com/ufund-me/qbot
- **语言**: Python
- **描述**: AI驱动的量化投资研究平台，支持本地部署，包含量化策略研究和回测功能。
- **A股相关**: ⚠️ 有A股相关功能
- **Backtrader集成**: ❌ 独立平台

### 12. abu (阿布量化) ⭐ 16,700
- **URL**: https://github.com/bbfamily/abu
- **语言**: Python
- **描述**: 阿布量化交易系统，支持股票、期权、期货、比特币。有配套书籍《量化交易之路》。
- **A股相关**: ✅ 支持A股
- **Backtrader集成**: ❌ 独立框架，但策略逻辑可参考移植

### 13. QUANTAXIS ⭐ 10,200
- **URL**: https://github.com/yutiansut/QUANTAXIS
- **语言**: Python (73.0%), Rust (20.1%)
- **描述**: 全栈式中文量化平台，支持任务调度、分布式部署。Rust核心100倍性能提升，支持QMT对接A股实盘。
- **A股相关**: ✅ 完全支持，专为中国金融设计
- **Backtrader集成**: ❌ 独立全栈平台

### 14. Backtrader (框架本体) ⭐ 10,000+
- **URL**: https://github.com/mementum/backtrader
- **语言**: Python
- **描述**: 功能丰富的Python回测和交易框架，事件驱动架构，支持指标、策略、分析器的模块化组合。
- **A股相关**: ✅ 支持任何市场数据（通过自定义数据Feed）
- **Backtrader集成**: ✅ 自身即为Backtrader框架

### 15. backtesting.py ⭐ 8,100
- **URL**: https://github.com/kernc/backtesting.py
- **语言**: Python (99.4%)
- **描述**: 轻量级Python回测框架，API简洁，内置参数优化器和交互式可视化，学习曲线平缓。
- **A股相关**: ✅ 支持任何有K线数据的品种
- **Backtrader集成**: ⚠️ 独立框架，API不同，但策略逻辑可参考。backtrader策略模式类似（Strategy.next()），移植较容易

### 16. quant-trading ⭐ 9,600
- **URL**: https://github.com/je-suis-tm/quant-trading
- **语言**: Python
- **描述**: 包含VIX计算、模式识别、配对交易、RSI、布林带等多种Python量化策略的实现集合。
- **A股相关**: ⚠️ 部分策略适用
- **Backtrader集成**: ✅ 纯Python策略代码，可直接移植为Backtrader Strategy类

### 17. zvt ⭐ 4,041
- **URL**: https://github.com/zvtvz/zvt
- **语言**: Python
- **描述**: 模块化量化框架，覆盖数据采集、分析、回测全流程。
- **A股相关**: ✅ 支持A股
- **Backtrader集成**: ❌ 独立框架

### 18. TradeMaster ⭐ 2,549
- **URL**: https://github.com/kungfucode/TradeMaster
- **语言**: Jupyter Notebook
- **描述**: 基于强化学习的开源量化交易平台。
- **A股相关**: ⚠️ 有A股支持
- **Backtrader集成**: ❌ 独立RL平台

### 19. zipline-reloaded ⭐ 1,700
- **URL**: https://github.com/stefan-jansen/zipline-reloaded
- **语言**: Python (93.5%)
- **描述**: 由Quantopian最初开发的回测框架，事件驱动系统。PyData生态集成（Pandas/Scikit-learn）。
- **A股相关**: ❌ 面向美股（需自行适配A股交易规则）
- **Backtrader集成**: ❌ 独立框架

### 20. vectorbt ⭐ 3,000+
- **URL**: https://github.com/polakowo/vectorbt
- **语言**: Python
- **描述**: 基于向量化操作的高性能量化分析和回测库，并行计算，交互式可视化。
- **A股相关**: ✅ 支持任何市场数据
- **Backtrader集成**: ❌ 独立框架（向量化 vs 事件驱动，范式不同）

---

## 二、分类整理

### 🇨🇳 直接支持A股的项目

| 项目 | Stars | 类型 | 可为Backtrader提供什么 |
|------|-------|------|----------------------|
| Qlib | 40k | AI量化平台 | Alpha因子、ML模型 |
| vn.py | 38.8k | 量化平台 | A股数据接口、实盘通道 |
| daily_stock_analysis | 27.7k | AI分析器 | 新闻/舆情数据 |
| AKShare | 12k+ | 数据接口 | **A股数据Feed** |
| abu | 16.7k | 量化框架 | 策略参考 |
| QUANTAXIS | 10.2k | 全栈平台 | A股数据+实盘 |
| Backtrader | 10k+ | 回测框架 | **核心框架本体** |
| FinRL | 14.6k | RL框架 | DRL策略思路 |
| quant-trading | 9.6k | 策略集合 | **可直接移植的策略代码** |
| zvt | 4k | 量化框架 | A股数据 |
| backtesting.py | 8.1k | 回测框架 | 策略参考 |

### 🔌 可直接集成到Backtrader的项目

1. **AKShare** — 作为Data Feed提供A股/港股/美股数据
2. **quant-trading** — 纯Python策略代码，可直接改写为Backtrader Strategy
3. **BaoStock** — 当前QuantAnalyzer已在用的数据源（稳定直连）

### 🤖 AI/ML 量化项目（可借鉴策略思路）

| 项目 | Stars | AI技术 | A股支持 |
|------|-------|--------|---------|
| Qlib | 40k | 监督学习 + 强化学习 | ✅ |
| FinRL | 14.6k | 深度强化学习 | ✅ |
| TradeMaster | 2.5k | 强化学习 | ⚠️ |
| daily_stock_analysis | 27.7k | LLM大模型 | ✅ |

### 📊 回测框架对比

| 框架 | Stars | 语言 | 性能 | 学习曲线 | A股 |
|------|-------|------|------|----------|-----|
| Backtrader | 10k+ | Python | 中 | 中 | ✅ |
| backtesting.py | 8.1k | Python | 中高 | 低 | ✅ |
| LEAN | 18.1k | C#/Python | 高 | 高 | ❌ |
| NautilusTrader | 21.6k | Rust/Python | 极高 | 高 | ❌ |
| QUANTAXIS | 10.2k | Python/Rust | 高 | 中 | ✅ |
| zipline-reloaded | 1.7k | Python | 中 | 中 | ❌ |
| vectorbt | 3k+ | Python | 高 | 中 | ✅ |

---

## 三、关键发现与建议

### 1. 直接可用于QuantAnalyzer的策略资源
- **quant-trading** (⭐9.6k): 策略代码最易移植到Backtrader，包含RSI、布林带、配对交易等经典策略
- **AKShare**: 可替代BaoStock作为更丰富的数据源（但BaoStock稳定性更好）

### 2. AI增强方向
- **Qlib** (⭐40k): 微软出品，直接支持A股因子库，ML模型可用于生成交易信号
- **FinRL** (⭐14.6k): 强化学习策略可用于Backtrader的Signal机制
- **daily_stock_analysis** (⭐27.7k): LLM驱动的分析工具，可借鉴其新闻/舆情集成方式

### 3. 实盘交易路径
- **vn.py** (⭐38.8k): 成熟的A股实盘框架，有券商接口（XTP/奇点/OST/EMT）
- **QUANTAXIS** (⭐10.2k): 支持QMT对接

### 4. 项目活跃度排名（2025-2026最活跃）
1. daily_stock_analysis — v3.12.0 (2026-04-01)
2. Qlib — v0.9.7 (2025-08-15)
3. NautilusTrader — v1.224.0 (2026-03-03)
4. FinRL — v0.3.8 (2026-03-20)
5. Freqtrade — 持续高频更新
