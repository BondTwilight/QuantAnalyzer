# 长期记忆

## 用户偏好
- 小原，微信机器人客户端接入
- 倾向完整解决方案，不需要逐步确认

## 项目记录

### QuantAnalyzer (量化策略分析平台) - 2026-04-02
- 路径: `quant-analyzer/`
- 技术栈: Python + Streamlit + Backtrader + AKShare + Plotly + SQLite
- 功能: 6个量化策略回测 + 10+专业指标 + AI分析 + 每日自动调度 + 公网部署
- 配置: 回测10年, 沪深300基准, 初始资金10万
- 平台调研: 果仁网无API(禁爬虫), 聚宽有jqdatasdk(需注册), AKShare免费推荐
- Python版本: 3.14 (empyrical不兼容, 已自行实现指标计算)
