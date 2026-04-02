"""
首页仪表盘 - QuantAnalyzer v3.1
第一眼就能看到：今日抓取策略 + 今日因子 + 粘贴策略回测
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

# ═══════════════════════════════════════════
# 因子库定义（10个核心因子）
# ═══════════════════════════════════════════

FACTOR_LIBRARY = {
    "市值因子": {
        "icon": "📊", "desc": "总市值、自由流通市值", "tag": "alpha",
        "color": "#3b82f6", "formula": "market_cap = price × total_shares"
    },
    "价值因子": {
        "icon": "💰", "desc": "PE、PB、PS、PCF", "tag": "value",
        "color": "#10b981", "formula": "PE = price / eps; PB = price / book_per_share"
    },
    "动量因子": {
        "icon": "🚀", "desc": "20/60/120日动量、RSI", "tag": "momentum",
        "color": "#f59e0b", "formula": "momentum = price_t / price_t-n - 1"
    },
    "反转因子": {
        "icon": "🔄", "desc": "短期反转、跳空反转", "tag": "reversal",
        "color": "#8b5cf6", "formula": "reversal = -momentum(short_period)"
    },
    "波动率因子": {
        "icon": "📈", "desc": "历史波动率、IV、ATR", "tag": "volatility",
        "color": "#ef4444", "formula": "vol = std(returns) × sqrt(252)"
    },
    "质量因子": {
        "icon": "🏆", "desc": "ROE、ROA、毛利率、资产负债率", "tag": "quality",
        "color": "#06b6d4", "formula": "ROE = net_income / equity"
    },
    "成长因子": {
        "icon": "📈", "desc": "营收增速、利润增速、EPS增长", "tag": "growth",
        "color": "#ec4899", "formula": "growth = (eps_t / eps_t-1) - 1"
    },
    "流动性因子": {
        "icon": "💧", "desc": "日均成交额、换手率、成交额占比", "tag": "liquidity",
        "color": "#14b8a6", "formula": "liquidity = turnover_rate / avg_turnover"
    },
    "北向资金": {
        "icon": "🌊", "desc": "沪深港通北向资金流向、持仓变化", "tag": "moneyflow",
        "color": "#0ea5e9", "formula": "north_flow = hk_sh_holdings + hk_sz_holdings"
    },
    "龙虎榜": {
        "icon": "🐉", "desc": "营业部游资席位、机构席位、溢价率", "tag": "toplist",
        "color": "#f97316", "formula": "inst_pct = inst_buy / total_buy"
    },
}


def get_today_strategies() -> List[Dict]:
    """获取今日策略列表（优先从缓存读取）"""
    import json
    from pathlib import Path

    cache_file = Path(__file__).parent.parent / "data" / "crawled_strategies.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("strategies", [])
        except Exception:
            pass

    # 默认预置策略（当无缓存时显示）
    return [
        {
            "name": "双均线交叉策略", "name_cn": "MA Cross",
            "category": "趋势", "source": "预置",
            "stars": 999, "framework": "backtrader",
            "backtest_ready": True,
            "description": "经典均线交叉趋势策略，快线穿慢线买/卖"
        },
        {
            "name": "MACD策略", "name_cn": "MACD Signal",
            "category": "趋势", "source": "预置",
            "stars": 888, "framework": "backtrader",
            "backtest_ready": True,
            "description": "MACD金叉死叉信号驱动交易"
        },
        {
            "name": "布林带均值回归", "name_cn": "Bollinger Reversion",
            "category": "均值回归", "source": "预置",
            "stars": 666, "framework": "backtrader",
            "backtest_ready": True,
            "description": "价格触及布林带上下轨时反向交易"
        },
        {
            "name": "RSI超买超卖", "name_cn": "RSI Oscillation",
            "category": "震荡", "source": "预置",
            "stars": 555, "framework": "backtrader",
            "backtest_ready": True,
            "description": "RSI低于30买入、高于70卖出"
        },
        {
            "name": "小市值价值策略", "name_cn": "Small Cap Value",
            "category": "多因子", "source": "预置",
            "stars": 777, "framework": "backtrader",
            "backtest_ready": True,
            "description": "选取市值小+ROE高的价值成长股"
        },
        {
            "name": "北向资金驱动", "name_cn": "North Money Flow",
            "category": "资金流", "source": "预置",
            "stars": 444, "framework": "backtrader",
            "backtest_ready": True,
            "description": "跟随北向资金增持信号择时"
        },
    ]


def render_home_page():
    """渲染首页仪表盘"""
    st.markdown("""
    <style>
    /* ── 首页卡片动画 ── */
    .metric-card {
        background: linear-gradient(135deg, #1a2235 0%, #0f1624 100%);
        border: 1px solid #1e2d40;
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        border-color: #3b82f6;
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(59,130,246,0.15);
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
    }
    .metric-number {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #6b7a90;
        margin-top: 4px;
        font-weight: 500;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 24px 0 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-title::before {
        content: '';
        width: 4px;
        height: 20px;
        background: linear-gradient(180deg, #3b82f6, #8b5cf6);
        border-radius: 2px;
    }
    .strategy-card {
        background: linear-gradient(135deg, #131c2e 0%, #0a1120 100%);
        border: 1px solid #1a2744;
        border-radius: 12px;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 16px;
        transition: all 0.2s ease;
        margin-bottom: 8px;
    }
    .strategy-card:hover {
        border-color: #3b82f6;
        background: linear-gradient(135deg, #1a2744 0%, #0f1830 100%);
    }
    .strategy-icon {
        width: 40px; height: 40px;
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem;
        flex-shrink: 0;
    }
    .strategy-info { flex: 1; min-width: 0; }
    .strategy-name {
        font-weight: 600;
        color: #e2e8f0;
        font-size: 0.95rem;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .strategy-meta {
        font-size: 0.78rem;
        color: #4a5568;
        margin-top: 2px;
    }
    .strategy-tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
        background: rgba(59,130,246,0.15);
        color: #60a5fa;
        margin-right: 4px;
    }
    .tag-ready {
        background: rgba(16,185,129,0.15);
        color: #34d399;
    }
    .tag-unready {
        background: rgba(239,68,68,0.15);
        color: #f87171;
    }
    .factor-chip {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 4px 6px 4px 0;
        cursor: pointer;
        transition: all 0.2s;
        border: 1px solid transparent;
    }
    .factor-chip:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .paste-box {
        background: #0d1117;
        border: 2px dashed #1e3a5f;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        color: #4a5568;
        font-size: 0.9rem;
        transition: all 0.2s;
    }
    .paste-box:hover, .paste-box:focus-within {
        border-color: #3b82f6;
        background: #0d1320;
    }
    .stCodeBlock { border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════
    # 顶部：标题栏
    # ═══════════════════════════════════════════
    col_t, col_s = st.columns([1, 1])
    with col_t:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="font-size:1.8rem;">🤖</div>
            <div>
                <div style="font-size:1.3rem;font-weight:800;color:#e2e8f0;">QuantAnalyzer</div>
                <div style="font-size:0.75rem;color:#4a5568;">v3.1 · 量化策略PK竞技场</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_s:
        st.markdown(f"""
        <div style="text-align:right;color:#4a5568;font-size:0.78rem;">
            🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ═══════════════════════════════════════════
    # 第一行：核心指标卡片
    # ═══════════════════════════════════════════
    strategies = get_today_strategies()
    cached_strategies = len(strategies)
    live_strategies = cached_strategies if cached_strategies > 0 else 6
    total_factors = len(FACTOR_LIBRARY)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{live_strategies}</div>
            <div class="metric-label">可用策略</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{total_factors}</div>
            <div class="metric-label">核心因子</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        ready = sum(1 for s in strategies if s.get("backtest_ready", False))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{ready}</div>
            <div class="metric-label">可回测</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        sources = len(set(s.get("source", "") for s in strategies if s.get("source")))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{sources}</div>
            <div class="metric-label">来源平台</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ═══════════════════════════════════════════
    # 第二行：今日因子库
    # ═══════════════════════════════════════════
    st.markdown('<div class="section-title">📋 今日因子库（10个核心量化因子）</div>', unsafe_allow_html=True)

    # 按行显示因子芯片
    factor_rows = [
        list(FACTOR_LIBRARY.items())[:5],
        list(FACTOR_LIBRARY.items())[5:],
    ]
    for row in factor_rows:
        cols = st.columns(5)
        for col, (fname, fdata) in zip(cols, row):
            with col:
                st.markdown(f"""
                <div class="factor-chip" style="border-color:{fdata['color']}40;background:{fdata['color']}10;color:{fdata['color']};">
                    <span>{fdata['icon']}</span>
                    <span>{fname}</span>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("")

    # ═══════════════════════════════════════════
    # 第三行：策略卡片列表
    # ═══════════════════════════════════════════
    st.markdown('<div class="section-title">📡 今日策略库（可直接回测）</div>', unsafe_allow_html=True)

    # 策略分类颜色
    cat_colors = {
        "趋势": "#3b82f6", "均值回归": "#10b981",
        "震荡": "#8b5cf6", "多因子": "#f59e0b",
        "资金流": "#0ea5e9", "其他": "#6b7280"
    }

    # 分两列显示策略卡片
    half = (len(strategies) + 1) // 2
    left_strategies = strategies[:half]
    right_strategies = strategies[half:]

    left_col, right_col = st.columns(2)
    with left_col:
        for s in left_strategies:
            color = cat_colors.get(s.get("category", "其他"), cat_colors["其他"])
            ready = s.get("backtest_ready", False)
            tag_cls = "tag-ready" if ready else "tag-unready"
            tag_txt = "✅可回测" if ready else "⚠️需适配"
            st.markdown(f"""
            <div class="strategy-card">
                <div class="strategy-icon" style="background:{color}20;color:{color};">
                    {"📈" if s.get("category")=="趋势" else "📊" if "多因子" in s.get("category","") else "💰" if "资金" in s.get("category","") else "📉"}
                </div>
                <div class="strategy-info">
                    <div class="strategy-name">{s.get('name','')}</div>
                    <div class="strategy-meta">
                        <span class="strategy-tag" style="background:{color}20;color:{color};">{s.get('category','')}</span>
                        <span class="strategy-tag {tag_cls}">{tag_txt}</span>
                        ⭐{s.get('stars',0)}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with right_col:
        for s in right_strategies:
            color = cat_colors.get(s.get("category", "其他"), cat_colors["其他"])
            ready = s.get("backtest_ready", False)
            tag_cls = "tag-ready" if ready else "tag-unready"
            tag_txt = "✅可回测" if ready else "⚠️需适配"
            st.markdown(f"""
            <div class="strategy-card">
                <div class="strategy-icon" style="background:{color}20;color:{color};">
                    {"📈" if s.get("category")=="趋势" else "📊" if "多因子" in s.get("category","") else "💰" if "资金" in s.get("category","") else "📉"}
                </div>
                <div class="strategy-info">
                    <div class="strategy-name">{s.get('name','')}</div>
                    <div class="strategy-meta">
                        <span class="strategy-tag" style="background:{color}20;color:{color};">{s.get('category','')}</span>
                        <span class="strategy-tag {tag_cls}">{tag_txt}</span>
                        ⭐{s.get('stars',0)}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    # ═══════════════════════════════════════════
    # 第四行：⚡快速回测（核心入口）
    # ═══════════════════════════════════════════
    st.markdown('<div class="section-title">⚡ 快速回测（粘贴策略直接跑）</div>', unsafe_allow_html=True)

    # 预置示例策略
    EXAMPLE_CODE = '''import backtrader as bt

classMAStrategy(bt.Strategy):
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

    # 粘贴区 + 参数区 横向并排
    paste_col, param_col = st.columns([2, 1])

    with paste_col:
        st.markdown("**📋 粘贴你的策略代码（支持Backtrader）**")
        user_code = st.text_area(
            "粘贴策略代码",
            value="",
            placeholder="import backtrader as bt\n\nclass MyStrategy(bt.Strategy):\n    def __init__(self):\n        self.sma = bt.indicators.SMA(self.data.close, period=20)\n\n    def next(self):\n        if self.data.close > self.sma:\n            self.buy()\n        elif self.data.close < self.sma:\n            self.sell()",
            height=280,
            label_visibility="collapsed",
            key="home_code"
        )

        if st.button("🚀 **立即回测这个策略**", type="primary", use_container_width=True):
            if user_code.strip():
                st.session_state["home_backtest_code"] = user_code
                st.session_state["page_navigate"] = "🔬 回测结果"
                st.rerun()
            else:
                st.warning("请先粘贴策略代码")

        if st.button("📋 **加载双均线示例策略**", use_container_width=True):
            st.session_state["home_code"] = EXAMPLE_CODE
            st.rerun()

    with param_col:
        st.markdown("**⚙️ 回测参数**")
        default_stock = st.selectbox(
            "回测标的",
            [
                ("000001.SZ", "平安银行"),
                ("000002.SZ", "万科A"),
                ("600000.SH", "浦发银行"),
                ("600519.SH", "贵州茅台"),
                ("000858.SZ", "五粮液"),
                ("601318.SH", "中国平安"),
                ("000300.SH", "沪深300"),
            ],
            key="home_stock"
        )

        start_date = st.date_input(
            "开始日期",
            value=datetime(2023, 1, 1),
            key="home_start"
        )
        end_date = st.date_input(
            "结束日期",
            value=datetime(2024, 12, 31),
            key="home_end"
        )
        cash = st.number_input(
            "初始资金",
            value=100000,
            step=10000,
            key="home_cash"
        )
        st.markdown(f"""
        <div style="background:#1a2235;border-radius:10px;padding:12px;margin-top:8px;">
            <div style="color:#6b7a90;font-size:0.78rem;margin-bottom:4px;">回测周期</div>
            <div style="color:#e2e8f0;font-size:0.85rem;font-weight:600;">
                {(end_date - start_date).days} 天
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ═══════════════════════════════════════════
    # 第五行：策略PK入口
    # ═══════════════════════════════════════════
    st.markdown('<div class="section-title">⚔️ 策略PK竞技场（多个策略对比）</div>', unsafe_allow_html=True)

    pk_col1, pk_col2 = st.columns(2)

    with pk_col1:
        st.markdown("""
        <div class="paste-box">
            <div style="font-size:2rem;margin-bottom:8px;">📋</div>
            <div style="font-weight:600;color:#e2e8f0;margin-bottom:4px;">粘贴多个策略</div>
            <div>复制别人的策略代码，粘贴到这里</div>
            <div style="margin-top:8px;font-size:0.78rem;">最多同时粘贴 <b>5个</b> 策略代码</div>
        </div>
        """, unsafe_allow_html=True)
        st.info("👆 前往「⚔️ 策略PK」页面粘贴多个策略，一键对比回测结果")

    with pk_col2:
        st.markdown("""
        <div class="paste-box">
            <div style="font-size:2rem;margin-bottom:8px;">📡</div>
            <div style="font-weight:600;color:#e2e8f0;margin-bottom:4px;">抓取最新策略</div>
            <div>从GitHub和量化社区自动获取</div>
            <div style="margin-top:8px;font-size:0.78rem;">包含 <b>10个因子</b> + <b>多个策略</b></div>
        </div>
        """, unsafe_allow_html=True)
        st.info("👆 前往「📚 策略库」查看所有抓取的内置策略")

    st.markdown("")

    # ═══════════════════════════════════════════
    # 底部：快速导航
    # ═══════════════════════════════════════════
    st.markdown("---")
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
    nav_items = [
        ("📊 策略总览", "📊 策略总览", "查看所有策略回测结果"),
        ("📚 策略库", "📚 策略库", "20+预置策略直接回测"),
        ("📉 K线分析", "📉 K线分析", "查看股票K线和指标"),
        ("🤖 AI分析", "🤖 AI分析", "AI协同分析策略优劣"),
    ]
    for col, (label, page, desc) in zip([nav_col1, nav_col2, nav_col3, nav_col4], nav_items):
        with col:
            if st.button(f"{label}\n\n{desc}", use_container_width=True, key=f"nav_{label}"):
                st.session_state["page_navigate"] = page
                st.rerun()


# ═══════════════════════════════════════════
# 快速回测结果页面
# ═══════════════════════════════════════════

def render_quick_backtest_result():
    """快速回测结果展示"""
    st.markdown("""
    <style>
    .result-card {
        background: linear-gradient(135deg, #1a2235, #0f1624);
        border: 1px solid #1e2d40;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 🔬 快速回测结果")

    code = st.session_state.get("home_backtest_code", "")
    stock = st.session_state.get("home_stock", ("000001.SZ", "平安银行"))
    start = st.session_state.get("home_start", datetime(2023, 1, 1))
    end = st.session_state.get("home_end", datetime(2024, 12, 31))
    cash = st.session_state.get("home_cash", 100000)

    if not code:
        st.warning("没有找到回测代码，请先在首页粘贴策略")
        if st.button("← 返回首页"):
            st.session_state["page_navigate"] = "🏠 首页"
            st.rerun()
        return

    with st.spinner("正在回测策略，请稍候..."):
        from core.strategy_arena import safe_backtest_strategy
        success, results, equity_df = safe_backtest_strategy(
            code=code,
            stock=stock[0] if isinstance(stock, tuple) else stock,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            initial_cash=float(cash),
        )

    if success:
        # 核心指标
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            color = "#10b981" if results["total_return"] >= 0 else "#ef4444"
            st.markdown(f"""
            <div class="result-card">
                <div style="color:#6b7a90;font-size:0.8rem;">累计收益率</div>
                <div style="font-size:2rem;font-weight:800;color:{color};">
                    {results['total_return']:.2f}%
                </div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="result-card">
                <div style="color:#6b7a90;font-size:0.8rem;">夏普比率</div>
                <div style="font-size:2rem;font-weight:800;color:#60a5fa;">
                    {results['sharpe']:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="result-card">
                <div style="color:#6b7a90;font-size:0.8rem;">最大回撤</div>
                <div style="font-size:2rem;font-weight:800;color:#f87171;">
                    -{results['max_drawdown']:.2f}%
                </div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="result-card">
                <div style="color:#6b7a90;font-size:0.8rem;">交易次数</div>
                <div style="font-size:2rem;font-weight:800;color:#a78bfa;">
                    {results['total_trades']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 收益曲线
        if equity_df is not None and not equity_df.empty:
            st.markdown("#### 📈 收益曲线")
            fig = plot_equity_curve(equity_df, results["total_return"])
            st.plotly_chart(fig, use_container_width=True)

        # 策略信息
        st.markdown(f"""
        <div class="result-card">
            <div style="color:#6b7a90;font-size:0.8rem;margin-bottom:8px;">策略名称</div>
            <div style="color:#e2e8f0;font-size:1.1rem;font-weight:700;">{results['strategy_name']}</div>
            <div style="color:#4a5568;font-size:0.82rem;margin-top:4px;">
                年化收益 {results['annual_return']:.2f}% · 胜率 {results['win_rate']:.1f}% ·
                最终资金 ¥{results['final_value']:,.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error(f"回测失败: {results.get('error', '未知错误')}")

    if st.button("← 返回首页继续回测"):
        st.session_state["page_navigate"] = "🏠 首页"
        st.rerun()


def plot_equity_curve(equity_df: pd.DataFrame, total_return: float):
    """绘制收益曲线"""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=("", "日收益"),
    )

    # 收益曲线
    fig.add_trace(go.Scatter(
        x=equity_df.index,
        y=equity_df["value"] if "value" in equity_df.columns else equity_df.iloc[:, 0],
        mode="lines",
        line=dict(color="#3b82f6", width=2),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.1)",
        name="策略收益",
    ), row=1, col=1)

    # 基准线
    if "benchmark" in equity_df.columns:
        fig.add_trace(go.Scatter(
            x=equity_df.index,
            y=equity_df["benchmark"],
            mode="lines",
            line=dict(color="#6b7280", width=1.5, dash="dot"),
            name="沪深300",
        ), row=1, col=1)

    # 日收益
    if len(equity_df) > 1:
        values = equity_df["value"] if "value" in equity_df.columns else equity_df.iloc[:, 0]
        daily_returns = values.pct_change().fillna(0) * 100
        colors = ["#10b981" if r >= 0 else "#ef4444" for r in daily_returns]
        fig.add_trace(go.Bar(
            x=equity_df.index,
            y=daily_returns,
            marker_color=colors,
            name="日收益%",
        ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=40, b=40),
        height=400,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#1e2d40")
    fig.update_yaxes(showgrid=True, gridcolor="#1e2d40")
    return fig
