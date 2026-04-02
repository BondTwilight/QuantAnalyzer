"""
自动化调度模块 — 每日自动回测 + AI分析
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


def run_all_backtests():
    """运行所有策略回测"""
    logger.info(f"=== 开始自动回测 {datetime.now()} ===")

    try:
        from data.fetcher import DataFetcher, db
        from core.engine import BacktestEngine
        from strategies.ma_cross import MACrossStrategy
        from strategies.rsi_strategy import RSIStrategy
        from strategies.momentum import MomentumStrategy
        from strategies.multi_factor import MultiFactorStrategy
        from strategies.sector_rotation import SectorRotationStrategy
        from strategies.bollinger import BollingerBandStrategy
        from config import STOCK_POOL, BENCHMARK, DEFAULT_PERIOD

        fetcher = DataFetcher()
        engine = BacktestEngine()

        # 策略列表
        strategies = [
            ("双均线交叉", MACrossStrategy, {}),
            ("RSI均值回归", RSIStrategy, {}),
            ("动量策略", MomentumStrategy, {}),
            ("多因子选股", MultiFactorStrategy, {}),
            ("行业轮动", SectorRotationStrategy, {}),
            ("布林带策略", BollingerBandStrategy, {}),
        ]

        # 选几个代表性股票进行回测
        test_stocks = STOCK_POOL[:5]  # 前5只股票

        for strategy_name, strategy_class, params in strategies:
            for stock_code in test_stocks:
                try:
                    logger.info(f"回测: {strategy_name} @ {stock_code}")

                    # 获取数据
                    data = fetcher.get_stock_daily(stock_code)
                    if data.empty:
                        logger.warning(f"  跳过 {stock_code}: 无数据")
                        continue

                    # 获取基准
                    benchmark = fetcher.get_index_daily("000300")

                    # 运行回测
                    result = engine.run(strategy_class, data, benchmark, **params)
                    result["strategy_name"] = f"{strategy_name}_{stock_code.split('.')[0]}"
                    result["stock_code"] = stock_code

                    # 保存结果
                    db.save_backtest_result(result)
                    if "daily_values" in result and not result["daily_values"].empty:
                        db.save_daily_values(result["strategy_name"], result["daily_values"])
                    if "trades" in result:
                        db.save_trades(result["strategy_name"], result["trades"])

                    logger.info(f"  完成: 年化={result.get('annual_return', 0):.2%} 夏普={result.get('sharpe_ratio', 0):.2f}")

                except Exception as e:
                    logger.error(f"  失败: {e}")
                    continue

        logger.info("=== 自动回测完成 ===")

        # 尝试运行AI分析
        try:
            from core.ai_analyzer import AIAnalyzer
            analyzer = AIAnalyzer()
            latest = db.get_latest_results()
            if not latest.empty:
                comparison = analyzer.compare_strategies(latest.to_dict("records")[:5])
                logger.info("AI对比分析完成")
        except Exception as e:
            logger.warning(f"AI分析跳过: {e}")

    except ImportError as e:
        logger.error(f"导入失败: {e}，请确保已安装所有依赖")


def setup_scheduler():
    """设置定时调度"""
    scheduler = BackgroundScheduler()

    # 工作日 15:30 自动回测 (A股收盘后)
    scheduler.add_job(
        run_all_backtests,
        trigger="cron",
        hour=15,
        minute=30,
        day_of_week="mon-fri",
        id="daily_backtest",
        name="每日自动回测",
    )

    # 每周日晚运行AI自学习
    scheduler.add_job(
        run_ai_learning,
        trigger="cron",
        hour=20,
        minute=0,
        day_of_week="sun",
        id="weekly_ai_learning",
        name="每周AI自学习",
    )

    scheduler.start()
    logger.info("调度器已启动 — 工作日15:30自动回测, 每周日AI自学习")
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
    """手动执行一次全部回测（立即运行）"""
    run_all_backtests()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    import argparse
    parser = argparse.ArgumentParser(description="量化策略自动回测")
    parser.add_argument("--once", action="store_true", help="立即执行一次回测")
    parser.add_argument("--daemon", action="store_true", help="启动守护进程（定时回测）")
    args = parser.parse_args()

    if args.once:
        run_once()
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
