# QuantAnalyzer — 量化策略分析平台

一个全自动的量化策略分析平台，集成Backtrader回测引擎、专业量化指标、AI智能分析、每日自动调度。

## ✨ 功能特性

- **6个内置策略**: 双均线交叉、RSI均值回归、动量、多因子选股、行业轮动、布林带
- **10+专业指标**: 年化收益、最大回撤、夏普/Sortino/Calmar比率、胜率、盈亏比、Beta等
- **AI智能分析**: 接入DeepSeek/智谱/OpenAI等多模型，策略分析+市场解读+自学习进化
- **每日自动回测**: 工作日15:30自动运行全策略回测 + AI分析
- **可视化仪表盘**: 净值曲线、雷达图、回撤图、散点图等交互式图表
- **自定义策略**: 支持上传Backtrader策略文件
- **公网访问**: 支持Cloudflare Tunnel/ngrok随时随地访问

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. (可选) 配置AI API Key

在系统设置页面配置，或创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_key_here
```

### 3. 启动

```bash
# 启动Web应用
streamlit run app.py

# 同时启动自动调度
python -c "from core.scheduler import setup_scheduler; setup_scheduler()" &
```

## 📁 项目结构

```
quant-analyzer/
├── app.py                    # 主入口
├── config.py                 # 全局配置
├── requirements.txt          # 依赖
├── Dockerfile                # Docker部署
├── core/
│   ├── engine.py             # Backtrader回测引擎
│   ├── metrics.py            # 量化指标计算
│   ├── ai_analyzer.py        # AI分析模块
│   └── scheduler.py          # 自动调度
├── strategies/
│   ├── ma_cross.py           # 双均线交叉
│   ├── rsi_strategy.py       # RSI策略
│   ├── momentum.py           # 动量策略
│   ├── multi_factor.py       # 多因子选股
│   ├── sector_rotation.py    # 行业轮动
│   └── bollinger.py          # 布林带策略
├── data/
│   └── fetcher.py            # AKShare数据层
├── pages/
│   ├── 1_compare.py          # 策略总览
│   ├── 2_compare.py          # 策略对比
│   ├── 3_detail.py           # 策略详情
│   ├── 4_ai.py               # AI分析
│   ├── 5_reports.py          # 回测报告
│   └── 6_settings.py         # 系统设置
├── utils/
│   └── report.py             # 报告生成
├── uploads/                  # 自定义策略
└── reports/                  # 生成的报告
```

## 🌐 公网部署

### 方法1: Streamlit Cloud (免费)
推送代码到GitHub，在 [streamlit.io/cloud](https://streamlit.io/cloud) 创建应用。

### 方法2: Cloudflare Tunnel (推荐)
```bash
cloudflared tunnel --url http://localhost:8501
```

### 方法3: Docker
```bash
docker build -t quant-analyzer .
docker run -p 8501:8501 -v ./data:/app/data quant-analyzer
```

## ⚠️ 免责声明

本平台仅供学习研究使用，不构成任何投资建议。历史回测不代表未来收益，投资有风险，入市需谨慎。
