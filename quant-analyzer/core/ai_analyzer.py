"""
AI分析模块 — 多大模型接入，策略智能分析
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
        if not self.config.get("api_key"):
            return self._mock_response(prompt)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['api_key']}",
        }

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
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """无API Key时的模拟响应"""
        return f"[AI分析不可用] 请在设置页面配置 {self.config['name']} API Key 以启用AI分析功能。\n\n当前使用模拟模式，以下是基于规则的初步分析：\n\n1. 建议关注策略的夏普比率和最大回撤\n2. 胜率和盈亏比需要综合考量\n3. 建议与基准对比，分析超额收益来源"

    def analyze_strategy(self, strategy_result: Dict) -> str:
        """分析单个策略"""
        prompt = f"""你是一位专业的量化策略分析师。请分析以下回测结果，给出专业评估：

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
1. **收益质量**：年化收益是否优秀？收益来源是什么？
2. **风险控制**：最大回撤是否在可接受范围？风险调整收益如何？
3. **策略稳定性**：夏普比率和胜率是否稳定？换手率是否合理？
4. **适用场景**：该策略适合什么市场环境？
5. **改进建议**：如何优化该策略？

请用专业但易懂的语言回答。"""

        system_prompt = "你是一位拥有10年经验的量化基金经理，擅长策略分析和风险管理。分析时注重数据支撑，给出具体可行的建议。"

        analysis = self._call_api(prompt, system_prompt)

        # 保存到数据库
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

        prompt = f"""你是一位专业的量化分析师。请对比以下策略：

{strategies_text}

请分析：
1. **综合排名**：按收益/风险/稳定性综合排名
2. **优劣对比**：各策略的核心优势和劣势
3. **相关性**：策略之间是否有互补性？能否组合？
4. **推荐配置**：如果资金100万，你会如何分配？
5. **市场环境适应性**：各策略适合什么行情？
6. **风险提示**：需要注意哪些系统性风险？

请给出明确的建议。"""

        system_prompt = "你是量化团队的首席分析师，需要给出客观、专业、有深度的策略对比分析。"

        analysis = self._call_api(prompt, system_prompt)

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
        prompt = """请分析当前A股市场环境：
1. 大盘走势判断（近期趋势）
2. 市场风格特征（价值/成长/周期）
3. 建议关注的行业板块
4. 风险提示
5. 对量化策略的影响

请给出简明扼要的分析。"""

        system_prompt = "你是A股市场的资深分析师，擅长市场趋势判断和风格分析。"

        return self._call_api(prompt, system_prompt)

    def auto_learn(self, historical_results: list) -> str:
        """
        自学习进化 — 基于历史回测结果学习优化
        """
        results_text = json.dumps([
            {k: v for k, v in r.items() if k not in ("daily_values", "trades")}
            for r in historical_results[-20:]  # 最近20次结果
        ], ensure_ascii=False, indent=2, default=str)

        prompt = f"""你是量化策略的"进化引擎"。根据以下历史回测数据，分析规律并提出优化方向：

{results_text}

请从以下角度思考：
1. 哪些策略近期表现退化？可能的原因？
2. 哪些参数组合可能更优？
3. 是否需要增加新的策略类型？
4. 市场环境发生了什么变化？
5. 具体的参数调优建议（给出具体数值）

输出格式：
## 洞察
...

## 优化建议
...

## 新策略建议
..."""

        system_prompt = "你是一个能从数据中学习的量化AI系统，目标是通过分析历史数据不断优化策略。"

        return self._call_api(prompt, system_prompt, temperature=0.8)
