"""
🧠 QuantAnalyzer v4.0 — AI量化策略自学习系统
核心功能: 自动搜索策略 → AI学习优化 → 生成买卖信号 → 跟踪收益 → 持续进化
"""
import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core.quant_brain import QuantBrain, DataProvider
from core.performance_optimizer import (
    optimize_quant_brain, 
    cached, 
    SmartCache,
    PerformanceMonitor,
    OptimizedDataProvider
)
from core.async_task_manager import AsyncTasks, task_manager
from core.database_optimizer import get_database_optimizer

# ═══════════════════════════════════════════════
# 全局配置
# ═══════════════════════════════════════════════
st.set_page_config(
    page_title="QuantBrain AI量化",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义CSS
st.markdown("""<style>
/* 全局暗色主题 */
.stApp { background: #0a0e1a !important; }
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }

/* 侧边栏 */
.css-1d391kg { background: #0f1629; }
section[data-testid="stSidebar"] { background: #0f1629; border-right: 1px solid #1e293b; }

/* 卡片 */
.metric-card {
    background: linear-gradient(135deg, #1a1f35, #141929);
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 12px;
}
.metric-value { font-size: 28px; font-weight: 700; color: #f8fafc; }
.metric-label { font-size: 13px; color: #64748b; margin-bottom: 4px; }
.metric-change { font-size: 13px; margin-top: 4px; }
.profit-up { color: #10b981; }
.profit-down { color: #ef4444; }

/* 信号卡片 */
.signal-card {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 8px;
    transition: all 0.2s;
}
.signal-card:hover { border-color: #3b82f6; }
.signal-buy { border-left: 4px solid #10b981; }
.signal-sell { border-left: 4px solid #ef4444; }

/* 按钮 */
.stButton > button { border-radius: 10px; font-weight: 600; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6, #6366f1);
    border: none; color: white;
}

/* 标题 */
.page-title {
    font-size: 24px; font-weight: 700; color: #f8fafc;
    margin-bottom: 4px;
}
.page-subtitle {
    font-size: 14px; color: #64748b;
}

/* 标签 */
.tag { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; margin-right: 4px; }
.tag-buy { background: #10b98122; color: #10b981; }
.tag-sell { background: #ef444422; color: #ef4444; }
.tag-strategy { background: #3b82f622; color: #3b82f6; }
.tag-ai { background: #a855f722; color: #a855f7; }

/* 进度条 */
.stProgress > div > div > div { background: linear-gradient(90deg, #3b82f6, #a855f7); }

/* 表格 */
.dataframe { background: #111827; border-radius: 8px; }
.dataframe th { background: #1a1f35; color: #94a3b8; }
.dataframe td { color: #e2e8f0; border-bottom: 1px solid #1e293b; }

/* 代码块 */
.stCodeBlock { background: #0f1629 !important; border-radius: 8px; }

/* Tab */
.stTabs [data-baseweb="tab-list"] { gap: 2px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 16px; }
</style>""", unsafe_allow_html=True)

# 性能监控初始化
performance_monitor = PerformanceMonitor()

# 初始化 - 使用优化版的QuantBrain
@st.cache_resource
def get_brain():
    OptimizedQuantBrain = optimize_quant_brain()
    return OptimizedQuantBrain()

brain = get_brain()

# 优化数据提供器
optimized_data = OptimizedDataProvider()

# 全局缓存
cache_system = SmartCache("app")


# ═══════════════════════════════════════════════
# 侧边栏导航
# ═══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🧠 QuantBrain")
    st.caption("AI量化策略自进化系统 v5.0")

    page = st.radio("导航", [
        "📊 信号仪表盘",
        "📡 每日扫描",
        "💼 持仓跟踪",
        "📈 K线分析",
        "🧬 策略进化中心",
        "🔄 策略回测",
        "⚙️ 设置",
    ], label_visibility="collapsed")

    st.markdown("---")
    st.caption(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption("数据源: AkShare + BaoStock (免费)")

    # 快捷操作
    from core.button_fixer import ButtonResponseFixer
    
    def quick_scan_action():
        st.session_state["quick_scan"] = True
        return True
    
    if ButtonResponseFixer.create_action_button(
        "🚀 一键扫描自选股",
        quick_scan_action,
        success_msg="已触发一键扫描",
        error_msg="触发扫描失败",
        use_container_width=True,
        type="primary"
    ):
        pass


# ═══════════════════════════════════════════════
# 页面1: 信号仪表盘
# ═══════════════════════════════════════════════
if page == "📊 信号仪表盘":
    st.markdown('<div class="page-title">📊 信号仪表盘</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">AI策略实时信号 + 持仓收益 + 学习进度</div>', unsafe_allow_html=True)

    # 获取数据
    dashboard = brain.get_dashboard_data()
    pf = dashboard["portfolio"]

    # 核心指标卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        profit_class = "profit-up" if pf["total_profit_pct"] >= 0 else "profit-down"
        profit_sign = "+" if pf["total_profit_pct"] >= 0 else ""
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">总资产</div>
            <div class="metric-value">¥{pf['total_market_value']:,.0f}</div>
            <div class="metric-change {profit_class}">{profit_sign}{pf['total_profit_pct']:.2f}%</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">持仓数</div>
            <div class="metric-value">{pf['total_positions']}</div>
            <div class="metric-change" style="color:#94a3b8">可用 ¥{pf['available_cash']:,.0f}</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        total_buy = sum(1 for s in dashboard["recent_signals"] if s["direction"] == "BUY")
        total_sell = sum(1 for s in dashboard["recent_signals"] if s["direction"] == "SELL")
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">今日信号</div>
            <div class="metric-value">{len(dashboard['recent_signals'])}</div>
            <div class="metric-change"><span style="color:#10b981">买{total_buy}</span> / <span style="color:#ef4444">卖{total_sell}</span></div>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">已学策略</div>
            <div class="metric-value">{dashboard['strategy_count']}</div>
            <div class="metric-change" style="color:#94a3b8">学习记录 {dashboard['learning_count']}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # 两列布局: 持仓 + 信号
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("### 💼 当前持仓")
        positions = pf["positions"]
        if positions:
            for pos in positions:
                pct_class = "profit-up" if pos["profit_pct"] >= 0 else "profit-down"
                pct_sign = "+" if pos["profit_pct"] >= 0 else ""
                st.markdown(f"""
                <div class="signal-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div style="font-size:16px;font-weight:600;color:#f8fafc;">
                                {pos['stock_name']} <span style="color:#64748b;font-size:12px;">{pos['stock_code']}</span>
                            </div>
                            <div style="font-size:12px;color:#64748b;margin-top:4px;">
                                {pos['shares']}股 · 成本 ¥{pos['avg_cost']:.2f} · 策略: {pos['strategy_name']}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:18px;font-weight:700;" class="{pct_class}">
                                {pct_sign}{pos['profit_pct']}%
                            </div>
                            <div style="font-size:12px;color:#94a3b8;">
                                ¥{pos['current_price']:.2f}
                            </div>
                        </div>
                    </div>
                    <div style="display:flex;gap:8px;margin-top:8px;">
                        <span style="color:#64748b;font-size:11px;">止损: ¥{pos['stop_loss']:.2f}</span>
                        <span style="color:#64748b;font-size:11px;">目标: ¥{pos['target_price']:.2f}</span>
                    </div>
                    <div style="margin-top:8px;">
                        <button onclick="this.closest('form').querySelector('input').value='SELL_{pos['stock_code']}'"
                            style="background:#ef4444;color:white;border:none;padding:4px 12px;border-radius:6px;font-size:12px;cursor:pointer;">
                            卖出平仓
                        </button>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("暂无持仓。去「每日扫描」发现交易信号吧！")

    with col_right:
        st.markdown("### 📡 最新信号")
        recent = dashboard["recent_signals"]
        if recent:
            for sig in reversed(recent[-10:]):
                dir_class = "signal-buy" if sig["direction"] == "BUY" else "signal-sell"
                dir_tag = "tag-buy" if sig["direction"] == "BUY" else "tag-sell"
                dir_text = "买入" if sig["direction"] == "BUY" else "卖出"
                st.markdown(f"""
                <div class="signal-card {dir_class}">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <span class="tag {dir_tag}">{dir_text}</span>
                            <span class="tag tag-strategy">{sig['strategy_name']}</span>
                            <span style="color:#f59e0b;font-size:12px;">置信度 {sig['confidence']}%</span>
                        </div>
                        <div style="font-size:14px;font-weight:600;color:#f8fafc;">
                            {sig['stock_name'] or sig['stock_code']}
                        </div>
                    </div>
                    <div style="color:#94a3b8;font-size:12px;margin-top:6px;">{sig['reason'][:100]}</div>
                    <div style="color:#64748b;font-size:11px;margin-top:4px;">
                        {sig['created_at']} · ¥{sig['price']:.2f}
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("暂无信号。点击「每日扫描」开始！")

    st.markdown("---")

    # 历史交易
    closed = dashboard["closed_trades"]
    if closed:
        st.markdown("### 📜 历史交易")
        df_closed = pd.DataFrame(closed)
        df_closed["收益"] = df_closed["profit_pct"].apply(lambda x: f"{'+'if x>=0 else ''}{x:.2f}%")
        st.dataframe(df_closed[["stock_code", "stock_name", "direction", "executed_price",
                                 "closed_price", "收益", "created_at", "closed_at"]],
                     use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════
# 页面2: 每日扫描（增强版）
# ═══════════════════════════════════════════════
elif page == "📡 每日扫描":
    st.markdown('<div class="page-title">📡 每日扫描</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">AI扫描自选股，自动生成买卖信号</div>', unsafe_allow_html=True)

    scan_tab1, scan_tab2, scan_tab3, scan_tab4 = st.tabs(["🔍 智能扫描", "📊 市场概览", "⚡ 批量操作", "🌏 全A股扫描"])

    with scan_tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            watchlist = brain.get_watchlist_stocks()
            stock_input = st.text_area(
                "自选股列表（一行一个股票代码）",
                value="\n".join(watchlist),
                height=200,
            )
        with col2:
            st.markdown("### 扫描设置")
            scan_days = st.slider("回看天数", 30, 365, 120)
            min_confidence = st.slider("最低置信度", 40, 90, 60)

            st.markdown("---")
            st.markdown("### 🔥 快捷添加")
            preset_lists = {
                "蓝筹白马": ["600519", "000858", "600036", "601318", "000333",
                             "601888", "600276", "000568", "601166", "600887"],
                "科技龙头": ["002415", "300750", "002230", "603501", "688981",
                             "300059", "002475", "300782", "002371", "603019"],
                "新能源": ["300014", "002594", "601012", "600438", "002129",
                           "300274", "600905", "002074", "300750", "688599"],
                "医药消费": ["600276", "000538", "300015", "002007", "300347",
                            "000661", "603259", "002821", "300760", "688185"],
            }
            preset_name = st.selectbox("热门组合", list(preset_lists.keys()))
            
            def add_preset_action():
                current = [s.strip() for s in stock_input.strip().split("\n") if s.strip()]
                combined = list(set(current + preset_lists[preset_name]))
                return True
            
            if ButtonResponseFixer.create_action_button(
                f"添加{preset_name}组合",
                add_preset_action,
                success_msg=f"已添加{preset_name}组合",
                error_msg="添加组合失败",
                use_container_width=True
            ):
                pass
                stock_input = "\n".join(combined)
                st.rerun()

            st.markdown("---")
            st.markdown("### 策略说明")
            st.caption("• **多信号共振**: RSI+MACD+均线三重确认\n"
                      "• **突破策略**: N日新高/低突破\n"
                      "• **布林带回归**: 触及上下轨反弹\n"
                      "• **放量突破**: 量价齐升突破均线\n"
                      "• **动量反转**: 超跌反弹+放量\n"
                      "• **趋势跟踪**: 多头排列+MACD正向")

        # 检查是否有正在进行的扫描任务
        if "daily_scan_task" in st.session_state:
            task_id = st.session_state.daily_scan_task
            task_status = task_manager.get_task_status(task_id)
            
            if task_status:
                if task_status["status"] == "running":
                    st.info(f"🔍 正在扫描股票... 进度: {task_status.get('progress', 0):.0f}%")
                    st.progress(task_status.get("progress", 0) / 100.0)
                    st.caption(task_status.get("message", ""))
                    
                    # 自动刷新
                    time.sleep(1)
                    st.rerun()
                    
                elif task_status["status"] == "completed":
                    st.success("✅ 扫描完成！")
                    
                    # 显示结果
                    result = task_status.get("result", {})
                    signals_data = result.get("signals", [])
                    
                    # 转换为TradeSignal对象
                    from core.quant_brain import TradeSignal
                    signals = []
                    for sig_data in signals_data:
                        sig = TradeSignal()
                        for key, value in sig_data.items():
                            if hasattr(sig, key):
                                setattr(sig, key, value)
                        signals.append(sig)
                    
                    # 过滤
                    signals = [s for s in signals if s.confidence >= min_confidence]
                    
                    if signals:
                        # 显示结果
                        pass  # 继续下面的显示逻辑
                    else:
                        st.info("未发现符合条件的信号")
                    
                    # 清理任务状态
                    del st.session_state.daily_scan_task
                    
                elif task_status["status"] == "failed":
                    st.error(f"❌ 扫描失败: {task_status.get('error', '未知错误')}")
                    del st.session_state.daily_scan_task

        def start_scan_action():
            return True
        
        scan_clicked = ButtonResponseFixer.create_action_button(
            "🚀 开始扫描",
            start_scan_action,
            success_msg="开始扫描",
            error_msg="启动扫描失败",
            type="primary",
            use_container_width=True
        ) or st.session_state.get("quick_scan")
        if "quick_scan" in st.session_state:
            st.session_state.pop("quick_scan")

        if scan_clicked:
            stocks = [s.strip() for s in stock_input.strip().split("\n") if s.strip()]
            if not stocks:
                st.warning("请输入股票代码")
            else:
                brain.save_watchlist(stocks)
                
                # 提交异步扫描任务
                result = AsyncTasks.daily_scan_stocks(stocks)
                st.session_state.daily_scan_task = result["task_id"]
                st.success(f"✅ 扫描任务已提交，ID: {result['task_id']}")
                st.info("任务将在后台执行，页面会自动刷新显示进度...")
                time.sleep(1)
                st.rerun()

        # 如果有扫描结果（来自异步任务完成后的继续执行）
        if "scan_signals" in st.session_state:
            signals = st.session_state.scan_signals
            del st.session_state.scan_signals
            
            # 过滤
            signals = [s for s in signals if s.confidence >= min_confidence]

            if signals:
                    # 信号统计
                    buy_sigs = [s for s in signals if s.direction == "BUY"]
                    sell_sigs = [s for s in signals if s.direction == "SELL"]

                    # 统计卡片
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric("总信号数", len(signals))
                    sc2.metric("买入信号", len(buy_sigs), "🟢")
                    sc3.metric("卖出信号", len(sell_sigs), "🔴")
                    sc4.metric("平均置信度", f"{sum(s.confidence for s in signals)/len(signals):.0f}%")

                    st.markdown("---")

                    # 买入信号
                    if buy_sigs:
                        st.markdown("### 🟢 买入信号")
                        for sig in buy_sigs:
                            col_sig, col_act = st.columns([3, 1])
                            with col_sig:
                                st.markdown(f"""
                                <div class="signal-card signal-buy">
                                    <div style="display:flex;justify-content:space-between;">
                                        <div>
                                            <span class="tag tag-buy">买入</span>
                                            <span class="tag tag-strategy">{sig.strategy_name}</span>
                                            <span class="tag tag-ai">置信度 {sig.confidence}%</span>
                                        </div>
                                        <div style="font-weight:600;font-size:16px;">{sig.stock_name or sig.stock_code}</div>
                                    </div>
                                    <div style="color:#94a3b8;font-size:13px;margin-top:6px;">{sig.reason}</div>
                                    <div style="display:flex;gap:16px;color:#64748b;font-size:12px;margin-top:6px;">
                                        <span>信号价 <b style="color:#f8fafc">¥{sig.price:.2f}</b></span>
                                        <span>止损 <b style="color:#ef4444">¥{sig.stop_loss:.2f}</b></span>
                                        <span>目标 <b style="color:#10b981">¥{sig.target_price:.2f}</b></span>
                                        <span>盈亏比 <b style="color:#f59e0b">{(sig.target_price-sig.price)/(sig.price-sig.stop_loss):.1f}R</b></span>
                                    </div>
                                </div>""", unsafe_allow_html=True)
                            with col_act:
                                from core.button_fixer import ButtonResponseFixer
                                
                                def buy_action():
                                    try:
                                        brain.portfolio.execute_buy(sig)
                                        return True
                                    except Exception as e:
                                        st.error(f"买入失败: {e}")
                                        return False
                                
                                if ButtonResponseFixer.create_action_button(
                                    "确认买入",
                                    buy_action,
                                    success_msg=f"✅ 已买入 {sig.stock_code}",
                                    error_msg="买入操作失败",
                                    key=f"buy_{sig.id}",
                                    use_container_width=True
                                ):
                                    # 使用experimental_rerun替代rerun
                                    st.rerun()

                    # 卖出信号
                    if sell_sigs:
                        st.markdown("### 🔴 卖出信号")
                        for sig in sell_sigs:
                            st.markdown(f"""
                            <div class="signal-card signal-sell">
                                <div style="display:flex;justify-content:space-between;align-items:center;">
                                    <div>
                                        <span class="tag tag-sell">卖出</span>
                                        <span class="tag tag-strategy">{sig.strategy_name}</span>
                                        <span class="tag tag-ai">{sig.confidence}%</span>
                                    </div>
                                    <div style="font-weight:600;">{sig.stock_name or sig.stock_code}</div>
                                </div>
                                <div style="color:#94a3b8;font-size:13px;margin-top:6px;">{sig.reason}</div>
                                <div style="color:#64748b;font-size:12px;margin-top:4px;">
                                    信号价 ¥{sig.price:.2f} | {sig.created_at}
                                </div>
                            </div>""", unsafe_allow_html=True)

                    # 保存并触发AI学习
                    for sig in signals:
                        brain.portfolio.add_signal(sig)

                    # 一键买入所有
                    if buy_sigs:
                        st.markdown("---")
                        bc1, bc2 = st.columns([1, 1])
                        with bc1:
                            def buy_all_action():
                                count = 0
                                for sig in buy_sigs:
                                    try:
                                        brain.portfolio.execute_buy(sig)
                                        count += 1
                                    except Exception as e:
                                        st.error(f"买入{sig.stock_code}失败: {e}")
                                if count > 0:
                                    st.success(f"✅ 成功买入 {count} 只股票！")
                                    st.rerun()
                                return count > 0
                            
                            if ButtonResponseFixer.create_action_button(
                                f"⚡ 一键买入全部（{len(buy_sigs)}只）",
                                buy_all_action,
                                success_msg="一键买入操作已执行",
                                error_msg="一键买入失败",
                                type="primary",
                                use_container_width=True
                            ):
                                pass
                        with bc2:
                            st.info("💡 信号已保存，AI正在后台分析信号质量并学习优化...")

                    else:
                        st.info("没有发现符合条件的信号。可以：\n- 降低置信度阈值\n- 增加自选股数量\n- 更换热门组合")

    with scan_tab2:
        """市场概览 — 快速了解大盘走势"""
        st.markdown("### 📊 市场概览")
        st.caption("主要指数实时走势")

        # 指数代码映射：纯数字（AkShare格式）
        indices = {
            "上证指数": "000001",
            "深证成指": "399001",
            "创业板指": "399006",
            "沪深300": "000300",
            "中证500": "000905",
        }

        @st.cache_data(ttl=300)  # 5分钟缓存
        def get_index_data(idx_code):
            return DataProvider.get_index_daily(idx_code, days=10)

        idx_cols = st.columns(5)
        for i, (name, code) in enumerate(indices.items()):
            with idx_cols[i]:
                try:
                    data = get_index_data(code)
                    if not data.empty:
                        latest = data.iloc[-1]
                        prev = data.iloc[-2] if len(data) > 1 else latest
                        pct = (latest["close"] - prev["close"]) / prev["close"] * 100
                        color = "#10b981" if pct >= 0 else "#ef4444"
                        sign = "+" if pct >= 0 else ""
                        st.markdown(f"""
                        <div class="metric-card" style="text-align:center;">
                            <div class="metric-label">{name}</div>
                            <div style="font-size:20px;font-weight:700;color:{color};">
                                {latest['close']:.2f}
                            </div>
                            <div style="color:{color};font-size:13px;">{sign}{pct:.2f}%</div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{name}**: 数据加载失败")
                except Exception as e:
                    st.markdown(f"**{name}**: 加载异常")

        st.markdown("---")
        st.markdown("### 📋 涨停跌停监控")
        st.caption("基于最新市场数据")

        # 使用AkShare获取涨停/跌停数据
        @st.cache_data(ttl=300)
        def get_limit_data():
            try:
                from core.multi_data_source import MultiDataSource
                limit_up = MultiDataSource.get_limit_up_stocks()
                limit_down = MultiDataSource.get_limit_down_stocks()
                return limit_up, limit_down
            except:
                return pd.DataFrame(), pd.DataFrame()

        limit_up_df, limit_down_df = get_limit_data()

        tab_zt, tab_dt = st.tabs(["🟢 涨停板", "🔴 跌停板"])

        with tab_zt:
            if limit_up_df is not None and not limit_up_df.empty:
                st.success(f"今日涨停 {len(limit_up_df)} 只")
                # 显示列名适配
                show_cols = [c for c in ["代码", "名称", "涨跌幅", "最新价", "成交额", "连板数", "首次封板时间", "最后封板时间", "封板资金", "打开次数"] if c in limit_up_df.columns]
                if show_cols:
                    st.dataframe(limit_up_df[show_cols].head(30), use_container_width=True, hide_index=True)
            else:
                st.info("暂无涨停数据（可能非交易时间或数据源不可用）")

        with tab_dt:
            if limit_down_df is not None and not limit_down_df.empty:
                st.error(f"今日跌停 {len(limit_down_df)} 只")
                show_cols = [c for c in ["代码", "名称", "跌停价", "最新价", "成交额"] if c in limit_down_df.columns]
                if show_cols:
                    st.dataframe(limit_down_df[show_cols].head(30), use_container_width=True, hide_index=True)
            else:
                st.info("暂无跌停数据（可能非交易时间或数据源不可用）")

        st.markdown("---")
        st.markdown("### 🔥 热门股异动扫描")
        hot_stocks = ["600519", "000858", "300750", "601318", "002594",
                      "600036", "000333", "300059", "002415", "688981",
                      "601012", "600438", "300014", "002230", "603501"]
        def scan_hot_stocks_action():
            with st.spinner("扫描异动中..."):
                hot_signals = brain.signal_gen.scan_stocks(hot_stocks)
                if hot_signals:
                    for sig in hot_signals[:10]:
                        dir_emoji = "🟢" if sig.direction == "BUY" else "🔴"
                        st.markdown(f"{dir_emoji} **{sig.stock_name}({sig.stock_code})** — {sig.strategy_name} — 置信度{sig.confidence}% — {sig.reason[:80]}")
                else:
                    st.info("暂无异动信号")
            return True
        
        if ButtonResponseFixer.create_action_button(
            "🔍 扫描热门股异动",
            scan_hot_stocks_action,
            success_msg="热门股扫描完成",
            error_msg="扫描失败",
            use_container_width=True
        ):
            pass

    with scan_tab3:
        """批量操作"""
        st.markdown("### ⚡ 批量操作")

        st.markdown("#### 一键卖出所有持仓")
        positions = brain.portfolio.positions
        if positions:
            st.warning(f"当前持有 {len(positions)} 只股票，卖出将全部平仓")
            
            def sell_all_action():
                for pos in positions:
                    brain.portfolio.execute_sell(pos.stock_code)
                st.success("✅ 已全部卖出！")
                st.rerun()
                return True
            
            if ButtonResponseFixer.create_action_button(
                "🗑️ 确认全部卖出",
                sell_all_action,
                success_msg="全部卖出操作已执行",
                error_msg="卖出失败",
                type="secondary",
                use_container_width=True
            ):
                pass
        else:
            st.info("当前没有持仓")

        st.markdown("---")
        st.markdown("#### 智能止损")
        st.caption("自动卖出亏损超过阈值的持仓")
        stop_loss_pct = st.slider("止损阈值", 2, 20, 8, format="%d%%")
        if positions:
            loss_positions = [p for p in positions if p.profit_pct < -stop_loss_pct]
            if loss_positions:
                st.error(f"⚠️ {len(loss_positions)} 只持仓亏损超过 {stop_loss_pct}%")
                for p in loss_positions:
                    st.markdown(f"- **{p.stock_name}({p.stock_code})** 亏损 {p.profit_pct}%")
                def stop_loss_action():
                    for p in loss_positions:
                        brain.portfolio.execute_sell(p.stock_code)
                    st.success("✅ 止损完成")
                    st.rerun()
                    return True
                
                if ButtonResponseFixer.create_action_button(
                    f"🛡️ 止损卖出（{len(loss_positions)}只）",
                    stop_loss_action,
                    success_msg="止损操作已执行",
                    error_msg="止损失败",
                    type="secondary",
                    use_container_width=True
                ):
                    pass
            else:
                st.success(f"✅ 所有持仓亏损都在 {stop_loss_pct}% 以内")
        else:
            st.info("当前没有持仓")

    with scan_tab4:
        """全A股智能扫描 — AI进化策略 × 全市场覆盖"""
        st.markdown("### 🌏 全A股扫描")
        st.caption("获取全部A股列表，AI筛选有价值的标的（分批处理，避免超时）")

        # 获取全股列表 - 使用优化版本
        @st.cache_data(ttl=86400)  # 24小时缓存
        @performance_monitor.track("get_all_a_stocks")
        def get_all_a_stocks():
            return optimized_data.get_stock_list()

        all_stocks_df = get_all_a_stocks()
        if all_stocks_df.empty:
            st.error("无法获取全股列表，请检查数据源连接")
        else:
            total = len(all_stocks_df)
            st.info(f"当前A股总数: **{total}** 只 | 数据来源: AkShare")

            # 扫描配置
            col_cfg1, col_cfg2, col_cfg3 = st.columns([1, 1, 1])
            with col_cfg1:
                scan_size = st.selectbox("本次扫描数量", [50, 100, 200, 500], index=1,
                    help="每次扫描的股票数量，避免超时")
            with col_cfg2:
                min_price = st.number_input("最低股价（元）", min_value=0.0, value=5.0, step=1.0)
            with col_cfg3:
                max_price = st.number_input("最高股价（元）", min_value=0.0, value=500.0, step=10.0)

            # 板块/行业过滤
            sectors = {
                "全部": None,
                "沪深300": "hs300",
                "中证500": "zz500",
                "创业板": "cyb",
                "科创板": "kcb",
            }
            sector = st.selectbox("板块筛选", list(sectors.keys()))

            st.markdown("---")

            # 扫描按钮
            def full_scan_action():
                # 预处理：过滤价格范围
                scan_df = all_stocks_df.copy()

                # 更新价格（批量获取太慢，用默认范围过滤）
                # 实际价格由 signal_gen 扫描时获取
                return True
            
            if ButtonResponseFixer.create_action_button(
                "🚀 开始全A股扫描",
                full_scan_action,
                success_msg="开始全A股扫描",
                error_msg="启动扫描失败",
                type="primary",
                use_container_width=True
            ):
                pass
                scan_stocks = scan_df["code"].tolist()[:scan_size]

                st.warning(f"⚠️ 即将扫描前 {len(scan_stocks)} 只股票，预计耗时 3-10 分钟")
                st.info("💡 建议：先使用「智能扫描」测试少量股票，确认策略有效后再扩大范围")

                progress_bar = st.progress(0, text="全A股扫描中...")
                all_signals = []
                batch_size = 20
                total_batches = (len(scan_stocks) + batch_size - 1) // batch_size

                for batch_i in range(total_batches):
                    batch = scan_stocks[batch_i * batch_size:(batch_i + 1) * batch_size]
                    try:
                        batch_signals = brain.signal_gen.scan_stocks(
                            batch,
                            progress_cb=lambda p, t: progress_bar.progress(
                                (batch_i + p) / total_batches,
                                text=f"批次{batch_i+1}/{total_batches} | {t}"
                            )
                        )
                        all_signals.extend(batch_signals)
                    except Exception as e:
                        st.warning(f"批次 {batch_i+1} 出错: {e}")

                progress_bar.empty()

                if all_signals:
                    # 过滤高质量信号
                    quality_signals = [s for s in all_signals if s.confidence >= 65]
                    quality_signals.sort(key=lambda x: -x.confidence)

                    st.success(f"✅ 扫描完成！发现 {len(quality_signals)} 个高质量信号（置信度≥65%）")

                    # 信号分布
                    buy_sigs = [s for s in quality_signals if s.direction == "BUY"]
                    sell_sigs = [s for s in quality_signals if s.direction == "SELL"]

                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric("扫描股票", len(scan_stocks))
                    sc2.metric("高质量信号", len(quality_signals))
                    sc3.metric("买入信号", len(buy_sigs), "🟢")
                    sc4.metric("卖出信号", len(sell_sigs), "🔴")

                    st.markdown("---")

                    if buy_sigs:
                        st.markdown("### 🟢 全市场买入信号 TOP 20")
                        for sig in buy_sigs[:20]:
                            col_sig, col_act = st.columns([3, 1])
                            with col_sig:
                                st.markdown(f"""
                                <div class="signal-card signal-buy">
                                    <div style="display:flex;justify-content:space-between;">
                                        <div>
                                            <span class="tag tag-buy">买入</span>
                                            <span class="tag tag-strategy">{sig.strategy_name}</span>
                                            <span class="tag tag-ai">置信度 {sig.confidence}%</span>
                                        </div>
                                        <div style="font-weight:600;font-size:16px;">{sig.stock_name or sig.stock_code}</div>
                                    </div>
                                    <div style="color:#94a3b8;font-size:13px;margin-top:6px;">{sig.reason}</div>
                                    <div style="display:flex;gap:16px;color:#64748b;font-size:12px;margin-top:6px;">
                                        <span>信号价 <b style="color:#f8fafc">¥{sig.price:.2f}</b></span>
                                        <span>止损 <b style="color:#ef4444">¥{sig.stop_loss:.2f}</b></span>
                                        <span>目标 <b style="color:#10b981">¥{sig.target_price:.2f}</b></span>
                                        <span>盈亏比 <b style="color:#f59e0b">{(sig.target_price-sig.price)/(sig.price-sig.stop_loss+0.01):.1f}R</b></span>
                                    </div>
                                </div>""", unsafe_allow_html=True)
                            with col_act:
                                def buy_single_action():
                                    brain.portfolio.execute_buy(sig)
                                    return True
                                
                                if ButtonResponseFixer.create_action_button(
                                    "买入",
                                    buy_single_action,
                                    success_msg=f"✅ 已买入 {sig.stock_code}",
                                    error_msg="买入失败",
                                    key=f"full_buy_{sig.id}",
                                    use_container_width=True
                                ):
                                    st.rerun()
                    else:
                        st.info("本次扫描未发现买入信号，可降低置信度阈值或扩大扫描范围")
                else:
                    st.info("未发现任何信号")

    # ← 结束全A股扫描


# ═══════════════════════════════════════════════
# 页面3: 持仓跟踪
# ═══════════════════════════════════════════════
elif page == "💼 持仓跟踪":
    st.markdown('<div class="page-title">💼 持仓跟踪</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">实时跟踪持仓盈亏，自动触发卖出信号</div>', unsafe_allow_html=True)

    brain.portfolio.update_prices()
    summary = brain.portfolio.get_summary()

    # 总览卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总资产", f"¥{summary['total_market_value']:,.0f}")
    with col2:
        pct = summary['total_profit_pct']
        st.metric("总盈亏", f"¥{summary['total_profit']:,.0f}", f"{pct:+.2f}%")
    with col3:
        st.metric("持仓数", summary['total_positions'])
    with col4:
        st.metric("可用资金", f"¥{summary['available_cash']:,.0f}")

    st.markdown("---")

    # 持仓列表
    positions = summary["positions"]
    if positions:
        st.markdown("### 持仓明细")
        df_pos = pd.DataFrame(positions)
        df_pos["盈亏%"] = df_pos["profit_pct"].apply(lambda x: f"{'+'if x>=0 else ''}{x:.2f}%")
        df_pos["盈亏额"] = df_pos["profit_amount"].apply(lambda x: f"¥{x:+,.0f}")
        st.dataframe(df_pos[["stock_code", "stock_name", "shares", "avg_cost", "current_price",
                              "盈亏%", "盈亏额", "strategy_name"]],
                     use_container_width=True, hide_index=True)

        st.markdown("---")

        # 手动卖出
        st.markdown("### 📤 卖出操作")
        sell_col1, sell_col2, sell_col3 = st.columns([2, 1, 1])
        with sell_col1:
            code_options = [f"{p['stock_name']}({p['stock_code']})" for p in positions]
            selected = st.selectbox("选择持仓", code_options)
            selected_code = selected.split("(")[1].replace(")", "") if selected else ""
        with sell_col2:
            sell_price = st.number_input("卖出价格（留空用现价）", min_value=0.0, step=0.01, value=0.0)
        with sell_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            from core.button_fixer import ButtonResponseFixer
            
            def sell_action():
                if not selected_code:
                    st.error("请选择要卖出的股票")
                    return False
                
                try:
                    price = sell_price if sell_price > 0 else None
                    profit = brain.portfolio.execute_sell(selected_code, price)
                    if profit is not None:
                        return profit
                    else:
                        st.error("卖出失败")
                        return False
                except Exception as e:
                    st.error(f"卖出失败: {e}")
                    return False
            
            if ButtonResponseFixer.create_action_button(
                "确认卖出",
                sell_action,
                success_msg=lambda profit: f"✅ 卖出成功！收益: {profit:+.2f}%" if isinstance(profit, (int, float)) else "✅ 卖出成功！",
                error_msg="卖出操作失败",
                type="primary"
            ):
                st.rerun()
    else:
        st.info("暂无持仓。去「每日扫描」发现交易机会！")

    st.markdown("---")
    st.markdown("### 📜 全部交易记录")
    all_signals = brain.portfolio.signals
    if all_signals:
        df_all = pd.DataFrame([{
            "时间": s.created_at,
            "股票": f"{s.stock_name or ''}({s.stock_code})",
            "方向": "买入" if s.direction == "BUY" else "卖出",
            "策略": s.strategy_name,
            "置信度": f"{s.confidence}%",
            "状态": {"PENDING": "待执行", "EXECUTED": "已执行", "CLOSED": "已平仓"}.get(s.status, s.status),
            "收益": f"{s.profit_pct:+.2f}%" if s.status == "CLOSED" else "-",
        } for s in all_signals[-50:]])
        st.dataframe(df_all, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════
# 页面4: K线分析
# ═══════════════════════════════════════════════
elif page == "📈 K线分析":
    st.markdown('<div class="page-title">📈 K线分析</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">技术指标分析 + AI诊断</div>', unsafe_allow_html=True)

    col_input, col_btn = st.columns([3, 1])
    with col_input:
        stock_code = st.text_input("股票代码", value="600519", placeholder="如 600519, 000001")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        
        def view_kline_action():
            st.rerun()
            return True
        
        if ButtonResponseFixer.create_action_button(
            "📊 查看K线",
            view_kline_action,
            success_msg="正在加载K线",
            error_msg="加载失败",
            type="primary"
        ):
            pass

    if stock_code:
        with st.spinner(f"正在加载 {stock_code} 数据..."):
            # 使用优化后的数据获取，带缓存
            @performance_monitor.track("get_stock_daily")
            def load_stock_data():
                return optimized_data.get_stock_daily(stock_code, days=180)
            
            data = load_stock_data()

        if not data.empty:
            # 计算指标 - 带缓存
            @st.cache_data(ttl=3600)
            @performance_monitor.track("calculate_indicators")
            def calculate_cached_indicators(df):
                return DataProvider.calculate_indicators(df)
            
            data = calculate_cached_indicators(data)
            
            # 获取股票信息 - 带缓存
            @st.cache_data(ttl=86400)
            @performance_monitor.track("get_stock_info")
            def get_cached_stock_info(code):
                return DataProvider.get_stock_info(code)
            
            info = get_cached_stock_info(stock_code)
            name = info.get("name", stock_code)

            st.markdown(f"### {name}（{stock_code}）")
            latest = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else latest
            pct = latest["pct_change"]

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("最新价", f"¥{latest['close']:.2f}", f"{pct:+.2f}%")
            col2.metric("RSI(14)", f"{latest['rsi']:.1f}", "超买" if latest['rsi'] > 70 else "超卖" if latest['rsi'] < 30 else "正常")
            col3.metric("MACD", f"{latest['macd_hist']:.4f}", "金叉" if latest['macd_hist'] > 0 and prev['macd_hist'] <= 0 else "死叉" if latest['macd_hist'] < 0 and prev['macd_hist'] >= 0 else "")
            col4.metric("KDJ-J", f"{latest['j']:.1f}", "超买" if latest['j'] > 100 else "超卖" if latest['j'] < 0 else "正常")
            col5.metric("布林带", f"{latest['boll_upper']:.2f}", f"下轨{latest['boll_lower']:.2f}")

            # K线图
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                               row_heights=[0.7, 0.3],
                               vertical_spacing=0.03)

            # K线
            fig.add_trace(go.Candlestick(
                x=data["date"], open=data["open"], high=data["high"],
                low=data["low"], close=data["close"],
                name="K线", increasing_line_color="#10b981", decreasing_line_color="#ef4444",
            ), row=1, col=1)

            # 均线
            for period, color in [(5, "#f59e0b"), (10, "#3b82f6"), (20, "#a855f7"), (60, "#ef4444")]:
                fig.add_trace(go.Scatter(
                    x=data["date"], y=data[f"ma_{period}"],
                    name=f"MA{period}", line=dict(color=color, width=1),
                ), row=1, col=1)

            # 布林带
            fig.add_trace(go.Scatter(
                x=data["date"], y=data["boll_upper"],
                name="BOLL上", line=dict(color="#3b82f6", width=0.5, dash="dash"), showlegend=False,
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=data["date"], y=data["boll_lower"],
                name="BOLL下", line=dict(color="#3b82f6", width=0.5, dash="dash"),
                fill="tonexty", fillcolor="rgba(59, 130, 246, 0.06)", showlegend=False,
            ), row=1, col=1)

            # 成交量
            colors = ["#10b981" if c >= 0 else "#ef4444" for c in data["pct_change"]]
            fig.add_trace(go.Bar(
                x=data["date"], y=data["volume"],
                name="成交量", marker_color=colors, opacity=0.6,
            ), row=2, col=1)

            fig.update_layout(
                template="plotly_dark",
                height=600,
                xaxis_rangeslider_visible=False,
                paper_bgcolor="#0a0e1a",
                plot_bgcolor="#0f1629",
                font=dict(color="#94a3b8", size=12),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                           font=dict(size=10)),
                margin=dict(t=30, b=30, l=50, r=20),
            )
            fig.update_yaxes(gridcolor="#1e293b", row=1, col=1)
            fig.update_yaxes(gridcolor="#1e293b", row=2, col=1)

            st.plotly_chart(fig, use_container_width=True)

            # AI诊断
            def ai_diagnose_action():
                with st.spinner("AI分析中..."):
                    indicators_text = f"""
最新数据:
- 收盘价: {latest['close']:.2f}, 涨跌幅: {pct:+.2f}%
- RSI(14): {latest['rsi']:.1f}
- MACD DIF: {latest['dif']:.4f}, DEA: {latest['dea']:.4f}, 柱状: {latest['macd_hist']:.4f}
- KDJ: K={latest['k']:.1f}, D={latest['d']:.1f}, J={latest['j']:.1f}
- 布林带: 上轨{latest['boll_upper']:.2f}, 中轨{latest['boll_mid']:.2f}, 下轨{latest['boll_lower']:.2f}
- 均线: MA5={latest['ma_5']:.2f}, MA20={latest['ma_20']:.2f}, MA60={latest['ma_60']:.2f}
- 成交量: {latest['volume']:.0f}, 5日均量: {latest['vol_ma_5']:.0f}
- ATR(14): {latest['atr']:.2f}"""

                    try:
                        from core.llm_manager import get_llm_manager
                        llm = get_llm_manager()
                        analysis = llm.diagnose_stock(name, stock_code, indicators_text)
                        if analysis:
                            st.markdown(f"### 🤖 AI诊断结果\n\n{analysis}")
                        else:
                            st.error("AI诊断暂时不可用，请检查API Key配置")
                    except Exception as e:
                        st.error(f"AI分析失败: {e}")
                return True
            
            if ButtonResponseFixer.create_action_button(
                "🤖 AI诊断该股",
                ai_diagnose_action,
                success_msg="AI诊断完成",
                error_msg="AI诊断失败",
                use_container_width=True
            ):
                pass
        else:
            st.error(f"无法获取 {stock_code} 的数据，请检查代码是否正确")




# ═══════════════════════════════════════════════
# 页面5: 策略进化中心 v2.0（实时可视化版）
# ═══════════════════════════════════════════════
elif page == "🧬 策略进化中心":
    st.markdown('<div class="page-title">🧬 策略进化中心 v3.0</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">生产级稳定版：使用经过验证的策略模板，确保100%可回测</div>', unsafe_allow_html=True)

    try:
        from core.evolution_v3 import get_evolution_engine_v3
        engine = get_evolution_engine_v3()
        v3_available = True
    except ImportError as e:
        st.warning(f"进化引擎v3加载失败: {e}")
        try:
            from core.evolution_v2 import get_evolution_engine_v2
            engine = get_evolution_engine_v2()
            v3_available = False
        except ImportError:
            from core.auto_evolution import get_evolution_engine
            engine = get_evolution_engine()
            v3_available = False

    # 初始化session state
    if "evolution_logs" not in st.session_state:
        st.session_state.evolution_logs = []
    if "evolution_running" not in st.session_state:
        st.session_state.evolution_running = False
    if "current_record" not in st.session_state:
        st.session_state.current_record = None
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False

    # 状态概览
    status = engine.get_status()
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">进化轮次</div>
            <div class="metric-value">{status['cycle_count']}</div>
            <div class="metric-change" style="color:#94a3b8">上次: {status['last_run'][:16] if status['last_run'] != '从未运行' else '从未'}</div>
        </div>""", unsafe_allow_html=True)
    with col_s2:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">候选策略</div>
            <div class="metric-value">{status['total_candidates']}</div>
            <div class="metric-change" style="color:#94a3b8">策略库总数</div>
        </div>""", unsafe_allow_html=True)
    with col_s3:
        latest = engine.get_latest_cycle()
        best_score = latest.get('best_strategy_score', 0) if latest else 0
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">最佳评分</div>
            <div class="metric-value">{best_score:.1f}</div>
            <div class="metric-change" style="color:#94a3b8">历史最高</div>
        </div>""", unsafe_allow_html=True)
    with col_s4:
        run_status = "🟡 运行中" if st.session_state.evolution_running else "🟢 就绪"
        run_color = "#f59e0b" if st.session_state.evolution_running else "#10b981"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">当前状态</div>
            <div class="metric-value" style="color:{run_color};font-size:20px;">{run_status}</div>
            <div class="metric-change" style="color:#94a3b8">v3.0 稳定版</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # 六阶段流水线可视化
    st.markdown("### 🔄 进化流水线")
    
    phases = ["discovery", "backtest", "optimize", "factor_extraction"]
    phase_names = {
        "discovery": ("🔍", "策略发现"),
        "backtest": ("📊", "回测验证"),
        "optimize": ("⚡", "AI优化"),
        "factor_extraction": ("🧪", "因子提取"),
    }
    
    # 获取当前阶段状态
    phase_data = {}
    if latest and "phases" in latest:
        for phase in phases:
            phase_data[phase] = latest["phases"].get(phase, {"status": "pending", "progress_pct": 0, "message": ""})
    else:
        for phase in phases:
            phase_data[phase] = {"status": "pending", "progress_pct": 0, "message": "等待启动..."}

    # 渲染阶段卡片
    phase_cols = st.columns(4)
    for i, phase in enumerate(phases):
        icon, name = phase_names[phase]
        data = phase_data.get(phase, {})
        status = data.get("status", "pending")
        progress = data.get("progress_pct", 0)
        message = data.get("message", "")
        
        status_colors = {
            "pending": ("#334155", "#94a3b8"),
            "running": ("#3b82f6", "#3b82f6"),
            "completed": ("#10b981", "#10b981"),
            "failed": ("#ef4444", "#ef4444"),
        }
        border_color, glow = status_colors.get(status, ("#334155", "#94a3b8"))
        
        with phase_cols[i]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1f35, #141929); 
                        border: 2px solid {border_color}; 
                        border-radius: 12px; padding: 12px; 
                        {'box-shadow: 0 0 15px ' + glow + '40;' if status == 'running' else ''}
                        text-align: center;">
                <div style="font-size: 20px; margin-bottom: 4px;">{icon}</div>
                <div style="font-size: 11px; font-weight: 600; color: #f8fafc;">{name}</div>
                <div style="font-size: 10px; color: {glow}; margin-top: 4px;">{status.upper()}</div>
                <div style="background: #0f1629; border-radius: 4px; height: 4px; margin-top: 8px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #3b82f6, #a855f7); 
                                height: 100%; width: {progress}%; border-radius: 4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # 控制按钮 + 实时统计
    col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns([1, 1, 1, 2])
    
    with col_ctrl1:
        if st.button("🚀 开始进化", type="primary", use_container_width=True,
                     disabled=st.session_state.evolution_running):
            st.session_state.evolution_running = True
            st.session_state.auto_refresh = True
            
            import threading
            def run_evolution():
                try:
                    def progress_cb(pct, msg):
                        st.session_state.current_progress = pct
                        st.session_state.current_message = msg
                    
                    result = engine.run_cycle(progress_cb=progress_cb)
                    st.session_state.current_record = result.to_dict() if hasattr(result, 'to_dict') else result
                    st.session_state.evolution_running = False
                except Exception as e:
                    st.session_state.evolution_running = False
                    st.session_state.evolution_error = str(e)
            
            thread = threading.Thread(target=run_evolution, daemon=True)
            thread.start()
            time.sleep(0.5)
            st.rerun()

    with col_ctrl2:
        if st.button("⏹️ 停止", use_container_width=True,
                     disabled=not st.session_state.evolution_running):
            st.session_state.evolution_running = False
            st.session_state.auto_refresh = False
            st.rerun()

    with col_ctrl3:
        auto_refresh = st.toggle("自动刷新", value=st.session_state.auto_refresh)
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
            st.rerun()

    with col_ctrl4:
        # 本轮统计
        if latest:
            st.markdown(f"""
            <div style="display: flex; gap: 16px; align-items: center; justify-content: flex-end;">
                <div style="text-align: center;">
                    <div style="font-size: 20px; font-weight: 700; color: #3b82f6;">{latest.get('strategies_discovered', 0)}</div>
                    <div style="font-size: 10px; color: #64748b;">发现</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 20px; font-weight: 700; color: #10b981;">{latest.get('strategies_passed', 0)}</div>
                    <div style="font-size: 10px; color: #64748b;">通过</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 20px; font-weight: 700; color: #a855f7;">{latest.get('strategies_optimized', 0)}</div>
                    <div style="font-size: 10px; color: #64748b;">优化</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 20px; font-weight: 700; color: #f59e0b;">{latest.get('factors_extracted', 0)}</div>
                    <div style="font-size: 10px; color: #64748b;">因子</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # 策略排行榜
    st.markdown("### 🏆 策略排行榜")
    
    ranking = engine.get_strategy_ranking(limit=10)
    if ranking:
        df_data = []
        for i, s in enumerate(ranking):
            metrics = s.get("backtest_metrics", {}) or {}
            df_data.append({
                "排名": i + 1,
                "策略名称": s.get("name", "")[:20],
                "来源": s.get("source", "")[:10],
                "综合评分": f"{s.get('composite_score', 0):.1f}",
                "年化收益": f"{metrics.get('annual_return', 0):.1%}",
                "夏普": f"{metrics.get('sharpe_ratio', 0):.2f}",
                "回撤": f"{metrics.get('max_drawdown', 0):.1%}",
                "胜率": f"{metrics.get('win_rate', 0):.1%}",
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无策略数据，点击「开始进化」启动第一轮进化")

    st.markdown("---")

    # 进化历史
    st.markdown("### 📊 进化历史")
    
    history = engine.get_evolution_history(limit=5)
    if history:
        history_cols = st.columns(min(len(history), 5))
        for i, record in enumerate(history[:5]):
            with history_cols[i]:
                status_emoji = {"completed": "✅", "failed": "❌", "running": "🔄"}.get(record.get("status"), "❓")
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1a1f35, #141929); 
                            border: 1px solid #1e293b; border-radius: 12px; padding: 12px;">
                    <div style="font-size: 12px; color: #64748b;">第 {record.get('cycle_id')} 轮</div>
                    <div style="font-size: 16px; margin: 4px 0;">{status_emoji}</div>
                    <div style="font-size: 11px; color: #94a3b8;">
                        发现 {record.get('strategies_discovered', 0)} | 
                        通过 {record.get('strategies_passed', 0)}
                    </div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">
                        {record.get('started_at', '')[:10]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("暂无进化历史")

    # 自动刷新
    if st.session_state.auto_refresh and st.session_state.evolution_running:
        time.sleep(3)
        st.rerun()


# ═══════════════════════════════════════════════
# 页面6: AI策略学习
# ═══════════════════════════════════════════════
elif page == "🤖 AI策略学习":
    st.markdown('<div class="page-title">🤖 AI策略学习</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">AI自动搜索、学习、优化量化策略</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🌐 搜索策略", "🧠 AI生成", "⚡ 优化策略", "📚 策略库"])

    with tab1:
        st.markdown("### 从GitHub学习策略")
        st.caption("自动抓取GitHub开源量化项目，提取可用的策略代码（异步执行，不阻塞UI）")

        # 检查是否有正在进行的任务
        if "github_search_task" in st.session_state:
            task_id = st.session_state.github_search_task
            task_status = task_manager.get_task_status(task_id)
            
            if task_status:
                if task_status["status"] == "running":
                    st.info(f"🔍 正在搜索GitHub... 进度: {task_status.get('progress', 0):.0f}%")
                    st.progress(task_status.get("progress", 0) / 100.0)
                    st.caption(task_status.get("message", ""))
                    
                    # 自动刷新
                    time.sleep(1)
                    st.rerun()
                    
                elif task_status["status"] == "completed":
                    st.success("✅ GitHub搜索完成！")
                    
                    # 显示结果
                    result = task_status.get("result", [])
                    if result:
                        st.success(f"新发现 {len(result)} 个策略")
                        for s in result:
                            st.markdown(f"""
                            <div class="signal-card">
                                <div style="font-weight:600;color:#f8fafc;">{s['name']}</div>
                                <div style="color:#64748b;font-size:12px;margin-top:4px;">
                                    来源: {s['source']} | 分类: {s['category']} | 评分: {s['quality_score']:.0f}
                                </div>
                                <div style="color:#94a3b8;font-size:12px;margin-top:4px;">{s['description']}</div>
                            </div>""", unsafe_allow_html=True)
                    else:
                        st.info("未发现新策略（可能已全部学习过，或GitHub API受限）")
                    
                    # 清理任务状态
                    del st.session_state.github_search_task
                    
                elif task_status["status"] == "failed":
                    st.error(f"❌ GitHub搜索失败: {task_status.get('error', '未知错误')}")
                    del st.session_state.github_search_task

        def search_github_action():
            # 提交异步任务
            result = AsyncTasks.search_github_strategies()
            st.session_state.github_search_task = result["task_id"]
            st.success(f"✅ 任务已提交，ID: {result['task_id']}")
            st.info("任务将在后台执行，页面会自动刷新显示进度...")
            return True
        
        if ButtonResponseFixer.create_action_button(
            "🔍 开始搜索GitHub策略",
            search_github_action,
            success_msg="GitHub搜索任务已提交",
            error_msg="提交任务失败",
            type="primary",
            use_container_width=True
        ):
            pass
            time.sleep(1)
            st.rerun()

    with tab2:
        st.markdown("### AI生成新策略")
        st.caption("让GLM大模型为你创造全新的量化策略（异步执行，不阻塞UI）")

        # 检查是否有正在进行的AI生成任务
        if "ai_generate_task" in st.session_state:
            task_id = st.session_state.ai_generate_task
            task_status = task_manager.get_task_status(task_id)
            
            if task_status:
                if task_status["status"] == "running":
                    st.info(f"🧠 AI正在生成策略... 进度: {task_status.get('progress', 0):.0f}%")
                    st.progress(task_status.get("progress", 0) / 100.0)
                    st.caption(task_status.get("message", ""))
                    
                    # 自动刷新
                    time.sleep(1)
                    st.rerun()
                    
                elif task_status["status"] == "completed":
                    st.success("✅ AI策略生成完成！")
                    
                    # 显示结果
                    result = task_status.get("result")
                    if result and result.get("status") == "success":
                        st.code(result.get("strategy_code", ""), language="python")
                        st.info(f"策略代码长度: {result.get('length', 0)} 字符")
                        
                        # 将生成的策略添加到知识库
                        try:
                            from core.quant_brain import StrategyKnowledge
                            strategy = StrategyKnowledge(
                                name=f"AI生成策略_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                code=result.get("strategy_code", ""),
                                source="AI生成",
                                category="AI生成",
                                description="由AI大模型生成的量化策略",
                                quality_score=75.0
                            )
                            brain.learner.knowledge_base.append(strategy)
                            brain.learner._save_data()
                            st.success("策略已添加到知识库！")
                        except Exception as e:
                            st.warning(f"添加到知识库失败: {e}")
                    else:
                        st.error("AI生成失败，请重试")
                    
                    # 清理任务状态
                    del st.session_state.ai_generate_task
                    
                elif task_status["status"] == "failed":
                    st.error(f"❌ AI生成失败: {task_status.get('error', '未知错误')}")
                    del st.session_state.ai_generate_task

        preset_prompts = [
            "生成一个适合A股震荡市的量化策略",
            "生成一个基于量价关系的突破策略",
            "生成一个低回撤的防守型策略",
            "生成一个多因子选股策略(技术指标版)",
            "生成一个基于支撑压力位的策略",
        ]
        prompt = st.selectbox("选择生成方向", preset_prompts)
        custom_prompt = st.text_input("或输入自定义需求", placeholder="如: 结合RSI和布林带的中线策略")

        def ai_generate_action():
            final_prompt = custom_prompt if custom_prompt else prompt
            
            # 提交异步任务
            result = AsyncTasks.ai_generate_strategy(final_prompt)
            st.session_state.ai_generate_task = result["task_id"]
            st.success(f"✅ AI生成任务已提交，ID: {result['task_id']}")
            st.info("AI将在后台生成策略，页面会自动刷新显示进度...")
            time.sleep(1)
            st.rerun()
            return True
        
        if ButtonResponseFixer.create_action_button(
            "🧠 AI生成策略",
            ai_generate_action,
            success_msg="AI生成任务已提交",
            error_msg="提交任务失败",
            type="primary",
            use_container_width=True
        ):
            pass

    with tab3:
        st.markdown("### AI优化策略")
        st.caption("选择已有策略，让AI根据实盘/回测表现进行优化（异步执行，不阻塞UI）")

        # 检查是否有正在进行的AI优化任务
        if "ai_optimize_task" in st.session_state:
            task_id = st.session_state.ai_optimize_task
            task_status = task_manager.get_task_status(task_id)
            
            if task_status:
                if task_status["status"] == "running":
                    st.info(f"⚡ AI正在优化策略... 进度: {task_status.get('progress', 0):.0f}%")
                    st.progress(task_status.get("progress", 0) / 100.0)
                    st.caption(task_status.get("message", ""))
                    
                    # 自动刷新
                    time.sleep(1)
                    st.rerun()
                    
                elif task_status["status"] == "completed":
                    st.success("✅ AI策略优化完成！")
                    
                    # 显示结果
                    result = task_status.get("result")
                    if result and result.get("status") == "success":
                        st.code(result.get("optimized_code", ""), language="python")
                        st.info(f"优化提升: +{result.get('improvement', 0):.0f}分 (原{result.get('quality_score', 0)-result.get('improvement', 0):.0f} → 现{result.get('quality_score', 0):.0f})")
                        
                        # 更新知识库中的策略
                        try:
                            for kb in brain.learner.knowledge_base:
                                if kb.name == result.get("original_name"):
                                    kb.code = result.get("optimized_code")
                                    kb.quality_score = result.get("quality_score")
                                    kb.description = f"AI优化版本 - {kb.description}"
                                    break
                            brain.learner._save_data()
                            st.success("策略知识库已更新！")
                        except Exception as e:
                            st.warning(f"更新知识库失败: {e}")
                    else:
                        st.error(f"AI优化失败: {result.get('error', '未知错误')}")
                    
                    # 清理任务状态
                    del st.session_state.ai_optimize_task
                    
                elif task_status["status"] == "failed":
                    st.error(f"❌ AI优化失败: {task_status.get('error', '未知错误')}")
                    del st.session_state.ai_optimize_task

        if brain.learner.knowledge_base:
            strategy_names = [kb.name for kb in brain.learner.knowledge_base]
            selected = st.selectbox("选择策略", strategy_names)

            if selected:
                kb = next(kb for kb in brain.learner.knowledge_base if kb.name == selected)
                st.markdown(f"**当前策略**: {kb.name}")
                st.markdown(f"评分: {kb.quality_score:.0f} | 来源: {kb.source} | 实盘交易: {kb.real_trade_count}次")

                def ai_optimize_action():
                    # 提交异步任务
                    result = AsyncTasks.ai_optimize_strategy(selected)
                    st.session_state.ai_optimize_task = result["task_id"]
                    st.success(f"✅ AI优化任务已提交，ID: {result['task_id']}")
                    st.info("AI将在后台优化策略，页面会自动刷新显示进度...")
                    time.sleep(1)
                    st.rerun()
                    return True
                
                if ButtonResponseFixer.create_action_button(
                    "⚡ 让AI优化这个策略",
                    ai_optimize_action,
                    success_msg="AI优化任务已提交",
                    error_msg="提交任务失败",
                    type="primary",
                    use_container_width=True
                ):
                    pass
        else:
            st.info("策略库为空，请先从GitHub搜索或AI生成策略")

    with tab4:
        st.markdown("### 📚 策略知识库")
        st.caption(f"已学习 {len(brain.learner.knowledge_base)} 个策略")

        for kb in brain.learner.knowledge_base:
            with st.expander(f"📊 {kb.name} (评分:{kb.quality_score:.0f})"):
                st.write(f"**分类**: {kb.category}")
                st.write(f"**来源**: {kb.source}")
                st.write(f"**描述**: {kb.description[:200]}")
                st.write(f"**因子**: {', '.join(kb.factors)}")
                st.write(f"**实盘**: {kb.real_trade_count}次交易, 胜率{kb.real_win_rate:.0f}%")
                st.code(kb.code, language="python")

        st.markdown("---")
        st.markdown("### 📖 学习日志")
        for log in reversed(brain.learner.learning_log[-20:]):
            action_emoji = {"learn": "📥", "optimize": "⚡", "trade": "💰", "evaluate": "📊"}.get(log.action, "📝")
            st.markdown(f"{action_emoji} `{log.date}` {log.action} | {log.strategy} | {log.result}")
            if log.ai_insight:
                st.caption(f"💡 {log.ai_insight[:100]}")


# ═══════════════════════════════════════════════
# 页面6: 多源策略学习
# ═══════════════════════════════════════════════
elif page == "🌐 多源策略学习":
    st.markdown('<div class="page-title">🌐 多源策略学习</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">从 arXiv论文、GitHub开源项目、量化社区爬取和学习策略，AI提取知识入库</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 搜索策略", "📚 已学策略", "⚡ 一键学习", "🎯 策略推荐"])
    
    with tab1:
        st.markdown("### 🔍 搜索多源策略")
        st.caption("同时搜索 arXiv论文、GitHub开源项目、量化社区（聚宽/米筐/雪球）")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            search_keyword = st.text_input("搜索关键词", value="量化交易策略")
        with col2:
            search_sources = st.multiselect(
                "选择来源",
                options=["📄 arXiv论文", "💻 GitHub", "🌐 量化社区"],
                default=["📄 arXiv论文", "💻 GitHub", "🌐 量化社区"]
            )
        
        search_limit = st.slider("每源搜索数量", min_value=1, max_value=10, value=5)
        
        def search_all_sources_action():
            try:
                from core.multi_source_strategy import get_multi_source_learner
                learner = get_multi_source_learner()
                
                results = {}
                if "📄 arXiv论文" in search_sources:
                    results["arxiv"] = learner.search_arxiv(search_keyword, search_limit)
                if "💻 GitHub" in search_sources:
                    results["github"] = learner.search_github(search_keyword, search_limit)
                if "🌐 量化社区" in search_sources:
                    results["community"] = learner.search_community(search_keyword, max_results=search_limit)
                
                total = sum(len(v) for v in results.values())
                if total > 0:
                    st.session_state["multi_source_results"] = results
                    st.session_state["multi_source_total"] = total
                    return True
                else:
                    st.warning("未找到相关策略，请尝试其他关键词")
                    return False
            except Exception as e:
                st.error(f"搜索失败: {e}")
                return False
        
        if ButtonResponseFixer.create_action_button(
            "🔍 开始搜索",
            search_all_sources_action,
            success_msg="搜索完成",
            error_msg="搜索失败",
            type="primary",
            use_container_width=True
        ):
            pass
        
        # 显示搜索结果
        if "multi_source_results" in st.session_state:
            results = st.session_state["multi_source_results"]
            total = st.session_state.get("multi_source_total", 0)
            st.success(f"共找到 {total} 条结果")
            
            # 按来源分组显示
            source_names = {"arxiv": "📄 arXiv论文", "github": "💻 GitHub", "community": "🌐 量化社区"}
            
            for source_key, source_label in source_names.items():
                items = results.get(source_key, [])
                if not items:
                    continue
                
                with st.expander(f"{source_label} ({len(items)} 条)", expanded=True):
                    for i, item in enumerate(items):
                        platform_badge = f"_{item.platform}" if hasattr(item, 'platform') else ""
                        title = item.title if hasattr(item, 'title') else str(item)
                        
                        st.markdown(f"**{i+1}. {title}**")
                        
                        col_info, col_act = st.columns([4, 1])
                        with col_info:
                            if hasattr(item, 'author') and item.author:
                                st.caption(f"作者: {item.author}")
                            if hasattr(item, 'publish_date') and item.publish_date:
                                st.caption(f"日期: {item.publish_date}")
                            if hasattr(item, 'like_count') and item.like_count > 0:
                                st.caption(f"⭐ {item.like_count} Stars")
                            if hasattr(item, 'description') and item.description:
                                st.caption(item.description[:200])
                            if hasattr(item, 'url') and item.url:
                                st.markdown(f"[🔗 查看]({item.url})")
                        
                        with col_act:
                            st.markdown("<br>", unsafe_allow_html=True)
                            def learn_single_action(src=item):
                                try:
                                    from core.multi_source_strategy import get_multi_source_learner, add_to_main_knowledge_base
                                    learner = get_multi_source_learner()
                                    knowledge = learner.extract_knowledge(src)
                                    if knowledge and knowledge.core_logic and knowledge.core_logic != "未提取到核心逻辑":
                                        entry = {
                                            "strategy": {
                                                "platform": src.platform,
                                                "url": src.url,
                                                "title": src.title,
                                                "author": getattr(src, 'author', ''),
                                            },
                                            "knowledge": {
                                                "strategy_type": knowledge.strategy_type,
                                                "core_logic": knowledge.core_logic,
                                                "indicators": knowledge.indicators,
                                                "key_factors": knowledge.key_factors,
                                                "risk_control": knowledge.risk_control,
                                                "market_condition": knowledge.market_condition,
                                                "quality_score": knowledge.quality_score,
                                            },
                                            "learned_at": datetime.now().isoformat(),
                                        }
                                        learner.learned_strategies.append(entry)
                                        learner._save_learned()
                                        add_to_main_knowledge_base(entry, brain.learner)
                                        st.success(f"✅ 已学习并入库: {src.title[:30]}")
                                        return True
                                    else:
                                        st.warning("AI未能提取有效知识")
                                        return False
                                except Exception as e:
                                    st.error(f"学习失败: {e}")
                                    return False
                            
                            if ButtonResponseFixer.create_action_button(
                                "📖 学习",
                                lambda s=item: learn_single_action(s),
                                success_msg="学习完成",
                                error_msg="学习失败",
                                key=f"learn_{source_key}_{i}",
                                use_container_width=True
                            ):
                                pass
            
            # 一键全部学习按钮
            all_items = []
            for source_key in ["arxiv", "github", "community"]:
                all_items.extend(results.get(source_key, []))
            
            if all_items:
                st.markdown("---")
                def learn_all_action():
                    try:
                        from core.multi_source_strategy import get_multi_source_learner, add_to_main_knowledge_base
                        learner = get_multi_source_learner()
                        
                        learned_count = 0
                        for src in all_items:
                            try:
                                knowledge = learner.extract_knowledge(src)
                                if knowledge and knowledge.core_logic and knowledge.core_logic != "未提取到核心逻辑":
                                    entry = {
                                        "strategy": {
                                            "platform": src.platform,
                                            "url": src.url,
                                            "title": src.title,
                                            "author": getattr(src, 'author', ''),
                                        },
                                        "knowledge": {
                                            "strategy_type": knowledge.strategy_type,
                                            "core_logic": knowledge.core_logic,
                                            "indicators": knowledge.indicators,
                                            "key_factors": knowledge.key_factors,
                                            "risk_control": knowledge.risk_control,
                                            "market_condition": knowledge.market_condition,
                                            "quality_score": knowledge.quality_score,
                                        },
                                        "learned_at": datetime.now().isoformat(),
                                    }
                                    learner.learned_strategies.append(entry)
                                    add_to_main_knowledge_base(entry, brain.learner)
                                    learned_count += 1
                                time.sleep(0.5)
                            except Exception as e:
                                st.warning(f"学习 {src.title[:30]} 失败: {e}")
                                continue
                        
                        learner._save_learned()
                        st.success(f"✅ 成功学习 {learned_count}/{len(all_items)} 个策略！")
                        return learned_count > 0
                    except Exception as e:
                        st.error(f"批量学习失败: {e}")
                        return False
                
                if ButtonResponseFixer.create_action_button(
                    f"⚡ 一键学习全部 ({len(all_items)} 个)",
                    learn_all_action,
                    success_msg="批量学习完成",
                    error_msg="批量学习失败",
                    type="primary",
                    use_container_width=True
                ):
                    pass
    
    with tab2:
        st.markdown("### 📚 已学习的多源策略")
        
        try:
            from core.multi_source_strategy import get_multi_source_learner
            learner = get_multi_source_learner()
            stats = learner.get_stats()
            
            if stats["total"] == 0:
                st.info("尚未学习任何策略，请先搜索并学习策略")
            else:
                # 统计概览
                col_s1, col_s2, col_s3 = st.columns(3)
                col_s1.metric("已学策略", stats["total"])
                with col_s2:
                    by_platform = stats.get("by_platform", {})
                    st.metric("来源平台", len(by_platform))
                with col_s3:
                    by_type = stats.get("by_type", {})
                    st.metric("策略类型", len(by_type))
                
                st.markdown("---")
                
                # 来源分布
                if stats.get("by_platform"):
                    st.markdown("**📊 来源分布**")
                    pcols = st.columns(min(len(stats["by_platform"]), 4))
                    for i, (platform, count) in enumerate(stats["by_platform"].items()):
                        with pcols[i]:
                            st.metric(platform, count)
                    st.markdown("---")
                
                # 最近学习的策略
                recent = learner.get_recent_learned(20)
                if recent:
                    st.markdown("### 📖 最近学习的策略")
                    for i, item in enumerate(reversed(recent)):
                        strategy = item.get("strategy", {})
                        knowledge = item.get("knowledge", {})
                        
                        platform = strategy.get("platform", "未知")
                        platform_emoji = {"arxiv": "📄", "github": "💻", "joinquant": "🌐", "ricequant": "🌐", "xueqiu": "🌐"}.get(platform, "📋")
                        quality = knowledge.get("quality_score", 0)
                        
                        with st.expander(f"{platform_emoji} {strategy.get('title', '未知标题')[:50]} (评分:{quality:.0f})"):
                            col_kb, col_btn = st.columns([4, 1])
                            with col_kb:
                                st.markdown(f"""
                                **来源**: {platform}  \n
                                **策略类型**: {knowledge.get('strategy_type', '未知')}  \n
                                **质量评分**: {quality:.0f}/100  \n
                                **核心逻辑**: {knowledge.get('core_logic', '未提取')[:300]}  \n
                                **适用市场**: {knowledge.get('market_condition', '通用')}  \n
                                """)
                                
                                indicators = knowledge.get("indicators", [])
                                if indicators:
                                    st.markdown(f"**技术指标**: {', '.join(indicators)}")
                                
                                key_factors = knowledge.get("key_factors", [])
                                if key_factors:
                                    st.markdown(f"**关键因子**: {', '.join(key_factors)}")
                                
                                risk = knowledge.get("risk_control", "")
                                if risk and risk != "未提及":
                                    st.markdown(f"**风险控制**: {risk}")
                                
                                improvement = knowledge.get("improvement_suggestions", "")
                                if improvement:
                                    st.markdown(f"**改进建议**: {improvement[:300]}")
                                
                                url = strategy.get("url", "")
                                if url:
                                    st.markdown(f"[🔗 查看原文]({url})")
                            
                            with col_btn:
                                st.markdown("<br><br>", unsafe_allow_html=True)
                                def add_to_kb_action(entry=item):
                                    try:
                                        from core.multi_source_strategy import add_to_main_knowledge_base
                                        success = add_to_main_knowledge_base(entry, brain.learner)
                                        if success:
                                            st.success("✅ 已添加到主策略库！")
                                        else:
                                            st.info("已在主策略库中")
                                        return True
                                    except Exception as e:
                                        st.error(f"添加失败: {e}")
                                        return False
                                
                                if ButtonResponseFixer.create_action_button(
                                    "📥 入库",
                                    add_to_kb_action,
                                    success_msg="已入库",
                                    error_msg="入库失败",
                                    key=f"add_kb_{i}",
                                    use_container_width=True
                                ):
                                    pass
        except Exception as e:
            st.error(f"加载已学习策略失败: {e}")
    
    with tab3:
        st.markdown("### ⚡ 一键智能学习")
        st.caption("AI自动从多源搜索、学习最新量化策略（异步执行，不阻塞UI）")
        
        quick_keywords = [
            "量化交易策略 机器学习",
            "A股动量策略",
            "A股均值回归",
            "深度学习股票预测",
            "多因子选股",
        ]
        
        keyword = st.selectbox("选择学习方向", quick_keywords)
        
        # 检查是否有正在进行的任务
        if "multi_learn_task" in st.session_state:
            task_id = st.session_state.multi_learn_task
            task_status = task_manager.get_task_status(task_id)
            
            if task_status:
                if task_status["status"] == "running":
                    st.info(f"🤖 AI正在多源学习... 进度: {task_status.get('progress', 0):.0f}%")
                    st.progress(task_status.get("progress", 0) / 100.0)
                    st.caption(task_status.get("message", ""))
                    time.sleep(1)
                    st.rerun()
                elif task_status["status"] == "completed":
                    result = task_status.get("result", {})
                    total_learned = result.get("total", 0)
                    st.success(f"✅ 学习完成！共学习 {total_learned} 个策略")
                    
                    details = result.get("details", {})
                    for source, count in details.items():
                        if count > 0:
                            st.markdown(f"- {source}: {count} 个策略")
                    
                    del st.session_state.multi_learn_task
                elif task_status["status"] == "failed":
                    st.error(f"❌ 学习失败: {task_status.get('error', '未知错误')}")
                    del st.session_state.multi_learn_task
        
        def quick_learn_action():
            try:
                from core.multi_source_strategy import get_multi_source_learner, add_to_main_knowledge_base
                learner = get_multi_source_learner()
                
                # 提交异步任务
                result = AsyncTasks.multi_source_learn(keyword)
                st.session_state.multi_learn_task = result["task_id"]
                st.success(f"✅ 多源学习任务已提交，ID: {result['task_id']}")
                time.sleep(1)
                st.rerun()
                return True
            except Exception as e:
                st.error(f"提交任务失败: {e}")
                return False
        
        if ButtonResponseFixer.create_action_button(
            "🚀 开始一键学习",
            quick_learn_action,
            success_msg="学习任务已提交",
            error_msg="提交失败",
            type="primary",
            use_container_width=True
        ):
            pass
    
    with tab4:
        st.markdown("### 🎯 策略推荐")
        st.caption("基于AI质量评分和市场环境，推荐最佳策略")
        
        market_condition = st.selectbox(
            "当前市场环境",
            options=["牛市", "熊市", "震荡市", "不确定"],
            index=3
        )
        
        def get_recommendations_action():
            try:
                from core.multi_source_strategy import get_multi_source_learner
                learner = get_multi_source_learner()
                
                recommendations = learner.get_recommendations(
                    market_condition if market_condition != "不确定" else None,
                    top_n=10
                )
                
                if recommendations:
                    st.session_state["strategy_recommendations"] = recommendations
                    return True
                else:
                    st.info("没有已学习的策略，请先搜索并学习策略")
                    return False
            except Exception as e:
                st.error(f"获取推荐失败: {e}")
                return False
        
        if ButtonResponseFixer.create_action_button(
            "🎯 获取推荐",
            get_recommendations_action,
            success_msg="推荐生成完成",
            error_msg="推荐生成失败",
            use_container_width=True
        ):
            pass
        
        if "strategy_recommendations" in st.session_state:
            recs = st.session_state["strategy_recommendations"]
            st.success(f"已推荐 {len(recs)} 个策略")
            
            for i, rec in enumerate(recs):
                knowledge = rec.get("knowledge", {})
                strategy = rec.get("strategy", {})
                score = rec.get("recommend_score", 0)
                platform = strategy.get("platform", "未知")
                
                stars = "⭐" * min(int(score / 2), 5)
                
                with st.expander(f"#{i+1} {strategy.get('title', '未知')[:40]} ({stars} {score:.1f}分)"):
                    st.markdown(f"""
                    **来源**: {platform}  \n
                    **策略类型**: {knowledge.get('strategy_type', '未知')}  \n
                    **推荐分数**: {score:.1f}  \n
                    **质量评分**: {knowledge.get('quality_score', 0):.0f}/100  \n
                    **适用市场**: {knowledge.get('market_condition', '通用')}  \n
                    """)
                    
                    core_logic = knowledge.get("core_logic", "")
                    if core_logic:
                        st.markdown(f"**核心逻辑**: {core_logic[:400]}")
                    
                    url = strategy.get("url", "")
                    if url:
                        st.markdown(f"[🔗 查看原文]({url})")


# ═══════════════════════════════════════════════
# 页面7: 策略回测
# ═══════════════════════════════════════════════
elif page == "🔄 策略回测":
    st.markdown('<div class="page-title">🔄 策略回测</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">回测策略代码，验证历史表现</div>', unsafe_allow_html=True)

    tab_backtest, tab_strategy = st.tabs(["运行回测", "内置策略"])

    with tab_backtest:
        stock_code = st.text_input("回测股票代码", value="600519")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=pd.Timestamp(datetime.now()) - pd.Timedelta(days=365))
        with col2:
            end_date = st.date_input("结束日期", value=pd.Timestamp(datetime.now()))

        st.markdown("### 策略代码")
        default_code = '''import backtrader as bt

class MyStrategy(bt.Strategy):
    params = (("fast_period", 5), ("slow_period", 20))

    def __init__(self):
        self.strategy_name = "双均线策略"
        self.ma_fast = bt.indicators.SMA(self.data.close, period=self.p.fast_period)
        self.ma_slow = bt.indicators.SMA(self.data.close, period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.ma_fast, self.ma_slow)
        self.order = None

    def next(self):
        if self.order:
            return
        if self.crossover > 0:
            self.order = self.buy()
        elif self.crossover < 0:
            self.order = self.close()

    def notify_order(self, order):
        self.order = None
'''
        code = st.text_area("Backtrader策略代码", value=default_code, height=250)

        def run_backtest_action():
            with st.spinner("回测中..."):
                result = brain.backtest_strategy_code(
                    code, stock_code,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )

                if "error" in result:
                    st.error(f"回测失败: {result['error']}")
                else:
                    st.success("✅ 回测完成！")

                    # 结果卡片
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("年化收益", f"{result['annual_return']*100:.2f}%")
                    col2.metric("夏普比率", f"{result['sharpe_ratio']:.2f}")
                    col3.metric("最大回撤", f"{result['max_drawdown']*100:.2f}%")
                    col4.metric("胜率", f"{result['win_rate']*100:.1f}%")

                    # 净值曲线
                    if "daily_values" in result and result["daily_values"] is not None:
                        daily = result["daily_values"]
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=daily.index, y=daily["portfolio_value"],
                            name="策略净值", line=dict(color="#3b82f6", width=2),
                        ))
                        if "benchmark_value" in daily and daily["benchmark_value"].notna().any():
                            fig.add_trace(go.Scatter(
                                x=daily.index, y=daily["benchmark_value"],
                                name="基准净值", line=dict(color="#64748b", width=1, dash="dash"),
                            ))
                        fig.update_layout(
                            template="plotly_dark",
                            height=400,
                            paper_bgcolor="#0a0e1a",
                            plot_bgcolor="#0f1629",
                            font=dict(color="#94a3b8"),
                            margin=dict(t=20, b=20, l=50, r=20),
                        )
                        st.plotly_chart(fig, use_container_width=True)
                return True

        if ButtonResponseFixer.create_action_button(
            "▶️ 运行回测",
            run_backtest_action,
            success_msg="回测任务已开始",
            error_msg="启动回测失败",
            type="primary",
            use_container_width=True
        ):
            pass

    with tab_strategy:
        st.markdown("### 内置策略快速回测")
        strategies = brain.signal_gen.STRATEGIES
        for name, info in strategies.items():
            with st.expander(f"📊 {info['name']} — {info['desc']}"):
                def strategy_backtest_action(strategy_name=info['name']):
                    st.info(f"策略「{strategy_name}」已集成到信号系统中，在「每日扫描」页面直接使用")
                    return True
                
                if ButtonResponseFixer.create_action_button(
                    f"回测 {info['name']}",
                    lambda s=info['name']: strategy_backtest_action(s),
                    success_msg="策略信息已显示",
                    error_msg="操作失败",
                    key=f"bt_{name}"
                ):
                    pass


# ═══════════════════════════════════════════════
# 页面8: 数据库性能
# ═══════════════════════════════════════════════
elif page == "📊 数据库性能":
    # 导入数据库监控模块
    from core.database_monitor import create_database_performance_page
    create_database_performance_page()


# ═══════════════════════════════════════════════
# 页面9: 设置
# ═══════════════════════════════════════════════
elif page == "⚙️ 设置":
    st.markdown('<div class="page-title">⚙️ 设置</div>', unsafe_allow_html=True)

    tab_set1, tab_set2, tab_set3, tab_set4 = st.tabs(["基本设置", "数据源", "AI模型", "公网访问"])

    with tab_set1:
        st.markdown("### 资金设置")
        new_cash = st.number_input("初始资金", min_value=10000.0, max_value=10000000.0,
                                    value=float(brain.portfolio.initial_cash), step=10000.0)
        def save_cash_action():
            brain.portfolio.initial_cash = new_cash
            brain.portfolio._save_data()
            return True
        
        if ButtonResponseFixer.create_action_button(
            "保存",
            save_cash_action,
            success_msg="已保存",
            error_msg="保存失败",
            use_container_width=True
        ):
            pass

        st.markdown("---")
        st.markdown("### 清除数据")
        def clear_data_action():
            brain.portfolio.positions.clear()
            brain.portfolio.signals.clear()
            brain.portfolio._save_data()
            return True
        
        if ButtonResponseFixer.create_action_button(
            "🗑️ 清除所有持仓和信号",
            clear_data_action,
            success_msg="已清除",
            error_msg="清除失败",
            use_container_width=True,
            type="secondary"
        ):
            st.rerun()

    with tab_set2:
        st.markdown("### 当前数据源")
        st.info("当前使用 **BaoStock + AkShare**（免费，自动切换）")

        st.markdown("---")
        st.markdown("### AKShare 配置（可选）")
        st.caption("AKShare可获取实时行情，但需要关闭代理或配置白名单")
        st.code("""
# 测试AKShare连接
import akshare as ak
df = ak.stock_zh_a_spot_em()
print(df.head())
""", language="python")
        st.warning("⚠️ 如果遇到代理错误(ProxyError)，需要: 1)关闭系统代理 2)或设置NO_PROXY环境变量")

    with tab_set3:
        st.markdown("### 🤖 AI模型配置")
        st.info("QuantBrain 支持多LLM自动切换，自动优先使用已配置模型")

        # 加载配置
        try:
            from config import AI_MODELS, DEFAULT_MODEL_PRIORITY
            available = []
            not_configured = []
            for key, model in AI_MODELS.items():
                needs_key = model.get("needs_key", False)
                has_key = bool(model.get("api_key"))
                if needs_key and not has_key:
                    not_configured.append(model)
                else:
                    available.append((key, model))

            st.markdown("#### ✅ 已就绪的模型（按优先级）")
            if available:
                for key, model in available:
                    recommended_mark = "⭐ 推荐" if model.get("recommended") else ""
                    st.markdown(f"""
**{model['name']}** {recommended_mark}
- 提供商: {model.get('provider', 'unknown')}
- 用途: {', '.join(model.get('strengths', []))}
- 速率限制: {model.get('rate_limit', 'N/A')}
""")
                priority_str = " → ".join([AI_MODELS[k]["name"] for k in DEFAULT_MODEL_PRIORITY if k in [x[0] for x in available]])
                st.caption(f"当前优先级: {priority_str}")
            else:
                st.warning("没有已就绪的模型，请配置API Key")

            st.markdown("---")
            st.markdown("#### ⚙️ 未配置的模型（需要API Key）")
            for key, model in not_configured:
                st.markdown(f"""
**{model['name']}**
- 提供商: {model.get('provider', 'unknown')}
- 注册地址: [{model.get('key_url', 'N/A')}]({model.get('key_url', '#')})
- 用途: {', '.join(model.get('strengths', []))}
- 费用: {model.get('rate_limit', 'N/A')}
""")
            st.caption("💡 配置方式：在 HuggingFace Spaces 的 Settings → Secrets 中添加环境变量")

        except Exception as e:
            st.error(f"无法加载配置: {e}")

        st.markdown("---")
        
        # AI协同工作测试
        st.markdown("#### 🤝 AI协同工作测试")
        st.info("测试多AI模型协同分析功能，系统会自动选择最适合的模型组合")
        
        test_prompt = st.text_area(
            "测试提示词",
            value="分析贵州茅台(600519.SH)的投资价值，给出买入/持有/卖出的建议",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            def single_model_test_action():
                try:
                    from core.llm_manager import get_llm_manager
                    llm = get_llm_manager()
                    result = llm.chat([{"role": "user", "content": test_prompt}])
                    if result:
                        st.success("✅ 单模型测试成功")
                        st.text_area("分析结果", value=result, height=200)
                        return True
                    else:
                        st.error("❌ 单模型测试失败")
                        return False
                except Exception as e:
                    st.error(f"测试失败: {e}")
                    return False
            
            if ButtonResponseFixer.create_action_button(
                "🚀 单模型测试",
                single_model_test_action,
                success_msg="单模型测试完成",
                error_msg="单模型测试失败",
                type="secondary",
                use_container_width=True
            ):
                pass
        
        with col2:
            def multi_model_test_action():
                try:
                    from core.ai_collaboration import get_collaboration_engine, TaskType
                    engine = get_collaboration_engine()
                    
                    with st.spinner("多模型协同分析中..."):
                        result = engine.sync_collaborative_analysis(
                            task_type=TaskType.STRATEGY_ANALYSIS,
                            prompt=test_prompt,
                            model_count=2
                        )
                    
                    if result["success"]:
                        st.success(f"✅ 协同分析成功（使用 {result['model_count']} 个模型）")
                        
                        # 显示融合结果
                        fused = result["fused_result"]
                        st.markdown("### 📊 融合分析结果")
                        st.markdown(f"**置信度**: {fused['confidence']:.2f}")
                        st.markdown(f"**共识类型**: {fused['consensus']}")
                        st.text_area("分析内容", value=fused["content"], height=300)
                        
                        # 显示各模型结果
                        with st.expander("查看各模型详细结果"):
                            for i, individual in enumerate(result["individual_results"]):
                                st.markdown(f"#### 模型 {i+1}: {individual['model_name']}")
                                st.text_area(f"结果 {i+1}", value=individual["content"], height=150)
                        return True
                    else:
                        st.error(f"❌ 协同分析失败: {result.get('error')}")
                        return False
                except Exception as e:
                    st.error(f"测试失败: {e}")
                    return False
            
            if ButtonResponseFixer.create_action_button(
                "🤝 多模型协同测试",
                multi_model_test_action,
                success_msg="多模型协同测试完成",
                error_msg="多模型协同测试失败",
                type="primary",
                use_container_width=True
            ):
                pass
        
        st.markdown("---")
        st.markdown("#### 🔥 DeepSeek 申请指南（极便宜）")
        st.markdown("""
1. 访问 [DeepSeek Platform](https://platform.deepseek.com/) 注册账号
2. 在 API Keys 页面创建新 Key
3. 在 HuggingFace Spaces Secrets 中添加: `DEEPSEEK_API_KEY = 你的Key`
4. DeepSeek V3 模型费用：**¥1/M tokens**（极便宜）
""")

    with tab_set4:
        st.markdown("### ☁️ HuggingFace Spaces（当前部署）")
        st.success("✅ 已部署到 HuggingFace Spaces")
        st.markdown(f"👉 **[打开 QuantBrain](https://bondtwilight-quantbrain.hf.space)**")
        st.caption("• 2 vCPU / 16GB RAM / 50GB 存储（免费）\n"
                 "• 数据通过 GitHub 仓库持久化\n"
                 "• 代码更新后自动重新部署")

        st.markdown("---")
        st.markdown("### 本地内网穿透（备用）")

        st.markdown("#### 方法1: Ngrok（推荐，最简单）")
        st.code("""
# 1. 下载 ngrok: https://ngrok.com/download
# 2. 注册免费账号获取 authtoken
# 3. 运行:
ngrok http 8501
# 4. 复制生成的 https://xxxx.ngrok.io 地址即可访问
""", language="bash")

        st.markdown("#### 方法2: LocalTunnel")
        st.code("""
# 使用 npx 直接运行（无需安装）
npx localtunnel --port 8501
""", language="bash")

        st.markdown("#### 方法3: Cloudflare Tunnel")
        st.code("""
# 1. 下载 cloudflared
# 2. 运行:
cloudflared tunnel --url http://localhost:8501
""", language="bash")

        st.markdown("---")
        current_url = f"http://localhost:8501"
        st.markdown(f"### 当前本地地址: {current_url}")
        def copy_address_action():
            st.toast("地址已复制（模拟）")
            return True
        
        if ButtonResponseFixer.create_action_button(
            "📋 复制地址",
            copy_address_action,
            success_msg="地址已复制",
            error_msg="复制失败",
            use_container_width=True
        ):
            pass
