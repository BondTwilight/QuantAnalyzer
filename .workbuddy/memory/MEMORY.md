# 长期记忆

## 用户偏好
- 小原，微信机器人客户端接入
- 倾向完整解决方案，不需要逐步确认

## 项目记录

### QuantAnalyzer (量化策略分析平台) - 2026-04-02 更新

**版本: v3.0**
- 路径: `quant-analyzer/`
- GitHub: https://github.com/BondTwilight/QuantAnalyzer
- 技术栈: Python 3.14 + Streamlit + Backtrader + BaoStock + Plotly + SQLite

**新增功能:**
- 策略库补全: 20个策略 (原有10个 + 新增10个)
- 量化平台对比页面: 12+平台对比 (🌐导航)
- AI模型精简: 17个→7个精选模型
- 一键配置脚本: `setup_ai.py`
- 聚宽数据源: `data/joinquant.py`
- 市场看板改进: 手动刷新 + 双数据源切换

**AI推荐模型:**
- Cerebras (免费无限制)
- 智谱GLM-4-Flash (国产)
- Groq (超快推理)

**公网: https://bondtwilight-quant-analyzer.hf.space**

**注意:**
- 小原网络有代理/VPN会拦截部分443端口
- gh CLI已登录但GitHub网络不稳定
- BaoStock稳定可用，聚宽需注册
