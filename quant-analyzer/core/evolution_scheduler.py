"""
⏰ 进化调度器 — EvolutionScheduler

核心功能:
- 定时触发策略进化循环（每日收盘后 / 自定义频率）
- 定时触发因子IC更新（每周）
- Streamlit 集成（页面内自动运行）
- 手动触发接口
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, Dict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SCHEDULER_STATE_FILE = DATA_DIR / "scheduler_state.json"


class EvolutionScheduler:
    """进化调度器 — 管理自动进化循环的定时执行"""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_cycle_time: Optional[datetime] = None
        self._last_factor_update: Optional[datetime] = None
        self._cycle_interval_hours: float = 24  # 进化循环间隔（小时）
        self._factor_interval_hours: float = 168  # 因子更新间隔（小时，默认7天）
        self._evolution_count = 0
        self._is_cycle_running = False  # 防止重复触发
        self._progress_callback: Optional[Callable] = None
        self._load_state()

    def _load_state(self):
        """加载调度器状态"""
        if SCHEDULER_STATE_FILE.exists():
            try:
                data = json.loads(SCHEDULER_STATE_FILE.read_text(encoding="utf-8"))
                self._evolution_count = data.get("evolution_count", 0)
                last_cycle = data.get("last_cycle_time")
                if last_cycle:
                    self._last_cycle_time = datetime.fromisoformat(last_cycle)
                last_factor = data.get("last_factor_update")
                if last_factor:
                    self._last_factor_update = datetime.fromisoformat(last_factor)
                self._cycle_interval_hours = data.get("cycle_interval_hours", 24)
            except Exception as e:
                logger.warning(f"加载调度器状态失败: {e}")

    def _save_state(self):
        """保存调度器状态"""
        try:
            data = {
                "evolution_count": self._evolution_count,
                "last_cycle_time": self._last_cycle_time.isoformat() if self._last_cycle_time else None,
                "last_factor_update": self._last_factor_update.isoformat() if self._last_factor_update else None,
                "cycle_interval_hours": self._cycle_interval_hours,
                "updated_at": datetime.now().isoformat(),
            }
            SCHEDULER_STATE_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"保存调度器状态失败: {e}")

    def set_progress_callback(self, callback: Callable):
        """设置进度回调"""
        self._progress_callback = callback

    def set_cycle_interval(self, hours: float):
        """设置进化循环间隔"""
        self._cycle_interval_hours = hours
        self._save_state()

    def manual_trigger(self) -> Dict:
        """手动触发一轮进化

        Returns:
            {"status": "started" | "already_running" | "error", "message": str}
        """
        if self._is_cycle_running:
            return {"status": "already_running", "message": "进化循环正在运行中，请等待完成"}

        # 检查间隔是否满足
        if self._last_cycle_time:
            elapsed = (datetime.now() - self._last_cycle_time).total_seconds() / 3600
            if elapsed < self._cycle_interval_hours:
                remaining = self._cycle_interval_hours - elapsed
                return {
                    "status": "error",
                    "message": f"距上次进化仅 {elapsed:.1f} 小时，需等待 {remaining:.1f} 小时",
                }

        # 在后台线程执行
        thread = threading.Thread(target=self._run_evolution_cycle, daemon=True)
        thread.start()

        return {"status": "started", "message": "进化循环已启动"}

    def force_trigger(self) -> Dict:
        """强制触发（忽略间隔限制）"""
        if self._is_cycle_running:
            return {"status": "already_running", "message": "进化循环正在运行中"}

        thread = threading.Thread(target=self._run_evolution_cycle, daemon=True)
        thread.start()
        return {"status": "started", "message": "进化循环已强制启动"}

    def _run_evolution_cycle(self):
        """执行一轮进化循环"""
        self._is_cycle_running = True

        def progress_cb(pct, msg):
            logger.info(f"[Evolution] {pct:.0f}% - {msg}")
            if self._progress_callback:
                try:
                    self._progress_callback(pct, msg)
                except Exception:
                    pass

        try:
            from core.auto_evolution import get_evolution_engine
            engine = get_evolution_engine()
            result = engine.run_cycle(progress_cb=progress_cb)

            self._last_cycle_time = datetime.now()
            self._evolution_count += 1
            self._save_state()

            logger.info(f"进化循环 #{self._evolution_count} 完成，"
                        f"发现 {result.strategies_discovered} 个策略，"
                        f"通过 {result.strategies_passed} 个")

        except Exception as e:
            logger.error(f"进化循环异常: {e}")
        finally:
            self._is_cycle_running = False

    def update_factors(self) -> Dict:
        """手动触发因子IC更新"""
        try:
            from core.factor_manager import FactorManager
            fm = FactorManager()

            stock_pool = ["000001", "000333", "600519", "601318", "300750"]
            fm.batch_update_ic(stock_pool)

            # 去冗余
            removed = fm.deduplicate_factors()

            self._last_factor_update = datetime.now()
            self._save_state()

            return {
                "status": "success",
                "total_factors": len(fm.factors),
                "effective_factors": len(fm.get_effective_factors()),
                "removed_factors": removed,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ─── 后台自动运行（可选） ───

    def start_background(self):
        """启动后台调度线程"""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._background_loop, daemon=True)
        self._thread.start()
        logger.info("进化调度器后台线程已启动")

    def stop_background(self):
        """停止后台调度"""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("进化调度器后台线程已停止")

    def _background_loop(self):
        """后台循环"""
        while self._running and not self._stop_event.is_set():
            try:
                now = datetime.now()

                # 检查是否到了进化时间（工作日 15:30 后）
                should_evolve = False
                if self._last_cycle_time is None:
                    should_evolve = True
                else:
                    elapsed_hours = (now - self._last_cycle_time).total_seconds() / 3600
                    if elapsed_hours >= self._cycle_interval_hours:
                        # 仅在工作日 15:30-23:59 运行
                        if now.weekday() < 5 and now.hour >= 15:
                            should_evolve = True

                if should_evolve and not self._is_cycle_running:
                    logger.info("后台调度器触发进化循环")
                    self._run_evolution_cycle()

                # 检查因子更新
                should_update_factors = False
                if self._last_factor_update is None:
                    should_update_factors = True
                else:
                    elapsed_hours = (now - self._last_factor_update).total_seconds() / 3600
                    if elapsed_hours >= self._factor_interval_hours:
                        should_update_factors = True

                if should_update_factors:
                    logger.info("后台调度器触发因子更新")
                    self.update_factors()

            except Exception as e:
                logger.error(f"后台调度异常: {e}")

            # 每分钟检查一次
            self._stop_event.wait(60)

    # ─── 状态查询 ───

    def get_status(self) -> Dict:
        """获取调度器状态"""
        now = datetime.now()

        next_cycle_time = "未安排"
        if self._last_cycle_time:
            next_dt = self._last_cycle_time + timedelta(hours=self._cycle_interval_hours)
            if next_dt > now:
                remaining = (next_dt - now).total_seconds() / 3600
                next_cycle_time = f"{remaining:.1f} 小时后"

        next_factor_time = "未安排"
        if self._last_factor_update:
            next_dt = self._last_factor_update + timedelta(hours=self._factor_interval_hours)
            if next_dt > now:
                remaining = (next_dt - now).total_seconds() / 3600
                next_factor_time = f"{remaining:.1f} 小时后"

        return {
            "is_running": self._is_cycle_running,
            "background_enabled": self._running,
            "evolution_count": self._evolution_count,
            "cycle_interval_hours": self._cycle_interval_hours,
            "last_cycle_time": self._last_cycle_time.strftime("%Y-%m-%d %H:%M") if self._last_cycle_time else "从未",
            "last_factor_update": self._last_factor_update.strftime("%Y-%m-%d %H:%M") if self._last_factor_update else "从未",
            "next_cycle": next_cycle_time,
            "next_factor_update": next_factor_time,
        }


# ═══════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════

_scheduler_instance = None

def get_scheduler() -> EvolutionScheduler:
    """获取全局调度器单例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = EvolutionScheduler()
    return _scheduler_instance
