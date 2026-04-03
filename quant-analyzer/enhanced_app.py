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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core.quant_brain import QuantBrain, DataProvider

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

# 初始化
@st.cache_resource
def get_brain():
    return QuantBrain()

brain = get_brain()


# ═══════════════════════════════════════════════
# 侧边栏导航
# ═══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🧠 QuantBrain")
    st.caption("AI量化策略自学习系统 v4.0")

    page = st.radio("导航", [
        "📊 信号仪表盘",
        "📡 每日扫描",
        "💼 持仓跟踪",
        "📈 K线分析",
        "🤖 AI策略学习",
        "🔄 策略回测",
        "⚙️ 设置",
    ], label_visibility="collapsed")

    st.markdown("---")
    st.caption(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption("数据源: BaoStock (免费)")

    # 快捷操作
    if st.button("🚀 一键扫描自选股", use_container_width=True, type="primary"):
        st.session_state["quick_scan"] = True


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
# 页面2: 每日扫描
# ═══════════════════════════════════════════════
elif page == "📡 每日扫描":
    st.markdown('<div class="page-title">📡 每日扫描</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">AI扫描自选股，自动生成买卖信号</div>', unsafe_allow_html=True)

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
        st.markdown("### 策略说明")
        st.caption("• 多信号共振: RSI+MACD+均线\n• 突破策略: N日新高突破\n• 布林带回归: 触及上下轨\n• 放量突破: 量价齐升\n• 动量反转: 超跌反弹")

    scan_clicked = st.button("🚀 开始扫描", type="primary", use_container_width=True) or st.session_state.get("quick_scan")
    if "quick_scan" in st.session_state:
        st.session_state.pop("quick_scan")

    if scan_clicked:
        stocks = [s.strip() for s in stock_input.strip().split("\n") if s.strip()]
        if not stocks:
            st.warning("请输入股票代码")
        else:
            brain.save_watchlist(stocks)
            progress = st.progress(0, text="正在扫描...")
            signals = brain.signal_gen.scan_stocks(
                stocks,
                progress_cb=lambda p, t: progress.progress(p, text=t)
            )
            progress.empty()

            # 过滤
            signals = [s for s in signals if s.confidence >= min_confidence]

            if signals:
                st.success(f"✅ 扫描完成！发现 **{len(signals)}** 个信号（置信度 ≥ {min_confidence}%）")

                # 信号详情
                for sig in signals:
                    dir_class = "signal-buy" if sig.direction == "BUY" else "signal-sell"
                    dir_tag = "tag-buy" if sig.direction == "BUY" else "tag-sell"
                    dir_text = "🟢 买入" if sig.direction == "BUY" else "🔴 卖出"

                    col_sig, col_act = st.columns([3, 1])
                    with col_sig:
                        st.markdown(f"""
                        <div class="signal-card {dir_class}">
                            <div style="display:flex;justify-content:space-between;">
                                <div>
                                    <span class="tag {dir_tag}">{dir_text}</span>
                                    <span class="tag tag-strategy">{sig.strategy_name}</span>
                                    <span style="color:#f59e0b;">{sig.confidence}%</span>
                                </div>
                                <div style="font-weight:600;">{sig.stock_name or sig.stock_code}</div>
                            </div>
                            <div style="color:#94a3b8;font-size:13px;margin-top:6px;">{sig.reason}</div>
                            <div style="color:#64748b;font-size:12px;margin-top:4px;">
                                信号价 ¥{sig.price:.2f} | 止损 ¥{sig.stop_loss:.2f} | 目标 ¥{sig.target_price:.2f}
                            </div>
                        </div>""", unsafe_allow_html=True)
                    with col_act:
                        if sig.direction == "BUY":
                            if st.button("确认买入", key=f"buy_{sig.id}", use_container_width=True):
                                brain.portfolio.execute_buy(sig)
                                st.success(f"✅ 已买入 {sig.stock_code}")
                                st.rerun()

                # 保存并触发AI学习
                for sig in signals:
                    brain.portfolio.add_signal(sig)

                st.info("💡 信号已保存，AI正在后台分析信号质量并学习优化...")

            else:
                st.info("没有发现符合条件的信号。可以降低置信度阈值再试试。")


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
            if st.button("确认卖出", type="primary"):
                if selected_code:
                    price = sell_price if sell_price > 0 else None
                    profit = brain.portfolio.execute_sell(selected_code, price)
                    if profit is not None:
                        st.success(f"✅ 卖出成功！收益: {profit:+.2f}%")
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
        if st.button("📊 查看K线", type="primary"):
            st.rerun()

    if stock_code:
        with st.spinner(f"正在加载 {stock_code} 数据..."):
            data = DataProvider.get_stock_daily(stock_code, days=180)

        if not data.empty:
            data = DataProvider.calculate_indicators(data)
            info = DataProvider.get_stock_info(stock_code)
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
                fill="tonexty", fillcolor="#3b82f610", showlegend=False,
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
            if st.button("🤖 AI诊断该股", use_container_width=True):
                with st.spinner("AI分析中..."):
                    from config import ZHIPU_API_KEY
                    import requests

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
                        resp = requests.post(
                            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                            headers={"Content-Type": "application/json",
                                    "Authorization": f"Bearer {ZHIPU_API_KEY}"},
                            json={
                                "model": "glm-4-flash",
                                "messages": [
                                    {"role": "system", "content": "你是资深A股技术分析师。根据指标给出简洁的投资建议。"},
                                    {"role": "user", "content": f"请分析{name}({stock_code})的技术指标:{indicators_text}\n\n给出: 1)当前趋势判断 2)支撑位/压力位 3)操作建议(买入/观望/卖出) 4)风险提示。简洁回答，200字以内。"},
                                ],
                                "temperature": 0.3,
                                "max_tokens": 800,
                            },
                            timeout=30,
                        )
                        analysis = resp.json()["choices"][0]["message"]["content"].strip()
                        st.markdown(f"### 🤖 AI诊断结果\n\n{analysis}")
                    except Exception as e:
                        st.error(f"AI分析失败: {e}")
        else:
            st.error(f"无法获取 {stock_code} 的数据，请检查代码是否正确")


# ═══════════════════════════════════════════════
# 页面5: AI策略学习
# ═══════════════════════════════════════════════
elif page == "🤖 AI策略学习":
    st.markdown('<div class="page-title">🤖 AI策略学习</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">AI自动搜索、学习、优化量化策略</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🌐 搜索策略", "🧠 AI生成", "⚡ 优化策略", "📚 策略库"])

    with tab1:
        st.markdown("### 从GitHub学习策略")
        st.caption("自动抓取GitHub开源量化项目，提取可用的策略代码")

        if st.button("🔍 开始搜索GitHub策略", type="primary", use_container_width=True):
            with st.spinner("正在搜索GitHub..."):
                new_strategies = brain.learner.learn_from_github()
                if new_strategies:
                    st.success(f"✅ 学习完成！新发现 {len(new_strategies)} 个策略")
                    for s in new_strategies:
                        st.markdown(f"""
                        <div class="signal-card">
                            <div style="font-weight:600;color:#f8fafc;">{s.name}</div>
                            <div style="color:#64748b;font-size:12px;margin-top:4px;">
                                来源: {s.source} | 分类: {s.category} | 评分: {s.quality_score:.0f}
                            </div>
                            <div style="color:#94a3b8;font-size:12px;margin-top:4px;">{s.description[:150]}</div>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.info("未发现新策略（可能已全部学习过，或GitHub API受限）")

    with tab2:
        st.markdown("### AI生成新策略")
        st.caption("让GLM大模型为你创造全新的量化策略")

        preset_prompts = [
            "生成一个适合A股震荡市的量化策略",
            "生成一个基于量价关系的突破策略",
            "生成一个低回撤的防守型策略",
            "生成一个多因子选股策略(技术指标版)",
            "生成一个基于支撑压力位的策略",
        ]
        prompt = st.selectbox("选择生成方向", preset_prompts)
        custom_prompt = st.text_input("或输入自定义需求", placeholder="如: 结合RSI和布林带的中线策略")

        if st.button("🧠 AI生成策略", type="primary", use_container_width=True):
            final_prompt = custom_prompt if custom_prompt else prompt
            with st.spinner("GLM正在生成策略..."):
                result = brain.learner.learn_from_ai(final_prompt)
                if result:
                    st.success(f"✅ 策略「{result.name}」已生成并加入策略库！")
                    st.code(result.code, language="python")
                else:
                    st.error("AI生成失败，请重试")

    with tab3:
        st.markdown("### AI优化策略")
        st.caption("选择已有策略，让AI根据实盘/回测表现进行优化")

        if brain.learner.knowledge_base:
            strategy_names = [kb.name for kb in brain.learner.knowledge_base]
            selected = st.selectbox("选择策略", strategy_names)

            if selected:
                kb = next(kb for kb in brain.learner.knowledge_base if kb.name == selected)
                st.markdown(f"**当前策略**: {kb.name}")
                st.markdown(f"评分: {kb.quality_score:.0f} | 来源: {kb.source} | 实盘交易: {kb.real_trade_count}次")

                if st.button("⚡ 让AI优化这个策略", type="primary", use_container_width=True):
                    with st.spinner("AI优化中..."):
                        result = brain.learner.optimize_strategy(selected)
                        if result:
                            st.success("✅ 策略已优化！")
                            st.code(result.code, language="python")
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
# 页面6: 策略回测
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

        if st.button("▶️ 运行回测", type="primary", use_container_width=True):
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

    with tab_strategy:
        st.markdown("### 内置策略快速回测")
        strategies = brain.signal_gen.STRATEGIES
        for name, info in strategies.items():
            with st.expander(f"📊 {info['name']} — {info['desc']}"):
                if st.button(f"回测 {info['name']}", key=f"bt_{name}"):
                    st.info("该策略已集成到信号系统中，在「每日扫描」页面直接使用")


# ═══════════════════════════════════════════════
# 页面7: 设置
# ═══════════════════════════════════════════════
elif page == "⚙️ 设置":
    st.markdown('<div class="page-title">⚙️ 设置</div>', unsafe_allow_html=True)

    tab_set1, tab_set2, tab_set3 = st.tabs(["基本设置", "数据源", "公网访问"])

    with tab_set1:
        st.markdown("### 资金设置")
        new_cash = st.number_input("初始资金", min_value=10000, max_value=10000000,
                                    value=brain.portfolio.initial_cash, step=10000)
        if st.button("保存"):
            brain.portfolio.initial_cash = new_cash
            brain.portfolio._save_data()
            st.success("已保存")

        st.markdown("---")
        st.markdown("### 清除数据")
        if st.button("🗑️ 清除所有持仓和信号", type="secondary"):
            brain.portfolio.positions.clear()
            brain.portfolio.signals.clear()
            brain.portfolio._save_data()
            st.success("已清除")
            st.rerun()

    with tab_set2:
        st.markdown("### 当前数据源")
        st.info("当前使用 **BaoStock**（免费，无需API Key）")

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
        st.markdown("### 公网访问配置")
        st.info("通过内网穿透工具将本机Streamlit服务暴露到公网")

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
        if st.button("📋 复制地址"):
            st.toast("地址已复制（模拟）")
