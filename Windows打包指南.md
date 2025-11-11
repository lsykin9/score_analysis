# Windows系统打包为exe指南

## 📋 准备工作

### 1. 需要的文件
将以下文件复制到Windows电脑：
- `app.py`
- `score_analysis_v0.1.py`
- `score_analysis_v0_1.py`
- `requirements.txt`
- `build_windows.py`
- `启动程序.bat`

### 2. 在Windows电脑上安装Python
1. 访问 https://www.python.org/downloads/
2. 下载并安装Python 3.8或更高版本
3. **重要**：安装时勾选 "Add Python to PATH"

### 3. 安装依赖
打开命令提示符（CMD）或PowerShell：
```bash
# 进入项目文件夹
cd "项目文件夹路径"

# 安装依赖
pip install -r requirements.txt

# 安装打包工具
pip install pyinstaller
```

---

## 🚀 开始打包

### 方法一：使用自动化脚本（推荐）

在Windows电脑上双击运行或在CMD中执行：
```bash
python build_windows.py
```

### 方法二：手动打包

在CMD或PowerShell中执行：
```bash
pyinstaller --name=学生成绩分析系统 ^
    --onedir ^
    --windowed ^
    --add-data=score_analysis_v0.1.py;. ^
    --add-data=score_analysis_v0_1.py;. ^
    --hidden-import=streamlit ^
    --hidden-import=pandas ^
    --hidden-import=numpy ^
    --hidden-import=plotly ^
    --hidden-import=openpyxl ^
    --collect-all=streamlit ^
    --collect-all=plotly ^
    --noconfirm ^
    app.py
```

---

## 📦 打包后的文件

打包成功后会生成：

```
dist/
└── 学生成绩分析系统/
    ├── 学生成绩分析系统.exe  ← 主程序
    ├── _internal/               ← 依赖库文件夹
    └── 其他dll文件
```

**文件大小**：整个文件夹约300-500MB

---

## 📤 交付给老师

### 步骤1：压缩文件夹
1. 右键点击 `dist\学生成绩分析系统` 文件夹
2. 选择"发送到" → "压缩(zipped)文件夹"
3. 得到 `学生成绩分析系统.zip`（约200-300MB）

### 步骤2：创建使用说明
在压缩包旁边放一个 `使用说明.txt`：

```
学生成绩分析系统 - 使用说明

1. 解压 学生成绩分析系统.zip
2. 打开解压后的文件夹
3. 双击 学生成绩分析系统.exe 运行
4. 等待30秒-1分钟（首次运行较慢）
5. 浏览器会自动打开程序界面

注意事项：
- 首次运行Windows防火墙可能会弹出提示，请点击"允许访问"
- 杀毒软件可能误报，请添加到信任列表
- 不要删除_internal文件夹，否则程序无法运行
- 如果浏览器没有自动打开，手动访问 http://localhost:8501

联系方式：[您的联系方式]
```

---

## ⚠️ 常见问题

### Q1: 打包失败，提示找不到模块？
**A**: 确保所有依赖都已安装：
```bash
pip install -r requirements.txt
pip install pyinstaller
```

### Q2: exe运行后没反应？
**A**: 
- 查看任务管理器，可能在后台运行
- 等待1-2分钟，首次启动较慢
- 检查是否被杀毒软件拦截

### Q3: 防火墙提示？
**A**: 点击"允许访问"，Streamlit需要使用本地网络端口

### Q4: 如何减小文件体积？
**A**: 使用`--onefile`参数打包成单个exe（但启动会更慢）：
```bash
pyinstaller --name=学生成绩分析系统 ^
    --onefile ^
    --windowed ^
    --add-data=score_analysis_v0.1.py;. ^
    --add-data=score_analysis_v0_1.py;. ^
    --hidden-import=streamlit ^
    --collect-all=streamlit ^
    app.py
```

### Q5: 打包后运行报错？
**A**: 
1. 在开发环境先测试程序是否正常运行
2. 检查`--add-data`路径是否正确
3. 查看打包过程的警告信息

---

## 🎯 完整操作流程

### 在Mac上准备文件
```bash
# 1. 确保所有文件都在
cd "/Users/kin9/python_code/score analysis"

# 2. 创建压缩包准备传输
zip -r score_analysis_source.zip \
    app.py \
    score_analysis_v0.1.py \
    score_analysis_v0_1.py \
    requirements.txt \
    build_windows.py \
    启动程序.bat

# 3. 将压缩包传到Windows电脑
```

### 在Windows上打包
```bash
# 1. 解压文件
# 2. 打开CMD，进入文件夹
cd "解压路径"

# 3. 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 4. 打包
python build_windows.py

# 5. 测试运行
cd dist\学生成绩分析系统
学生成绩分析系统.exe

# 6. 如果测试成功，压缩整个文件夹交付
```

---

## 📊 方案对比

| 方案 | 文件大小 | 启动速度 | 易用性 | 更新难度 |
|------|---------|---------|--------|---------|
| --onedir | 300-500MB | 快 | ⭐⭐⭐⭐⭐ | 中等 |
| --onefile | 200-400MB | 慢 | ⭐⭐⭐⭐ | 困难 |
| 源码+脚本 | 几MB | 快 | ⭐⭐⭐ | 简单 |

**推荐**：使用 `--onedir` 模式（默认），虽然文件多但启动快且稳定。

---

## 🔄 后续更新

如果需要更新程序：
1. 修改源代码
2. 在Windows上重新打包
3. 只需替换老师电脑上的整个文件夹

---

**祝打包顺利！** 🎉
