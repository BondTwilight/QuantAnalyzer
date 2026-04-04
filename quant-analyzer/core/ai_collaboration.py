"""
🤖 AI协同工作引擎 - QuantBrain v4.0
支持多AI模型协同工作、任务分配、结果融合
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """AI任务类型"""
    STRATEGY_ANALYSIS = "strategy_analysis"      # 策略分析
    CODE_GENERATION = "code_generation"          # 代码生成
    DATA_ANALYSIS = "data_analysis"              # 数据分析
    RISK_ASSESSMENT = "risk_assessment"          # 风险评估
    MARKET_PREDICTION = "market_prediction"      # 市场预测
    SENTIMENT_ANALYSIS = "sentiment_analysis"    # 情感分析
    OPTIMIZATION = "optimization"                # 优化建议
    DEBUGGING = "debugging"                      # 调试修复


@dataclass
class AIModel:
    """AI模型配置"""
    name: str
    key: str
    provider: str
    model: str
    api_base: str
    strengths: List[str]
    cost: float = 0.0
    speed: float = 1.0
    reliability: float = 0.95


@dataclass
class TaskResult:
    """任务结果"""
    model: str
    task_type: TaskType
    content: str
    confidence: float
    reasoning: str = ""
    metadata: Dict[str, Any] = None


class AICollaborationEngine:
    """
    AI协同工作引擎
    - 智能任务分配
    - 多模型并行处理
    - 结果融合与投票
    - 故障转移与重试
    """
    
    def __init__(self):
        self.models: Dict[str, AIModel] = {}
        self.task_assignments: Dict[TaskType, List[str]] = {}
        self._load_config()
        self._setup_task_assignments()
        
    def _load_config(self):
        """加载AI模型配置"""
        try:
            from config import AI_MODELS
            for key, cfg in AI_MODELS.items():
                self.models[key] = AIModel(
                    name=cfg["name"],
                    key=cfg.get("api_key", ""),
                    provider=cfg["provider"],
                    model=cfg["model"],
                    api_base=cfg["api_base"],
                    strengths=cfg.get("strengths", []),
                    cost=0.0 if cfg.get("tier", 3) == 1 else 0.001,
                    speed=1.0 if "turbo" in key or "flash" in key else 0.8,
                    reliability=0.98 if cfg.get("recommended", False) else 0.9
                )
            logger.info(f"✅ 加载了 {len(self.models)} 个AI模型")
        except Exception as e:
            logger.error(f"加载AI配置失败: {e}")
            self.models = {}
    
    def _setup_task_assignments(self):
        """设置任务分配策略"""
        # 根据模型优势分配任务
        self.task_assignments = {
            TaskType.STRATEGY_ANALYSIS: ["glm-5", "deepseek-v3"],
            TaskType.CODE_GENERATION: ["deepseek-coder", "glm-5"],
            TaskType.DATA_ANALYSIS: ["glm-turbo", "deepseek-v3"],
            TaskType.RISK_ASSESSMENT: ["glm-5", "deepseek-v3"],
            TaskType.MARKET_PREDICTION: ["glm-turbo", "siliconflow-qwen"],
            TaskType.SENTIMENT_ANALYSIS: ["glm-turbo", "deepseek-v3"],
            TaskType.OPTIMIZATION: ["deepseek-v3", "glm-5"],
            TaskType.DEBUGGING: ["deepseek-coder", "glm-5"],
        }
    
    def get_best_models_for_task(self, task_type: TaskType, count: int = 2) -> List[str]:
        """获取最适合某个任务的模型"""
        assigned = self.task_assignments.get(task_type, [])
        available = [m for m in assigned if m in self.models]
        
        # 如果指定模型不够，补充其他可用模型
        if len(available) < count:
            other_models = [m for m in self.models.keys() 
                          if m not in available and "turbo" in m or "flash" in m]
            available.extend(other_models[:count - len(available)])
        
        return available[:count]
    
    async def call_model_async(self, model_key: str, prompt: str, 
                              system_prompt: str = None, temperature: float = 0.7) -> Dict:
        """异步调用单个模型"""
        model = self.models.get(model_key)
        if not model:
            return {"success": False, "error": f"模型 {model_key} 不存在"}
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {model.key}",
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        
        try:
            import aiohttp
            import asyncio
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{model.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        return {
                            "success": True,
                            "content": content,
                            "model": model_key,
                            "model_name": model.name,
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "model": model_key,
                        }
        except Exception as e:
            logger.error(f"模型 {model_key} 调用失败: {e}")
            return {"success": False, "error": str(e), "model": model_key}
    
    async def collaborative_analysis(self, task_type: TaskType, prompt: str,
                                   system_prompt: str = None, 
                                   model_count: int = 3) -> Dict:
        """
        多模型协同分析
        """
        # 1. 选择最适合的模型
        model_keys = self.get_best_models_for_task(task_type, model_count)
        logger.info(f"🤖 协同分析: 使用 {len(model_keys)} 个模型 ({', '.join(model_keys)})")
        
        # 2. 并行调用所有模型
        tasks = []
        for model_key in model_keys:
            task = self.call_model_async(model_key, prompt, system_prompt)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. 处理结果
        successful = []
        failed = []
        
        for i, result in enumerate(results):
            model_key = model_keys[i]
            if isinstance(result, Exception):
                failed.append({"model": model_key, "error": str(result)})
            elif result.get("success"):
                successful.append(result)
            else:
                failed.append({"model": model_key, "error": result.get("error", "未知错误")})
        
        # 4. 结果融合
        if successful:
            fused_result = self._fuse_results(successful, task_type)
            return {
                "success": True,
                "task_type": task_type.value,
                "fused_result": fused_result,
                "individual_results": successful,
                "failed_models": failed,
                "model_count": len(successful),
            }
        else:
            return {
                "success": False,
                "error": "所有模型调用失败",
                "failed_models": failed,
            }
    
    def _fuse_results(self, results: List[Dict], task_type: TaskType) -> Dict:
        """融合多个模型的结果"""
        if len(results) == 1:
            return {
                "content": results[0]["content"],
                "confidence": 0.8,
                "consensus": "single_model",
            }
        
        # 提取所有回答
        contents = [r["content"] for r in results]
        models = [r["model_name"] for r in results]
        
        # 根据任务类型使用不同的融合策略
        if task_type in [TaskType.CODE_GENERATION, TaskType.DEBUGGING]:
            # 代码任务：选择最详细的回答
            best_idx = max(range(len(contents)), key=lambda i: len(contents[i]))
            return {
                "content": contents[best_idx],
                "confidence": 0.85,
                "consensus": "most_detailed",
                "selected_model": models[best_idx],
            }
        elif task_type in [TaskType.RISK_ASSESSMENT, TaskType.MARKET_PREDICTION]:
            # 风险/预测任务：提取共识
            consensus = self._extract_consensus(contents)
            return {
                "content": consensus,
                "confidence": self._calculate_confidence(contents),
                "consensus": "extracted",
                "model_agreement": len(set(contents)) / len(contents),
            }
        else:
            # 其他任务：合并回答
            merged = self._merge_responses(contents)
            return {
                "content": merged,
                "confidence": 0.75,
                "consensus": "merged",
                "model_count": len(contents),
            }
    
    def _extract_consensus(self, contents: List[str]) -> str:
        """提取共识内容"""
        # 简单实现：取第一个回答作为基础
        if not contents:
            return "无共识"
        
        base = contents[0]
        # 在实际应用中，这里可以使用更复杂的NLP技术
        # 比如提取关键观点、计算相似度等
        return f"基于{len(contents)}个模型的分析，主要观点如下：\n\n{base}"
    
    def _calculate_confidence(self, contents: List[str]) -> float:
        """计算置信度"""
        if len(contents) <= 1:
            return 0.7
        
        # 简单实现：基于回答相似度
        # 在实际应用中，这里可以计算文本相似度
        unique_answers = len(set(contents))
        agreement = 1.0 - (unique_answers / len(contents))
        return 0.5 + agreement * 0.5
    
    def _merge_responses(self, contents: List[str]) -> str:
        """合并多个回答"""
        if not contents:
            return "无回答"
        
        merged = f"## 🤖 多模型协同分析报告\n\n"
        merged += f"**参与模型**: {len(contents)} 个\n\n"
        
        for i, content in enumerate(contents):
            merged += f"### 模型 {i+1} 的分析\n\n"
            merged += f"{content}\n\n"
            merged += "---\n\n"
        
        merged += "### 📊 综合分析结论\n\n"
        merged += "综合以上分析，建议：\n"
        merged += "1. 优先考虑多个模型都提到的关键点\n"
        merged += "2. 注意不同模型之间的分歧点\n"
        merged += "3. 根据具体任务选择最合适的建议\n"
        
        return merged
    
    def sync_collaborative_analysis(self, task_type: TaskType, prompt: str,
                                  system_prompt: str = None, 
                                  model_count: int = 3) -> Dict:
        """同步版本的协同分析"""
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.collaborative_analysis(task_type, prompt, system_prompt, model_count)
            )
            loop.close()
            return result
        except Exception as e:
            logger.error(f"同步协同分析失败: {e}")
            return {"success": False, "error": str(e)}


# 全局实例
_collaboration_engine = None

def get_collaboration_engine() -> AICollaborationEngine:
    """获取协同引擎单例"""
    global _collaboration_engine
    if _collaboration_engine is None:
        _collaboration_engine = AICollaborationEngine()
    return _collaboration_engine


# 使用示例
if __name__ == "__main__":
    engine = get_collaboration_engine()
    
    # 测试协同分析
    prompt = "分析贵州茅台(600519.SH)的投资价值，给出买入/持有/卖出的建议"
    
    result = engine.sync_collaborative_analysis(
        task_type=TaskType.STRATEGY_ANALYSIS,
        prompt=prompt,
        model_count=2
    )
    
    if result["success"]:
        print("✅ 协同分析成功")
        print(f"使用模型: {result['model_count']} 个")
        print(f"融合结果:\n{result['fused_result']['content'][:500]}...")
    else:
        print(f"❌ 协同分析失败: {result.get('error')}")