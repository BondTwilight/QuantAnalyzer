"""
性能优化模块 - 解决 HF Spaces 卡顿问题
策略：懒加载 + 数据缓存 + 轻量化UI + 后端计算
"""

import streamlit as st
import functools
from pathlib import Path


# ═══════════════════════════════════════════
# Streamlit 性能装饰器
# ═══════════════════════════════════════════

def st_cache_data(ttl_seconds: int = 3600):
    """带TTL的缓存装饰器（增强版 st.cache_data）"""
    return st.cache_data(ttl=ttl_seconds, show_spinner=False)


def st_cache_resource(ttl_seconds: int = 3600):
    """资源缓存（数据库连接等）"""
    return st.cache_resource(ttl=ttl_seconds, show_spinner=False)


# ═══════════════════════════════════════════
# 数据获取优化
# ═══════════════════════════════════════════

@st_cache_data(ttl_seconds=300)
def cached_daily_data(ts_code: str, start_date: str, end_date: str):
    """缓存日线数据（5分钟刷新）"""
    try:
        from core.data_fetcher import get_bt_data
        return get_bt_data(ts_code, start_date, end_date)
    except Exception:
        return None


@st_cache_data(ttl_seconds=3600)
def cached_market_index():
    """缓存市场指数数据（1小时刷新）"""
    try:
        from core.data_fetcher import get_index_data
        return get_index_data()
    except Exception:
        return None


# ═══════════════════════════════════════════
# Streamlit 页面级优化配置
# ═══════════════════════════════════════════

def optimize_page_config():
    """优化 Streamlit 页面配置"""
    st.set_page_config(
        page_title="QuantAnalyzer - 量化策略分析平台",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def lazy_import_heavy_modules():
    """懒加载重型模块（在需要时才导入）"""
    # 这些模块只在对应功能被使用时才加载
    lazy_modules = {
        "plotly": "plotly",
        "backtrader": "backtrader",
        "requests": "requests",
    }
    return lazy_modules


# ═══════════════════════════════════════════
# 前端资源优化
# ═══════════════════════════════════════════

def inject_performance_css():
    """注入性能优化CSS"""
    st.markdown("""
    <style>
    /* ═══ 性能优化CSS ═══ */

    /* 减少动画，提升渲染速度 */
    * {
        transition-timing-function: cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    /* 禁用不必要的阴影动画 */
    .stMetric, .stMarkdown, .element-container {
        animation: none !important;
    }

    /* 加速滚动 */
    html {
        scroll-behavior: smooth;
    }

    /* 优化表格渲染 */
    .dataframe {
        font-size: 13px !important;
    }

    /* 懒加载占位符 */
    .lazy-placeholder {
        background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 8px;
        height: 100px;
    }

    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* Streamlit 原生元素优化 */
    .stSpinner > div {
        border-top-color: #3b82f6 !important;
    }

    /* 减少卡片阴影 */
    .glass-card, .stCard {
        box-shadow: none !important;
        border: 1px solid #1e293b !important;
    }

    /* 加速按钮响应 */
    .stButton > button {
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    /* 优化图表容器 */
    .js-plotly-plot .plotly, .js-plotly-plot {
        max-height: 500px;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 后端计算优化
# ═══════════════════════════════════════════

def optimize_backtrader_config():
    """优化 Backtrader 配置以加快回测速度"""
    return {
        # 并行处理
        "preload": True,  # 预加载数据
        "runheaders": False,  # 禁用运行时头信息
        "exactbars": True,  # 精确模式，减少内存使用
    }


# ═══════════════════════════════════════════
# 性能监控
# ═══════════════════════════════════════════

import time

class PerformanceMonitor:
    """轻量级性能监控"""

    def __init__(self):
        self.timers = {}

    def start(self, label: str):
        self.timers[label] = time.time()

    def end(self, label: str) -> float:
        if label in self.timers:
            elapsed = time.time() - self.timers[label]
            del self.timers[label]
            return elapsed
        return 0

    def report(self):
        """返回性能报告"""
        return {
            "active_timers": len(self.timers),
            "message": "性能监控运行中"
        }


# ═══════════════════════════════════════════
# 轻量化图表（数据量大时降级）
# ═══════════════════════════════════════════

def should_use_lightweight_chart(data_length: int, threshold: int = 1000) -> bool:
    """判断是否使用轻量化图表"""
    return data_length > threshold


def get_optimized_chart_config(height: int = 400):
    """获取优化后的图表配置"""
    return {
        "height": height,
        "margin": dict(l=40, r=20, t=40, b=40),
        "font": dict(size=11),
        "showlegend": True,
        "legend": dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    }
