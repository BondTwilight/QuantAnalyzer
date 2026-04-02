"""
自动化调度模块 — 每日自动回测 + AI分析
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import time

sys.path.insert(0, str(Path(__file__).parent.parent))
logger = logging.getLogger(__name__)


def run_all_backtests():
    """运行所有策略回测 — 每个策略只回测一只代表性股票(沪深300ETF)"""
    logger.info(f"=== 开始自动回测 {datetime.now()} ===")
    results_summary = []

    try:
        from data.fetcher import DataFetcher, db
        from core.engine import BacktestEngine
        from strategies.ma_cross import MACrossStrategy
        from strategies.rsi_strategy import RSIStrategy
        from strategies.momentum import MomentumStrategy
        from strategies.multi_factor import MultiFactorStrategy
        from strategies.sector_rotation import SectorRotationStrategy
        from strategies.bollinger import BollingerBandStrategy
        from strategies.jq_small_cap import JQSmallCapStrategy, JQDualThrustStrategy
        from config import BENCHMARK, DEFAULT_PERIOD

        fetcher = DataFetcher()
        engine = BacktestEngine()

        # 使用贵州茅台作为回测标的
        test_stock = "600519.SH"

        # 策略列表 (含聚宽经典策略)
        strategies = [
            ("双均线交叉", MACrossStrategy, {}),
            ("RSI均值回归", RSIStrategy, {}),
            ("动量策略", MomentumStrategy, {}),
            ("多因子选股", MultiFactorStrategy, {}),
            ("行业轮动", SectorRotationStrategy, {}),
            ("布林带策略", BollingerBandStrategy, {}),
            ("聚宽小市值", JQSmallCapStrategy, {}),
            ("聚宽DualThrust", JQDualThrustStrategy, {}),
        ]

        # 获取回测数据
        logger.info(f"获取 {test_stock} 日线数据...")
        data = fetcher.get_stock_daily(test_stock)
        if data.empty:
            logger.error(f"获取 {test_stock} 数据失败，尝试其他标的")
            # 备选: 贵州茅台
            test_stock = "600519.SH"
            data = fetcher.get_stock_daily(test_stock)
        if data.empty:
            logger.error("所有备选标的数据获取失败")
            return results_summary

        logger.info(f"获取到 {len(data)} 条日线数据 ({data.index[0].strftime('%Y-%m-%d')} ~ {data.index[-1].strftime('%Y-%m-%d')})")

        # 获取基准数据
        logger.info("获取沪深300基准数据...")
        benchmark = fetcher.get_index_daily("000300")
        if benchmark.empty:
            logger.warning("基准数据获取失败，将无基准对比")
            benchmark = None

        # 逐策略回测
        for strategy_name, strategy_class, params in strategies:
            try:
                t0 = time.time()
                logger.info(f"回测: {strategy_name}")

                result = engine.run(strategy_class, data, benchmark, **params)
                result["strategy_name"] = strategy_name
                result["stock_code"] = test_stock

                # 保存结果
                db.save_backtest_result(result)
                if "daily_values" in result and not result["daily_values"].empty:
                    db.save_daily_values(result["strategy_name"], result["daily_values"])
                if "trades" in result:
                    db.save_trades(result["strategy_name"], result["trades"])

                elapsed = time.time() - t0
                logger.info(f"  完成: 年化={result.get('annual_return', 0):.2%} 夏普={result.get('sharpe_ratio', 0):.2f} ({elapsed:.1f}s)")
                results_summary.append({
                    "strategy": strategy_name,
                    "annual_return": result.get("annual_return", 0),
                    "sharpe": result.get("sharpe_ratio", 0),
                    "max_dd": result.get("max_drawdown", 0),
                    "time": f"{elapsed:.1f}s",
                })

            except Exception as e:
                logger.error(f"  失败: {e}")
                import traceback; traceback.print_exc()
                continue

        logger.info("=== 自动回测完成 ===")
        return results_summary

    except ImportError as e:
        logger.error(f"导入失败: {e}")
        return results_summary


def setup_scheduler():
    """设置定时调度"""
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        run_all_backtests,
        trigger="cron", hour=15, minute=30, day_of_week="mon-fri",
        id="daily_backtest", name="每日自动回测",
    )

    scheduler.start()
    logger.info("调度器已启动 — 工作日15:30自动回测")
    return scheduler


def run_ai_learning():
    """AI自学习任务"""
    logger.info("=== 开始AI自学习 ===")
    try:
        from data.fetcher import db
        from core.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        results = db.get_latest_results()
        if not results.empty:
            insight = analyzer.auto_learn(results.to_dict("records"))
            logger.info("AI自学习完成")
    except Exception as e:
        logger.error(f"AI自学习失败: {e}")


def run_once():
    """手动执行一次全部回测"""
    return run_all_backtests()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    import argparse
    parser = argparse.ArgumentParser(description="量化策略自动回测")
    parser.add_argument("--once", action="store_true", help="立即执行一次回测")
    parser.add_argument("--daemon", action="store_true", help="启动守护进程")
    args = parser.parse_args()

    if args.once:
        results = run_once()
        if results:
            print("\n=== 回测结果汇总 ===")
            for r in results:
                print(f"  {r['strategy']}: 年化={r['annual_return']:.2%} 夏普={r['sharpe']:.2f} 回撤={r['max_dd']:.2%} ({r['time']})")
    elif args.daemon:
        scheduler = setup_scheduler()
        try:
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            scheduler.shutdown()
    else:
        print("用法:")
        print("  python -m core.scheduler --once    # 立即执行一次回测")
        print("  python -m core.scheduler --daemon  # 启动定时守护进程")
