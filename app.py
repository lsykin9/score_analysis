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

# 初始化 session state 来存储上传的成绩文件
if 'score_files' not in st.session_state:
    st.session_state.score_files = []
if 'analysis_started' not in st.session_state:
    st.session_state.analysis_started = False
if 'config_file_content' not in st.session_state:
    st.session_state.config_file_content = None

# 侧边栏 - 文件上传
with st.sidebar:
    st.header("📁 文件上传")
    
    # 参数配置文件上传
    config_file = st.file_uploader(
        "1️⃣ 上传参数配置文件",
        type=['xlsx'],
        help="上传包含评分参数的Excel文件",
        key="config_uploader"
    )
    
    # 保存配置文件到 session state
    if config_file is not None:
        st.session_state.config_file_content = config_file.getvalue()
        st.success("✅ 配置文件已上传")
    
    st.markdown("---")
    st.subheader("📚 上传成绩文件")
    
    # 成绩文件上传 - 支持多次上传
    score_file = st.file_uploader(
        "2️⃣ 上传成绩文件（可多次上传）",
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
                'content': score_file.getvalue()
            })
            st.rerun()
    
    # 显示已上传的文件列表
    if st.session_state.score_files:
        st.markdown("### 📋 已上传的成绩文件")
        for idx, file_info in enumerate(st.session_state.score_files):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"{idx + 1}. {file_info['name']}")
            with col2:
                if st.button("🗑️", key=f"delete_{idx}", disabled=st.session_state.analysis_started):
                    st.session_state.score_files.pop(idx)
                    st.rerun()
    
    st.markdown("---")
    
    # 操作按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 开始分析", type="primary", disabled=st.session_state.analysis_started or len(st.session_state.score_files) == 0):
            st.session_state.analysis_started = True
            st.rerun()
    
    with col2:
        if st.button("🔄 重置", disabled=not st.session_state.analysis_started):
            st.session_state.score_files = []
            st.session_state.analysis_started = False
            st.session_state.config_file_content = None
            st.rerun()
    
    st.markdown("---")
    st.markdown("### ℹ️ 使用说明")
    st.info("""
    📌 **操作流程**
    1. 上传参数配置文件
    2. 连续上传多次成绩文件
    3. 确认文件列表无误
    4. 点击「开始分析」
    5. 查看分析结果和图表
    6. 需要重新分析时点击「重置」
    """)

# 检查文件是否上传和是否开始分析
if st.session_state.config_file_content is None:
    st.info("👈 请在侧边栏上传参数配置文件")
    st.stop()

if len(st.session_state.score_files) == 0:
    st.info("👈 请在侧边栏上传至少一个成绩文件")
    st.stop()

if not st.session_state.analysis_started:
    st.info("👈 文件已上传，请点击「开始分析」按钮")
    st.markdown(f"### 📊 已准备分析 {len(st.session_state.score_files)} 次考试成绩")
    for idx, file_info in enumerate(st.session_state.score_files):
        st.write(f"**第 {idx + 1} 次**: {file_info['name']}")
    st.stop()

# 处理上传的文件
try:
    # 保存配置文件
    with open("参数配置_temp.xlsx", "wb") as f:
        f.write(st.session_state.config_file_content)
    
    # 读取配置
    config = read_config("参数配置_temp.xlsx")
    
    # 定义科目
    subjects = ["语文", "数学", "英语", "物理", "化学", "生物"]
    
    # 处理所有成绩文件
    all_dfs = []
    for idx, file_info in enumerate(st.session_state.score_files):
        # 保存临时文件
        temp_filename = f"成绩_第{idx + 1}次_temp.xlsx"
        with open(temp_filename, "wb") as f:
            f.write(file_info['content'])
        
        # 读取成绩
        df = pd.read_excel(temp_filename)
        all_dfs.append(df)
    
    # 检查第一个文件的格式
    first_df = all_dfs[0]
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
    
    # 检查所有文件格式是否一致
    for idx, df in enumerate(all_dfs):
        if df.shape[1] != col_count:
            st.error(f"❌ 第 {idx + 1} 次成绩格式不一致！\n第1次：{col_count}列\n第{idx + 1}次：{df.shape[1]}列\n\n请确保所有成绩使用相同格式")
            st.stop()
    
    # 统一列名并重命名
    df_all = None
    for idx, df in enumerate(all_dfs):
        exam_num = idx + 1
        
        # 设置基础列名
        if col_count == 2:
            df.columns = ["姓名", "本次排名"]
        elif col_count == 3:
            df.columns = ["姓名", "本次排名", "本次总分"]
        elif col_count == 9:
            df.columns = ["姓名", "本次排名", "本次总分"] + subjects
        
        # 重命名为第N次
        rename_dict = {"本次排名": f"排名_第{exam_num}次"}
        if has_score:
            rename_dict["本次总分"] = f"总分_第{exam_num}次"
        if has_subjects:
            for subj in subjects:
                rename_dict[subj] = f"{subj}_第{exam_num}次"
        
        df_renamed = df.rename(columns=rename_dict)
        
        # 合并数据
        if df_all is None:
            df_all = df_renamed
        else:
            df_all = pd.merge(df_all, df_renamed, on="姓名", how="outer").fillna(0)
    
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
        ranks = [row[col] for col in rank_cols]
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
                chain_progress = progress_score(_pre, _cur, config["weights"])
            else:
                chain_progress = 0.0

        # 排名加分
        latest_rank = ranks[-1]
        previous_rank = ranks[-2] if len(ranks) > 1 else 9999
        rank_add = ranking_bonus(latest_rank, previous_rank, config)
        
        # 连续进步加分
        chain_add = chain_bonus_score(chain_len, config)
        
        # 总分奖励加分
        score_add = 0
        if score_cols and len(score_cols) > 0:
            latest_total_score = row[score_cols[-1]]
            score_add = total_score_bonus(latest_total_score, config)
        
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
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 总得分 Top 10")
        top10 = df_final.nlargest(10, "总得分")[["姓名", "总得分"]]
        
        fig = px.bar(
            top10,
            x="总得分",
            y="姓名",
            orientation='h',
            text="总得分",
            color="总得分",
            color_continuous_scale="Viridis"
        )
        fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig.update_layout(
            showlegend=False,
            yaxis={'categoryorder':'total ascending'},
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 得分分布")
        fig = px.histogram(
            df_final,
            x="总得分",
            nbins=20,
            title="",
            labels={"总得分": "总得分", "count": "人数"}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # 详细数据表格
    st.subheader("📋 详细数据")
    st.dataframe(
        df_final.style.background_gradient(subset=['总得分'], cmap='RdYlGn'),
        use_container_width=True,
        height=400
    )

with tab2:
    st.header("📈 进步分析")
    
    if len(rank_cols) < 2:
        st.info("💡 **提示**：当前只有 1 次考试数据，无法查看进步情况。\n\n请上传更多成绩文件后点击「重置」重新分析。")
    else:
        # 进步趋势图
        st.subheader("📉 排名趋势（选择学生）")
        
        selected_students = st.multiselect(
            "选择要对比的学生（最多5个）",
            df_all["姓名"].tolist(),
            default=df_all["姓名"].tolist()[:3]
        )
        
        if selected_students:
            fig = go.Figure()
            
            for student in selected_students[:5]:
                student_data = df_all[df_all["姓名"] == student]
                ranks = [student_data[col].values[0] for col in rank_cols]
                exam_numbers = [f"第{i+1}次" for i in range(len(ranks))]
                
                fig.add_trace(go.Scatter(
                    x=exam_numbers,
                    y=ranks,
                    mode='lines+markers',
                    name=student,
                    hovertemplate='<b>%{fullData.name}</b><br>排名: %{y}<extra></extra>'
                ))
            
            fig.update_layout(
                title="排名趋势对比（排名越小越好）",
                xaxis_title="考试次数",
                yaxis_title="排名",
                yaxis_autorange='reversed',
                hovermode='x unified',
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 进步榜单
        col1, col2 = st.columns(2)
        
        with col1:
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
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🔥 连续进步奖励")
            continuous_progress = df_score[df_score["连续进步次数"] > 0]
            
            if len(continuous_progress) > 0:
                fig = px.scatter(
                    continuous_progress,
                    x="连续进步次数",
                    y="连续进步加分",
                    size="连续进步加分",
                    hover_data=["姓名"],
                    text="姓名",
                    color="连续进步加分",
                    color_continuous_scale="Reds"
                )
                fig.update_traces(textposition='top center')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无连续进步的学生")

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
            st.dataframe(
                problem_students.style.background_gradient(subset=['标准差'], cmap='Reds'),
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
            st.subheader("📉 个人排名趋势")
            ranks = [student_history[col] for col in rank_cols]
            exam_numbers = [f"第{i+1}次" for i in range(len(ranks))]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=exam_numbers,
                y=ranks,
                mode='lines+markers+text',
                text=ranks,
                textposition='top center',
                line=dict(width=3),
                marker=dict(size=12)
            ))
            fig.update_layout(
                yaxis_autorange='reversed',
                yaxis_title="排名",
                xaxis_title="考试次数",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 得分构成
            st.subheader("🥧 得分构成")
            
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
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 各科成绩雷达图
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
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("需要科目成绩数据才能显示雷达图")

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
