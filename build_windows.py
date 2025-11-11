"""
Windows exe打包脚本
在Windows电脑上运行此脚本来打包成exe文件
"""

import os
import sys
import subprocess

def build_windows_exe():
    """构建Windows exe文件"""
    
    print("=" * 60)
    print("开始打包学生成绩分析系统 (Windows版)...")
    print("=" * 60)
    
    # PyInstaller命令
    cmd = [
        'pyinstaller',
        '--name=学生成绩分析系统',
        '--onedir',  # 打包成文件夹
        '--windowed',  # 无控制台窗口
        '--add-data=score_analysis_v0.1.py;.',  # 添加评分模块（Windows用分号）
        '--add-data=score_analysis_v0_1.py;.',  # 添加中转模块
        '--hidden-import=streamlit',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=plotly',
        '--hidden-import=openpyxl',
        '--hidden-import=streamlit.runtime.scriptrunner.magic_funcs',
        '--hidden-import=streamlit.components.v1',
        '--collect-all=streamlit',
        '--collect-all=plotly',
        '--exclude-module=torch',
        '--exclude-module=sklearn',
        '--exclude-module=matplotlib',
        '--exclude-module=PIL',
        '--noconfirm',
        'app.py'
    ]
    
    try:
        print("\n正在执行PyInstaller打包...")
        print(f"命令: {' '.join(cmd)}\n")
        
        result = subprocess.run(cmd, check=True)
        
        print("\n" + "=" * 60)
        print("✅ 打包成功！")
        print("=" * 60)
        print("\n程序位置：dist\\学生成绩分析系统\\")
        print("\n使用方法：")
        print("1. 打开 dist 文件夹")
        print("2. 进入 学生成绩分析系统 文件夹")
        print("3. 双击 学生成绩分析系统.exe 运行")
        print("\n注意：")
        print("1. 首次运行可能需要允许防火墙访问")
        print("2. 杀毒软件可能误报，请添加信任")
        print("3. 整个文件夹约300-500MB")
        print("4. 需要将整个文件夹一起分发给老师")
        
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("❌ 打包失败！")
        print("=" * 60)
        print(f"\n错误信息：{e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n" + "=" * 60)
        print("❌ 未找到PyInstaller！")
        print("=" * 60)
        print("\n请先安装PyInstaller：")
        print("pip install pyinstaller")
        sys.exit(1)

if __name__ == '__main__':
    build_windows_exe()
