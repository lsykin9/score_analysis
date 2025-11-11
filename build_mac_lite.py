"""
精简版macOS应用打包脚本
排除不必要的依赖，减小应用体积
"""

import os
import sys
import subprocess

def build_mac_app_lite():
    """构建精简版macOS应用"""
    
    print("=" * 60)
    print("开始打包学生成绩分析系统 (精简版)...")
    print("=" * 60)
    
    # PyInstaller命令 - 精简版
    cmd = [
        'pyinstaller',
        '--name=学生成绩分析系统',
        '--onedir',
        '--windowed',
        '--add-data=score_analysis_v0_1.py:.',
        '--hidden-import=streamlit',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=plotly',
        '--hidden-import=openpyxl',
        '--collect-all=streamlit',
        '--exclude-module=torch',
        '--exclude-module=torchvision',
        '--exclude-module=torchaudio',
        '--exclude-module=sklearn',
        '--exclude-module=scipy',
        '--exclude-module=PIL',
        '--exclude-module=matplotlib',
        '--exclude-module=skimage',
        '--exclude-module=astropy',
        '--exclude-module=notebook',
        '--exclude-module=jupyter',
        '--exclude-module=IPython',
        '--exclude-module=PyQt5',
        '--noconfirm',
        'streamlit_runner.py'
    ]
    
    try:
        print("\n正在执行PyInstaller打包...")
        print(f"命令: {' '.join(cmd)}\n")
        
        result = subprocess.run(cmd, check=True)
        
        print("\n" + "=" * 60)
        print("✅ 打包成功！")
        print("=" * 60)
        print("\n应用位置：dist/学生成绩分析系统.app")
        print("\n使用方法：")
        print("1. 打开访达(Finder)")
        print("2. 进入 dist 文件夹")
        print("3. 双击 '学生成绩分析系统.app' 运行")
        print("\n注意：")
        print("1. 首次运行可能需要右键→打开（安全设置）")
        print("2. 精简版体积约200-400MB")
        print("3. 仅支持macOS系统")
        print("4. 如需分发，建议压缩整个.app文件夹")
        
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
    build_mac_app_lite()
