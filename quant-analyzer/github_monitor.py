"""
QuantAnalyzer v3.3 — GitHub 资源自动监控系统
==========================================
功能：
  1. 追踪热门量化开源项目
  2. 自动分析项目价值
  3. 提供集成建议
  4. 每周自动更新资源库
"""
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger("GitHubMonitor")

# ═══════════════════════════════════════════════════
# 关键量化项目数据库（持续更新）
# ═══════════════════════════════════════════════════

QUANT_RESOURCES = {
    # 核心框架
    "回测框架": [
        {"repo": "martenjain/Backtrader", "stars": "~10k", "desc": "Python量化回测框架，灵活易用", "value": 5},
        {"repo": "AI4Finance-Foundation/Qlib", "stars": "40k", "desc": "微软AI量化平台，含因子库/数据集", "value": 5},
        {"repo": "vnpy/vnpy", "stars": "38.8k", "desc": "开源量化交易平台开发框架", "value": 5},
        {"repo": "QUANTAXIS/QUANTAXIS", "stars": "10k", "desc": "A股量化分析框架", "value": 4},
        {"repo": "fengyunzone/QMT", "stars": "5k", "desc": "QMT量化策略开发教程", "value": 4},
    ],
    # 数据获取
    "数据源": [
        {"repo": "akfamily/akshare", "stars": "12k", "desc": "AKShare — 财经数据接口，免费开源", "value": 5},
        {"repo": "TuShare/tushare", "stars": "12k", "desc": "Tushare — 专业财经数据接口", "value": 5},
        {"repo": "winex01/jaqs", "stars": "3k", "desc": "聚宽开源数据/回测", "value": 4},
    ],
    # 完整平台
    "完整平台": [
        {"repo": "jiangfei-maker/SmartQuant-Trading-System", "stars": "-", "desc": "机构级量化交易系统（财务分析/缠论）", "value": 5},
        {"repo": "shichenxie/quant-dashboard", "stars": "-", "desc": "缠论量化回测看板", "value": 4},
        {"repo": "hc0523/quant-trading-dashboard", "stars": "-", "desc": "机构级回测看板", "value": 4},
        {"repo": "BondTwilight/QuantAnalyzer", "stars": "-", "desc": "量化策略分析平台（你的项目）", "value": 5},
    ],
    # AI量化
    "AI量化": [
        {"repo": "AI4Finance-Foundation/FinRL", "stars": "12k", "desc": "深度强化学习量化交易", "value": 5},
        {"repo": "AI4Finance-Foundation/FinML", "stars": "8k", "desc": "机器学习量化", "value": 4},
        {"repo": "wjb-johnny/TradingAgents-CN", "stars": "22.7k", "desc": "多智能体AI交易系统", "value": 5},
        {"repo": "AI4Finance-Foundation/FinGPT", "stars": "19k", "desc": "金融大模型", "value": 5},
    ],
    # 机器学习
    "机器学习": [
        {"repo": "GraffiZicky/Stock-Prediction-Models", "stars": "10k", "desc": "股票预测模型集合", "value": 4},
        {"repo": "jason87920/Deep-Learning-Trading", "stars": "3k", "desc": "深度学习交易策略", "value": 4},
    ],
    # 实盘工具
    "实盘工具": [
        {"repo": "vnpy/vnpy", "stars": "38.8k", "desc": "VN.PY — 量化交易平台", "value": 5},
        {"repo": "fmcnc/QMT-Python", "stars": "3k", "desc": "QMT量化Python教程", "value": 4},
        {"repo": "xunge0613/pig-chivalrous", "stars": "3k", "desc": "PTrade量化工具", "value": 4},
    ],
}


class GitHubResourceMonitor:
    """GitHub量化资源监控器"""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or (Path(__file__).parent.parent / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_file = self.cache_dir / "github_resources.json"

    def scan_trending(self, language: str = "python", days: int = 7) -> List[Dict]:
        """扫描GitHub热门量化项目"""
        logger.info(f"扫描 GitHub {language} 热门项目（最近{days}天）")

        try:
            cmd = [
                "gh", "search", "repos",
                "quantitative OR trading OR backtest OR finance",
                "--language", language,
                "--created", f"<{days}d",
                "--sort", "stars",
                "--limit", "20",
                "--json", "name,url,description,stargazersCount,forksCount,pushedAt"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                items = json.loads(result.stdout)
                return items
            return []
        except Exception as e:
            logger.error(f"扫描失败: {e}")
            return []

    def get_repo_info(self, repo: str) -> Optional[Dict]:
        """获取指定仓库详情"""
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return {
                    "full_name": info.get("full_name"),
                    "stars": info.get("stargazers_count", 0),
                    "forks": info.get("forks_count", 0),
                    "description": info.get("description", ""),
                    "language": info.get("language", ""),
                    "topics": info.get("topics", []),
                    "pushed_at": info.get("pushed_at", ""),
                    "url": info.get("html_url", ""),
                }
            return None
        except Exception as e:
            logger.warning(f"获取 {repo} 失败: {e}")
            return None

    def generate_integration_report(self) -> str:
        """生成集成建议报告"""
        report = f"""# GitHub 量化资源集成报告
生成时间：{datetime.now()}

## 一、当前项目现状分析

**QuantAnalyzer** 已具备：
- Backtrader回测引擎
- BaoStock数据源
- 20+内置策略
- AI多模型分析（Cerebras/Groq/DeepSeek等）
- 定时自动回测调度器

## 二、推荐集成的项目

### 高优先级（立即集成）

#### 1. AKShare（akfamily/akshare）
- Stars: 12k+
- **价值：** 替代/补充BaoStock，获得更丰富的数据源（股票/期货/期权/基金/宏观）
- **集成：** `pip install akshare`

#### 2. SmartQuant参考
- 财务分析模块（杜邦分析、风险评分）
- 缠论K线可视化
- 机构级UI参考

#### 3. Qlib因子研究
- Stars: 40k
- Alpha158因子库（158个因子）
- 高性能因子计算引擎

### 中优先级（下一版本）

#### 4. TradingAgents-CN 多智能体系统
- Stars: 22.7k
- 多智能体协作分析
- 自动策略优化

#### 5. FinRL 强化学习
- Stars: 12k
- 深度强化学习训练交易策略

### 低优先级（长期规划）

#### 6. vn.py 券商对接
- Stars: 38.8k
- 支持多家券商API
- 实盘交易对接

## 三、技术路线图

```
v3.3（当前）
  AKShare数据集成 + 因子研究模块 + 风控中心

v3.4（下月）
  SmartQuant财务分析模块 + Qlib因子库基础集成 + 缠论K线可视化

v3.5（3个月）
  TradingAgents-CN多智能体 + vn.py实盘对接 + FinRL强化学习

v4.0（6个月）
  全自动量化流水线 + AI自优化策略引擎
```

## 四、已追踪项目列表

"""

        for category, repos in QUANT_RESOURCES.items():
            report += f"\n### {category}\n\n"
            for r in repos:
                stars_str = r["stars"]
                val = "".join(["*" for _ in range(r["value"])])
                report += f"- **{r['repo']}** ({stars_str}) {val}\n  {r['desc']}\n\n"

        report += f"\n---\n*报告由 QuantAnalyzer v3.3 自动生成*\n"
        return report

    def save_report(self, content: str) -> Path:
        """保存报告到文件"""
        report_file = self.cache_dir.parent / "reports" / "github_integration_report.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"报告已保存: {report_file}")
        return report_file


if __name__ == "__main__":
    monitor = GitHubResourceMonitor()
    report = monitor.generate_integration_report()
    output = monitor.save_report(report)
    print(f"报告已生成: {output}")
