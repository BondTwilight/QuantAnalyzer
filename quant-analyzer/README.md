# 📊 QuantAnalyzer — 量化策略分析平台

> 全自动量化策略回测 + AI智能分析 + 公网访问

## ✨ 功能特性

- **8大量化策略**: 双均线交叉、RSI均值回归、动量、多因子选股、行业轮动、布林带、聚宽小市值、聚宽DualThrust
- **专业指标**: 夏普比率、Sortino、Calmar、最大回撤、Beta、胜率、盈亏比等10+指标
- **AI分析**: 智谱AI(免费)、DeepSeek、OpenAI 多模型接入，无Key也能用规则分析
- **数据源**: BaoStock（免费A股数据，无需API Key）
- **自动化**: 支持定时调度，每日自动回测
- **公网部署**: 支持 Hugging Face Spaces 免费部署

## 🚀 快速启动

### 本地运行
```bash
pip install -r requirements.txt
streamlit run app.py
```
然后打开 http://localhost:8501

### 首次使用
1. 打开网站后，点击左侧「运行全部回测」
2. 等待数据获取和回测完成（首次约30秒）
3. 查看策略排名、净值曲线、AI分析等

### 配置AI（可选）
在设置页面配置智谱AI API Key（[免费注册](https://open.bigmodel.cn/)），
获得更深入的策略分析和市场解读。

## ☁️ 免费公网部署 (Hugging Face Spaces)

1. Fork 此仓库到你的 GitHub
2. 访问 [huggingface.co/new-space](https://huggingface.co/new-space)
3. 选择 **Docker** 类型
4. 连接你的 GitHub 仓库
5. 等待构建完成，获得公网地址

## 📁 项目结构

```
quant-analyzer/
├── app.py                    # Streamlit 主入口
├── config.py                 # 全局配置
├── core/
│   ├── engine.py             # Backtrader 回测引擎
│   ├── metrics.py            # 量化指标计算
│   ├── ai_analyzer.py        # AI 分析模块
│   └── scheduler.py          # 自动调度
├── strategies/
│   ├── ma_cross.py           # 双均线交叉
│   ├── rsi_strategy.py       # RSI 均值回归
│   ├── momentum.py           # 动量策略
│   ├── multi_factor.py       # 多因子选股
│   ├── sector_rotation.py    # 行业轮动
│   ├── bollinger.py          # 布林带策略
│   └── jq_small_cap.py       # 聚宽经典策略
├── data/fetcher.py           # BaoStock 数据层 + SQLite
└── utils/report.py           # 日报生成
```

## ⚠️ 免责声明

本平台仅供学习和研究使用，不构成任何投资建议。
量化策略的过往表现不代表未来收益，投资有风险，入市需谨慎。
