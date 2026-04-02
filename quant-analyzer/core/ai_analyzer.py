"""
AI分析模块 — 多大模型接入，策略智能分析
支持: DeepSeek, 智谱AI(GLM-4-Flash免费), OpenAI
"""
import json
import requests
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import AI_PROVIDERS, DEFAULT_AI_PROVIDER
from data.fetcher import db

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI 分析器 — 支持多模型"""

    def __init__(self, provider: str = None):
        self.provider = provider or DEFAULT_AI_PROVIDER
        self.config = AI_PROVIDERS.get(self.provider)
        if not self.config:
            raise ValueError(f"未知的AI提供商: {self.provider}")

    def _call_api(self, prompt: str, system_prompt: str = None, temperature: float = 0.7) -> str:
        """调用AI API"""
        api_key = self.config.get("api_key", "")
        
        # 检查环境变量中的 key
        env_key = f"{self.provider.upper()}_API_KEY"
        if not api_key:
            api_key = os.getenv(env_key, "")
            if api_key:
                self.config["api_key"] = api_key

        if not api_key:
            return self._rule_based_analysis(prompt)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # 智谱AI用不同的auth格式
        if self.provider == "zhipu":
            headers["Authorization"] = f"Bearer {api_key}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4000,
        }

        try:
            resp = requests.post(
                f"{self.config['api_base']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"AI API调用失败 ({self.provider}): {e}")
            return self._rule_based_analysis(prompt)

    def _rule_based_analysis(self, prompt: str) -> str:
        """无API Key时的基于规则的分析"""
        # 尝试从prompt中提取策略数据
        import re
        
        annual_match = re.search(r"年化收益[率]?\D*([-\d.]+)%?", prompt)
        sharpe_match = re.search(r"夏普比率\D*([-\d.]+)", prompt)
        dd_match = re.search(r"最大回撤\D*([-\d.]+)%?", prompt)
        win_match = re.search(r"胜率\D*([-\d.]+)%?", prompt)
        
        ar = float(annual_match.group(1)) if annual_match else 0
        sr = float(sharpe_match.group(1)) if sharpe_match else 0
        mdd = abs(float(dd_match.group(1))) if dd_match else 0
        wr = float(win_match.group(1)) if win_match else 0

        analysis = "## 📊 基于规则的量化分析报告\n\n"
        analysis += "> 💡 **提示**: 配置AI API Key可获得更深入的分析。推荐使用[智谱AI](https://open.bigmodel.cn/)的GLM-4-Flash（免费）。\n\n"

        # 收益评估
        if ar > 15:
            analysis += f"### ✅ 收益评估\n年化收益率 **{ar:.2f}%** 表现优秀，显著跑赢大盘。属于高收益策略。\n\n"
        elif ar > 5:
            analysis += f"### 📈 收益评估\n年化收益率 **{ar:.2f}%** 表现尚可，超过银行理财和多数基金平均收益。\n\n"
        elif ar > 0:
            analysis += f"### ⚠️ 收益评估\n年化收益率 **{ar:.2f}%** 偏低，仅略高于无风险利率。\n\n"
        else:
            analysis += f"### ❌ 收益评估\n年化收益率 **{ar:.2f}%** 为负，策略需要重新审视。\n\n"

        # 风险评估
        if mdd < 10:
            analysis += f"### ✅ 风险控制\n最大回撤 **{mdd:.2f}%** 控制良好，风险可控。\n\n"
        elif mdd < 25:
            analysis += f"### ⚠️ 风险控制\n最大回撤 **{mdd:.2f}%** 中等水平，需要注意风险管理。\n\n"
        else:
            analysis += f"### ❌ 风险控制\n最大回撤 **{mdd:.2f}%** 偏大，可能面临较大亏损风险。\n\n"

        # 夏普比率
        if sr > 1.5:
            analysis += f"### ✅ 风险调整收益\n夏普比率 **{sr:.2f}** 非常优秀，单位风险回报高。\n\n"
        elif sr > 0.5:
            analysis += f"### 📊 风险调整收益\n夏普比率 **{sr:.2f}** 合理水平。\n\n"
        else:
            analysis += f"### ⚠️ 风险调整收益\n夏普比率 **{sr:.2f}** 偏低，性价比不足。\n\n"

        # 综合建议
        score = min(100, max(0, ar * 3 + (2 - mdd / 10) * 15 + sr * 10 + wr * 10))
        if score >= 70:
            analysis += f"### 🏆 综合评分: {score:.0f}/100 — **推荐**\n策略综合表现优秀，建议配置。\n"
        elif score >= 40:
            analysis += f"### 📋 综合评分: {score:.0f}/100 — **观望**\n策略表现一般，建议结合其他策略组合使用。\n"
        else:
            analysis += f"### ⛔ 综合评分: {score:.0f}/100 — **不推荐**\n策略表现不佳，需要优化或更换。\n"

        return analysis

    def analyze_strategy(self, strategy_result: Dict) -> str:
        """分析单个策略"""
        prompt = f"""你是一位专业的量化策略分析师。请分析以下回测结果：

## 策略: {strategy_result.get('strategy_name', '未知')}
- 回测区间: {strategy_result.get('start_date', '')} ~ {strategy_result.get('end_date', '')}
- 初始资金: ¥{strategy_result.get('initial_cash', 0):,.0f}
- 最终净值: ¥{strategy_result.get('final_value', 0):,.0f}
- 总收益率: {strategy_result.get('total_return', 0):.2%}
- 年化收益率: {strategy_result.get('annual_return', 0):.2%}
- 最大回撤: {abs(strategy_result.get('max_drawdown', 0)):.2%}
- 夏普比率: {strategy_result.get('sharpe_ratio', 0):.2f}
- Sortino比率: {strategy_result.get('sortino_ratio', '-') or '-'}
- Calmar比率: {strategy_result.get('calmar_ratio', '-') or '-'}
- 胜率: {strategy_result.get('win_rate', 0):.2%}
- 盈亏比: {strategy_result.get('profit_loss_ratio', 0):.2f}
- 总交易次数: {strategy_result.get('total_trades', 0)}
- Beta: {strategy_result.get('beta', '-') or '-'}
- 波动率: {strategy_result.get('volatility', 0):.2%}

请从以下维度分析：
1. **收益质量**：年化收益是否优秀？
2. **风险控制**：最大回撤是否可接受？
3. **策略稳定性**：夏普比率和胜率如何？
4. **改进建议**：如何优化？
请用中文回答。"""

        system_prompt = "你是一位拥有10年经验的量化基金经理，擅长策略分析和风险管理。"

        analysis = self._call_api(prompt, system_prompt)

        db.save_ai_report(
            strategy_name=strategy_result.get("strategy_name", ""),
            report_date=datetime.now().strftime("%Y-%m-%d"),
            provider=self.provider,
            analysis_type="strategy_analysis",
            content=analysis,
        )

        return analysis

    def compare_strategies(self, results: list) -> str:
        """对比分析多个策略"""
        strategies_text = ""
        for r in results:
            strategies_text += f"""
### {r.get('strategy_name', '未知')}
- 年化收益: {r.get('annual_return', 0):.2%}
- 最大回撤: {abs(r.get('max_drawdown', 0)):.2%}
- 夏普比率: {r.get('sharpe_ratio', 0):.2f}
- 胜率: {r.get('win_rate', 0):.2%}
- 盈亏比: {r.get('profit_loss_ratio', 0):.2f}
- 交易次数: {r.get('total_trades', 0)}
"""

        prompt = f"""对比以下量化策略：
{strategies_text}

请给出：1.综合排名 2.优劣对比 3.推荐配置 4.风险提示
请用中文回答。"""

        analysis = self._call_api(prompt, "你是量化团队首席分析师。")

        db.save_ai_report(
            strategy_name="__comparison__",
            report_date=datetime.now().strftime("%Y-%m-%d"),
            provider=self.provider,
            analysis_type="strategy_comparison",
            content=analysis,
        )

        return analysis

    def market_analysis(self) -> str:
        """市场环境分析"""
        prompt = """请分析当前A股市场环境（2026年4月）：
1. 大盘走势
2. 市场风格
3. 关注板块
4. 风险提示
请用中文回答。"""

        return self._call_api(prompt, "你是A股市场资深分析师。")

    def auto_learn(self, historical_results: list) -> str:
        """自学习进化"""
        results_text = json.dumps([
            {k: v for k, v in r.items() if k not in ("daily_values", "trades")}
            for r in historical_results[-20:]
        ], ensure_ascii=False, indent=2, default=str)

        prompt = f"""你是量化策略的"进化引擎"。根据历史回测数据提出优化方向：
{results_text}

请分析：1.策略退化 2.参数优化 3.新策略建议
用中文回答。"""

        return self._call_api(prompt, "你是能从数据中学习的量化AI系统。", temperature=0.8)
