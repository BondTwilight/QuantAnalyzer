"""
异步任务管理器 — 处理耗时的AI任务，避免阻塞UI
"""

import asyncio
import threading
import queue
import time
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 任务状态目录
TASK_DIR = Path(__file__).parent.parent / "cache" / "tasks"
TASK_DIR.mkdir(parents=True, exist_ok=True)


class AsyncTask:
    """异步任务"""
    
    def __init__(self, task_id: str, task_type: str, func: Callable, *args, **kwargs):
        self.task_id = task_id
        self.task_type = task_type
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = "pending"  # pending, running, completed, failed
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.progress = 0.0  # 0-100
        self.message = ""
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "result": self.result,
            "error": str(self.error) if self.error else None,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "message": self.message
        }
    
    def save_state(self):
        """保存任务状态到文件"""
        state_file = TASK_DIR / f"{self.task_id}.json"
        try:
            state_file.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"保存任务状态失败: {e}")
    
    def update_progress(self, progress: float, message: str = ""):
        """更新进度"""
        self.progress = min(100.0, max(0.0, progress))
        self.message = message
        self.save_state()
    
    def execute(self, progress_cb=None):
        """执行任务"""
        try:
            self.status = "running"
            self.started_at = datetime.now()
            self.save_state()
            
            logger.info(f"开始执行任务: {self.task_type} ({self.task_id})")
            
            # 将任务实例绑定到当前线程，方便内部函数通过 threading.current_thread()._task 更新进度
            threading.current_thread()._task = self
            
            # 执行函数（支持传入 progress_cb）
            if progress_cb:
                self.result = self.func(*self.args, **self.kwargs, progress_cb=self.update_progress)
            else:
                self.result = self.func(*self.args, **self.kwargs)
            
            self.status = "completed"
            self.completed_at = datetime.now()
            self.progress = 100.0
            self.message = "任务完成"
            self.save_state()
            
            logger.info(f"任务完成: {self.task_type} ({self.task_id})")
            
        except Exception as e:
            self.status = "failed"
            self.completed_at = datetime.now()
            self.error = e
            self.message = f"任务失败: {str(e)}"
            self.save_state()
            
            logger.error(f"任务失败: {self.task_type} ({self.task_id}): {e}")


class AsyncTaskManager:
    """异步任务管理器"""
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.task_queue = queue.Queue()
            self.tasks: Dict[str, AsyncTask] = {}
            self.worker_thread = None
            self.running = False
            self.max_workers = 2  # 最大并发任务数
            self._initialized = True
            logger.info("异步任务管理器初始化完成")
    
    def start(self):
        """启动任务管理器"""
        with self._lock:
            if not self.running:
                self.running = True
                self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self.worker_thread.start()
                logger.info("异步任务管理器已启动")
    
    def stop(self):
        """停止任务管理器"""
        with self._lock:
            self.running = False
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
            logger.info("异步任务管理器已停止")
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.running:
            try:
                # 获取任务
                task = self.task_queue.get(timeout=1)
                if task is None:
                    continue
                
                # 执行任务（传入 progress_cb）
                task.execute(progress_cb=task.update_progress)
                
                # 清理已完成的任务（保留最近100个）
                self._cleanup_old_tasks()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程异常: {e}")
                time.sleep(1)
    
    def submit_task(self, task_type: str, func: Callable, *args, **kwargs) -> str:
        """提交新任务"""
        with self._lock:
            # 生成任务ID
            task_id = f"{task_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(str(args) + str(kwargs)) % 10000:04d}"
            
            # 创建任务
            task = AsyncTask(task_id, task_type, func, *args, **kwargs)
            self.tasks[task_id] = task
            
            # 添加到队列
            self.task_queue.put(task)
            
            # 确保工作线程运行
            if not self.running:
                self.start()
            
            logger.info(f"提交新任务: {task_type} ({task_id})")
            return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        with self._lock:
            if task_id in self.tasks:
                return self.tasks[task_id].to_dict()
            
            # 尝试从文件加载
            state_file = TASK_DIR / f"{task_id}.json"
            if state_file.exists():
                try:
                    return json.loads(state_file.read_text(encoding="utf-8"))
                except:
                    pass
            
            return None
    
    def wait_for_task(self, task_id: str, timeout: float = 300.0) -> Optional[Any]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            if not status:
                return None
            
            if status["status"] == "completed":
                return status.get("result")
            elif status["status"] == "failed":
                raise Exception(f"任务失败: {status.get('error', '未知错误')}")
            
            time.sleep(0.5)
        
        raise TimeoutError(f"任务超时: {task_id}")
    
    def _cleanup_old_tasks(self):
        """清理旧任务"""
        try:
            # 获取所有任务文件
            task_files = list(TASK_DIR.glob("*.json"))
            if len(task_files) <= 100:  # 保留最近100个任务
                return
            
            # 按修改时间排序
            task_files.sort(key=lambda f: f.stat().st_mtime)
            
            # 删除旧任务
            files_to_delete = task_files[:-100]
            for f in files_to_delete:
                try:
                    f.unlink()
                    task_id = f.stem
                    if task_id in self.tasks:
                        del self.tasks[task_id]
                except:
                    pass
            
            logger.debug(f"清理了 {len(files_to_delete)} 个旧任务")
        except Exception as e:
            logger.warning(f"清理旧任务失败: {e}")


# 全局任务管理器实例
task_manager = AsyncTaskManager()


# 装饰器：将函数转换为异步任务
def async_task(task_type: str = "default"):
    """异步任务装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 提交异步任务
            task_id = task_manager.submit_task(task_type, func, *args, **kwargs)
            
            # 立即返回任务ID，不等待结果
            return {
                "task_id": task_id,
                "status": "submitted",
                "message": f"任务已提交，ID: {task_id}"
            }
        
        return wrapper
    return decorator


# 预定义的异步任务函数
class AsyncTasks:
    """预定义的异步任务"""
    
    @staticmethod
    @async_task("github_search")
    def search_github_strategies(keywords: List[str] = None):
        """异步搜索GitHub策略"""
        from core.quant_brain import QuantBrain
        brain = QuantBrain()
        
        # 更新进度
        task_id = threading.current_thread().name
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(10, "正在初始化...")
        
        # 搜索策略
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(30, "正在搜索GitHub...")
        
        strategies = brain.learner.learn_from_github(keywords)
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(80, "正在分析策略...")
        
        # 格式化结果
        result = []
        for s in strategies:
            result.append({
                "name": s.name,
                "source": s.source,
                "category": s.category,
                "quality_score": s.quality_score,
                "description": s.description[:200] + "..." if len(s.description) > 200 else s.description
            })
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(100, "搜索完成")
        
        return result
    
    @staticmethod
    @async_task("ai_generate_strategy")
    def ai_generate_strategy(prompt: str, strategy_type: str = "trend_following"):
        """异步AI生成策略"""
        from core.quant_brain import QuantBrain
        brain = QuantBrain()
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(20, "正在初始化AI模型...")
        
        # 生成策略
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(50, "AI正在生成策略...")
        
        strategy = brain.learner.generate_strategy_with_ai(prompt, strategy_type)
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(80, "正在验证策略...")
        
        # 简单验证
        if strategy and "def " in strategy:
            status = "success"
        else:
            status = "failed"
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(100, "生成完成")
        
        return {
            "strategy_code": strategy,
            "status": status,
            "length": len(strategy) if strategy else 0
        }
    
    @staticmethod
    @async_task("daily_scan")
    def daily_scan_stocks(watch_list: List[str] = None):
        """异步每日扫描"""
        from core.quant_brain import QuantBrain
        brain = QuantBrain()
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(10, "正在初始化...")
        
        # 获取股票列表
        if watch_list is None:
            from core.performance_optimizer import optimized_data_provider
            stocks_df = optimized_data_provider.get_stock_list()
            if not stocks_df.empty:
                watch_list = stocks_df["code"].head(100).tolist()  # 限制前100只
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(30, f"正在扫描 {len(watch_list)} 只股票...")
        
        # 扫描股票
        signals = []
        total = len(watch_list)
        
        for i, code in enumerate(watch_list):
            try:
                # 生成信号
                sig = brain.signal_gen.generate_signal(code)
                if sig:
                    signals.append(sig)
                
                # 更新进度
                progress = 30 + (i / total) * 60
                if hasattr(threading.current_thread(), "_task"):
                    threading.current_thread()._task.update_progress(
                        progress, 
                        f"已扫描 {i+1}/{total} 只股票，发现 {len(signals)} 个信号"
                    )
                
                # 避免请求过快
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"扫描股票 {code} 失败: {e}")
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(100, "扫描完成")
        
        return {
            "total_scanned": total,
            "signals_found": len(signals),
            "signals": [s.__dict__ for s in signals[:10]]  # 只返回前10个信号
        }
    
    @staticmethod
    @async_task("ai_optimize_strategy")
    def ai_optimize_strategy(strategy_name: str):
        """异步AI优化策略"""
        from core.quant_brain import QuantBrain
        brain = QuantBrain()
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(20, "正在加载策略...")
        
        # 查找策略
        strategy = None
        for kb in brain.learner.knowledge_base:
            if kb.name == strategy_name:
                strategy = kb
                break
        
        if not strategy:
            raise ValueError(f"未找到策略: {strategy_name}")
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(40, "AI正在分析策略...")
        
        # 优化策略
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(60, "AI正在优化策略...")
        
        optimized = brain.learner.optimize_strategy(strategy_name)
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(80, "正在验证优化结果...")
        
        # 返回结果
        if optimized:
            result = {
                "status": "success",
                "original_name": strategy_name,
                "optimized_name": optimized.name,
                "optimized_code": optimized.code,
                "quality_score": optimized.quality_score,
                "improvement": optimized.quality_score - strategy.quality_score
            }
        else:
            result = {
                "status": "failed",
                "error": "优化失败"
            }
        
        if hasattr(threading.current_thread(), "_task"):
            threading.current_thread()._task.update_progress(100, "优化完成")
        
        return result
    
    @staticmethod
    @async_task("multi_source_learn")
    def multi_source_learn(keyword: str = "量化策略"):
        """异步多源策略学习"""
        import time as _time
        
        try:
            from core.multi_source_strategy import get_multi_source_learner, add_to_main_knowledge_base
            from core.quant_brain import QuantBrain
            brain = QuantBrain()
            learner = get_multi_source_learner()
            
            if hasattr(threading.current_thread(), "_task"):
                threading.current_thread()._task.update_progress(5, "开始搜索arXiv论文...")
            
            # arXiv搜索
            en_keyword = learner._to_english_keyword(keyword)
            arxiv_results = learner.learn_from_arxiv(en_keyword, limit=3)
            
            if hasattr(threading.current_thread(), "_task"):
                threading.current_thread()._task.update_progress(35, "搜索GitHub项目...")
            
            # GitHub搜索
            github_results = learner.learn_from_github(keyword, limit=3)
            
            if hasattr(threading.current_thread(), "_task"):
                threading.current_thread()._task.update_progress(65, "搜索量化社区...")
            
            # 量化社区搜索
            community_results = learner.learn_from_community(keyword, limit=3)
            
            if hasattr(threading.current_thread(), "_task"):
                threading.current_thread()._task.update_progress(85, "添加到主策略库...")
            
            # 将所有学习结果添加到主知识库
            total_added = 0
            all_results = arxiv_results + github_results + community_results
            for entry in all_results:
                try:
                    add_to_main_knowledge_base(entry, brain.learner)
                    total_added += 1
                except Exception:
                    pass
            
            if hasattr(threading.current_thread(), "_task"):
                threading.current_thread()._task.update_progress(100, "学习完成")
            
            return {
                "total": len(all_results),
                "details": {
                    "arXiv论文": len(arxiv_results),
                    "GitHub": len(github_results),
                    "量化社区": len(community_results),
                },
                "added_to_kb": total_added,
            }
        except Exception as e:
            logger.error(f"多源学习失败: {e}")
            raise

    @staticmethod
    @async_task("auto_evolution")
    def run_evolution_cycle(**kwargs):
        """异步执行一轮策略自进化循环"""
        from core.auto_evolution import get_evolution_engine

        engine = get_evolution_engine()

        # 定义进度回调
        def progress_cb(pct, msg):
            task = getattr(threading.current_thread(), "_task", None)
            if task:
                task.update_progress(pct, msg)

        result = engine.run_cycle(progress_cb=progress_cb)
        return result.to_dict()


# 启动任务管理器
task_manager.start()