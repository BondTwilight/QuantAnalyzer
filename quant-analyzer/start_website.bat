@echo off
echo 正在启动 QuantBrain v4.0 量化策略自学习系统...
echo.

REM 检查Python环境
python --version
if errorlevel 1 (
    echo 错误: Python未安装或不在PATH中
    pause
    exit /b 1
)

REM 检查依赖
echo 检查依赖包...
pip install -r requirements.txt

REM 启动Streamlit应用
echo.
echo 启动网站 (http://localhost:8501)...
echo 按 Ctrl+C 停止服务
echo.

streamlit run enhanced_app.py

pause