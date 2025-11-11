@echo off
REM Windows 启动脚本

echo ==========================================
echo 学生成绩分析系统 - 启动中...
echo ==========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python
    echo 请先安装Python: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM 检查依赖是否安装
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  检测到依赖未安装，正在安装...
    pip install -r requirements.txt
)

REM 启动Streamlit应用
echo.
echo ✅ 启动成功！浏览器将自动打开...
echo 如果浏览器没有自动打开，请手动访问：
echo 👉 http://localhost:8501
echo.
echo 按 Ctrl+C 停止程序
echo ==========================================
echo.

streamlit run app.py

pause
