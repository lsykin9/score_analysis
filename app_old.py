import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import sys
import os
import atexit
import glob

# 导入原有的评分逻辑
from score_analysis_v0_1 import (
    read_config,
    progress_score,
    ranking_bonus,
    chain_bonus_score,
    total_score_bonus,
    detect_subject_bias,
    bias_penalty_score
)

# 程序退出时自动清理临时文件
def cleanup_temp_files():
    temp_files = glob.glob("*_temp.xlsx")
    for f in temp_files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass

atexit.register(cleanup_temp_files)

# 页面配置
st.set_page_config(
    page_title="学生成绩进步评分系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)

# 标题
st.title("📊 学生成绩进步评分系统")
st.markdown("---")

# 初始化 session state 来存储上传的成绩文件和配置参数
if 'score_files' not in st.session_state:
    st.session_state.score_files = []
if 'analysis_started' not in st.session_state:
    st.session_state.analysis_started = False
if 'history_file_content' not in st.session_state:
    st.session_state.history_file_content = None
if 'history_exam_count' not in st.session_state:
    st.session_state.history_exam_count = 0

# 初始化删除标记
if 'interval_to_delete' not in st.session_state:
    st.session_state.interval_to_delete = None
if 'bonus_to_delete' not in st.session_state:
    st.session_state.bonus_to_delete = None

# 初始化ID计数器(用于生成唯一ID)
if 'next_interval_id' not in st.session_state:
    st.session_state.next_interval_id = 0
if 'next_bonus_id' not in st.session_state:
    st.session_state.next_bonus_id = 0

# 初始化动态区间权重列表 (格式: [{"id": 0, "start": 0, "end": 5, "weight": 2.0}, ...])
if 'rank_intervals' not in st.session_state:
    st.session_state.rank_intervals = [
        {"id": 0, "start": 0, "end": 20, "weight": 2.0},
        {"id": 1, "start": 21, "end": 50, "weight": 1.8},
        {"id": 2, "start": 51, "end": 100, "weight": 1.5},
        {"id": 3, "start": 101, "end": 150, "weight": 1.2},
        {"id": 4, "start": 151, "end": 200, "weight": 1.0},
        {"id": 5, "start": 201, "end": 300, "weight": 0.8},
        {"id": 6, "start": 301, "end": 430, "weight": 0.6},
        {"id": 7, "start": 431, "end": 99999, "weight": 0.5}
    ]
    st.session_state.next_interval_id = 8

# 初始化动态排名奖励列表
if 'rank_bonuses' not in st.session_state:
    st.session_state.rank_bonuses = [
        {"id": 0, "threshold": 10, "bonus": 30},
        {"id": 1, "threshold": 20, "bonus": 25},
        {"id": 2, "threshold": 30, "bonus": 20},
        {"id": 3, "threshold": 50, "bonus": 15},
        {"id": 4, "threshold": 100, "bonus": 10}
    ]
    st.session_state.next_bonus_id = 5

# 初始化默认参数配置
if 'config_params' not in st.session_state:
    st.session_state.config_params = {
        "线（排名）": 430,
        "过线奖励": 5,
        "连续进步第1次奖励": 5,
        "连续进步第2次奖励": 8,
        "连续进步第3次奖励": 12,
        "连续进步第4次奖励": 18,
        "连续进步第5次奖励": 25,
        "总分大于600奖励": 15,
        "总分大于650奖励": 20,
        "总分大于700奖励": 30,
        "轻微偏科扣分": 5,
        "明显偏科扣分": 15,
        "严重偏科扣分": 30
    }

# 侧边栏 - 参数配置和文件上传
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    # 在expander之前处理删除操作，避免在expander内部修改状态
    if 'interval_to_delete' in st.session_state and st.session_state.interval_to_delete is not None:
        st.session_state.rank_intervals = [
            interval for interval in st.session_state.rank_intervals 
            if interval["id"] != st.session_state.interval_to_delete
        ]
        st.session_state.interval_to_delete = None
    
    if 'bonus_to_delete' in st.session_state and st.session_state.bonus_to_delete is not None:
        st.session_state.rank_bonuses = [
            bonus for bonus in st.session_state.rank_bonuses 
            if bonus["id"] != st.session_state.bonus_to_delete
        ]
        st.session_state.bonus_to_delete = None
    
    # 创建可折叠的参数设置区域
    with st.expander("📊 评分参数设置", expanded=False):
        st.subheader("区间权重")
        
        # 显示当前所有区间
        for idx, interval in enumerate(st.session_state.rank_intervals):
            interval_id = interval["id"]
            # 区间标题
            st.markdown(f"**区间 {idx + 1}**: `({interval['start']}-{interval['end']})`")
            
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                new_start = st.number_input("起始", value=int(interval["start"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"start_{interval_id}", label_visibility="visible")
                if not st.session_state.analysis_started and new_start != interval["start"]:
                    st.session_state.rank_intervals[idx]["start"] = new_start
            
            with col2:
                new_end = st.number_input("结束", value=int(interval["end"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"end_{interval_id}", label_visibility="visible")
                if not st.session_state.analysis_started and new_end != interval["end"]:
                    st.session_state.rank_intervals[idx]["end"] = new_end
            
            with col3:
                new_weight = st.number_input("权重", value=float(interval["weight"]), step=0.1, min_value=0.0, disabled=st.session_state.analysis_started, key=f"weight_{interval_id}", label_visibility="visible")
                if not st.session_state.analysis_started and new_weight != interval["weight"]:
                    st.session_state.rank_intervals[idx]["weight"] = new_weight
            
            with col4:
                st.write("")  # 空行对齐
                # 删除按钮(保留至少1个区间)
                can_delete = len(st.session_state.rank_intervals) > 1
                if st.button("🗑️", key=f"del_{interval_id}", disabled=st.session_state.analysis_started or not can_delete):
                    st.session_state.interval_to_delete = interval_id
                    st.rerun()
        
        # 添加新区间按钮
        if not st.session_state.analysis_started:
            if st.button("➕ 添加区间", key="add_interval"):
                # 在末尾添加新区间
                if len(st.session_state.rank_intervals) > 0:
                    last_interval = st.session_state.rank_intervals[-1]
                    # 默认新区间起始为最后一个区间结束+1
                    new_start = last_interval["end"] + 1
                    new_end = new_start + 50
                else:
                    new_start = 0
                    new_end = 50
                
                new_id = st.session_state.next_interval_id
                st.session_state.next_interval_id += 1
                
                st.session_state.rank_intervals.append({
                    "id": new_id,
                    "start": new_start,
                    "end": new_end,
                    "weight": 1.0
                })
                st.rerun()
        
        st.markdown("---")
        st.subheader("排名线和过线奖励")
        st.session_state.config_params["线（排名）"] = st.number_input("线（排名）", value=st.session_state.config_params["线（排名）"], step=1, disabled=st.session_state.analysis_started)
        st.session_state.config_params["过线奖励"] = st.number_input("过线奖励", value=st.session_state.config_params["过线奖励"], step=1, disabled=st.session_state.analysis_started)
        
        st.markdown("---")
        st.subheader("排名奖励")
        
        # 显示当前所有排名奖励
        for idx, bonus in enumerate(st.session_state.rank_bonuses):
            bonus_id = bonus["id"]
            # 奖励标题
            st.markdown(f"**奖励档位 {idx + 1}**: `前 {bonus['threshold']} 名 → {bonus['bonus']} 分`")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                new_threshold = st.number_input("前N名", value=int(bonus["threshold"]), step=1, min_value=1, disabled=st.session_state.analysis_started, key=f"bonus_thresh_{bonus_id}")
                if not st.session_state.analysis_started and new_threshold != bonus["threshold"]:
                    st.session_state.rank_bonuses[idx]["threshold"] = new_threshold
            
            with col2:
                new_bonus = st.number_input("奖励分", value=int(bonus["bonus"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"bonus_val_{bonus_id}")
                if not st.session_state.analysis_started and new_bonus != bonus["bonus"]:
                    st.session_state.rank_bonuses[idx]["bonus"] = new_bonus
            
            with col3:
                st.write("")  # 空行对齐
                # 删除按钮(保留至少1个奖励)
                if st.button("🗑️", key=f"del_bonus_{bonus_id}", disabled=st.session_state.analysis_started or len(st.session_state.rank_bonuses) <= 1):
                    st.session_state.bonus_to_delete = bonus_id
                    st.rerun()
        
        # 添加新排名奖励按钮
        if not st.session_state.analysis_started:
            if st.button("➕ 添加排名奖励", key="add_bonus"):
                # 默认新奖励阈值为最后一个+10
                last_threshold = st.session_state.rank_bonuses[-1]["threshold"] if st.session_state.rank_bonuses else 0
                
                new_id = st.session_state.next_bonus_id
                st.session_state.next_bonus_id += 1
                
                st.session_state.rank_bonuses.append({
                    "id": new_id,
                    "threshold": last_threshold + 10,
                    "bonus": 5
                })
                st.rerun()
        
        st.markdown("---")
        st.subheader("连续进步奖励")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.config_params["连续进步第1次奖励"] = st.number_input("第1次", value=st.session_state.config_params["连续进步第1次奖励"], step=1, disabled=st.session_state.analysis_started)
            st.session_state.config_params["连续进步第2次奖励"] = st.number_input("第2次", value=st.session_state.config_params["连续进步第2次奖励"], step=1, disabled=st.session_state.analysis_started)
            st.session_state.config_params["连续进步第3次奖励"] = st.number_input("第3次", value=st.session_state.config_params["连续进步第3次奖励"], step=1, disabled=st.session_state.analysis_started)
        with col2:
            st.session_state.config_params["连续进步第4次奖励"] = st.number_input("第4次", value=st.session_state.config_params["连续进步第4次奖励"], step=1, disabled=st.session_state.analysis_started)
            st.session_state.config_params["连续进步第5次奖励"] = st.number_input("第5次", value=st.session_state.config_params["连续进步第5次奖励"], step=1, disabled=st.session_state.analysis_started)
        
        st.markdown("---")
        st.subheader("总分奖励")
        st.session_state.config_params["总分大于600奖励"] = st.number_input("总分>600", value=st.session_state.config_params["总分大于600奖励"], step=1, disabled=st.session_state.analysis_started)
        st.session_state.config_params["总分大于650奖励"] = st.number_input("总分>650", value=st.session_state.config_params["总分大于650奖励"], step=1, disabled=st.session_state.analysis_started)
        st.session_state.config_params["总分大于700奖励"] = st.number_input("总分>700", value=st.session_state.config_params["总分大于700奖励"], step=1, disabled=st.session_state.analysis_started)
        
        st.markdown("---")
        st.subheader("偏科扣分")
        st.session_state.config_params["轻微偏科扣分"] = st.number_input("轻微偏科", value=st.session_state.config_params["轻微偏科扣分"], step=1, disabled=st.session_state.analysis_started)
        st.session_state.config_params["明显偏科扣分"] = st.number_input("明显偏科", value=st.session_state.config_params["明显偏科扣分"], step=1, disabled=st.session_state.analysis_started)
        st.session_state.config_params["严重偏科扣分"] = st.number_input("严重偏科", value=st.session_state.config_params["严重偏科扣分"], step=1, disabled=st.session_state.analysis_started)
    
    st.markdown("---")
    st.header("📁 文件上传")
    
    # 历史成绩总表上传（可选）
    history_file = st.file_uploader(
        "1️⃣ 上传历史成绩总表（可选）",
        type=['xlsx'],
        help="如果已有历史数据，可以上传成绩总表.xlsx，新成绩将接续在后面",
        key="history_uploader"
    )
    
    # 保存历史文件到 session state 并分析次数
    if history_file is not None and not st.session_state.analysis_started:
        st.session_state.history_file_content = history_file.getvalue()
        # 分析历史文件有多少次考试
        try:
            import io
            df_history = pd.read_excel(io.BytesIO(history_file.getvalue()))
            rank_cols = [col for col in df_history.columns if col.startswith("排名_")]
            st.session_state.history_exam_count = len(rank_cols)
            st.success(f"✅ 历史总表已上传 (包含 {st.session_state.history_exam_count} 次考试)")
        except Exception as e:
            st.error(f"❌ 历史文件读取失败: {str(e)}")
            st.session_state.history_file_content = None
            st.session_state.history_exam_count = 0
    
    # 计算当前应该是第几次
    if st.session_state.history_exam_count > 0:
        next_exam_num = st.session_state.history_exam_count + len(st.session_state.score_files) + 1
        upload_label = f"2️⃣ 上传第 {next_exam_num} 次成绩（接续历史总表）"
    else:
        next_exam_num = len(st.session_state.score_files) + 1
        upload_label = f"2️⃣ 上传第 {next_exam_num} 次成绩"
    
    # 成绩文件上传 - 支持多次上传
    score_file = st.file_uploader(
        upload_label,
        type=['xlsx'],
        help="上传学生成绩Excel文件，可以连续上传多次考试成绩",
        key=f"score_uploader_{len(st.session_state.score_files)}"
    )
    
    # 添加到列表
    if score_file is not None and not st.session_state.analysis_started:
        # 检查是否已存在同名文件
        file_names = [f['name'] for f in st.session_state.score_files]
        if score_file.name not in file_names:
            st.session_state.score_files.append({
                'name': score_file.name,
                'content': score_file.getvalue(),
                'exam_num': next_exam_num,
                'exam_label': f"第{next_exam_num}次考试"  # 默认标签
            })
            st.rerun()
    
    # 显示已上传的文件列表
    if st.session_state.history_exam_count > 0 or st.session_state.score_files:
        st.markdown("### 📋 考试成绩列表")
        
        # 显示历史总表信息
        if st.session_state.history_exam_count > 0:
            st.info(f"📦 历史总表: 第 1-{st.session_state.history_exam_count} 次")
        
        # 显示新上传的文件，允许编辑标签
        if st.session_state.score_files:
            st.markdown("**📝 新上传的成绩 (可编辑名称)**")
        
        for idx, file_info in enumerate(st.session_state.score_files):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # 可编辑的考试名称
                new_label = st.text_input(
                    f"考试{idx+1}名称",
                    value=file_info.get('exam_label', f"第{file_info['exam_num']}次考试"),
                    key=f"label_{idx}",
                    disabled=st.session_state.analysis_started,
                    label_visibility="collapsed",
                    placeholder="例如: 期中考试、期末考试、月考"
                )
                # 更新标签
                if new_label != file_info.get('exam_label'):
                    st.session_state.score_files[idx]['exam_label'] = new_label
            
            with col2:
                st.caption(f"📄 {file_info['name']}")
            
            with col3:
                if st.button("🗑️", key=f"delete_{idx}", disabled=st.session_state.analysis_started):
                    st.session_state.score_files.pop(idx)
                    st.rerun()
    
    st.markdown("---")
    
    # 操作按钮
    col1, col2 = st.columns(2)
    with col1:
        # 允许只有历史总表或只有新成绩时都能开始分析
        can_analyze = (len(st.session_state.score_files) > 0 or st.session_state.history_exam_count > 0)
        if st.button("🚀 开始分析", type="primary", disabled=st.session_state.analysis_started or not can_analyze):
            st.session_state.analysis_started = True
            st.rerun()
    
    with col2:
        if st.button("🔄 重置", disabled=not st.session_state.analysis_started):
            st.session_state.score_files = []
            st.session_state.analysis_started = False
            st.session_state.history_file_content = None
            st.session_state.history_exam_count = 0
            # 注意: 不清除 config_params，保留用户的参数设置
            st.rerun()
    
    st.markdown("---")
    st.markdown("### ℹ️ 使用说明")
    st.info("""
    📌 **操作流程**
    1. (可选) 在「评分参数设置」中调整参数
    2. (可选) 上传历史成绩总表
    3. 连续上传新的成绩文件
    4. 确认文件列表和顺序无误
    5. 点击「开始分析」
    6. 查看分析结果和图表
    7. 需要重新分析时点击「重置」
    
    💡 **提示**
    - 参数配置可在顶部「评分参数设置」中调整
    - 如果上传了历史总表，新成绩将接续在后面
    - 文件顺序会自动标记（第N次）
    - 可以随时删除已上传的文件重新上传
    """)

# 检查是否至少有历史总表或新成绩文件
if len(st.session_state.score_files) == 0 and st.session_state.history_file_content is None:
    st.info("👈 请在侧边栏上传至少一个成绩文件或历史总表")
    st.stop()

if not st.session_state.analysis_started:
    st.info("👈 文件已上传，请点击「开始分析」按钮")
    
    if st.session_state.history_exam_count > 0 and len(st.session_state.score_files) > 0:
        # 有历史总表 + 新成绩
        st.markdown(f"### 📊 已准备分析")
        st.write(f"- 📦 历史总表: 包含第 1-{st.session_state.history_exam_count} 次考试")
        st.write(f"- 📄 新增成绩: {len(st.session_state.score_files)} 次")
        st.write(f"- 📈 总计: {st.session_state.history_exam_count + len(st.session_state.score_files)} 次考试")
        st.markdown("#### 新增考试列表:")
        for idx, file_info in enumerate(st.session_state.score_files):
            exam_label = file_info.get('exam_label', f"第{file_info['exam_num']}次考试")
            st.write(f"**{exam_label}**: {file_info['name']}")
    elif st.session_state.history_exam_count > 0:
        # 只有历史总表
        st.markdown(f"### 📊 已准备分析")
        st.write(f"- 📦 历史总表: 包含第 1-{st.session_state.history_exam_count} 次考试")
        st.info("💡 当前仅分析历史总表数据，未添加新成绩")
    else:
        # 只有新成绩
        st.markdown(f"### 📊 已准备分析 {len(st.session_state.score_files)} 次考试成绩")
        st.markdown("#### 考试列表:")
        for idx, file_info in enumerate(st.session_state.score_files):
            exam_label = file_info.get('exam_label', f"第{file_info['exam_num']}次考试")
            st.write(f"**{exam_label}**: {file_info['name']}")
    st.stop()

# ===== 以下代码只有在开始分析后才会执行 =====

# 处理上传的文件
try:
    # 从 session state 构建配置
    cfg = st.session_state.config_params
    
    # 直接从动态区间构建weights (不再处理"线"等特殊值)
    weights = []
    for interval in st.session_state.rank_intervals:
        start = int(interval["start"])
        end = int(interval["end"])
        weight = float(interval["weight"])
        weights.append((start, end, weight))
    
    # 从动态排名奖励构建rank_bonus
    rank_bonus = {item["threshold"]: item["bonus"] for item in st.session_state.rank_bonuses}
    
    # 连续进步加分
    chain_bonus = {
        1: cfg.get("连续进步第1次奖励", 5),
        2: cfg.get("连续进步第2次奖励", 10),
        3: cfg.get("连续进步第3次奖励", 20),
        4: cfg.get("连续进步第4次奖励", 30),
        5: cfg.get("连续进步第5次奖励", 50)
    }
    
    # 总分奖励阈值
    score_bonus = {
        600: cfg.get("总分大于600奖励", 30),
        650: cfg.get("总分大于650奖励", 40),
        700: cfg.get("总分大于700奖励", 50)
    }
    
    # 偏科扣分参数
    bias_penalty = {
        "轻微偏科": cfg.get("轻微偏科扣分", 10),
        "明显偏科": cfg.get("明显偏科扣分", 30),
        "严重偏科": cfg.get("严重偏科扣分", 60)
    }
    
    config = {
        "weights": weights,
        "rank_bonus": rank_bonus,
        "chain_bonus": chain_bonus,
        "score_bonus": score_bonus,
        "bias_penalty": bias_penalty,
        "line": int(cfg.get("线（排名）", 430)),
        "bonus_line": cfg.get("过线奖励", 5)
    }
    
    # 定义科目
    subjects = ["语文", "数学", "英语", "物理", "化学", "生物"]
    
    # 处理历史总表（如果有）
    df_all = None
    if st.session_state.history_file_content is not None:
        with open("成绩总表_temp.xlsx", "wb") as f:
            f.write(st.session_state.history_file_content)
        df_all = pd.read_excel("成绩总表_temp.xlsx")
        
        # 检查历史总表的格式
        rank_cols_history = [col for col in df_all.columns if col.startswith("排名_")]
        score_cols_history = [col for col in df_all.columns if col.startswith("总分_")]
        
        # 推断格式
        if len(score_cols_history) > 0:
            # 检查是否有科目列
            subject_cols_check = [col for col in df_all.columns if any(col.startswith(f"{subj}_") for subj in subjects)]
            if len(subject_cols_check) > 0:
                has_subjects = True
                has_score = True
            else:
                has_subjects = False
                has_score = True
        else:
            has_subjects = False
            has_score = False
    
    # 处理新上传的成绩文件
    all_dfs = []
    exam_labels = {}  # 存储考试编号到标签的映射
    
    if len(st.session_state.score_files) > 0:
        for idx, file_info in enumerate(st.session_state.score_files):
            exam_num = file_info['exam_num']
            exam_label = file_info.get('exam_label', f"第{exam_num}次考试")
            exam_labels[exam_num] = exam_label
            
            # 保存临时文件
            temp_filename = f"成绩_第{exam_num}次_temp.xlsx"
            with open(temp_filename, "wb") as f:
                f.write(file_info['content'])
            
            # 读取成绩
            df = pd.read_excel(temp_filename)
            all_dfs.append((exam_num, exam_label, df))
    
    # 如果没有历史总表,需要从新文件推断格式
    if df_all is None and len(all_dfs) > 0:
        # 检查第一个文件的格式
        first_df = all_dfs[0][2]
        col_count = first_df.shape[1]
        
        if col_count == 2:
            has_score = False
            has_subjects = False
        elif col_count == 3:
            has_score = True
            has_subjects = False
        elif col_count == 9:
            has_score = True
            has_subjects = True
        else:
            st.error(f"❌ 数据格式错误！当前列数：{col_count}\n\n支持格式：\n- 2列（姓名、排名）\n- 3列（姓名、排名、总分）\n- 9列（姓名、排名、总分、6科成绩）")
            st.stop()
    
    # 如果只有历史总表,没有新文件,跳过后续处理
    if df_all is not None and len(all_dfs) == 0:
        st.info("📦 仅分析历史总表数据")
    
    # 检查所有新文件格式是否一致
    if len(all_dfs) > 0:
        expected_col_count = all_dfs[0][2].shape[1]
        for exam_num, exam_label, df in all_dfs:
            if df.shape[1] != expected_col_count:
                st.error(f"❌ {exam_label} 成绩格式不一致！\n第1次新增：{expected_col_count}列\n{exam_label}：{df.shape[1]}列\n\n请确保所有成绩使用相同格式")
                st.stop()
    
    # 合并新上传的成绩到历史总表
    for exam_num, exam_label, df in all_dfs:
        # 设置基础列名
        col_count = df.shape[1]
        if col_count == 2:
            df.columns = ["姓名", "本次排名"]
        elif col_count == 3:
            df.columns = ["姓名", "本次排名", "本次总分"]
        elif col_count == 9:
            df.columns = ["姓名", "本次排名", "本次总分"] + subjects
        
        # 重命名为自定义标签
        rename_dict = {"本次排名": f"排名_{exam_label}"}
        if has_score:
            rename_dict["本次总分"] = f"总分_{exam_label}"
        if has_subjects:
            for subj in subjects:
                rename_dict[subj] = f"{subj}_{exam_label}"
        
        df_renamed = df.rename(columns=rename_dict)
        
        # 合并数据 - 确保只保留"姓名"列作为合并键,避免列名冲突
        if df_all is None:
            df_all = df_renamed
        else:
            # 检查是否有重复列名(除了"姓名")
            existing_cols = set(df_all.columns) - {"姓名"}
            new_cols = set(df_renamed.columns) - {"姓名"}
            duplicate_cols = existing_cols & new_cols
            
            if duplicate_cols:
                st.warning(f"⚠️ 警告: 检测到重复列名 {duplicate_cols}，请修改考试名称以避免冲突")
                # 删除重复列
                df_renamed = df_renamed[[col for col in df_renamed.columns if col not in duplicate_cols or col == "姓名"]]
            
            df_all = pd.merge(df_all, df_renamed, on="姓名", how="outer", suffixes=('', '_重复')).fillna(0)
            
            # 删除任何带有"_重复"后缀的列
            duplicate_cols_after = [col for col in df_all.columns if col.endswith('_重复')]
            if duplicate_cols_after:
                df_all = df_all.drop(columns=duplicate_cols_after)
    
    # 检查并清理所有带有 _x, _y 等后缀的列名
    cols_to_rename = {}
    for col in df_all.columns:
        if col.endswith('_x') or col.endswith('_y'):
            # 移除后缀
            base_col = col.rsplit('_', 1)[0]
            st.warning(f"⚠️ 检测到异常列名: {col}，已重命名为: {base_col}")
            cols_to_rename[col] = base_col
    
    if cols_to_rename:
        df_all = df_all.rename(columns=cols_to_rename)
        # 如果有重复列,保留第一个
        df_all = df_all.loc[:, ~df_all.columns.duplicated()]
    
    # 确保至少有一些数据
    if df_all is None or df_all.empty:
        st.error("❌ 没有可用的数据进行分析")
        st.stop()
    
    # 分析得分
    results = []
    rank_cols = [col for col in df_all.columns if col.startswith("排名_")]
    score_cols = [col for col in df_all.columns if col.startswith("总分_")]
    
    # 如果有科目成绩，需要计算偏科扣分
    bias_dict = {}
    if has_subjects:
        subject_cols_dict = {}
        for subj in subjects:
            subj_cols = [col for col in df_all.columns if col.startswith(f"{subj}_")]
            if subj_cols:
                subject_cols_dict[subj] = subj_cols[-1]
    
    for _, row in df_all.iterrows():
        name = row["姓名"]
        # 将排名转换为整数,处理浮点数和NaN
        ranks = []
        for col in rank_cols:
            val = row[col]
            if pd.isna(val) or val == 0:
                ranks.append(0)
            else:
                ranks.append(int(float(val)))
        
        chain_len = 0
        chain_progress = 0.0

        # 计算连续进步次数
        for i in range(1, len(ranks)):
            before, now = ranks[i - 1], ranks[i]
            if now != 0 and before != 0 and now < before:
                chain_len += 1
            else:
                chain_len = 0
        
        # 计算最近一次进步得分
        if len(ranks) >= 2:
            _cur = ranks[-1]
            _pre = ranks[-2]
            if _cur and _pre and _cur < _pre:
                # 确保传入整数
                chain_progress = progress_score(int(_pre), int(_cur), config["weights"])
            else:
                chain_progress = 0.0

        # 排名加分
        latest_rank = int(ranks[-1]) if ranks[-1] else 0
        previous_rank = int(ranks[-2]) if len(ranks) > 1 and ranks[-2] else 9999
        rank_add = ranking_bonus(latest_rank, previous_rank, config)
        
        # 连续进步加分
        chain_add = chain_bonus_score(chain_len, config)
        
        # 总分奖励加分
        score_add = 0
        if score_cols and len(score_cols) > 0:
            latest_total_score = row[score_cols[-1]]
            # 处理浮点数和NaN
            if pd.notna(latest_total_score):
                score_add = total_score_bonus(float(latest_total_score), config)
            else:
                score_add = 0
        
        # 偏科扣分
        bias_deduct = 0
        bias_level = "均衡发展"
        if has_subjects:
            latest_scores = {"姓名": name}
            for subj, col in subject_cols_dict.items():
                latest_scores[subj] = row[col]
            
            bias_info = detect_subject_bias(latest_scores, subjects)
            bias_level = bias_info["偏科等级"]
            bias_deduct = bias_penalty_score(bias_level, config)
            
            bias_dict[name] = bias_info
        
        # 总得分
        total = chain_progress + rank_add + chain_add + score_add + bias_deduct

        if has_subjects:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, score_add, bias_deduct, total])
        elif score_cols:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, score_add, total])
        else:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, total])

    # 生成结果DataFrame
    if has_subjects:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "排名加分", "总分奖励", "偏科扣分", "总得分"
        ])
    elif score_cols:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "排名加分", "总分奖励", "总得分"
        ])
    else:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "排名加分", "总得分"
        ])
    
    df_final = pd.merge(df_all, df_score, on="姓名")
    df_final = df_final.sort_values(by="总得分", ascending=False)
    
    # 偏科检测结果
    if has_subjects:
        bias_results = []
        for name, bias_info in bias_dict.items():
            penalty = bias_penalty_score(bias_info["偏科等级"], config)
            bias_results.append({
                "姓名": name,
                "标准差": bias_info["标准差"],
                "偏科等级": bias_info["偏科等级"],
                "平均标准化分": bias_info["平均标准化分"],
                "最强科目": bias_info["最强科目"],
                "最弱科目": bias_info["最弱科目"],
                "扣分": penalty
            })
        df_bias = pd.DataFrame(bias_results)
        df_bias = df_bias.sort_values(by="标准差", ascending=False)
    
    # 存储到session state
    st.session_state['df_all'] = df_all
    st.session_state['df_score'] = df_score
    st.session_state['df_final'] = df_final
    st.session_state['df_bias'] = df_bias if has_subjects else None
    st.session_state['has_subjects'] = has_subjects
    st.session_state['rank_cols'] = rank_cols
    st.session_state['score_cols'] = score_cols
    st.session_state['subjects'] = subjects
    st.session_state['bias_dict'] = bias_dict if has_subjects else None
    st.session_state['exam_labels'] = exam_labels  # 保存考试标签映射
    
    st.success("✅ 数据处理完成！")
    
except Exception as e:
    st.error(f"❌ 处理数据时出错：{str(e)}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

# 主界面 - 标签页
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 总览", 
    "📈 进步分析", 
    "🎯 偏科检测", 
    "👤 学生详情", 
    "💾 导出结果"
])

with tab1:
    st.header("📊 数据总览")
    
    # 关键指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总人数", len(df_final))
    
    with col2:
        avg_score = df_final["总得分"].mean()
        st.metric("平均总得分", f"{avg_score:.1f}")
    
    with col3:
        if has_subjects:
            bias_count = len(df_bias[df_bias["偏科等级"] != "均衡发展"])
            st.metric("偏科人数", bias_count)
        else:
            st.metric("偏科检测", "需要科目成绩")
    
    with col4:
        if len(rank_cols) >= 2:
            progress_count = len(df_score[df_score["区间进步得分"] > 0])
            st.metric("进步人数", progress_count)
        else:
            st.metric("考试次数", len(rank_cols))
    
    st.markdown("---")
    
    # 得分排行榜
    st.subheader("🏆 总得分 Top 10")
    top10 = df_final.nlargest(10, "总得分")[["姓名", "总得分"]]
    
    fig = px.bar(
        top10,
        x="总得分",
        y="姓名",
        orientation='h',
        text="总得分",
        color="总得分",
        color_continuous_scale="Sunset",  # 日落色: 紫-粉-橙渐变
    )
    fig.update_traces(
        texttemplate='%{text:.1f}', 
        textposition='outside',
        opacity=0.9  # 透明度: 0-1之间，0完全透明，1完全不透明
    )
    fig.update_layout(
        showlegend=False,
        yaxis={'categoryorder':'total ascending'},
        height=600,  # 放大高度
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📊 得分分布")
    
    fig = px.histogram(
        df_final,
        x="总得分",
        nbins=30,  # 增加箱子数，让分布更细致连续
        title="",
        labels={"总得分": "总得分", "count": "人数"}
    )
    
    # 设置杏色填充和半透明黑色描边
    fig.update_traces(
        marker=dict(
            color='rgba(255, 200, 120, 0.8)',  # 清新杏色 + 80%不透明度
            line=dict(color='rgba(0, 0, 0, 0.6)', width=0.5)  # 黑色描边 + 60%不透明度
        )
    )
    
    fig.update_layout(
        height=500,  # 放大高度
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # 详细数据表格
    st.subheader("📋 详细数据")
    
    # 格式化数据显示
    df_display = df_final.copy()
    
    # 创建格式化字典
    format_dict = {}
    
    # 1. 将所有排名列和次数列格式化为整数（无小数点）
    for col in df_display.columns:
        if col.startswith("排名_"):
            format_dict[col] = "{:.0f}"
    
    # 连续进步次数也格式化为整数
    if "连续进步次数" in df_display.columns:
        format_dict["连续进步次数"] = "{:.0f}"
    
    # 2. 将所有得分列格式化为一位小数
    score_columns = ["区间进步得分", "连续进步加分", "排名加分", "总得分"]
    if "总分奖励" in df_display.columns:
        score_columns.append("总分奖励")
    if "偏科扣分" in df_display.columns:
        score_columns.append("偏科扣分")
    
    for col in score_columns:
        if col in df_display.columns:
            format_dict[col] = "{:.1f}"
    
    # 3. 将总分列格式化为一位小数
    for col in df_display.columns:
        if col.startswith("总分_"):
            format_dict[col] = "{:.1f}"
        # 4. 将科目成绩列也格式化为一位小数
        if has_subjects:
            for subj in subjects:
                if col.startswith(f"{subj}_"):
                    format_dict[col] = "{:.1f}"
    
    st.dataframe(
        df_display.style.background_gradient(subset=['总得分'], cmap='RdYlGn').format(format_dict),
        use_container_width=True,
        height=400
    )

with tab2:
    st.header("📈 进步分析")
    
    if len(rank_cols) < 2:
        st.info("💡 **提示**：当前只有 1 次考试数据，无法查看进步情况。\n\n请上传更多成绩文件后点击「重置」重新分析。")
    else:
        # 进步趋势图
        st.subheader("排名趋势（选择学生）")
        
        selected_students = st.multiselect(
            "选择要对比的学生（最多5个）",
            df_all["姓名"].tolist(),
            default=df_all["姓名"].tolist()[:3]
        )
        
        if selected_students:
            fig = go.Figure()
            
            # 提取考试标签 - 从列名中提取
            exam_display_names = []
            for col in rank_cols:
                # 列名格式: "排名_考试名称"
                label = col.replace("排名_", "")
                exam_display_names.append(label)
            
            for student in selected_students[:5]:
                student_data = df_all[df_all["姓名"] == student]
                ranks = [student_data[col].values[0] for col in rank_cols]
                
                fig.add_trace(go.Scatter(
                    x=exam_display_names,
                    y=ranks,
                    mode='lines+markers',
                    name=student,
                    hovertemplate='<b>%{fullData.name}</b><br>排名: %{y}<extra></extra>'
                ))
            
            fig.update_layout(
                title="排名趋势对比（排名越小越好）",
                xaxis_title="考试",
                yaxis_title="排名",
                yaxis_autorange='reversed',
                hovermode='x unified',
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 进步榜单
        st.subheader("⬆️ 进步最大 Top 10")
        progress_top = df_score.nlargest(10, "区间进步得分")[["姓名", "区间进步得分"]]
        
        fig = px.bar(
            progress_top,
            x="区间进步得分",
            y="姓名",
            orientation='h',
            text="区间进步得分",
            color="区间进步得分",
            color_continuous_scale="Greens"
        )
        fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig.update_layout(
            showlegend=False,
            yaxis={'categoryorder':'total ascending'},
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("🎯 偏科检测")
    
    if not has_subjects:
        st.warning("⚠️ 需要包含各科成绩的数据才能进行偏科检测")
    else:
        # 偏科统计
        col1, col2, col3, col4 = st.columns(4)
        
        bias_stats = df_bias["偏科等级"].value_counts()
        
        with col1:
            count = bias_stats.get("均衡发展", 0)
            st.metric("均衡发展", f"{count}人", delta="优秀", delta_color="normal")
        
        with col2:
            count = bias_stats.get("轻微偏科", 0)
            st.metric("轻微偏科", f"{count}人", delta="-10分", delta_color="inverse")
        
        with col3:
            count = bias_stats.get("明显偏科", 0)
            st.metric("明显偏科", f"{count}人", delta="-30分", delta_color="inverse")
        
        with col4:
            count = bias_stats.get("严重偏科", 0)
            st.metric("严重偏科", f"{count}人", delta="-60分", delta_color="inverse")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 偏科分布饼图
            st.subheader("📊 偏科等级分布")
            fig = px.pie(
                df_bias,
                names="偏科等级",
                title="",
                hole=0.4,
                color="偏科等级",
                color_discrete_map={
                    "均衡发展": "#2ecc71",
                    "轻微偏科": "#f39c12",
                    "明显偏科": "#e74c3c",
                    "严重偏科": "#c0392b"
                }
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 标准差分布
            st.subheader("📈 标准差分布")
            fig = px.box(
                df_bias,
                y="标准差",
                color="偏科等级",
                title="",
                color_discrete_map={
                    "均衡发展": "#2ecc71",
                    "轻微偏科": "#f39c12",
                    "明显偏科": "#e74c3c",
                    "严重偏科": "#c0392b"
                }
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 偏科学生列表
        st.subheader("⚠️ 需要关注的学生")
        problem_students = df_bias[df_bias["偏科等级"] != "均衡发展"].copy()
        
        if len(problem_students) > 0:
            # 格式化最强科目和最弱科目中的百分比为一位小数
            def format_subject_with_percent(text):
                if pd.isna(text):
                    return text
                text = str(text)
                # 查找百分比模式: 数字后跟%
                import re
                def replace_percent(match):
                    number = float(match.group(1))
                    return f"{number:.1f}%"
                # 匹配数字+%的模式
                text = re.sub(r'(\d+\.?\d*)%', replace_percent, text)
                return text
            
            problem_students['最强科目'] = problem_students['最强科目'].apply(format_subject_with_percent)
            problem_students['最弱科目'] = problem_students['最弱科目'].apply(format_subject_with_percent)
            
            # 格式化数值列
            bias_format_dict = {
                "标准差": "{:.2f}",
                "平均标准化分": "{:.2f}",
                "扣分": "{:.1f}"  # 扣分保持一位小数
            }
            
            st.dataframe(
                problem_students.style.background_gradient(subset=['标准差'], cmap='Reds').format(bias_format_dict),
                use_container_width=True,
                height=300
            )
        else:
            st.success("🎉 全部学生均衡发展！")

with tab4:
    st.header("👤 学生详情")
    
    # 选择学生
    student_name = st.selectbox(
        "选择学生",
        df_all["姓名"].tolist()
    )
    
    if student_name:
        student_data = df_final[df_final["姓名"] == student_name].iloc[0]
        student_history = df_all[df_all["姓名"] == student_name].iloc[0]
        
        # 基本信息
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            latest_rank = student_history[rank_cols[-1]]
            st.metric("当前排名", int(latest_rank))
        
        with col2:
            st.metric("总得分", f"{student_data['总得分']:.1f}")
        
        with col3:
            if has_subjects:
                bias_info = bias_dict[student_name]
                st.metric("偏科等级", bias_info["偏科等级"])
            else:
                st.metric("偏科等级", "需要科目成绩")
        
        with col4:
            st.metric("连续进步次数", int(student_data["连续进步次数"]))
        
        st.markdown("---")
        
        # 排名趋势
        if len(rank_cols) >= 2:
            st.subheader("个人排名趋势")
            # 将排名转换为整数
            ranks = [int(float(student_history[col])) if pd.notna(student_history[col]) and student_history[col] != 0 else 0 for col in rank_cols]
            
            # 提取考试标签
            exam_display_names = []
            for col in rank_cols:
                label = col.replace("排名_", "")
                exam_display_names.append(label)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=exam_display_names,
                y=ranks,
                mode='lines+markers+text',
                text=ranks,  # 现在已经是整数了
                textposition='top center',
                line=dict(width=3),
                marker=dict(size=12)
            ))
            fig.update_layout(
                yaxis_autorange='reversed',
                yaxis_title="排名",
                xaxis_title="考试",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 各科成绩雷达图 - 放在上面
        if has_subjects:
            st.subheader("🎯 各科成绩分布")
            
            bias_info = bias_dict[student_name]
            subject_details = bias_info["科目详情"]
            
            categories = list(subject_details.keys())
            values = [subject_details[subj]["标准化分"] for subj in categories]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=student_name
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )
                ),
                showlegend=False,
                height=500  # 放大高度
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("需要科目成绩数据才能显示雷达图")
        
        st.markdown("---")
        
        # 得分构成 - 放在下面
        st.subheader("💯 得分构成")
        
        score_components = {
            "区间进步得分": student_data["区间进步得分"],
            "排名加分": student_data["排名加分"],
            "连续进步加分": student_data["连续进步加分"]
        }
        
        if "总分奖励" in student_data:
            score_components["总分奖励"] = student_data["总分奖励"]
        
        if "偏科扣分" in student_data:
            score_components["偏科扣分"] = student_data["偏科扣分"]
        
        # 只显示非零项
        score_components = {k: v for k, v in score_components.items() if v != 0}
        
        fig = go.Figure(data=[go.Pie(
            labels=list(score_components.keys()),
            values=[abs(v) for v in score_components.values()],
            hole=0.3,
            marker_colors=['#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#e74c3c']
        )])
        fig.update_layout(height=500)  # 放大高度
        st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.header("💾 导出结果")
    
    st.subheader("📥 下载Excel报告")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 下载成绩总表
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_all.to_excel(writer, index=False, sheet_name='成绩总表')
        
        st.download_button(
            label="📊 下载成绩总表",
            data=output.getvalue(),
            file_name="成绩总表.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        # 下载进步分析结果
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_score.to_excel(writer, index=False, sheet_name='进步分析')
        
        st.download_button(
            label="📈 下载进步分析结果",
            data=output.getvalue(),
            file_name="进步链分析结果.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col3:
        # 下载最终得分结果
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='最终得分')
        
        st.download_button(
            label="🏆 下载最终得分结果",
            data=output.getvalue(),
            file_name="最终得分结果.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    if has_subjects:
        st.markdown("---")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # 下载偏科检测报告
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_bias.to_excel(writer, index=False, sheet_name='偏科检测')
            
            st.download_button(
                label="🎯 下载偏科检测报告",
                data=output.getvalue(),
                file_name="偏科检测报告.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    st.markdown("---")
    
    st.info("""
    💡 **提示**
    - 所有Excel文件均可用Excel、WPS等软件打开
    - 数据表格支持进一步筛选和分析
    - 建议定期保存历史数据以便对比
    """)
