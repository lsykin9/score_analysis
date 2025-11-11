#!/bin/bash
# macOS 启动脚本

echo "=========================================="
echo "学生成绩分析系统 - 启动中..."
echo "=========================================="

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 激活虚拟环境（如果有的话）
if [ -d "$DIR/venv" ]; then
    source "$DIR/venv/bin/activate"
fi

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到Python3"
    echo "请先安装Python: https://www.python.org/downloads/"
    read -p "按任意键退出..."
    exit 1
fi

# 检查依赖是否安装
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "⚠️  检测到依赖未安装，正在安装..."
    pip3 install -r "$DIR/requirements.txt"
fi

# 启动Streamlit应用
echo ""
echo "✅ 启动成功！浏览器将自动打开..."
echo "如果浏览器没有自动打开，请手动访问："
echo "👉 http://localhost:8501"
echo ""
echo "按 Ctrl+C 停止程序"
echo "=========================================="
echo ""

cd "$DIR"
streamlit run app.py

# 等待用户确认
read -p "按任意键退出..."
