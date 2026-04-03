"""
QuantAnalyzer v3.3 — 全自动运行引擎
===============================
功能：
  1. 每日自动回测（收盘后15:30）
  2. 数据自动更新
  3. AI自动学习优化
  4. GitHub资源自动监控
  5. 自动报告生成
"""
import sys
import os
import time
import logging
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from threading import Thread
import pandas as pd

# ── 路径 ──
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── 确保目录存在 ──
for _d in ["logs", "data", "reports", "cache"]:
    (ROOT / _d).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(ROOT / "logs" / "auto_runner.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("AutoRunner")

# ═══════════════════════════════════════════════════
# 📊 核心调度器
# ═══════════════════════════════════════════════════

class QuantAutoRunner:
    """量化平台全自动运行引擎"""

    def __init__(self):
        self._running = False
        self._last_backtest = None
        self._last_data_update = None
        self._last_ai_learn = None
        self._last_github_sync = None
        self._log_file = ROOT / "logs" / "automation_log.jsonl"
        for d in ["logs", "data", "reports", "cache"]:
            (ROOT / d).mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _ensure_dirs(self):
        for d in ["logs", "data", "reports", "cache"]:
            (ROOT / d).mkdir(parents=True, exist_ok=True)

    def _load_state(self):
        state_file = ROOT / "cache" / "runner_state.json"
        if state_file.exists():
            try:
                with open(state_file, encoding="utf-8") as f:
                    state = json.load(f)
                    self._last_backtest = state.get("last_backtest")
                    self._last_data_update = state.get("last_data_update")
                    self._last_ai_learn = state.get("last_ai_learn")
                    self._last_github_sync = state.get("last_github_sync")
            except Exception:
                pass

    def _save_state(self):
        state = {
            "last_backtest": self._last_backtest,
            "last_data_update": self._last_data_update,
            "last_ai_learn": self._last_ai_learn,
            "last_github_sync": self._last_github_sync,
            "updated": datetime.now().isoformat(),
        }
        with open(ROOT / "cache" / "runner_state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    # ── ① 每日自动回测 ──
    def run_daily_backtest(self, force: bool = False) -> dict:
        """每日收盘后自动回测所有策略"""
        today = datetime.now().strftime("%Y-%m-%d")

        if not force and self._last_backtest == today:
            logger.info(f"今日({today})回测已完成，跳过")
            return {"skipped": True, "reason": "already_run_today"}

        logger.info(f"=== 开始每日自动回测 {today} ===")
        results = []

        try:
            from data.fetcher import DataFetcher, db
            from core.engine import BacktestEngine

            # 动态加载所有策略
            strategies = self._discover_strategies()
            logger.info(f"发现 {len(strategies)} 个策略待回测")

            fetcher = DataFetcher()
            engine = BacktestEngine()

            # 获取回测数据（沪深300ETF 510300）
            test_stocks = ["600519.SH", "000858.SZ", "600036.SH", "510300.SH"]
            data = pd.DataFrame()

            for stock in test_stocks:
                try:
                    data = fetcher.get_stock_daily(stock)
                    if not data.empty:
                        logger.info(f"获取 {stock} 数据成功，共 {len(data)} 条")
                        break
                except Exception:
                    continue

            if data.empty:
                logger.error("无法获取任何股票数据")
                return {"error": "no_data"}

            # 获取基准
            try:
                benchmark = fetcher.get_index_daily("000300")
            except Exception:
                benchmark = None

            # 回测每个策略
            for name, cls, params in strategies:
                try:
                    t0 = time.time()
                    result = engine.run(cls, data, benchmark, **params)
                    result["strategy_name"] = name
                    result["stock_code"] = stock
                    result["backtest_date"] = today

                    # 保存到数据库
                    db.save_backtest_result(result)
                    if "daily_values" in result and not result["daily_values"].empty:
                        db.save_daily_values(name, result["daily_values"])

                    elapsed = time.time() - t0
                    logger.info(f"  {name}: 年化={result.get('annual_return',0):.2%} 夏普={result.get('sharpe_ratio',0):.2f} ({elapsed:.1f}s)")
                    results.append(result)

                except Exception as e:
                    logger.error(f"  {name} 回测失败: {e}")

            self._last_backtest = today
            self._save_state()
            logger.info(f"=== 每日回测完成，共 {len(results)} 个策略 ===")

            return {"success": True, "count": len(results), "results": results}

        except ImportError as e:
            logger.error(f"导入失败: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"回测异常: {e}")
            import traceback; traceback.print_exc()
            return {"error": str(e)}

    def _discover_strategies(self):
        """动态发现所有可用策略"""
        strategies = []
        strategy_dir = ROOT / "strategy_library"

        # 内置策略映射（从 strategy_library/ 加载）
        builtin_map = [
            ("双均线交叉", "strategy_library.ma_cross", "MACross"),
            ("RSI策略", "strategy_library.rsi_strategy", "RSIStrategy"),
            ("动量策略", "strategy_library.momentum", "Momentum"),
            ("布林带策略", "strategy_library.bollinger", "BollingerBands"),
            ("MACD策略", "strategy_library.macd", "MACDStrategy"),
            ("CCI反转", "strategy_library.cci_reversal", "CCIReversal"),
            ("Donchian通道", "strategy_library.donchian", "DonchianChannel"),
            ("因子择时", "strategy_library.factor_timing", "FactorTiming"),
            ("一目均衡", "strategy_library.ichimoku", "IchimokuCloud"),
            ("均值回归", "strategy_library.mean_reversion", "MeanReversion"),
            ("多因子策略", "strategy_library.multi_factor", "MultiFactor"),
            ("OBV趋势", "strategy_library.obv_trend", "OBVTrend"),
            ("配对交易", "strategy_library.pair_trading", "PairTrading"),
            ("行业轮动", "strategy_library.sector_rotation", "SectorRotation"),
            ("小市值量化", "strategy_library.small_cap_quant", "SmallCapQuant"),
            ("超级趋势", "strategy_library.supertrend", "Supertrend"),
            ("海龟策略", "strategy_library.turtle", "Turtle"),
            ("波动率突破", "strategy_library.vol_breakout", "VolatilityBreakout"),
            ("VWAP策略", "strategy_library.vwap", "VWAPStrategy"),
        ]

        for display_name, module_path, class_name in builtin_map:
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                strategies.append((display_name, cls, {}))
            except (ImportError, AttributeError) as e:
                logger.warning(f"  跳过 {display_name}: {e}")
                continue

        return strategies

    # ── ② 数据自动更新 ──
    def update_market_data(self, force: bool = False) -> dict:
        """更新日线数据到最新"""
        today = datetime.now().strftime("%Y-%m-%d")

        if not force and self._last_data_update == today:
            logger.info(f"今日({today})数据已更新，跳过")
            return {"skipped": True}

        logger.info("=== 开始更新日线数据 ===")

        try:
            from data.fetcher import DataFetcher
            from config import STOCK_POOL

            fetcher = DataFetcher()
            updated = 0

            for ts_code in STOCK_POOL[:20]:  # 限制数量避免超时
                try:
                    data = fetcher.get_stock_daily(
                        ts_code,
                        start_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                        end_date=today,
                    )
                    if not data.empty:
                        # 缓存到本地CSV
                        cache_file = ROOT / "data" / f"{ts_code.replace('.', '_')}_daily.csv"
                        if cache_file.exists():
                            old = pd.read_csv(cache_file, parse_dates=["date"], index_col="date")
                            combined = pd.concat([old, data]).drop_duplicates().sort_index()
                            combined.to_csv(cache_file)
                        else:
                            data.to_csv(cache_file)
                        updated += 1
                        logger.info(f"  更新 {ts_code}: {len(data)} 条")
                except Exception as e:
                    logger.warning(f"  {ts_code} 更新失败: {e}")

            fetcher.close()
            self._last_data_update = today
            self._save_state()
            logger.info(f"=== 数据更新完成: {updated}/{len(STOCK_POOL[:20])} 只 ===")
            return {"success": True, "updated": updated}

        except Exception as e:
            logger.error(f"数据更新失败: {e}")
            return {"error": str(e)}

    # ── ③ AI自动学习 ──
    def run_ai_learning(self, force: bool = False) -> dict:
        """AI自学习优化策略"""
        today = datetime.now().strftime("%Y-%m-%d")

        # AI学习每3天执行一次
        should_run = force
        if self._last_ai_learn:
            days_since = (datetime.now() - datetime.fromisoformat(self._last_ai_learn)).days
            should_run = should_run or (days_since >= 3)

        if not should_run:
            logger.info("AI学习：距上次学习不足3天，跳过")
            return {"skipped": True}

        logger.info("=== 开始AI自学习 ===")

        try:
            from data.fetcher import db
            from core.ai_analyzer import AIAnalyzer

            results = db.get_latest_results()
            if results.empty:
                logger.warning("没有回测数据可学习")
                return {"error": "no_data"}

            analyzer = AIAnalyzer()
            insight = analyzer.auto_learn(results.to_dict("records"))

            # 保存学习报告
            report_file = ROOT / "reports" / f"ai_learn_{today}.md"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(f"# AI自学习报告\n\n")
                f.write(f"生成时间：{datetime.now()}\n\n")
                f.write(insight)

            self._last_ai_learn = today
            self._save_state()
            logger.info("=== AI自学习完成 ===")
            return {"success": True, "report": report_file}

        except Exception as e:
            logger.error(f"AI学习失败: {e}")
            return {"error": str(e)}

    # ── ④ GitHub自动同步 ──
    def sync_github_resources(self, force: bool = False) -> dict:
        """自动同步GitHub量化资源"""
        today = datetime.now().strftime("%Y-%m-%d")

        # GitHub同步每周一次
        should_run = force
        if self._last_github_sync:
            days_since = (datetime.now() - datetime.fromisoformat(self._last_github_sync)).days
            should_run = should_run or (days_since >= 7)

        if not should_run:
            return {"skipped": True}

        logger.info("=== 开始GitHub资源同步 ===")

        try:
            # 关键量化项目列表
            key_repos = [
                ("BondTwilight/QuantAnalyzer", "quant-analyzer"),
                ("AI4Finance-Foundation/Qlib", "qlib"),
                ("vnpy/vnpy", "vnpy"),
                ("martenjain/Backtrader", "backtrader"),
                ("mikedever/TradingBot", "tradingbot"),
                ("shichenxie/quant-dashboard", "quant-dashboard"),
                ("jiangfei-maker/SmartQuant-Trading-System", "smartquant"),
            ]

            sync_file = ROOT / "cache" / "github_sync.json"
            existing = {}
            if sync_file.exists():
                try:
                    with open(sync_file, encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    pass

            for repo, local_name in key_repos:
                try:
                    # 使用 gh CLI 检查更新
                    result = subprocess.run(
                        ["gh", "api", f"repos/{repo}"],
                        capture_output=True, text=True, timeout=15
                    )
                    if result.returncode == 0:
                        info = json.loads(result.stdout)
                        existing[repo] = {
                            "stars": info.get("stargazers_count", 0),
                            "forks": info.get("forks_count", 0),
                            "updated": info.get("pushed_at", ""),
                            "description": info.get("description", ""),
                            "language": info.get("language", ""),
                            "last_checked": today,
                        }
                except Exception as e:
                    logger.warning(f"  检查 {repo} 失败: {e}")

            with open(sync_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            self._last_github_sync = today
            self._save_state()
            logger.info(f"=== GitHub同步完成: {len(existing)} 个项目 ===")
            return {"success": True, "count": len(existing)}

        except Exception as e:
            logger.error(f"GitHub同步失败: {e}")
            return {"error": str(e)}

    # ── ⑤ 全自动主循环 ──
    def run_full_cycle(self):
        """执行完整自动化循环"""
        logger.info("=== 全自动循环开始 ===")

        cycle_results = {}

        # ① 更新数据
        cycle_results["data_update"] = self.update_market_data()

        # ② 每日回测
        cycle_results["backtest"] = self.run_daily_backtest()

        # ③ AI学习（每3天）
        cycle_results["ai_learn"] = self.run_ai_learning()

        # ④ GitHub同步（每周）
        cycle_results["github_sync"] = self.sync_github_resources()

        # 记录循环结果
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "results": cycle_results,
        }
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        logger.info("=== 全自动循环完成 ===")
        return cycle_results

    # ── 后台守护进程 ──
    def start_daemon(self, check_interval: int = 3600):
        """启动后台守护进程，每隔check_interval秒检查是否需要执行任务"""
        self._running = True
        logger.info(f"守护进程启动，检查间隔: {check_interval}s")

        while self._running:
            try:
                self._check_and_run()
            except Exception as e:
                logger.error(f"守护进程异常: {e}")
                import traceback; traceback.print_exc()

            time.sleep(check_interval)

    def _check_and_run(self):
        """检查并执行到期的任务"""
        now = datetime.now()
        weekday = now.weekday()  # 0=周一

        # 工作日 15:30 自动回测
        if weekday < 5:
            if now.hour == 15 and now.minute >= 25 and now.minute <= 35:
                if self._last_backtest != now.strftime("%Y-%m-%d"):
                    self.run_daily_backtest()
                    time.sleep(120)  # 避免重复执行

        # 每日数据更新（收盘后）
        if now.hour == 16 and now.minute >= 0 and now.minute <= 30:
            if self._last_data_update != now.strftime("%Y-%m-%d"):
                self.update_market_data()
                time.sleep(120)

    def stop_daemon(self):
        self._running = False
        logger.info("守护进程已停止")


# ═══════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="QuantAnalyzer 全自动运行引擎")
    parser.add_argument("--once", action="store_true", help="执行一次完整循环")
    parser.add_argument("--backtest", action="store_true", help="仅运行回测")
    parser.add_argument("--data", action="store_true", help="仅更新数据")
    parser.add_argument("--ai", action="store_true", help="仅运行AI学习")
    parser.add_argument("--daemon", action="store_true", help="启动守护进程")
    parser.add_argument("--force", action="store_true", help="强制执行（忽略时间检查）")
    args = parser.parse_args()

    runner = QuantAutoRunner()

    if args.once:
        runner.run_full_cycle()
    elif args.backtest:
        result = runner.run_daily_backtest(force=args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.data:
        result = runner.update_market_data(force=args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.ai:
        result = runner.run_ai_learning(force=args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.daemon:
        runner.start_daemon()
    else:
        print("用法:")
        print("  python auto_runner.py --once       # 执行一次完整循环")
        print("  python auto_runner.py --backtest   # 仅运行回测")
        print("  python auto_runner.py --data       # 仅更新数据")
        print("  python auto_runner.py --ai         # 仅运行AI学习")
        print("  python auto_runner.py --daemon     # 启动守护进程")
