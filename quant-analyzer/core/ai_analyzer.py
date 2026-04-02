"""
AI分析模块 — QuantAnalyzer v3.0
多模型协同分析 + 策略代码解析 + 智能路由
"""
import json
import requests
import os
import sys
import logging
import re
import ast
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import AI_MODELS, DEFAULT_MODEL_PRIORITY, ANALYSIS_TASKS

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# 🤖 多模型AI分析器
# ══════════════════════════════════════════════

class MultiModelAnalyzer:
    """
    多模型协同分析器
    - 自动选择可用模型
    - 多模型并行分析
    - 结果综合与投票
    - 故障自动转移
    """

    def __init__(self, model_priority: List[str] = None):
        self.priority = model_priority or DEFAULT_MODEL_PRIORITY
        self.available_models = []
        self._detect_available()

    def _detect_available(self):
        """检测哪些模型已配置可用"""
        for name in self.priority:
            cfg = AI_MODELS.get(name)
            if not cfg:
                continue
            api_key = cfg.get("api_key") or os.getenv(cfg["env_key"], "")
            if api_key:
                self.available_models.append(name)
                logger.info(f"✅ 模型可用: {cfg['name']}")

    def _get_best_available(self, exclude: List[str] = None) -> Optional[str]:
        """获取最优可用模型"""
        exclude = exclude or []
        for name in self.priority:
            if name not in exclude and name in self.available_models:
                return name
        return None

    def _call_single_model(
        self, model_name: str, prompt: str,
        system_prompt: str = None, temperature: float = 0.7
    ) -> Dict:
        """调用单个模型，返回结构化结果"""
        cfg = AI_MODELS[model_name]
        api_key = cfg.get("api_key") or os.getenv(cfg["env_key"], "")

        if not api_key:
            return {"success": False, "error": "No API key", "model": model_name}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }

        try:
            resp = requests.post(
                f"{cfg['api_base']}/chat/completions",
                headers=headers, json=payload, timeout=90
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return {
                "success": True,
                "content": content,
                "model": model_name,
                "model_display": cfg["name"],
            }
        except Exception as e:
            logger.warning(f"模型 {model_name} 调用失败: {e}")
            return {"success": False, "error": str(e), "model": model_name}

    def parallel_analyze(
        self, prompt: str, system_prompt: str = None,
        model_names: List[str] = None, temperature: float = 0.5
    ) -> Dict:
        """
        多模型并行分析，返回所有结果 + 综合报告
        """
        # 确定要使用的模型
        candidates = model_names or self.available_models[:5]
        active = [m for m in candidates if m in self.available_models]

        if not active:
            return self._rule_based_fallback(prompt)

        results = []
        with ThreadPoolExecutor(max_workers=len(active)) as executor:
            futures = {
                executor.submit(
                    self._call_single_model, m, prompt, system_prompt, temperature
                ): m for m in active
            }
            for future in as_completed(futures):
                r = future.result()
                if r["success"]:
                    results.append(r)

        if not results:
            # 所有模型都失败，尝试按优先级逐个降级
            for model_name in self.priority:
                if model_name not in candidates:
                    r = self._call_single_model(model_name, prompt, system_prompt, temperature)
                    if r["success"]:
                        results.append(r)
                        break

        if not results:
            return {"success": False, "content": self._rule_based_fallback(prompt)["content"]}

        # 综合多个模型的结果
        if len(results) == 1:
            combined = results[0]["content"]
        else:
            combined = self._synthesize(results, prompt)

        return {
            "success": True,
            "content": combined,
            "all_results": results,
            "model_count": len(results),
        }

    def _synthesize(self, results: List[Dict], original_prompt: str) -> str:
        """综合多个模型的结果"""
        synthesis_prompt = f"""你是一个AI分析结果综合引擎。有{len(results)}个不同的AI模型对同一问题给出了分析，请综合它们的核心观点，给出一份更全面、更准确的综合报告。

各模型分析：
{chr(10).join([f"【模型{i+1}】{r['model_display']}: {r['content']}" for i, r in enumerate(results)])}

请提炼各模型的共同观点和分歧点，给出综合结论。用中文回答，格式清晰。"""

        # 用第一个成功的模型来做综合
        first_model = results[0]["model"]
        cfg = AI_MODELS[first_model]
        api_key = cfg.get("api_key") or os.getenv(cfg["env_key"], "")

        try:
            resp = requests.post(
                f"{cfg['api_base']}/chat/completions",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                json={
                    "model": cfg["model"],
                    "messages": [
                        {"role": "system", "content": "你是一个专业的分析报告综合引擎。"},
                        {"role": "user", "content": synthesis_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
                timeout=90
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            # 综合失败，返回第一个结果
            return results[0]["content"]

    def _rule_based_fallback(self, prompt: str) -> Dict:
        """无任何模型可用时的规则兜底"""
        annual_match = re.search(r"年化收益[率]?\D*([-\d.]+)%?", prompt)
        sharpe_match = re.search(r"夏普比率\D*([-\d.]+)", prompt)
        dd_match = re.search(r"最大回撤\D*([-\d.]+)%?", prompt)
        win_match = re.search(r"胜率\D*([-\d.]+)%?", prompt)

        ar = float(annual_match.group(1)) if annual_match else 0
        sr = float(sharpe_match.group(1)) if sharpe_match else 0
        mdd = abs(float(dd_match.group(1))) if dd_match else 0
        wr = float(win_match.group(1)) if win_match else 0

        analysis = "## 📊 量化分析报告（规则引擎）\n\n"
        analysis += "> ⚠️ **提示**: 配置AI模型Key可获得更深入的分析。推荐：\n"
        analysis += "> - 🌐 [Groq](https://console.groq.com/keys) — 免费无限制，30秒注册\n"
        analysis += "> - 🤖 [智谱AI](https://open.bigmodel.cn/) — 国产免费，需注册\n"
        analysis += "> - ⚡ [Cerebras](https://cloud.cerebras.ai/) — 免费无限制\n\n"

        # 收益评估
        if ar > 15:
            analysis += "### ✅ 收益评估\n"
            analysis += f"年化收益率 **{ar:.2f}%** 表现优秀，显著跑赢大盘。\n\n"
        elif ar > 5:
            analysis += "### 📈 收益评估\n"
            analysis += f"年化收益率 **{ar:.2f}%** 表现尚可，超过银行理财平均收益。\n\n"
        elif ar > 0:
            analysis += "### ⚠️ 收益评估\n"
            analysis += f"年化收益率 **{ar:.2f}%** 偏低。\n\n"
        else:
            analysis += "### ❌ 收益评估\n"
            analysis += f"年化收益率 **{ar:.2f}%** 为负，策略需要重新审视。\n\n"

        # 风险评估
        if mdd < 10:
            analysis += f"### ✅ 风险控制\n最大回撤 **{mdd:.2f}%** 控制良好。\n\n"
        elif mdd < 25:
            analysis += f"### ⚠️ 风险控制\n最大回撤 **{mdd:.2f}%** 中等水平。\n\n"
        else:
            analysis += f"### ❌ 风险控制\n最大回撤 **{mdd:.2f}%** 偏大，风险较高。\n\n"

        # 综合评分
        score = min(100, max(0, ar * 3 + (2 - mdd / 10) * 15 + sr * 10 + wr * 10))
        if score >= 70:
            analysis += f"### 🏆 综合评分: {score:.0f}/100 — **推荐**"
        elif score >= 40:
            analysis += f"### 📋 综合评分: {score:.0f}/100 — **观望**"
        else:
            analysis += f"### ⛔ 综合评分: {score:.0f}/100 — **不推荐**"

        return {"success": True, "content": analysis}


# ══════════════════════════════════════════════
# 📋 策略代码解析器
# ══════════════════════════════════════════════

class StrategyParser:
    """
    策略代码解析器 — 分析用户粘贴的策略代码
    支持: Backtrader / 聚宽 / 伪代码
    """

    def __init__(self, analyzer: MultiModelAnalyzer = None):
        self.analyzer = analyzer or MultiModelAnalyzer()

    def parse_and_analyze(self, code: str, source_type: str = "auto") -> Dict:
        """
        解析并分析策略代码，返回结构化分析结果
        source_type: "backtrader" | "jqdata" | "pseudocode" | "auto"
        """
        # 1. 自动检测类型
        if source_type == "auto":
            source_type = self._detect_type(code)

        # 2. 代码结构分析 (规则层面)
        structure = self._analyze_structure(code)

        # 3. AI深度分析
        ai_analysis = self._ai_analyze(code, source_type, structure)

        # 4. 风险评估
        risk_info = self._assess_risk(code, structure)

        # 5. 综合结果
        return {
            "source_type": source_type,
            "structure": structure,
            "ai_analysis": ai_analysis,
            "risk_info": risk_info,
            "can_backtest": structure["can_backtest"],
            "estimated_risk": risk_info["level"],
        }

    def _detect_type(self, code: str) -> str:
        """自动检测策略代码类型"""
        code_lower = code.lower()

        # Backtrader特征
        if any(kw in code_lower for kw in ["bt.feeds", "cerebro", "addstrategy", "backtrader"]):
            return "backtrader"

        # 聚宽特征
        if any(kw in code_lower for kw in ["jqdata", "get_price", "jq.instruments", "initialize"]):
            return "jqdata"

        # 伪代码/自然语言
        if any(kw in code_lower for kw in ["如果", "当", "买入条件", "卖出条件"]):
            return "pseudocode"

        # 尝试AST解析
        try:
            ast.parse(code)
            return "backtrader"  # 默认为Backtrader
        except:
            return "unknown"

    def _analyze_structure(self, code: str) -> Dict:
        """基于规则分析策略代码结构"""
        result = {
            "has_init": False,
            "has_next": False,
            "has_buy_logic": False,
            "has_sell_logic": False,
            "indicators": [],
            "parameters": [],
            "can_backtest": False,
            "issues": [],
        }

        code_lower = code.lower()

        # 检测关键方法
        if "def __init__" in code:
            result["has_init"] = True
        if "def next" in code or "def on_bar" in code:
            result["has_next"] = True
        if any(kw in code_lower for kw in ["buy", "self.buy", "_buy"]):
            result["has_buy_logic"] = True
        if any(kw in code_lower for kw in ["sell", "self.sell", "_sell", "close"]):
            result["has_sell_logic"] = True

        # 检测指标
        indicators_map = {
            "sma": "SMA均线", "ema": "EMA均线", "ma": "均线",
            "rsi": "RSI", "macd": "MACD", "bollinger": "布林带",
            "atr": "ATR", "adx": "ADX", "obv": "OBV",
            "stoch": "KDJ", "kdj": "KDJ", "cci": "CCI",
            "volume": "成交量", "close": "收盘价",
        }
        for kw, name in indicators_map.items():
            if kw in code_lower:
                result["indicators"].append(name)

        # 检测参数
        param_pattern = re.findall(r"(\w+)\s*=\s*(\d+\.?\d*)", code)
        result["parameters"] = [{"name": p[0], "value": p[1]} for p in param_pattern[:20]]

        # 判断是否可回测
        result["can_backtest"] = (
            result["has_next"] and
            (result["has_buy_logic"] or result["has_sell_logic"])
        )

        if not result["has_next"]:
            result["issues"].append("缺少交易逻辑函数(next/on_bar)")
        if not result["has_buy_logic"]:
            result["issues"].append("未检测到买入逻辑")
        if not result["has_sell_logic"]:
            result["issues"].append("未检测到卖出逻辑")

        return result

    def _ai_analyze(self, code: str, source_type: str, structure: Dict) -> str:
        """AI深度分析策略代码"""
        structure_text = json.dumps(structure, ensure_ascii=False, indent=2)

        prompt = f"""你是量化策略代码审查专家。请分析以下策略代码：

## 策略类型: {source_type}

## 代码结构 (规则分析结果):
{structure_text}

## 策略代码:
```{code[:4000]}```

请分析以下维度并用中文回答：

### 1. 策略逻辑解读
- 核心买卖逻辑是什么？
- 使用了哪些技术指标？
- 入场和出场条件分别是什么？

### 2. 策略类型分类
- 趋势跟踪 / 均值回归 / 动量 / 多因子 / 其他？

### 3. 参数分析
- 主要参数有哪些？它们的作用是什么？
- 参数是否合理（不会过度拟合）？

### 4. 风险点识别
- 代码中是否存在明显的风险或bug？
- 是否有未来函数/前视偏差？
- 止损止盈机制是否完善？

### 5. 回测可行性评估
- 这段代码能否直接用于回测？
- 如果不能，需要哪些修改？

### 6. 改进建议
- 如何优化这段策略代码？
- 有什么可以提升收益或降低风险的建议？"""

        system_prompt = "你是一位有10年经验的量化策略代码审查专家，精通Backtrader、聚宽、果仁等量化平台。"

        task_cfg = ANALYSIS_TASKS.get("strategy_code_parse", {})
        models = task_cfg.get("models", ["zhipu", "deepseek", "groq"])

        result = self.analyzer.parallel_analyze(
            prompt, system_prompt,
            model_names=models,
            temperature=task_cfg.get("temperature", 0.3)
        )

        return result.get("content", "分析失败")

    def _assess_risk(self, code: str, structure: Dict) -> Dict:
        """评估策略代码风险等级"""
        risk_score = 0
        issues = []

        code_lower = code.lower()

        # 高风险检测
        if "all_in" in code_lower or "全仓" in code:
            risk_score += 20
            issues.append("使用全仓操作，风险较高")

        if "sleep" in code_lower:
            risk_score += 15
            issues.append("代码中有sleep，可能阻塞回测")

        if "time.sleep" in code_lower:
            risk_score += 15
            issues.append("存在time.sleep，回测性能差")

        if not structure["has_next"]:
            risk_score += 30
            issues.append("缺少核心交易逻辑")

        # 中风险
        if len(structure["parameters"]) > 15:
            risk_score += 10
            issues.append("参数过多，可能过拟合")

        if "self.buy" not in code_lower and "buy" not in code_lower:
            risk_score += 15
            issues.append("未检测到明确买入逻辑")

        # 级别判断
        if risk_score >= 50:
            level = "🔴 高风险"
        elif risk_score >= 25:
            level = "🟡 中风险"
        elif risk_score >= 10:
            level = "🟢 低风险"
        else:
            level = "✅ 风险可控"

        return {
            "level": level,
            "score": risk_score,
            "issues": issues,
        }


# ══════════════════════════════════════════════
# 📊 策略回测分析器 (兼容旧接口)
# ══════════════════════════════════════════════

class AIAnalyzer:
    """对外接口 — 兼容旧版代码"""

    def __init__(self, provider: str = None):
        self.multi = MultiModelAnalyzer()
        self.parser = StrategyParser(self.multi)

    def analyze_strategy(self, strategy_result: Dict) -> str:
        """分析单个策略回测结果"""
        task_cfg = ANALYSIS_TASKS.get("backtest_analysis", {})
        models = task_cfg.get("models", ["deepseek", "zhipu", "groq"])

        prompt = self._build_backtest_prompt(strategy_result)
        system_prompt = "你是一位拥有10年经验的量化基金经理，擅长策略分析和风险管理。"

        result = self.multi.parallel_analyze(
            prompt, system_prompt,
            model_names=models,
            temperature=task_cfg.get("temperature", 0.5)
        )
        return result.get("content", self.multi._rule_based_fallback(prompt)["content"])

    def compare_strategies(self, results: list) -> str:
        """对比分析多个策略"""
        task_cfg = ANALYSIS_TASKS.get("strategy_comparison", {})
        models = task_cfg.get("models", ["zhipu", "deepseek"])

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

        prompt = f"""对比以下量化策略，给出综合排名和配置建议：
{strategies_text}

请用中文回答，包含：1.综合排名 2.优劣对比 3.推荐配置 4.风险提示"""

        result = self.multi.parallel_analyze(
            prompt, "你是量化团队首席分析师。",
            model_names=models,
            temperature=task_cfg.get("temperature", 0.4)
        )
        return result.get("content", self.multi._rule_based_fallback(prompt)["content"])

    def analyze_code(self, code: str, source_type: str = "auto") -> Dict:
        """分析用户粘贴的策略代码"""
        return self.parser.parse_and_analyze(code, source_type)

    def market_analysis(self) -> str:
        """市场环境分析"""
        task_cfg = ANALYSIS_TASKS.get("market_sentiment", {})
        models = task_cfg.get("models", ["deepseek", "qwen"])

        prompt = """请分析当前A股市场环境：
1. 大盘走势 (上证、深证、创业板、沪深300)
2. 市场风格 (成长/价值/平衡)
3. 关注板块
4. 风险提示
请用中文回答，尽量结合当前日期2026年4月的市场背景。"""

        result = self.multi.parallel_analyze(
            prompt, "你是A股市场资深分析师。",
            model_names=models,
            temperature=task_cfg.get("temperature", 0.6)
        )
        return result.get("content", self.multi._rule_based_fallback(prompt)["content"])

    def auto_learn(self, historical_results: list) -> str:
        """自学习进化"""
        task_cfg = ANALYSIS_TASKS.get("auto_learning", {})
        models = task_cfg.get("models", ["deepseek", "google-gemini"])

        results_text = json.dumps([
            {k: v for k, v in r.items() if k not in ("daily_values", "trades")}
            for r in historical_results[-20:]
        ], ensure_ascii=False, indent=2, default=str)

        prompt = f"""你是量化策略的"进化引擎"。根据历史回测数据提出优化方向：

{results_text}

请分析：
1. 策略退化 — 哪些策略近期表现下降？
2. 参数优化 — 如何调整参数？
3. 新策略建议 — 什么样的策略值得尝试？
4. 组合建议 — 如何构建策略组合？
用中文回答。"""

        result = self.multi.parallel_analyze(
            prompt, "你是能从数据中学习的量化AI系统。",
            model_names=models,
            temperature=task_cfg.get("temperature", 0.8)
        )
        return result.get("content", self.multi._rule_based_fallback(prompt)["content"])

    def _build_backtest_prompt(self, strategy_result: Dict) -> str:
        """构建回测分析prompt"""
        return f"""你是一位专业的量化策略分析师。请分析以下回测结果：

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
