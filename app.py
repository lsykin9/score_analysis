"""
学生成绩进步评分系统 - 主入口
重构版：模块化架构
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import sys
import os
import atexit
import glob

# 导入配置模块
from config.session_state import initialize_session_state

# 导入组件
from components.sidebar import render_sidebar, auto_load_config

# 导入工具
from utils.data_processor import process_data

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
    /* 侧边栏宽度设置 */
    [data-testid="stSidebar"][aria-expanded="true"] {
        min-width: 400px;
        max-width: 400px;
    }
    
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
    
    /* 平滑过渡动画 */
    .element-container {
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* 输入框和按钮的过渡效果 */
    .stNumberInput, .stButton, .stMarkdown {
        transition: all 0.2s ease-in-out;
    }
    
    /* 按钮内容居中 */
    .stButton > button {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        text-align: center !important;
        padding: 0.4rem 0.2rem !important;  /* 增大上下padding */
        border-width: 2px !important;  /* 加粗边框 */
    }
    
    /* 确保按钮内的文本也居中 */
    .stButton button p {
        width: 100%;
        text-align: center;
        margin: 0 auto;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    /* 侧边栏按钮特殊处理 */
    section[data-testid="stSidebar"] .stButton > button {
        padding: 0.35rem 0.2rem !important;
        border-width: 1.5px !important;
    }
    
    /* 删除按钮悬停效果 */
    button[kind="secondary"] {
        transition: all 0.2s ease-in-out;
    }
    
    button[kind="secondary"]:hover {
        transform: scale(1.1);
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    
    /* 添加按钮悬停效果 */
    button[kind="primary"] {
        transition: all 0.2s ease-in-out;
    }
    
    button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* 区间卡片动画 */
    .stMarkdown h3, .stMarkdown h4 {
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* 数字输入框焦点效果 */
    .stNumberInput input:focus {
        border-color: #ff4b4b;
        box-shadow: 0 0 0 0.2rem rgba(255, 75, 75, 0.25);
        transition: all 0.2s ease-in-out;
    }
    
    /* Expander展开/收起动画优化 */
    .streamlit-expanderContent {
        transition: max-height 0.3s ease-in-out, opacity 0.2s ease-in-out;
    }
    </style>
""", unsafe_allow_html=True)

# 标题
st.title("📊 学生成绩进步评分系统（阿金专属）")
st.markdown("---")

# 初始化 session state
initialize_session_state()

# 自动加载保存的配置（仅在首次加载时）
auto_load_config()

# 渲染侧边栏
render_sidebar()

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

# 生成缓存键（基于文件内容和配置参数）
def generate_cache_key():
    """生成缓存键，用于识别相同的分析配置"""
    import hashlib
    
    # 收集关键参数
    key_parts = []
    
    # 1. 文件内容哈希
    if st.session_state.history_file_content:
        key_parts.append(hashlib.md5(st.session_state.history_file_content).hexdigest()[:16])
    
    for file_info in st.session_state.score_files:
        if 'content' in file_info:
            key_parts.append(hashlib.md5(file_info['content']).hexdigest()[:16])
    
    # 2. 配置参数
    config_str = str(sorted(st.session_state.config_params.items()))
    key_parts.append(hashlib.md5(config_str.encode()).hexdigest()[:8])
    
    # 3. 排名区间和奖励
    rank_str = str(sorted(st.session_state.rank_intervals.items()))
    key_parts.append(hashlib.md5(rank_str.encode()).hexdigest()[:8])
    
    return "_".join(key_parts)

# 检查缓存
cache_key = generate_cache_key()
use_cache = False

if 'analysis_cache' in st.session_state and 'cache_key' in st.session_state:
    if st.session_state.cache_key == cache_key:
        # 缓存有效，直接使用
        use_cache = True
        cached_data = st.session_state.analysis_cache
        
        df_all = cached_data['df_all']
        df_score = cached_data['df_score']
        df_final = cached_data['df_final']
        df_bias = cached_data['df_bias']
        has_subjects = cached_data['has_subjects']
        rank_cols = cached_data['rank_cols']
        score_cols = cached_data['score_cols']
        group_rank_cols = cached_data['group_rank_cols']
        subjects = cached_data['subjects']
        bias_dict = cached_data['bias_dict']
        exam_labels = cached_data['exam_labels']
        
        st.info("⚡ 使用缓存数据（页面刷新后自动恢复）")

# 如果没有缓存，执行分析
if not use_cache:
    try:
        df_all, df_score, df_final, df_bias, has_subjects, rank_cols, score_cols, subjects, bias_dict, exam_labels = process_data()
        
        # 获取集团排名列
        group_rank_cols = []
        for col in df_all.columns:
            # 新格式：总分集团排名_考试1 或 语文集团排名_考试1
            # 旧格式：总分_集团排名_考试1 或 集团排名_考试1
            if col.startswith("集团排名_"):
                group_rank_cols.append(col)
            elif "集团排名_" in col:
                group_rank_cols.append(col)
        
        # 保存到缓存
        st.session_state.analysis_cache = {
            'df_all': df_all,
            'df_score': df_score,
            'df_final': df_final,
            'df_bias': df_bias,
            'has_subjects': has_subjects,
            'rank_cols': rank_cols,
            'score_cols': score_cols,
            'group_rank_cols': group_rank_cols,
            'subjects': subjects,
            'bias_dict': bias_dict,
            'exam_labels': exam_labels
        }
        st.session_state.cache_key = cache_key
        
        st.success("✅ 数据处理完成！")
        
    except Exception as e:
        st.error(f"❌ 处理数据时出错：{str(e)}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

# 存储到session state（兼容后续代码）
st.session_state['df_all'] = df_all
st.session_state['df_score'] = df_score
st.session_state['df_final'] = df_final
st.session_state['df_bias'] = df_bias
st.session_state['has_subjects'] = has_subjects
st.session_state['rank_cols'] = rank_cols
st.session_state['score_cols'] = score_cols
st.session_state['group_rank_cols'] = group_rank_cols
st.session_state['subjects'] = subjects
st.session_state['bias_dict'] = bias_dict
st.session_state['exam_labels'] = exam_labels

# 主界面 - 标签页
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 总览", 
    "📈 进步分析", 
    "🎯 偏科检测", 
    "👤 学生详情", 
    "🔍 得分详情",
    "💾 导出结果"
])

# Tab 1: 总览
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
        color_continuous_scale="Sunset",
    )
    fig.update_traces(
        texttemplate='%{text:.1f}', 
        textposition='outside',
        opacity=0.9
    )
    fig.update_layout(
        showlegend=False,
        yaxis={'categoryorder':'total ascending'},
        height=600,
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📊 得分分布")
    
    fig = px.histogram(
        df_final,
        x="总得分",
        nbins=30,
        title="",
        labels={"总得分": "总得分", "count": "人数"}
    )
    
    fig.update_traces(
        marker=dict(
            color='rgba(99, 110, 250, 0.7)',  # 专业的靛蓝色
            line=dict(color='rgba(62, 68, 156, 0.9)', width=1.5)
        )
    )
    
    fig.update_layout(
        height=500,
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
    
    # 将所有排名列和次数列格式化为整数
    for col in df_display.columns:
        if col.startswith("排名_"):
            format_dict[col] = "{:.0f}"
    
    if "连续进步次数" in df_display.columns:
        format_dict["连续进步次数"] = "{:.0f}"
    
    # 将所有得分列格式化为一位小数
    score_columns = ["区间进步得分", "连续进步加分", "排名加分", "总得分"]
    if "总分奖励" in df_display.columns:
        score_columns.append("总分奖励")
    if "偏科扣分" in df_display.columns:
        score_columns.append("偏科扣分")
    
    for col in score_columns:
        if col in df_display.columns:
            format_dict[col] = "{:.1f}"
    
    # 将总分列格式化为一位小数
    for col in df_display.columns:
        if col.startswith("总分_"):
            format_dict[col] = "{:.1f}"
        if has_subjects:
            for subj in subjects:
                if col.startswith(f"{subj}_"):
                    format_dict[col] = "{:.1f}"
    
    st.dataframe(
        df_display.style.background_gradient(subset=['总得分'], cmap='RdYlGn').format(format_dict),
        use_container_width=True,
        height=400
    )

# Tab 2: 进步分析
with tab2:
    st.header("📈 进步分析")
    
    if len(rank_cols) < 2:
        st.info("💡 **提示**：当前只有 1 次考试数据，无法查看进步情况。\n\n请上传更多成绩文件后点击「重置」重新分析。")
    else:
        # 选择查看的内容和排名类型
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            # 选择查看总分还是各科
            if has_subjects:
                view_options = ["总分"] + subjects
            else:
                view_options = ["总分"]
            
            selected_subject = st.selectbox(
                "选择查看科目",
                view_options,
                index=0
            )
        
        with col2:
            # 选择年级排名还是集团排名
            rank_type_options = ["年级排名"]
            # 检查是否有集团排名数据
            has_group_rank = any("集团排名" in col for col in df_all.columns)
            if has_group_rank:
                rank_type_options.append("集团排名")
            
            rank_type = st.selectbox(
                "选择排名类型",
                rank_type_options,
                index=0
            )
        
        with col3:
            # 选择学生
            selected_students = st.multiselect(
                "选择要对比的学生（最多5个）",
                df_all["姓名"].tolist(),
                default=df_all["姓名"].tolist()[:3]
            )
        
        # 根据选择提取对应的排名列
        if selected_subject == "总分":
            if rank_type == "年级排名":
                # 查找总分年级排名列：支持新旧格式
                # 新格式：总分年级排名_考试1
                # 旧格式：总分_年级排名_考试1 或 年级排名_考试1
                target_cols = [col for col in df_all.columns 
                              if col.startswith("总分年级排名_") 
                              or col.startswith("总分_年级排名_") 
                              or (col.startswith("年级排名_") and not any(subj in col for subj in subjects))]
            else:
                # 查找总分集团排名列
                # 新格式：总分集团排名_考试1
                # 旧格式：总分_集团排名_考试1 或 集团排名_考试1
                target_cols = [col for col in df_all.columns 
                              if col.startswith("总分集团排名_") 
                              or col.startswith("总分_集团排名_") 
                              or (col.startswith("集团排名_") and not any(subj in col for subj in subjects))]
        else:
            # 各科排名
            if rank_type == "年级排名":
                # 新格式：语文年级排名_考试1
                # 旧格式：语文_年级排名_考试1
                target_cols = [col for col in df_all.columns 
                              if col.startswith(f"{selected_subject}年级排名_") 
                              or col.startswith(f"{selected_subject}_年级排名_")]
            else:
                # 新格式：语文集团排名_考试1
                # 旧格式：语文_集团排名_考试1
                target_cols = [col for col in df_all.columns 
                              if col.startswith(f"{selected_subject}集团排名_") 
                              or col.startswith(f"{selected_subject}_集团排名_")]
        
        if len(target_cols) < 2:
            st.warning(f"⚠️ {selected_subject}的{rank_type}数据不足，需要至少2次考试数据")
        elif selected_students:
            st.subheader(f"📊 {selected_subject} - {rank_type}趋势")
            
            fig = go.Figure()
            
            # 提取考试标签
            exam_display_names = []
            for col in target_cols:
                # 从列名中提取考试名称（从最后一个下划线后提取）
                if '_' in col:
                    label = col.rsplit('_', 1)[-1]
                else:
                    label = col
                exam_display_names.append(label)
            
            for student in selected_students[:5]:
                student_data = df_all[df_all["姓名"] == student]
                if not student_data.empty:
                    ranks = []
                    for col in target_cols:
                        val = student_data[col].values[0]
                        # 将0值（缺考）转换为None，在图表中不显示
                        ranks.append(None if val == 0 else val)
                    
                    fig.add_trace(go.Scatter(
                        x=exam_display_names,
                        y=ranks,
                        mode='lines+markers',
                        name=student,
                        line=dict(width=3),
                        marker=dict(size=10),
                        connectgaps=False  # 不连接缺考的点
                    ))
            
            fig.update_layout(
                yaxis_title=rank_type,
                xaxis_title="考试",
                yaxis=dict(autorange="reversed"),
                height=500,
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 进步得分分布
        st.subheader("区间进步得分分布")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.histogram(
                df_score,
                x="区间进步得分",
                nbins=20,
                labels={"区间进步得分": "区间进步得分", "count": "人数"},
                title="区间进步得分分布"
            )
            fig.update_traces(
                marker=dict(
                    color='rgba(0, 172, 193, 0.7)',
                    line=dict(color='rgba(0, 0, 0, 0.5)', width=1)
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 连续进步次数分布
            fig = px.histogram(
                df_score,
                x="连续进步次数",
                nbins=max(df_score["连续进步次数"].max(), 5),
                labels={"连续进步次数": "连续进步次数", "count": "人数"},
                title="连续进步次数分布"
            )
            fig.update_traces(
                marker=dict(
                    color='rgba(239, 85, 59, 0.7)',
                    line=dict(color='rgba(0, 0, 0, 0.5)', width=1)
                )
            )
            st.plotly_chart(fig, use_container_width=True)

# Tab 3: 偏科检测
with tab3:
    st.header("🎯 偏科检测")
    
    if not has_subjects:
        st.info("💡 **提示**：当前数据未包含科目成绩，无法进行偏科分析。\n\n请上传包含科目成绩的文件（9列格式）")
    else:
        # 偏科等级统计
        st.subheader("偏科等级分布")
        
        bias_counts = df_bias["偏科等级"].value_counts()
        
        fig = px.pie(
            values=bias_counts.values,
            names=bias_counts.index,
            title="",
            color=bias_counts.index,
            color_discrete_map={
                "均衡发展": "#90EE90",
                "轻微偏科": "#FFD700",
                "明显偏科": "#FFA500",
                "严重偏科": "#FF6347"
            }
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 偏科学生详情
        st.subheader("偏科学生详情")
        
        biased_students = df_bias[df_bias["偏科等级"] != "均衡发展"]
        
        if len(biased_students) > 0:
            # 格式化显示（差值为得分率百分比）
            format_dict = {
                "差值标准差": "{:.2f}%",
                "平均差值": "{:.2f}%",
                "最强科差值": "{:.2f}%",
                "最弱科差值": "{:.2f}%",
                "扣分": "{:.0f}"
            }
            st.dataframe(
                biased_students.style.background_gradient(subset=['差值标准差'], cmap='YlOrRd').format(format_dict),
                use_container_width=True
            )
        else:
            st.success("🎉 太棒了！所有学生均衡发展，没有偏科现象！")

# Tab 4: 学生详情
with tab4:
    st.header("👤 学生详情查询")
    
    selected_student = st.selectbox("选择学生", df_all["姓名"].tolist())
    
    if selected_student:
        student_data = df_all[df_all["姓名"] == selected_student].iloc[0]
        student_score = df_score[df_score["姓名"] == selected_student].iloc[0]
        
        # 基本信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总得分", f"{student_score['总得分']:.1f}")
        with col2:
            st.metric("连续进步次数", int(student_score['连续进步次数']))
        with col3:
            if has_subjects:
                student_bias = df_bias[df_bias["姓名"] == selected_student]
                if not student_bias.empty:
                    st.metric("偏科等级", student_bias.iloc[0]["偏科等级"])
        
        st.markdown("---")
        
        # 得分构成
        st.subheader("📊 得分构成")
        
        # 收集得分数据
        score_components = {}
        score_components["区间进步得分"] = student_score.get("区间进步得分", 0)
        score_components["连续进步加分"] = student_score.get("连续进步加分", 0)
        
        # 合并年级排名和集团排名加分
        year_rank_bonus = student_score.get("年级排名加分", 0)
        group_rank_bonus = student_score.get("集团排名加分", 0)
        total_rank_bonus = year_rank_bonus + group_rank_bonus
        if total_rank_bonus != 0:
            score_components["排名加分"] = total_rank_bonus
        
        if "总分奖励" in student_score.index:
            score_components["总分奖励"] = student_score.get("总分奖励", 0)
        
        if "偏科扣分" in student_score.index:
            bias_penalty = student_score.get("偏科扣分", 0)
            if bias_penalty != 0:
                score_components["偏科扣分"] = bias_penalty
        
        # 使用两列布局展示
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # 得分明细卡片
            for name, value in score_components.items():
                if name == "偏科扣分":
                    st.metric(name, f"{value:.1f}", delta=None, delta_color="inverse")
                else:
                    delta_text = f"+{value:.1f}" if value > 0 else (f"{value:.1f}" if value < 0 else "0.0")
                    st.metric(name, f"{value:.1f}", delta=delta_text if value != 0 else None)
        
        with col2:
            # 饼图展示得分构成（只显示正值部分）
            positive_scores = {k: v for k, v in score_components.items() if v > 0}
            
            if positive_scores:
                fig = px.pie(
                    values=list(positive_scores.values()),
                    names=list(positive_scores.keys()),
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    textfont_size=14
                )
                fig.update_layout(height=500, showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无得分数据")
        
        st.markdown("---")
        
        # 选择查看的内容和排名类型
        col1, col2 = st.columns([3, 3])
        
        with col1:
            # 选择查看总分还是各科
            if has_subjects:
                detail_view_options = ["总分"] + subjects
            else:
                detail_view_options = ["总分"]
            
            detail_selected_subject = st.selectbox(
                "选择查看科目趋势",
                detail_view_options,
                index=0,
                key="detail_subject"
            )
        
        with col2:
            # 选择年级排名还是集团排名
            detail_rank_type_options = ["年级排名"]
            has_group_rank = any("集团排名" in col for col in df_all.columns)
            if has_group_rank:
                detail_rank_type_options.append("集团排名")
            
            detail_rank_type = st.selectbox(
                "选择排名类型",
                detail_rank_type_options,
                index=0,
                key="detail_rank_type"
            )
        
        # 根据选择提取对应的排名列
        if detail_selected_subject == "总分":
            if detail_rank_type == "年级排名":
                # 新格式：总分年级排名_考试1 或 旧格式：总分_年级排名_考试1
                detail_target_cols = [col for col in df_all.columns 
                                    if col.startswith("总分年级排名_") 
                                    or col.startswith("总分_年级排名_") 
                                    or (col.startswith("年级排名_") and "总分" not in col and not any(subj in col for subj in subjects))]
            else:
                # 新格式：总分集团排名_考试1 或 旧格式：总分_集团排名_考试1
                detail_target_cols = [col for col in df_all.columns 
                                    if col.startswith("总分集团排名_") 
                                    or col.startswith("总分_集团排名_") 
                                    or (col.startswith("集团排名_") and "总分" not in col and not any(subj in col for subj in subjects))]
        else:
            if detail_rank_type == "年级排名":
                # 新格式：语文年级排名_考试1 或 旧格式：语文_年级排名_考试1
                detail_target_cols = [col for col in df_all.columns 
                                    if col.startswith(f"{detail_selected_subject}年级排名_") 
                                    or col.startswith(f"{detail_selected_subject}_年级排名_")]
            else:
                # 新格式：语文集团排名_考试1 或 旧格式：语文_集团排名_考试1
                detail_target_cols = [col for col in df_all.columns 
                                    if col.startswith(f"{detail_selected_subject}集团排名_") 
                                    or col.startswith(f"{detail_selected_subject}_集团排名_")]
        
        # 排名历史
        if len(detail_target_cols) > 0:
            st.subheader(f"{detail_selected_subject} - {detail_rank_type}历史")
            
            ranks = []
            exam_names = []
            
            for col in detail_target_cols:
                val = student_data[col]
                # 提取考试名称（统一使用rsplit从最后一个下划线分割）
                label = col.rsplit('_', 1)[-1]
                
                # 将0值（缺考）转换为None
                ranks.append(None if val == 0 else val)
                exam_names.append(label)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=exam_names,
                y=ranks,
                mode='lines+markers+text',
                text=[f"{int(r)}" if r is not None else "缺考" for r in ranks],
                textposition='top center',
                line=dict(width=3, color='#FF6B6B'),
                marker=dict(size=12, color='#FF6B6B'),
                connectgaps=False
            ))
            fig.update_layout(
                yaxis_title=detail_rank_type,
                xaxis_title="考试",
                yaxis=dict(autorange="reversed"),
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 科目成绩(如果有)
        if has_subjects:
            st.markdown("---")
            st.subheader("最近一次各科成绩")
            
            subject_scores = {}
            for subj in subjects:
                # 只提取分数列，排除年级排名和集团排名列
                subj_score_cols = [col for col in df_all.columns 
                                  if col.startswith(f"{subj}_") 
                                  and "年级排名" not in col 
                                  and "集团排名" not in col]
                if subj_score_cols:
                    subject_scores[subj] = student_data[subj_score_cols[-1]]
            
            fig = px.bar(
                x=list(subject_scores.keys()),
                y=list(subject_scores.values()),
                labels={'x': '科目', 'y': '分数'},
                text=list(subject_scores.values())
            )
            fig.update_traces(
                texttemplate='%{text:.1f}',
                textposition='outside',
                marker_color='lightsalmon'
            )
            st.plotly_chart(fig, use_container_width=True)

# Tab 5: 得分详情
with tab5:
    st.header("🔍 学生得分详情")
    
    st.markdown("""
    查看每位学生的详细得分构成，包括各项加分和扣分的具体计算过程。
    """)
    
    # 从session_state获取数据
    rank_cols = st.session_state.get('rank_cols', [])
    score_cols = st.session_state.get('score_cols', [])
    group_rank_cols = st.session_state.get('group_rank_cols', [])
    subjects = st.session_state.get('subjects', [])
    exam_labels = st.session_state.get('exam_labels', {})
    
    # 选择学生
    selected_student = st.selectbox("选择学生", df_all["姓名"].tolist(), key="student_detail_select")
    
    if selected_student:
        student_data = df_all[df_all["姓名"] == selected_student].iloc[0]
        student_score = df_score[df_score["姓名"] == selected_student].iloc[0]
        
        st.markdown(f"## 📋 {selected_student}")
        st.markdown("---")
        
        # 筛选出总分的年级排名列（用于计算进步得分的列）
        # 新格式：总分年级排名_考试1 或 旧格式：总分_年级排名_考试1
        total_rank_cols = [col for col in rank_cols 
                          if col.startswith("总分年级排名_") 
                          or col.startswith("总分_年级排名_") 
                          or (col.startswith("年级排名_") and not any(subj in col for subj in subjects))]
        
        # 1. 排名历史
        st.markdown("### 1️⃣ 排名历史（总分年级排名）")
        if len(total_rank_cols) == 0:
            st.warning("⚠️ 未找到总分年级排名数据")
        else:
            rank_data = []
            for col in total_rank_cols:
                # 统一使用rsplit从最后一个下划线分割提取考试标签
                exam_label = col.rsplit('_', 1)[-1]
                rank_val = student_data[col]
                
                # 检查该次考试是否有科目缺考
                is_exam_absent = False
                if subjects and exam_label:
                    for subj in subjects:
                        subj_col = f"{subj}_{exam_label}"
                        if subj_col in student_data.index:
                            score_val = student_data[subj_col]
                            if pd.isna(score_val) or score_val == 0:
                                is_exam_absent = True
                                break
                
                # 如果该次考试有科目缺考，显示为"缺考"
                if is_exam_absent or rank_val == 0 or pd.isna(rank_val):
                    rank_data.append({"考试": exam_label, "年级排名": "缺考"})
                else:
                    rank_data.append({"考试": exam_label, "年级排名": int(rank_val)})
            st.table(pd.DataFrame(rank_data))
        
        # 2. 区间进步得分
        st.markdown("### 2️⃣ 区间进步得分")
        
        if len(total_rank_cols) >= 2:
            # 重新应用缺考检测逻辑构建ranks数组
            ranks = []
            for col in total_rank_cols:
                rank_val = student_data[col]
                
                # 从列名提取考试标识（统一使用rsplit）
                exam_label = col.rsplit('_', 1)[-1]
                
                # 检查该次考试是否有科目缺考
                is_exam_absent = False
                if subjects and exam_label:
                    for subj in subjects:
                        subj_col = f"{subj}_{exam_label}"
                        if subj_col in student_data.index:
                            score_val = student_data[subj_col]
                            if pd.isna(score_val) or score_val == 0:
                                is_exam_absent = True
                                break
                
                # 如果该次考试有科目缺考，排名设为0
                if is_exam_absent or pd.isna(rank_val) or rank_val == 0:
                    ranks.append(0)
                else:
                    ranks.append(int(rank_val))
            
            # 计算每次进步得分
            from score_analysis_v0_1 import progress_score
            from utils.data_processor import process_data
            
            # 获取配置
            weights = []
            for interval in st.session_state.rank_intervals:
                weights.append((int(interval["start"]), int(interval["end"]), float(interval["weight"])))
            
            # 只显示最近一次进步（与实际计算逻辑一致）
            # 找到最近两次有效排名
            _cur = ranks[-1] if ranks[-1] > 0 else 0
            _pre = 0
            for i in range(len(ranks) - 2, -1, -1):
                if ranks[i] > 0:
                    _pre = ranks[i]
                    break
            
            progress_details = []
            if _cur > 0 and _pre > 0:
                if _cur < _pre:  # 有进步
                    score = progress_score(_pre, _cur, weights)
                    # 找到对应的考试编号
                    cur_exam_idx = len(ranks)  # 最后一次考试
                    pre_exam_idx = 0
                    for i in range(len(ranks) - 2, -1, -1):
                        if ranks[i] > 0:
                            pre_exam_idx = i + 1
                            break
                    
                    progress_details.append({
                        "对比": f"{exam_labels.get(pre_exam_idx, f'考试{pre_exam_idx}')} vs {exam_labels.get(cur_exam_idx, f'考试{cur_exam_idx}')}",
                        "排名变化": f"{_pre} → {_cur}",
                        "进步名次": _pre - _cur,
                        "得分": f"{score:.1f}"
                    })
                else:  # 退步或持平
                    cur_exam_idx = len(ranks)
                    pre_exam_idx = 0
                    for i in range(len(ranks) - 2, -1, -1):
                        if ranks[i] > 0:
                            pre_exam_idx = i + 1
                            break
                    
                    progress_details.append({
                        "对比": f"{exam_labels.get(pre_exam_idx, f'考试{pre_exam_idx}')} vs {exam_labels.get(cur_exam_idx, f'考试{cur_exam_idx}')}",
                        "排名变化": f"{_pre} → {_cur}",
                        "进步名次": _pre - _cur,
                        "得分": "0.0"
                    })
            
            if progress_details:
                st.table(pd.DataFrame(progress_details))
                st.info("💡 区间进步得分只计算最近一次有效考试的进步")
            else:
                st.write("无区间进步")
            st.write(f"**总区间进步得分**: {student_score['区间进步得分']:.1f}")
        else:
            st.info(f"💡 当前只有 {len(total_rank_cols)} 次考试数据，需要至少2次考试才能计算进步得分")
        
        # 3. 连续进步
        st.markdown("### 3️⃣ 连续进步加分")
        st.write(f"**连续进步次数**: {int(student_score['连续进步次数'])}")
        st.write(f"**连续进步加分**: {student_score['连续进步加分']:.1f}")
        
        # 调试信息：只有在只有1次考试但连续进步次数不为0时才显示警告
        if len(total_rank_cols) == 1 and int(student_score['连续进步次数']) > 0:
            st.warning("⚠️ 只有1次考试数据，理论上不应该有连续进步。这可能是计算错误。")
        
        # 显示连续进步配置
        with st.expander("查看连续进步配置"):
            chain_config = pd.DataFrame(st.session_state.chain_bonuses)[["times", "bonus"]]
            chain_config.columns = ["连续次数", "奖励分数"]
            st.table(chain_config)
        
        # 4. 年级排名加分
        st.markdown("### 4️⃣ 年级排名加分")
        if len(total_rank_cols) > 0:
            latest_rank = int(student_data[total_rank_cols[-1]]) if student_data[total_rank_cols[-1]] > 0 else 0
            st.write(f"**最新年级排名**: {latest_rank if latest_rank > 0 else '缺考'}")
            st.write(f"**年级排名加分**: {student_score['年级排名加分']:.1f}")
        else:
            st.write("**无年级排名数据**")
        
        # 显示年级排名配置
        with st.expander("查看年级排名奖励配置"):
            rank_config = pd.DataFrame(st.session_state.rank_bonuses)[["threshold", "bonus"]]
            rank_config.columns = ["排名阈值", "奖励分数"]
            st.table(rank_config)
            st.write(f"**A线**: 排名≤{st.session_state.config_params.get('A线（排名）', 430)}名，奖励: {st.session_state.config_params.get('A线过线奖励', 5)}分")
            st.write(f"**B线**: 排名≤{st.session_state.config_params.get('B线（排名）', 500)}名，奖励: {st.session_state.config_params.get('B线过线奖励', 3)}分")
        
        # 5. 集团排名加分
        if group_rank_cols and len(group_rank_cols) > 0:
            st.markdown("### 5️⃣ 集团排名加分")
            
            # 筛选出总分的集团排名列
            # 新格式：总分集团排名_考试1 或 旧格式：总分_集团排名_考试1
            total_group_rank_cols = [col for col in group_rank_cols 
                                    if col.startswith("总分集团排名_") 
                                    or col.startswith("总分_集团排名_") 
                                    or (col.startswith("集团排名_") and not any(subj in col for subj in subjects))]
            
            if total_group_rank_cols and len(total_group_rank_cols) > 0:
                latest_group_rank = student_data[total_group_rank_cols[-1]]
                if pd.notna(latest_group_rank) and latest_group_rank > 0:
                    st.write(f"**最新集团排名**: {int(latest_group_rank)}")
                    st.write(f"**集团排名加分**: {student_score['集团排名加分']:.1f}")
                    
                    with st.expander("查看集团排名奖励配置"):
                        group_config = pd.DataFrame(st.session_state.group_rank_bonuses)[["threshold", "bonus"]]
                        group_config.columns = ["排名阈值", "奖励分数"]
                        st.table(group_config)
                else:
                    st.write("无集团排名数据")
            else:
                st.write("无总分集团排名数据")
        
        # 6. 总分奖励
        if score_cols and len(score_cols) > 0:
            st.markdown("### 6️⃣ 总分奖励")
            latest_score = student_data[score_cols[-1]]
            st.write(f"**最新总分**: {latest_score:.1f}")
            st.write(f"**总分奖励**: {student_score['总分奖励']:.1f}")
            
            with st.expander("查看总分奖励配置"):
                score_config = pd.DataFrame(st.session_state.score_bonuses)[["threshold", "bonus"]]
                score_config.columns = ["分数阈值", "奖励分数"]
                st.table(score_config)
        
        # 7. 偏科扣分
        if has_subjects:
            st.markdown("### 7️⃣ 偏科扣分")
            student_bias = df_bias[df_bias["姓名"] == selected_student]
            if not student_bias.empty:
                bias_info = student_bias.iloc[0]
                st.write(f"**偏科等级**: {bias_info['偏科等级']}")
                st.write(f"**差值标准差**: {bias_info['差值标准差']:.2f}分")
                st.write(f"**平均差值**: {bias_info['平均差值']:.2f}分（整体水平）")
                st.write(f"**最强科目**: {bias_info['最强科目']}（超参考线{bias_info['最强科差值']:.1f}分）")
                st.write(f"**最弱科目**: {bias_info['最弱科目']}（{'超' if bias_info['最弱科差值'] >= 0 else '低于'}参考线{abs(bias_info['最弱科差值']):.1f}分）")
                st.write(f"**偏科扣分**: {student_score['偏科扣分']:.1f}")
        
        # 8. 总得分
        st.markdown("---")
        st.markdown("### 📊 总得分")
        col1, col2 = st.columns(2)
        with col1:
            score_breakdown = {
                "区间进步得分": student_score['区间进步得分'],
                "连续进步加分": student_score['连续进步加分'],
                "年级排名加分": student_score['年级排名加分'],
                "集团排名加分": student_score['集团排名加分'],
            }
            if '总分奖励' in student_score.index:
                score_breakdown["总分奖励"] = student_score['总分奖励']
            if '偏科扣分' in student_score.index:
                score_breakdown["偏科扣分"] = student_score['偏科扣分']
            
            breakdown_df = pd.DataFrame(list(score_breakdown.items()), columns=["项目", "得分"])
            st.table(breakdown_df)
        
        with col2:
            st.metric("总得分", f"{student_score['总得分']:.1f}", 
                     delta=None if student_score['总得分'] == 0 else f"+{student_score['总得分']:.1f}")

# Tab 6: 导出结果
with tab6:
    st.header("💾 导出结果")
    
    # 导出总表
    st.subheader("1. 导出成绩总表（仅原始数据）")
    st.info("💡 此文件包含多个工作表，每次考试一个工作表，方便管理和查看")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 新格式：每次考试单独保存为一个工作表
        # 从 df_all 中提取每次考试的数据
        import re
        
        # 获取所有考试的列名（通过识别带考试标识的列）
        exam_labels_dict = {}  # {exam_label: first_col_index}
        for idx, col in enumerate(df_all.columns):
            if col == "姓名":
                continue
            match = re.search(r'_(.+)$', col)
            if match:
                exam_label = match.group(1)
                if exam_label not in exam_labels_dict:
                    exam_labels_dict[exam_label] = idx  # 记录该考试第一次出现的列索引
        
        # 按列的出现顺序排序考试（从旧到新）
        exam_labels_sorted = sorted(exam_labels_dict.keys(), key=lambda x: exam_labels_dict[x])
        
        # 为每次考试创建一个工作表
        for exam_label in exam_labels_sorted:
            # 提取该次考试的所有列
            cols_for_exam = ["姓名"] + [col for col in df_all.columns if col.endswith(f"_{exam_label}")]
            df_exam = df_all[cols_for_exam].copy()
            
            # 去掉列名中的考试标识后缀（使工作表内数据更简洁）
            df_exam.columns = [col.replace(f"_{exam_label}", "") if col != "姓名" else col for col in df_exam.columns]
            
            # 使用考试名称作为工作表名称（Excel工作表名最长31字符）
            sheet_name = exam_label[:31] if len(exam_label) > 31 else exam_label
            df_exam.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 同时保留一个完整的总表（可选）
        df_all.to_excel(writer, sheet_name='完整总表', index=False)
    
    st.download_button(
        label="📥 下载成绩总表（原始数据）",
        data=output.getvalue(),
        file_name="成绩总表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("---")
    
    # 导出完整分析结果
    st.subheader("2. 导出完整分析结果")
    st.info("💡 此文件包含原始数据、得分明细和偏科分析，用于查看完整结果")
    
    output2 = BytesIO()
    with pd.ExcelWriter(output2, engine='openpyxl') as writer:
        df_final.to_excel(writer, sheet_name='完整结果', index=False)
        df_score.to_excel(writer, sheet_name='得分明细', index=False)
        if has_subjects and df_bias is not None:
            df_bias.to_excel(writer, sheet_name='偏科检测', index=False)
    
    st.download_button(
        label="📥 下载完整分析结果",
        data=output2.getvalue(),
        file_name="完整分析结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
