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
from components.sidebar import render_sidebar

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
st.title("📊 学生成绩进步评分系统")
st.markdown("---")

# 初始化 session state
initialize_session_state()

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

# 处理上传的文件
try:
    df_all, df_score, df_final, df_bias, has_subjects, rank_cols, score_cols, subjects, bias_dict, exam_labels = process_data()
    
    # 存储到session state
    st.session_state['df_all'] = df_all
    st.session_state['df_score'] = df_score
    st.session_state['df_final'] = df_final
    st.session_state['df_bias'] = df_bias
    st.session_state['has_subjects'] = has_subjects
    st.session_state['rank_cols'] = rank_cols
    st.session_state['score_cols'] = score_cols
    st.session_state['subjects'] = subjects
    st.session_state['bias_dict'] = bias_dict
    st.session_state['exam_labels'] = exam_labels
    
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
            color='rgba(255, 200, 120, 0.8)',
            line=dict(color='rgba(0, 0, 0, 0.6)', width=0.5)
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
        # 进步趋势图
        st.subheader("排名趋势（选择学生）")
        
        selected_students = st.multiselect(
            "选择要对比的学生（最多5个）",
            df_all["姓名"].tolist(),
            default=df_all["姓名"].tolist()[:3]
        )
        
        if selected_students:
            fig = go.Figure()
            
            # 提取考试标签
            exam_display_names = []
            for col in rank_cols:
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
                    line=dict(width=3),
                    marker=dict(size=10)
                ))
            
            fig.update_layout(
                yaxis_title="排名",
                xaxis_title="考试",
                yaxis=dict(autorange="reversed"),
                height=500,
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 进步得分分布
        st.subheader("区间进步得分分布")
        fig = px.histogram(
            df_score,
            x="区间进步得分",
            nbins=20,
            labels={"区间进步得分": "区间进步得分", "count": "人数"}
        )
        fig.update_traces(
            marker=dict(
                color='rgba(100, 200, 255, 0.7)',
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
            st.dataframe(
                biased_students.style.background_gradient(subset=['排名标准差'], cmap='YlOrRd'),
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
        
        # 排名历史
        if len(rank_cols) > 0:
            st.subheader("排名历史")
            ranks = [student_data[col] for col in rank_cols]
            exam_names = [col.replace("排名_", "") for col in rank_cols]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=exam_names,
                y=ranks,
                mode='lines+markers+text',
                text=ranks,
                textposition='top center',
                line=dict(width=3, color='#FF6B6B'),
                marker=dict(size=12, color='#FF6B6B')
            ))
            fig.update_layout(
                yaxis_title="排名",
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

# Tab 5: 导出结果
with tab5:
    st.header("💾 导出结果")
    
    # 导出总表
    st.subheader("1. 导出成绩总表（仅原始数据）")
    st.info("💡 此文件只包含原始成绩数据，可作为历史总表上传继续分析")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 只导出原始成绩数据（df_all），不包含计算的得分
        df_all.to_excel(writer, sheet_name='成绩总表', index=False)
    
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
