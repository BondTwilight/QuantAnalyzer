"""
🔧 按钮响应修复工具
解决Streamlit按钮无响应问题
"""

import streamlit as st
import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class ButtonResponseFixer:
    """
    按钮响应修复器
    解决常见按钮无响应问题：
    1. 回调函数错误
    2. 状态管理问题
    3. 异步操作阻塞
    4. 缺少错误处理
    """
    
    @staticmethod
    def safe_button(label: str, key: str = None, 
                   on_click: Callable = None, args: tuple = None, 
                   kwargs: dict = None, **button_kwargs) -> bool:
        """
        安全的按钮包装器
        
        Args:
            label: 按钮标签
            key: 按钮唯一键
            on_click: 点击回调函数
            args: 回调函数参数
            kwargs: 回调函数关键字参数
            **button_kwargs: 其他Streamlit按钮参数
            
        Returns:
            bool: 按钮是否被点击
        """
        # 生成唯一键
        if key is None:
            key = f"btn_{hash(label) & 0xFFFFFFFF}"
        
        # 检查回调函数
        if on_click is not None:
            # 使用Streamlit的on_click参数
            return st.button(label, key=key, on_click=on_click, 
                           args=args, kwargs=kwargs, **button_kwargs)
        else:
            # 直接返回按钮状态
            return st.button(label, key=key, **button_kwargs)
    
    @staticmethod
    def with_loading(label: str, loading_text: str = "处理中...", 
                    key: str = None, **button_kwargs) -> bool:
        """
        带加载状态的按钮
        
        Args:
            label: 按钮标签
            loading_text: 加载时显示的文字
            key: 按钮唯一键
            **button_kwargs: 其他Streamlit按钮参数
            
        Returns:
            bool: 按钮是否被点击
        """
        if key is None:
            key = f"loading_btn_{hash(label) & 0xFFFFFFFF}"
        
        clicked = st.button(label, key=key, **button_kwargs)
        
        if clicked:
            with st.spinner(loading_text):
                # 设置一个状态标记，让回调函数知道正在处理
                st.session_state[f"{key}_processing"] = True
                # 短暂延迟，确保UI更新
                time.sleep(0.1)
        
        return clicked
    
    @staticmethod
    def with_retry(label: str, max_retries: int = 3, 
                  retry_delay: float = 1.0, key: str = None, **button_kwargs) -> bool:
        """
        带重试机制的按钮
        
        Args:
            label: 按钮标签
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            key: 按钮唯一键
            **button_kwargs: 其他Streamlit按钮参数
            
        Returns:
            bool: 按钮是否被点击
        """
        if key is None:
            key = f"retry_btn_{hash(label) & 0xFFFFFFFF}"
        
        clicked = st.button(label, key=key, **button_kwargs)
        
        if clicked:
            # 初始化重试状态
            if f"{key}_retry_count" not in st.session_state:
                st.session_state[f"{key}_retry_count"] = 0
                st.session_state[f"{key}_last_error"] = None
            
            retry_count = st.session_state[f"{key}_retry_count"]
            
            if retry_count < max_retries:
                try:
                    # 这里应该调用实际的回调函数
                    # 由于我们不知道回调函数，这里只是框架
                    st.session_state[f"{key}_retry_count"] = 0
                    st.session_state[f"{key}_last_error"] = None
                    return True
                except Exception as e:
                    retry_count += 1
                    st.session_state[f"{key}_retry_count"] = retry_count
                    st.session_state[f"{key}_last_error"] = str(e)
                    
                    if retry_count < max_retries:
                        st.warning(f"操作失败，{retry_delay}秒后重试 ({retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                        st.rerun()
                    else:
                        st.error(f"操作失败，已重试{max_retries}次: {e}")
            else:
                st.error(f"已达到最大重试次数: {max_retries}")
        
        return clicked
    
    @staticmethod
    def fix_common_issues():
        """
        修复常见的按钮响应问题
        """
        # 1. 确保session_state初始化
        if "button_clicks" not in st.session_state:
            st.session_state["button_clicks"] = {}
        
        # 2. 清理过期的按钮状态
        current_time = time.time()
        if "button_timestamps" not in st.session_state:
            st.session_state["button_timestamps"] = {}
        
        # 清理30秒前的按钮状态
        expired_keys = [
            k for k, ts in st.session_state["button_timestamps"].items()
            if current_time - ts > 30
        ]
        for key in expired_keys:
            if key in st.session_state["button_clicks"]:
                del st.session_state["button_clicks"][key]
            if key in st.session_state["button_timestamps"]:
                del st.session_state["button_timestamps"][key]
        
        # 3. 添加全局错误处理
        st.session_state.setdefault("last_button_error", None)
    
    @staticmethod
    def create_action_button(label: str, action_func: Callable, 
                           success_msg: str = "操作成功",
                           error_msg: str = "操作失败",
                           **button_kwargs) -> bool:
        """
        创建动作按钮，自动处理结果反馈
        
        Args:
            label: 按钮标签
            action_func: 执行函数
            success_msg: 成功消息
            error_msg: 错误消息前缀
            **button_kwargs: 按钮参数
            
        Returns:
            bool: 是否成功执行
        """
        # 避免key重复传入
        button_kwargs.pop("key", None)
        key = f"action_btn_{hash(str(action_func)) & 0xFFFFFFFF}"
        
        # 兼容不同Streamlit版本：type参数处理
        type_val = button_kwargs.pop("type", None)
        
        try:
            clicked = st.button(label, key=key, type=type_val, **button_kwargs)
        except TypeError as e:
            err_msg = str(e)
            if "type" in err_msg:
                # 新版要求type必须是primary/secondary/tertiary，默认传primary
                clicked = st.button(label, key=key, type="primary", **button_kwargs)
            else:
                # 旧版不支持type参数，重试不带type
                clicked = st.button(label, key=key, **button_kwargs)
        
        if clicked:
            try:
                result = action_func()
                if result is not False:  # 允许函数返回False表示失败
                    st.success(success_msg)
                    return True
                else:
                    st.error(f"{error_msg}: 函数返回False")
                    return False
            except Exception as e:
                logger.error(f"按钮动作失败: {e}", exc_info=True)
                st.error(f"{error_msg}: {str(e)}")
                return False
        
        return False


def button_response_decorator(func: Callable) -> Callable:
    """
    按钮响应装饰器，自动修复常见问题
    
    Usage:
        @button_response_decorator
        def my_button_action():
            # 按钮点击后的操作
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 修复常见问题
            ButtonResponseFixer.fix_common_issues()
            
            # 执行函数
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"按钮操作失败: {e}", exc_info=True)
            
            # 在Streamlit中显示错误
            if "streamlit" in str(type(st)).lower():
                st.error(f"操作失败: {str(e)}")
            
            # 重新抛出异常，让调用者处理
            raise
    
    return wrapper


# 使用示例
if __name__ == "__main__":
    st.title("按钮响应测试")
    
    fixer = ButtonResponseFixer()
    
    # 示例1: 安全按钮
    if fixer.safe_button("安全按钮测试"):
        st.success("安全按钮被点击！")
    
    # 示例2: 带加载状态的按钮
    if fixer.with_loading("带加载的按钮", loading_text="正在处理..."):
        time.sleep(2)  # 模拟耗时操作
        st.success("操作完成！")
    
    # 示例3: 动作按钮
    def sample_action():
        time.sleep(1)
        return "操作结果"
    
    if fixer.create_action_button(
        "动作按钮",
        sample_action,
        success_msg="动作执行成功！",
        error_msg="动作执行失败"
    ):
        st.info("动作按钮回调执行完毕")
    
    # 示例4: 使用装饰器
    @button_response_decorator
    def decorated_action():
        st.info("装饰器保护的函数正在执行...")
        time.sleep(1)
        return "装饰器结果"
    
    if st.button("测试装饰器按钮"):
        result = decorated_action()
        st.success(f"结果: {result}")