"""
🤖 多LLM统一调用管理器
支持: 智谱GLM / DeepSeek / 硅基流动 / Ollama
"""
import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def get_llm_manager():
    """获取LLM管理器单例"""
    if not hasattr(get_llm_manager, "_instance"):
        get_llm_manager._instance = LLMManager()
    return get_llm_manager._instance


class LLMManager:
    """统一LLM调用接口 — 自动路由到可用模型"""

    def __init__(self):
        self._load_config()

    def _load_config(self):
        """加载LLM配置"""
        try:
            from config import AI_MODELS, DEFAULT_MODEL_PRIORITY
            self.models = AI_MODELS
            self.default_priority = DEFAULT_MODEL_PRIORITY
        except ImportError:
            self.models = {}
            self.default_priority = []
            logger.warning("无法加载 config.py，使用空配置")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model_key: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        timeout: int = 60,
    ) -> Optional[str]:
        """
        统一 chat 接口 — 按优先级自动选择可用模型

        Args:
            messages: [{"role": "system"/"user"/"assistant", "content": "..."}]
            model_key: 指定模型（如 "deepseek-v3"），None则按优先级自动选
            temperature: 创造性温度
            max_tokens: 最大token数
            timeout: 超时秒数

        Returns:
            模型回复文本，失败返回 None
        """
        import requests

        # 选定模型
        if model_key:
            candidates = [model_key]
        else:
            candidates = self.default_priority.copy()

        # 尝试每个模型
        for key in candidates:
            model = self.models.get(key)
            if not model:
                continue

            # 检查是否需要Key且未配置
            if model.get("needs_key") and not model.get("api_key"):
                logger.debug(f"模型 {key} 需要API Key但未配置，跳过")
                continue

            try:
                content = self._call_model(model, messages, temperature, max_tokens, timeout)
                if content:
                    logger.info(f"LLM调用成功: {key}")
                    return content
            except Exception as e:
                logger.warning(f"模型 {key} 调用失败: {e}")
                continue

        logger.error("所有模型均调用失败")
        return None

    def _call_model(
        self,
        model: Dict,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> Optional[str]:
        """根据 provider 类型调用对应API"""
        provider = model.get("provider", "openai")
        api_base = model["api_base"]
        api_key = model.get("api_key", "")
        model_name = model["model"]

        if provider == "ollama":
            return self._call_ollama(model_name, messages, temperature, api_base)
        else:
            return self._call_openai_compatible(
                api_base, api_key, model_name, messages, temperature, max_tokens, timeout
            )

    def _call_openai_compatible(
        self,
        api_base: str,
        api_key: str,
        model_name: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> Optional[str]:
        """调用 OpenAI 兼容接口（智谱/DeepSeek/硅基流动）"""
        import requests

        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        result = resp.json()

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"].strip()
        return None

    def _call_ollama(
        self,
        model_name: str,
        messages: List[Dict],
        temperature: float,
        api_base: str,
    ) -> Optional[str]:
        """调用 Ollama 本地模型"""
        import requests

        url = f"{api_base.rstrip('/')}/api/chat"
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        result = resp.json()

        if "message" in result:
            return result["message"]["content"].strip()
        return None

    def generate_strategy(
        self,
        prompt: str,
        model_key: str = None,
        temperature: float = 0.8,
    ) -> Optional[str]:
        """生成量化策略代码"""
        system_prompt = """你是一位资深量化交易策略专家。请生成一个基于Backtrader框架的A股量化策略。
要求:
1. 策略代码必须是完整的Python类，继承bt.Strategy
2. 包含明确的买入(self.buy)和卖出(self.sell/close)逻辑
3. 使用技术指标(均线/RSI/MACD/布林带/ATR等)组合
4. 加入止损逻辑和仓位管理
5. 策略要适合A股T+1规则
6. 直接输出Python代码，不要解释

只输出代码，不要其他文字。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        return self.chat(messages, model_key=model_key, temperature=temperature, max_tokens=4000, timeout=90)

    def optimize_strategy(
        self,
        code: str,
        performance_data: Dict = None,
        model_key: str = None,
    ) -> Optional[str]:
        """优化已有策略代码"""
        perf_desc = ""
        if performance_data:
            perf_desc = f"""当前策略表现:
- 总收益率: {performance_data.get('total_return', 'N/A')}
- 夏普比率: {performance_data.get('sharpe_ratio', 'N/A')}
- 最大回撤: {performance_data.get('max_drawdown', 'N/A')}
- 胜率: {performance_data.get('win_rate', 'N/A')}"""

        prompt = f"""请优化以下量化策略。{perf_desc}
原始策略代码:
```python
{code}
```

请输出优化后的完整策略代码。优化方向:
1. 改善买卖信号的准确性
2. 添加更好的止损/止盈逻辑
3. 优化仓位管理
4. 减少不必要的交易（过滤假信号）

只输出优化后的完整Python代码。"""

        messages = [
            {"role": "system", "content": "你是量化策略优化专家。只输出优化后的代码。"},
            {"role": "user", "content": prompt},
        ]
        return self.chat(messages, model_key=model_key, temperature=0.6, max_tokens=4000, timeout=90)

    def analyze_signals(
        self,
        signal_summary: str,
        model_key: str = None,
    ) -> Optional[str]:
        """分析交易信号质量"""
        prompt = f"""分析以下A股交易信号的质量，并给出改进建议:

{signal_summary}

请简要分析:
1. 哪些信号质量较高？
2. 是否存在假信号风险？
3. 如何提高信号准确率？

用简洁的中文回答，100字以内。"""

        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, model_key=model_key, temperature=0.3, max_tokens=500, timeout=30)

    def diagnose_stock(
        self,
        stock_name: str,
        stock_code: str,
        indicators: str,
        model_key: str = None,
    ) -> Optional[str]:
        """AI诊断股票"""
        prompt = f"""请分析{stock_name}({stock_code})的技术指标:
{indicators}

给出: 1)当前趋势判断 2)支撑位/压力位 3)操作建议(买入/观望/卖出) 4)风险提示。
简洁回答，200字以内。"""

        messages = [
            {"role": "system", "content": "你是资深A股技术分析师。根据指标给出简洁的投资建议。"},
            {"role": "user", "content": prompt},
        ]
        return self.chat(messages, model_key=model_key, temperature=0.3, max_tokens=800, timeout=30)
