@echo off
REM 学生成绩分析系统 - 一键启动脚本（简化版）
REM 此脚本会自动检查并安装所需环境

echo ==========================================
echo 学生成绩分析系统 - 启动中...
echo ==========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python
    echo.
    echo 请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    echo 安装时请务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo ✓ Python已安装
echo.

REM 检查依赖是否安装
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo 首次使用，正在安装依赖包...
    echo 这可能需要3-5分钟，请耐心等待...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ❌ 依赖安装失败，尝试使用国内镜像源...
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    )
    echo.
)

echo ✓ 依赖已就绪
echo.

REM 启动Streamlit应用
echo ==========================================
echo ✅ 正在启动程序...
echo.
echo 浏览器将自动打开程序界面
echo 如果没有自动打开，请手动访问:
echo.
echo    👉 http://localhost:8501
echo.
echo 按 Ctrl+C 可以停止程序
echo ==========================================
echo.

streamlit run app.py

pause
