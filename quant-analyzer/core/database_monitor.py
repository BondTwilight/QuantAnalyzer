"""
数据库性能监控模块
实时监控数据库查询性能，提供优化建议
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any

from .database_optimizer import get_database_optimizer


class DatabaseMonitor:
    """数据库性能监控器"""
    
    def __init__(self):
        self.optimizer = get_database_optimizer()
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """获取性能仪表板数据"""
        report = self.optimizer.get_query_performance_report()
        
        # 计算性能指标
        metrics = {
            "total_queries": report.get("total_queries", 0),
            "cache_hit_rate": report.get("cache_hit_rate", 0),
            "avg_execution_time": report.get("avg_execution_time", 0),
            "slow_queries_count": len(report.get("slow_queries", [])),
            "query_types": report.get("query_types", {})
        }
        
        return {
            "metrics": metrics,
            "slow_queries": report.get("slow_queries", []),
            "recommendations": report.get("recommendations", [])
        }
    
    def get_table_statistics(self) -> pd.DataFrame:
        """获取表统计信息"""
        optimizer = self.optimizer
        conn = optimizer.get_connection()
        
        tables = ["backtest_results", "daily_values", "trade_records", "ai_reports", "strategy_params"]
        stats = []
        
        for table in tables:
            try:
                # 获取行数
                count_result = optimizer.execute_query(f"SELECT COUNT(*) as count FROM {table}", use_cache=False)
                row_count = count_result[0]['count'] if count_result else 0
                
                # 获取表大小（近似）
                size_result = optimizer.execute_query(
                    f"SELECT SUM(pgsize) as size FROM dbstat WHERE name = ?", 
                    (table,), use_cache=False
                )
                table_size = size_result[0]['size'] if size_result else 0
                
                # 获取索引信息
                index_result = optimizer.execute_query(
                    f"SELECT COUNT(*) as index_count FROM sqlite_master WHERE type = 'index' AND tbl_name = ?",
                    (table,), use_cache=False
                )
                index_count = index_result[0]['index_count'] if index_result else 0
                
                stats.append({
                    "表名": table,
                    "行数": row_count,
                    "大小(KB)": round(table_size / 1024, 2) if table_size else 0,
                    "索引数": index_count,
                    "状态": "正常" if row_count > 0 else "空表"
                })
            except Exception as e:
                stats.append({
                    "表名": table,
                    "行数": 0,
                    "大小(KB)": 0,
                    "索引数": 0,
                    "状态": f"错误: {str(e)[:50]}"
                })
        
        return pd.DataFrame(stats)
    
    def get_query_trend(self, hours: int = 24) -> pd.DataFrame:
        """获取查询趋势数据"""
        optimizer = self.optimizer
        
        # 模拟查询趋势数据（实际应用中可以从日志或监控系统获取）
        now = datetime.now()
        trend_data = []
        
        for i in range(hours):
            hour_time = now - timedelta(hours=i)
            
            # 模拟不同类型查询的数量
            trend_data.append({
                "时间": hour_time.strftime("%H:%M"),
                "SELECT查询": max(0, 50 + i * 2),
                "INSERT查询": max(0, 10 + i),
                "UPDATE查询": max(0, 5 + i // 2),
                "缓存命中率": min(0.9, 0.6 + i * 0.01),
                "平均响应时间(ms)": max(10, 50 - i * 1.5)
            })
        
        return pd.DataFrame(trend_data[::-1])  # 反转，使时间从旧到新
    
    def optimize_database(self) -> Dict[str, Any]:
        """优化数据库"""
        results = {}
        
        try:
            # 优化表
            tables = ["backtest_results", "daily_values", "trade_records", "ai_reports", "strategy_params"]
            for table in tables:
                try:
                    self.optimizer.optimize_table(table)
                    results[table] = "优化成功"
                except Exception as e:
                    results[table] = f"优化失败: {str(e)}"
            
            # 清理缓存
            self.optimizer.query_cache.clear()
            results["缓存"] = "已清理"
            
            # 重新创建索引
            self.optimizer._create_indexes()
            results["索引"] = "已重建"
            
        except Exception as e:
            results["错误"] = str(e)
        
        return results


def create_database_performance_page():
    """创建数据库性能监控页面"""
    st.title("📊 数据库性能监控")
    
    monitor = DatabaseMonitor()
    
    # 性能概览
    st.header("性能概览")
    
    dashboard = monitor.get_performance_dashboard()
    metrics = dashboard["metrics"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总查询数", f"{metrics['total_queries']:,}")
    
    with col2:
        st.metric("缓存命中率", f"{metrics['cache_hit_rate']:.1%}")
    
    with col3:
        st.metric("平均响应时间", f"{metrics['avg_execution_time']*1000:.1f}ms")
    
    with col4:
        st.metric("慢查询数", metrics['slow_queries_count'])
    
    # 查询类型分布
    st.subheader("查询类型分布")
    if metrics['query_types']:
        query_types_df = pd.DataFrame(
            list(metrics['query_types'].items()),
            columns=["查询类型", "数量"]
        )
        fig = go.Figure(data=[go.Pie(
            labels=query_types_df["查询类型"],
            values=query_types_df["数量"],
            hole=.3
        )])
        fig.update_layout(title="查询类型分布")
        st.plotly_chart(fig, use_container_width=True)
    
    # 表统计信息
    st.subheader("表统计信息")
    table_stats = monitor.get_table_statistics()
    st.dataframe(table_stats, use_container_width=True)
    
    # 查询趋势
    st.subheader("查询趋势（最近24小时）")
    query_trend = monitor.get_query_trend()
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("查询数量趋势", "性能指标趋势"),
        vertical_spacing=0.15
    )
    
    # 查询数量趋势
    fig.add_trace(
        go.Scatter(
            x=query_trend["时间"],
            y=query_trend["SELECT查询"],
            name="SELECT查询",
            line=dict(color="#636efa")
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=query_trend["时间"],
            y=query_trend["INSERT查询"],
            name="INSERT查询",
            line=dict(color="#ef553b")
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=query_trend["时间"],
            y=query_trend["UPDATE查询"],
            name="UPDATE查询",
            line=dict(color="#00cc96")
        ),
        row=1, col=1
    )
    
    # 性能指标趋势
    fig.add_trace(
        go.Scatter(
            x=query_trend["时间"],
            y=query_trend["缓存命中率"],
            name="缓存命中率",
            line=dict(color="#ab63fa"),
            yaxis="y2"
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=query_trend["时间"],
            y=query_trend["平均响应时间(ms)"],
            name="平均响应时间(ms)",
            line=dict(color="#ffa15a"),
            yaxis="y3"
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=600,
        showlegend=True,
        xaxis2=dict(title="时间"),
        yaxis=dict(title="查询数量"),
        yaxis2=dict(title="缓存命中率", overlaying="y", side="right"),
        yaxis3=dict(title="响应时间(ms)", overlaying="y", side="left", position=0.15)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 慢查询分析
    if dashboard["slow_queries"]:
        st.subheader("慢查询分析")
        slow_queries_df = pd.DataFrame(dashboard["slow_queries"])
        st.dataframe(slow_queries_df, use_container_width=True)
    
    # 优化建议
    if dashboard["recommendations"]:
        st.subheader("优化建议")
        for i, rec in enumerate(dashboard["recommendations"], 1):
            st.info(f"{i}. {rec}")
    
    # 数据库优化工具
    st.header("数据库优化工具")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 优化数据库", use_container_width=True):
            with st.spinner("正在优化数据库..."):
                results = monitor.optimize_database()
                st.success("数据库优化完成！")
                
                for table, result in results.items():
                    st.write(f"**{table}**: {result}")
    
    with col2:
        if st.button("📊 刷新性能数据", use_container_width=True):
            st.rerun()
    
    # 数据库连接信息
    st.subheader("数据库连接信息")
    
    conn_info = {
        "数据库路径": str(monitor.optimizer.db_path),
        "最大缓存大小": monitor.optimizer.max_cache_size,
        "当前缓存条目": len(monitor.optimizer.query_cache),
        "活跃连接数": len(monitor.optimizer.connection_pool),
        "查询统计记录数": len(monitor.optimizer.query_stats)
    }
    
    for key, value in conn_info.items():
        st.write(f"**{key}**: {value}")


if __name__ == "__main__":
    create_database_performance_page()