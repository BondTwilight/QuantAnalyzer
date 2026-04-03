# 长期记忆

## 用户偏好
- 小原，微信机器人客户端接入
- 倾向完整解决方案，不需要逐步确认

## 项目记录

### QuantAnalyzer (量化策略分析平台) - 2026-04-03 更新

**版本: v3.2**
- 路径: `quant-analyzer/`
- GitHub: https://github.com/BondTwilight/QuantAnalyzer
- 技术栈: Python 3.14 + Streamlit + Backtrader + BaoStock + Plotly + SQLite

**v3.2 新增:**
- G-Prophet AI预测平台深度集成 (data/gprophet.py)
  - AI价格预测: 蒙特卡洛/LSTM/Transformer/集成
  - 多算法对比预测 (交叉验证)
  - 技术指标分析 (RSI/MACD/布林带/KDJ/SMA/EMA)
  - AI分析报告: 单股票(58点) / 5维深度分析(150点)
  - 市场情绪: 恐惧贪婪指数 + A股/美股市场概览
  - 支持 CN/US/HK/CRYPTO 4大市场
- 策略逻辑审查模块 (core/strategy_audit.py)
  - 程序逻辑: T+1/涨跌停/停牌/未来函数/状态机
  - 策略逻辑: 指标适用性/参数敏感性/过拟合风险
  - A-F评级 + Diff修复方案 + 极限推演

**v3.1 新增:**
- 首页重构 / 策略PK竞技场重构
- 专业分析: 收益率/财务数据/风险指标/策略审查

**v3.0 功能:**
- 策略库: 20个策略
- AI多模型: 7个精选模型
- 12+页面 / 聚宽+BaoStock数据源

**AI推荐模型:**
- Cerebras (免费无限制)
- 智谱GLM-4-Flash (国产)
- Groq (超快推理)

**公网: https://bondtwilight-quant-analyzer.hf.space**

**注意:**
- 小原网络有代理/VPN会拦截部分443端口
- gh CLI已登录但GitHub网络不稳定
- BaoStock稳定可用，聚宽需注册
- G-Prophet API: https://www.gprophet.com (需注册获取API Key)
