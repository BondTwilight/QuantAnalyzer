"""
策略PK竞技场 - 多策略粘贴 + 一键回测对比 + AI协同分析
这是网站的核心功能：确保粘贴/抓取的策略能直接回测PK
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ═══════════════════════════════════════════
# Backtrader 动态策略执行器
# ═══════════════════════════════════════════

def safe_backtest_strategy(
    code: str,
    stock: str,
    start_date: str,
    end_date: str,
    initial_cash: float = 100000.0,
) -> Tuple[bool, Dict, Optional[pd.DataFrame]]:
    """
    安全地回测策略代码
    返回: (是否成功, 结果字典, 收益曲线DataFrame)
    """
    import backtrader as bt
    import io
    import sys as _sys

    # 准备结果容器
    results = {
        "total_return": 0.0,
        "annual_return": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "total_trades": 0,
        "final_value": initial_cash,
        "error": None,
        "strategy_name": "Unknown",
        "returns_series": None,
        "equity_curve": None,
    }

    # 捕获输出
    old_stderr = _sys.stderr
    old_stdout = _sys.stdout
    sys_err = io.StringIO()
    sys_out = io.StringIO()

    try:
        _sys.stderr = sys_err
        _sys.stdout = sys_out

        # ═══ 编译策略代码 ═══
        compiled = compile(code, "<strategy>", "exec")
        namespace = {"bt": bt, "__name__": "__main__"}
        exec(compiled, namespace)

        # 找策略类
        StrategyClass = None
        for obj in namespace.values():
            if isinstance(obj, type) and issubclass(obj, bt.Strategy) and obj != bt.Strategy:
                StrategyClass = obj
                results["strategy_name"] = obj.__name__
                break

        if StrategyClass is None:
            results["error"] = "未找到继承 bt.Strategy 的策略类"
            return False, results, None

        # ═══ 加载数据 ═══
        cerebro = bt.Cerebro(stdstats=False)
        cerebro.broker.setcash(initial_cash)

        # 尝试从BaoStock获取数据
        try:
            from data.fetcher import DataFetcher
            fetcher = DataFetcher()
            data_df = fetcher.get_stock_daily(stock, start_date, end_date)
            if data_df is None or data_df.empty:
                results["error"] = f"无法获取 {stock} 的数据"
                return False, results, None
            
            # 转换为Backtrader数据格式
            data = bt.feeds.PandasData(
                dataname=data_df,
                datetime=None,
                open="open", high="high", low="low", close="close", volume="volume",
                openinterest=-1,
            )
            cerebro.adddata(data)
            if data is None:
                results["error"] = f"无法获取 {stock} 的数据"
                return False, results, None
            cerebro.adddata(data)
        except Exception as e:
            results["error"] = f"数据加载失败: {str(e)}"
            return False, results, None

        # ═══ 添加分析器 ═══
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.03, annualize=True)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")

        # ═══ 执行回测 ═══
        cerebro.addstrategy(StrategyClass)

        # 预处理数据
        for data in cerebro.datas:
            data.preload()

        # 运行
        strategies = cerebro.run()
        strategy = strategies[0]

        # ═══ 提取结果 ═══
        final_value = cerebro.broker.getvalue()
        results["final_value"] = final_value
        results["total_return"] = (final_value - initial_cash) / initial_cash * 100

        # 年化收益
        try:
            returns_analyzer = strategy.analyzers.returns.get_analysis()
            annual_return = returns_analyzer.get("rnorm100", 0)
            results["annual_return"] = annual_return
        except Exception:
            pass

        # 夏普比率
        try:
            sharpe_analyzer = strategy.analyzers.sharpe.get_analysis()
            sharpe = sharpe_analyzer.get("sharperatio", None)
            if sharpe and not np.isnan(float(sharpe)):
                results["sharpe"] = float(sharpe)
        except Exception:
            pass

        # 最大回撤
        try:
            dd_analyzer = strategy.analyzers.drawdown.get_analysis()
            max_dd = dd_analyzer.get("max", {}).get("drawdown", 0)
            results["max_drawdown"] = max_dd
        except Exception:
            pass

        # 交易统计
        try:
            trade_analyzer = strategy.analyzers.trades.get_analysis()
            total = trade_analyzer.get("total", {})
            results["total_trades"] = total.get("total", 0)

            won = trade_analyzer.get("won", {})
            lost = trade_analyzer.get("lost", {})
            win_count = won.get("total", 0)
            lose_count = lost.get("total", 0)
            total_closed = win_count + lose_count
            if total_closed > 0:
                results["win_rate"] = win_count / total_closed * 100
        except Exception:
            pass

        # 收益曲线
        try:
            time_return = strategy.analyzers.time_return.get_analysis()
            dates = list(time_return.keys())
            returns = list(time_return.values())
            equity = [initial_cash]
            for r in returns:
                equity.append(equity[-1] * (1 + r))
            equity = equity[1:]

            returns_df = pd.DataFrame({
                "date": dates,
                "return": returns,
                "equity": equity
            })
            results["returns_series"] = returns_df
            results["equity_curve"] = returns_df
        except Exception:
            pass

        _sys.stderr = old_stderr
        _sys.stdout = old_stdout

        return True, results, results.get("returns_series")

    except SyntaxError as e:
        _sys.stderr = old_stderr
        _sys.stdout = old_stdout
        results["error"] = f"语法错误: {e}"
        return False, results, None

    except Exception as e:
        _sys.stderr = old_stderr
        _sys.stdout = old_stdout
        results["error"] = f"运行错误: {str(e)}"
        return False, results, None


# ═══════════════════════════════════════════
# 多策略并行回测
# ═══════════════════════════════════════════

def run_strategy_pk(
    strategies: List[Dict],  # [{"name": "", "code": "", "framework": ""}]
    stock: str,
    start_date: str,
    end_date: str,
    initial_cash: float = 100000.0,
) -> pd.DataFrame:
    """
    并行回测多个策略，返回对比表格
    strategies: 策略列表
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = []

    def run_single(idx: int, strat: Dict):
        name = strat.get("name", f"策略{idx+1}")
        code = strat.get("code", "")
        framework = strat.get("framework", "backtrader")

        if not code:
            return {
                "idx": idx,
                "name": name,
                "success": False,
                "error": "无策略代码",
                "total_return": 0,
                "annual_return": 0,
                "sharpe": 0,
                "max_drawdown": 0,
                "win_rate": 0,
                "total_trades": 0,
                "final_value": initial_cash,
                "equity_curve": None,
            }

        success, res, _ = safe_backtest_strategy(
            code, stock, start_date, end_date, initial_cash
        )

        return {
            "idx": idx,
            "name": name,
            "success": success,
            "error": res.get("error", ""),
            "total_return": res.get("total_return", 0),
            "annual_return": res.get("annual_return", 0),
            "sharpe": res.get("sharpe", 0),
            "max_drawdown": res.get("max_drawdown", 0),
            "win_rate": res.get("win_rate", 0),
            "total_trades": res.get("total_trades", 0),
            "final_value": res.get("final_value", initial_cash),
            "equity_curve": res.get("equity_curve"),
            "returns_series": res.get("returns_series"),
            "strategy_name": res.get("strategy_name", name),
        }

    # 并行执行 (限制同时2个，避免资源竞争)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(run_single, i, s): i
            for i, s in enumerate(strategies)
        }
        for future in as_completed(futures):
            results.append(future.result())

    # 按idx排序
    results.sort(key=lambda x: x["idx"])

    # 生成对比DataFrame
    df = pd.DataFrame([{
        "策略名称": r["name"],
        "状态": "✅" if r["success"] else "❌",
        "累计收益%": round(r["total_return"], 2),
        "年化收益%": round(r["annual_return"], 2),
        "夏普比率": round(r["sharpe"], 3) if r["sharpe"] else 0,
        "最大回撤%": round(r["max_drawdown"], 2),
        "胜率%": round(r["win_rate"], 1),
        "交易次数": r["total_trades"],
        "最终资金": round(r["final_value"], 2),
        "错误": r.get("error", "")[:50] if not r["success"] else "",
    } for r in results])

    return df, [r for r in results if r["success"]]


# ═══════════════════════════════════════════
# AI 协同分析
# ═══════════════════════════════════════════

def ai_collaborative_analysis(
    pk_results: List[Dict],
    stock: str,
    start_date: str,
    end_date: str,
) -> str:
    """多模型协同分析PK结果"""
    from core.ai_analyzer import MultiModelAnalyzer
    import json

    # 构建分析提示
    strategies_summary = []
    for r in pk_results:
        if r["success"]:
            strategies_summary.append(f"""
- {r['name']} (代码策略名: {r.get('strategy_name', '')}):
  累计收益: {r['total_return']:.2f}% | 年化: {r['annual_return']:.2f}%
  夏普比率: {r['sharpe']:.3f} | 最大回撤: {r['max_drawdown']:.2f}%
  胜率: {r['win_rate']:.1f}% | 交易次数: {r['total_trades']}""")

    prompt = f"""你是量化投资专家，对以下{stock}在{start_date}至{end_date}的多策略回测结果进行协同分析：

策略回测结果：
{chr(10).join(strategies_summary)}

请从以下角度分析：

1. **综合评估**：哪个策略整体表现最好？给出明确排名
2. **收益维度**：累计收益和年化收益最高的策略是哪个？是否存在过拟合风险？
3. **风险维度**：最大回撤最小的策略是哪个？夏普比率最高的策略？
4. **效率维度**：在同等风险下，哪个策略性价比最高？
5. **交易特征**：胜率和交易次数的权衡，哪个策略更实用？
6. **实战建议**：对于当前A股市场，哪个策略最适合实盘？为什么？
7. **改进方向**：每个策略有哪些可以改进的地方？

请给出明确、可操作的结论，不要模棱两可。最后给出「推荐策略」和「推荐理由」。"""

    try:
        multi = MultiModelAnalyzer()
        result = multi.analyze(prompt)
        return result.get("summary", result.get("analysis", "分析生成失败"))
    except Exception as e:
        return f"AI分析暂时不可用 ({str(e)})。请在「⚙️ 系统设置」中配置 API Key。"


# ═══════════════════════════════════════════
# Streamlit UI - 策略PK竞技场页面
# ═══════════════════════════════════════════

def render_strategy_pk_arena():
    """策略PK竞技场 - 极简直观版"""
    import streamlit as st
    import re as regex

    st.markdown("""
    <style>
    .pk-box {
        background: #0d1117;
        border: 2px dashed #1e3a5f;
        border-radius: 16px;
        padding: 16px;
        min-height: 280px;
        transition: border-color 0.2s;
    }
    .pk-box:focus-within { border-color: #3b82f6; }
    .pk-label {
        font-size: 0.72rem;
        color: #4a5568;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .vs-badge {
        display: flex; align-items: center; justify-content: center;
        font-size: 2rem; font-weight: 900;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        width: 50px; height: 50px;
    }
    .result-row {
        display: flex; align-items: center; gap: 16px;
        background: linear-gradient(135deg, #131c2e, #0a1120);
        border: 1px solid #1e2d40;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 8px;
        transition: all 0.2s;
    }
    .result-row:hover { border-color: #3b82f6; }
    .result-rank {
        width: 32px; height: 32px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 1rem;
        flex-shrink: 0;
    }
    .rank-1 { background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; }
    .rank-2 { background: #1e3a5f; color: #60a5fa; }
    .rank-3 { background: #1e3a5f; color: #94a3b8; }
    .rank-other { background: #1e2d40; color: #6b7a90; }
    .result-name { font-weight: 700; color: #e2e8f0; flex: 1; }
    .result-metric { text-align: center; min-width: 100px; }
    .result-metric-label { font-size: 0.7rem; color: #4a5568; }
    .result-metric-value { font-size: 1.1rem; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">⚔️ 策略PK竞技场</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a2235,#0f1624);border:1px solid #1e2d40;
    border-radius:12px;padding:16px 20px;margin-bottom:20px;color:#94a3b8;font-size:0.88rem;">
        📋 <b style="color:#e2e8f0;">最简单的方式：</b>在下面粘贴两个策略的代码 → 点击「⚡ 一键PK」→ 立即看到对比结果！
        支持 <b style="color:#60a5fa;">Backtrader</b> / 聚宽 / AKShare 格式。
    </div>
    """, unsafe_allow_html=True)

    # ── 示例策略（点击自动填充）──
    EXAMPLE_A = '''import backtrader as bt

class StrategyA(bt.Strategy):
    """双均线交叉（趋势策略）"""
    params = (("fast", 5), ("slow", 20),)

    def __init__(self):
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.fast)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.slow)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        if self.crossover > 0:
            self.buy()
        elif self.crossover < 0:
            self.sell()
'''

    EXAMPLE_B = '''import backtrader as bt

class StrategyB(bt.Strategy):
    """RSI超买超卖（震荡策略）"""
    params = (("rsi_period", 14), ("rsi_buy", 30), ("rsi_sell", 70))

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

    def next(self):
        if self.rsi < self.params.rsi_buy:
            self.buy()
        elif self.rsi > self.params.rsi_sell:
            self.sell()
'''

    # ── 粘贴框：左右并排 ──
    col_left, col_vs, col_right = st.columns([5, 1, 5])

    with col_left:
        st.markdown('<div class="pk-label">📋 策略 A 代码</div>', unsafe_allow_html=True)
        code_a = st.text_area(
            "策略A",
            value=st.session_state.get("pk_code_a", ""),
            placeholder="import backtrader as bt\n\nclass MyStrategy(bt.Strategy):\n    def __init__(self):\n        ...\n    def next(self):\n        ...",
            height=280,
            key="pk_code_a",
            label_visibility="collapsed"
        )
        name_a = st.text_input("策略A名称", value=st.session_state.get("pk_name_a", "双均线策略"),
            key="pk_name_a", placeholder="给策略起个名字...")

    with col_vs:
        st.markdown("")

    with col_right:
        st.markdown('<div class="pk-label">📋 策略 B 代码</div>', unsafe_allow_html=True)
        code_b = st.text_area(
            "策略B",
            value=st.session_state.get("pk_code_b", ""),
            placeholder="import backtrader as bt\n\nclass MyStrategy(bt.Strategy):\n    def __init__(self):\n        ...",
            height=280,
            key="pk_code_b",
            label_visibility="collapsed"
        )
        name_b = st.text_input("策略B名称", value=st.session_state.get("pk_name_b", "RSI策略"),
            key="pk_name_b", placeholder="给策略起个名字...")

    # ── 示例按钮 + 参数 + PK按钮 ──
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])

    with btn_col1:
        if st.button("📋 加载双均线示例A", use_container_width=True):
            st.session_state["pk_code_a"] = EXAMPLE_A
            st.session_state["pk_name_a"] = "双均线策略"
            st.rerun()

    with btn_col2:
        if st.button("📋 加载RSI示例B", use_container_width=True):
            st.session_state["pk_code_b"] = EXAMPLE_B
            st.session_state["pk_name_b"] = "RSI策略"
            st.rerun()

    with btn_col3:
        # 回测参数（并排）
        p1, p2, p3 = st.columns(3)
        with p1:
            stock = st.selectbox("标的", [
                "000001.SZ", "000002.SZ", "600000.SH", "600519.SH",
                "000858.SZ", "601318.SH", "000300.SH"
            ], key="pk_stock",
            format_func=lambda x: {"000001.SZ":"平安银行","000002.SZ":"万科A","600000.SH":"浦发银行","600519.SH":"贵州茅台","000858.SZ":"五粮液","601318.SH":"中国平安","000300.SH":"沪深300"}.get(x, x))
        with p2:
            start = st.date_input("开始", value=datetime(2023, 1, 1), key="pk_start")
        with p3:
            end = st.date_input("结束", value=datetime(2024, 12, 31), key="pk_end")

    st.markdown("")

    if st.button("⚡ **一键PK回测**", type="primary", use_container_width=True):
        valid = [(name_a.strip(), code_a.strip()), (name_b.strip(), code_b.strip())]
        valid = [(n, c) for n, c in valid if c]

        if len(valid) < 2:
            st.warning("⚠️ 请至少粘贴 2 个策略代码")
        else:
            start_str = start.strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")

            with st.spinner(f"⚡ 正在回测 {len(valid)} 个策略..."):
                results = []
                for name, code in valid:
                    success, res, _ = safe_backtest_strategy(
                        code, stock, start_str, end_str, 100000.0
                    )
                    if success:
                        results.append({"name": name, **res})
                    else:
                        results.append({"name": name, "total_return": 0, "sharpe": 0,
                                        "max_drawdown": 0, "win_rate": 0,
                                        "total_trades": 0, "error": res.get("error", "未知错误")})

            st.session_state["pk_results"] = results

    # ── 显示PK结果 ──
    if st.session_state.get("pk_results"):
        results = st.session_state["pk_results"]

        # 找出冠军
        valid_results = [r for r in results if "error" not in r or not r.get("error")]
        if valid_results:
            best = max(valid_results, key=lambda x: x.get("total_return", 0))

            st.markdown("---")
            st.markdown("### 🏆 PK结果")

            # 冠军标识
            for i, r in enumerate(sorted(results, key=lambda x: -(x.get("total_return", -999)))):
                rank = i + 1
                rank_cls = f"rank-{min(rank, 3)}"
                ret = r.get("total_return", 0)
                ret_color = "#10b981" if ret >= 0 else "#ef4444"
                dd = r.get("max_drawdown", 0)

                st.markdown(f"""
                <div class="result-row">
                    <div class="result-rank {rank_cls}">{'🥇' if rank==1 else '🥈' if rank==2 else '🥉' if rank==3 else rank}</div>
                    <div class="result-name">{'✅ ' if 'error' not in r else '❌ '}{r.get('name','')}
                        {'<br><span style="color:#ef4444;font-size:0.78rem;">' + r.get('error','') + '</span>' if r.get('error') else ''}
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">累计收益</div>
                        <div class="result-metric-value" style="color:{ret_color};">{ret:+.2f}%</div>
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">夏普比率</div>
                        <div class="result-metric-value" style="color:#60a5fa;">{r.get('sharpe',0):.2f}</div>
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">最大回撤</div>
                        <div class="result-metric-value" style="color:#f87171;">-{dd:.1f}%</div>
                    </div>
                    <div class="result-metric">
                        <div class="result-metric-label">胜率</div>
                        <div class="result-metric-value" style="color:#a78bfa;">{r.get('win_rate',0):.1f}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 冠军总结
            if best.get("total_return", 0) != 0:
                ret = best.get("total_return", 0)
                color = "#10b981" if ret >= 0 else "#ef4444"
                st.success(
                    f"🏆 **收益冠军: {best.get('name','')}** — "
                    f"累计 {ret:+.2f}% | "
                    f"夏普 {best.get('sharpe',0):.2f} | "
                    f"回撤 -{best.get('max_drawdown',0):.1f}% | "
                    f"交易 {best.get('total_trades',0)}次"
                )

        # AI分析
        if valid_results:
            st.markdown("---")
            st.markdown("### 🤖 AI 分析（可跳过后自行判断）")
            try:
                from core.ai_analyzer import MultiModelAnalyzer
                multi = MultiModelAnalyzer()
                if multi.available_models:
                    prompt = "请分析以下两个量化策略回测结果的优劣：\n"
                    for r in results:
                        if "error" not in r:
                            prompt += f"\n策略: {r['name']}\n"
                            prompt += f"  累计收益: {r.get('total_return',0):.2f}%\n"
                            prompt += f"  夏普比率: {r.get('sharpe',0):.2f}\n"
                            prompt += f"  最大回撤: {r.get('max_drawdown',0):.2f}%\n"
                            prompt += f"  胜率: {r.get('win_rate',0):.1f}%\n"
                    with st.spinner("🤖 AI分析中..."):
                        resp = multi.analyze(prompt)
                    st.markdown(resp)
                else:
                    st.info("💡 在「⚙️ 系统设置」配置 API Key 后开启 AI 分析")
            except Exception:
                st.info("💡 配置 AI Key 后可获得策略优劣分析")

    # ── 抓取策略库入口 ──
    st.markdown("---")
    st.markdown("### 📡 或者：从策略库选择策略来PK")
    st.info("在「📚 策略库」页面选择一个策略，点击「加入PK」即可。内置20+策略直接可用。")

    # ── Tab2: 抓取UI（简洁版）──
    st.markdown("---")
    with st.expander("📡 查看/抓取最新量化策略和因子"):
        try:
            from core.strategy_crawler import render_crawler_ui
            render_crawler_ui()
        except Exception as e:
            st.error(f"策略爬虫加载失败: {e}")
