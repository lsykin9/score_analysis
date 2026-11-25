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
from components.critical_students import render_critical_students

# 导入工具
from utils.data_processor import process_data
from utils.progress_rules import (
    calculate_progress_chain, describe_progress_rule, get_tie_progress_rule,
    is_current_progress, get_rank_basis, rank_basis_label, RANK_BASIS,
)
from utils.rank_history import (
    get_grade_rank_columns, get_group_rank_columns, get_progress_rank_columns,
    get_exam_label, get_rank_history,
)
from config.scoring_schemes import SCHEME_LABELS, GRADE_REWARD_ENABLED, GROUP_REWARD_ENABLED
from config.bias_rules import BIAS_LEVELS, BIAS_BALANCED, describe_bias_rule
from utils.subject_bias import prepare_bias_exams
from utils.critical_students import build_critical_analysis

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

# 处理上传的文件
try:
    df_all, df_score, df_final, df_bias, has_subjects, rank_cols, score_cols, subjects, bias_dict, exam_labels = process_data()
    
    progress_rank_cols = get_progress_rank_columns(df_all.columns, st.session_state.config_params)
    progress_basis = rank_basis_label(st.session_state.config_params)

    # 获取集团排名列
    group_rank_cols = []
    for col in df_all.columns:
        # 新格式：总分集团排名_考试1 或 语文集团排名_考试1
        # 旧格式：总分_集团排名_考试1 或 集团排名_考试1
        if col.startswith("集团排名_"):
            group_rank_cols.append(col)
        elif "集团排名_" in col:
            group_rank_cols.append(col)
    
    st.success(f"✅ 数据处理完成！当前使用{SCHEME_LABELS[get_rank_basis(st.session_state.config_params)]}")
    
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
st.session_state['progress_rank_cols'] = progress_rank_cols
st.session_state['score_cols'] = score_cols
st.session_state['group_rank_cols'] = group_rank_cols
st.session_state['subjects'] = subjects
st.session_state['bias_dict'] = bias_dict
st.session_state['exam_labels'] = exam_labels

# 临界生结果只在当前数据或评分配置变化后重建，筛选和选择学生复用会话缓存。
critical_analysis = None
if has_subjects:
    critical_key = st.session_state['_analysis_cache']['key'] + ':critical-v1'
    if st.session_state.get('_critical_cache', {}).get('key') != critical_key:
        labels = [get_exam_label(col) for col in progress_rank_cols]
        st.session_state['_critical_cache'] = {
            'key': critical_key, 'data': build_critical_analysis(df_all, labels, bias_dict),
        }
    critical_analysis = st.session_state['_critical_cache']['data']

# 主界面 - 标签页
tab1, tab2, tab3, critical_tab, tab4, tab5, tab6 = st.tabs([
    "📊 总览", 
    "📈 进步分析", 
    "🎯 偏科检测", 
    "🎓 临界生",
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
            bias_count = len(df_bias[df_bias["偏科等级"].isin(BIAS_LEVELS)])
            st.metric("偏科人数", bias_count)
        else:
            st.metric("偏科检测", "需要科目成绩")
    
    with col4:
        if len(progress_rank_cols) >= 2:
            progress_count = sum(
                is_current_progress(
                    get_rank_history(row, progress_rank_cols, subjects if has_subjects else []),
                    st.session_state.config_params,
                )
                for _, row in df_final.iterrows()
            )
            st.metric("进步人数", progress_count)
        else:
            st.metric("考试次数", len(progress_rank_cols))
    
    st.markdown("---")
    
    st.subheader("年级 / 集团排名对照")
    st.caption("进步名次为正表示提升，为负表示下降；两种排名的变化仅作对照，不额外重复扣分。")
    st.dataframe(df_score[["姓名", "年级进步名次", "集团进步名次", "双排名对照"]],
                 use_container_width=True, hide_index=True)

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
    score_columns = ["区间进步得分", "连续进步加分", "年级排名加分", "A/B线奖励", "集团排名加分", "总得分"]
    if "总分奖励" in df_display.columns:
        score_columns.append("总分奖励")
    if "东校状元奖" in df_display.columns:
        score_columns.append("东校状元奖")
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
    
    # 使用 Streamlit 原生数值格式，避免 Styler 引入 Matplotlib 和 macOS 字体扫描。
    column_config = {
        column: st.column_config.NumberColumn(
            column, format="%.0f" if pattern == "{:.0f}" else "%.1f"
        )
        for column, pattern in format_dict.items()
    }
    st.dataframe(df_display, column_config=column_config,
                 use_container_width=True, height=400)

# Tab 2: 进步分析
with tab2:
    st.header("📈 进步分析")
    st.caption(describe_progress_rule(st.session_state.config_params))
    st.caption("进步人数包含排名提升和符合限定范围的持平；缺考不计入本次进步人数。")
    
    if len(progress_rank_cols) < 2:
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
                index=1 if get_rank_basis(st.session_state.config_params) == 'group' and has_group_rank else 0
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
                target_cols = get_grade_rank_columns(df_all.columns)
            else:
                target_cols = get_progress_rank_columns(df_all.columns, {RANK_BASIS: 'group'})

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
                if selected_subject == "总分":
                    label = get_exam_label(col)
                elif '_' in col:
                    label = col.rsplit('_', 1)[-1]
                else:
                    label = col
                exam_display_names.append(label)
            
            for student in selected_students[:5]:
                student_data = df_all[df_all["姓名"] == student]
                if not student_data.empty:
                    if selected_subject == "总分":
                        history = get_rank_history(student_data.iloc[0], target_cols, subjects)
                        ranks = [rank if rank else None for rank in history]
                    else:
                        ranks = []
                        for col in target_cols:
                            val = student_data[col].values[0]
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
                BIAS_BALANCED: "#90EE90",
                "轻微偏科": "#FFD700",
                "明显偏科": "#FFA500",
                "重度偏科": "#FF6347"
            }
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 偏科学生详情
        st.subheader("偏科学生详情")
        
        st.caption(describe_bias_rule())
        st.caption("以各场物理类 A/B 分数线为参照，不使用班级均分。化学、生物按选科线各取一半。偏科等级为最终计分档位，本次与持续诊断分别展示。")
        line_exams = prepare_bias_exams(df_all, [get_exam_label(col) for col in progress_rank_cols], subjects)
        line_issues = [f"{exam['考试']}：{exam['资料说明']}" for exam in line_exams if exam['资料说明']]
        if line_issues:
            st.info("以下考试不参与偏科判定，也不借用其他场次的分数线：" + "；".join(line_issues))
        line_rows = [dict(考试=exam['考试'], 科目=subject,
                          A线=exam['分数线']['A'].get(subject), B线=exam['分数线']['B'].get(subject),
                          来源=exam['分数线'].get('来源', ''), 资料说明=exam['资料说明'])
                     for exam in line_exams for subject in subjects]
        with st.expander("查看每场使用的 A/B 分数线"):
            st.dataframe(pd.DataFrame(line_rows), use_container_width=True, hide_index=True)
        biased_students = df_bias[df_bias["偏科等级"].isin(BIAS_LEVELS)]
        unavailable = df_bias[~df_bias["偏科等级"].isin((*BIAS_LEVELS, BIAS_BALANCED))]
        if len(biased_students) > 0:
            st.dataframe(biased_students, use_container_width=True, hide_index=True,
                         column_config={"偏科指数": st.column_config.NumberColumn(format="%.3f")})
        elif len(df_bias) > len(unavailable):
            st.success("可判定学生中，未发现达到当前计分条件的学科短板。")
        if len(unavailable):
            st.info(f"另有 {len(unavailable)} 人缺考或数据不足，本次不作偏科扣分。")
            st.dataframe(unavailable[['姓名', '偏科等级', '判定说明']],
                         use_container_width=True, hide_index=True)
        diagnosis_student = st.selectbox('查看个人偏科历史', df_all['姓名'].tolist(), key='bias_history_student')
        diagnosis = bias_dict.get(diagnosis_student, {})
        if diagnosis:
            cols = st.columns(3)
            cols[0].metric('本次偏科等级', diagnosis['本次偏科等级'])
            cols[1].metric('持续偏科等级', diagnosis['持续偏科等级'])
            cols[2].metric('最终计分等级', diagnosis['偏科等级'])
            st.caption(diagnosis['判定说明'])
            st.subheader('最近多场持续性分析')
            st.dataframe(pd.DataFrame(diagnosis['持续学科明细']), use_container_width=True, hide_index=True)
            st.subheader('历次总分与目标线差')
            st.dataframe(pd.DataFrame(diagnosis['考试汇总']), use_container_width=True, hide_index=True)
            history = pd.DataFrame(diagnosis['历史明细'])
            if not history.empty:
                st.subheader('各科短板差距变化')
                chart = px.line(history, x='考试', y='短板差距', color='科目', markers=True,
                                category_orders={'考试': list(dict.fromkeys(history['考试']))})
                chart.add_hline(y=st.session_state.config_params['轻微偏科_AB档差距'], line_dash='dash')
                chart.update_traces(connectgaps=False)
                st.plotly_chart(chart, use_container_width=True)
                with st.expander('查看历次各科分数、线差和判定明细'):
                    st.dataframe(history, use_container_width=True, hide_index=True)

with critical_tab:
    if critical_analysis is None:
        st.header('🎓 临界生')
        st.info('临界生分析需要六科成绩和物理类A线，请上传包含分数线的新模板。')
    else:
        render_critical_students(critical_analysis)

# 学生详情
with tab4:
    st.header("👤 学生详情查询")
    
    selected_student = st.selectbox("选择学生", df_all["姓名"].tolist())
    
    if selected_student:
        student_data = df_all[df_all["姓名"] == selected_student].iloc[0]
        student_score = df_score[df_score["姓名"] == selected_student].iloc[0]
        
        st.caption(describe_progress_rule(st.session_state.config_params))

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
        
        st.write(f"**双排名对照**：{student_score['双排名对照']}")
        comparison = pd.DataFrame([{
            "年级进步名次": student_score['年级进步名次'],
            "集团进步名次": student_score['集团进步名次'],
        }])
        st.dataframe(comparison, use_container_width=True, hide_index=True)

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
        score_components["A/B线奖励"] = student_score.get("A/B线奖励", 0)
        
        if "总分奖励" in student_score.index:
            score_components["总分奖励"] = student_score.get("总分奖励", 0)
        
        if "东校状元奖" in student_score.index:
            champion_bonus = student_score.get("东校状元奖", 0)
            if champion_bonus != 0:
                score_components["东校状元奖"] = champion_bonus
        
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
                index=1 if get_rank_basis(st.session_state.config_params) == 'group' and has_group_rank else 0,
                key="detail_rank_type"
            )
        
        # 根据选择提取对应的排名列
        if detail_selected_subject == "总分":
            if detail_rank_type == "年级排名":
                detail_target_cols = get_grade_rank_columns(df_all.columns)
            else:
                detail_target_cols = get_progress_rank_columns(df_all.columns, {RANK_BASIS: 'group'})

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
            
            if detail_selected_subject == "总分":
                history = get_rank_history(student_data, detail_target_cols, subjects)
                ranks = [rank if rank else None for rank in history]
                exam_names = [get_exam_label(col) for col in detail_target_cols]
            else:
                for col in detail_target_cols:
                    val = student_data[col]
                    ranks.append(None if val == 0 else val)
                    exam_names.append(col.rsplit('_', 1)[-1])
            
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
                latest_label = get_exam_label(progress_rank_cols[-1]) if progress_rank_cols else ''
                column = f'{subj}_{latest_label}'
                if column in df_all.columns:
                    subject_scores[subj] = student_data[column]
            
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
        
        # 与评分流程使用相同的年级排名列、考试名称及缺考规则。
        total_rank_cols = progress_rank_cols
        ranks = get_rank_history(student_data, total_rank_cols, subjects)
        detail_grade_ranks = get_rank_history(student_data, get_grade_rank_columns(df_all.columns), subjects)
        detail_group_ranks = get_rank_history(student_data,
            get_progress_rank_columns(df_all.columns, {RANK_BASIS: 'group'}), subjects)

        # 1. 排名历史
        st.markdown(f"### 1️⃣ 排名历史（总分{progress_basis}排名）")
        if not total_rank_cols:
            st.warning(f"⚠️ 未找到总分{progress_basis}排名数据")
        else:
            rank_data = [
                {"考试": get_exam_label(col), f"{progress_basis}排名": rank if rank else "缺考或无排名"}
                for col, rank in zip(total_rank_cols, ranks)
            ]
            st.table(pd.DataFrame(rank_data))

        # 2. 区间进步得分
        st.markdown("### 2️⃣ 区间进步得分")
        
        if len(total_rank_cols) >= 2:
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
                        "对比": f"{get_exam_label(total_rank_cols[pre_exam_idx - 1])} vs {get_exam_label(total_rank_cols[cur_exam_idx - 1])}",
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
                        "对比": f"{get_exam_label(total_rank_cols[pre_exam_idx - 1])} vs {get_exam_label(total_rank_cols[cur_exam_idx - 1])}",
                        "排名变化": f"{_pre} → {_cur}",
                        "进步名次": _pre - _cur,
                        "得分": "0.0"
                    })
            
            if progress_details:
                st.table(pd.DataFrame(progress_details))
                st.info("💡 区间进步分只计算最近一次有效考试的排名提升；符合限定范围的持平只增加连续次数，此项仍为 0。")
            else:
                st.write("无区间进步")
            st.write(f"**总区间进步得分**: {student_score['区间进步得分']:.1f}")
        else:
            st.info(f"💡 当前只有 {len(total_rank_cols)} 次考试数据，需要至少2次考试才能计算进步得分")
        
        # 3. 连续进步
        st.markdown("### 3️⃣ 连续进步加分")
        st.write(f"**连续进步次数**: {int(student_score['连续进步次数'])}")
        st.write(f"**连续进步加分**: {student_score['连续进步加分']:.1f}")
        st.caption(describe_progress_rule(st.session_state.config_params))
        _, chain_details = calculate_progress_chain(ranks, st.session_state.config_params)
        if chain_details:
            st.table(pd.DataFrame(chain_details))
        if ranks and ranks[-1] == 0:
            st.info("本次缺考，连续进步次数和奖励按此前有效考试保留，本次不增加次数。")
        
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
        if detail_grade_ranks:
            latest_rank = detail_grade_ranks[-1]
            st.write(f"**最新年级排名**: {latest_rank if latest_rank > 0 else '缺考'}")
            st.write(f"**年级排名加分**: {student_score['年级排名加分']:.1f}")
        else:
            st.write("**无年级排名数据**")
        
        if not st.session_state.config_params.get(GRADE_REWARD_ENABLED, True):
            st.caption("当前方案已关闭年级排名档位奖励。")
        if not st.session_state.config_params.get(GROUP_REWARD_ENABLED, True):
            st.caption("当前方案已关闭集团排名奖励。")

        # 显示年级排名配置
        with st.expander("查看年级排名奖励配置"):
            rank_config = pd.DataFrame(st.session_state.rank_bonuses)[["threshold", "bonus"]]
            rank_config.columns = ["排名阈值", "奖励分数"]
            st.table(rank_config)

        # A/B 线奖励独立展示，不受年级排名奖励开关影响。
        st.markdown("### 5️⃣ A/B线奖励")
        st.write(f"**A/B线奖励**: {student_score['A/B线奖励']:.1f}")
        with st.expander("查看 A/B 线奖励配置"):
            line_basis = rank_basis_label(st.session_state.config_params)
            st.write(f"**A线**: 总分{line_basis}排名≤{st.session_state.config_params.get('A线（排名）', 430)}名，奖励: {st.session_state.config_params.get('A线过线奖励', 5)}分")
            st.write(f"**B线**: 总分{line_basis}排名≤{st.session_state.config_params.get('B线（排名）', 500)}名，奖励: {st.session_state.config_params.get('B线过线奖励', 3)}分")
        
        # 5. 集团排名加分
        if group_rank_cols and len(group_rank_cols) > 0:
            st.markdown("### 6️⃣ 集团排名加分")
            
            # 筛选出总分的集团排名列
            # 新格式：总分集团排名_考试1 或 旧格式：总分_集团排名_考试1
            total_group_rank_cols = [col for col in group_rank_cols 
                                    if col.startswith("总分集团排名_") 
                                    or col.startswith("总分_集团排名_") 
                                    or (col.startswith("集团排名_") and not any(subj in col for subj in subjects))]
            
            if total_group_rank_cols and len(total_group_rank_cols) > 0:
                latest_group_rank = detail_group_ranks[-1] if detail_group_ranks else 0
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
            st.markdown("### 7️⃣ 总分奖励")
            latest_score = student_data[score_cols[-1]]
            st.write(f"**最新总分**: {latest_score:.1f}")
            st.write(f"**总分奖励**: {student_score['总分奖励']:.1f}")
            
            with st.expander("查看总分奖励配置"):
                score_config = pd.DataFrame(st.session_state.score_bonuses)[["threshold", "bonus"]]
                score_config.columns = ["分数阈值", "奖励分数"]
                st.table(score_config)
        
        # 7. 偏科扣分
        if has_subjects:
            st.markdown("### 8️⃣ 偏科扣分")
            student_bias = df_bias[df_bias["姓名"] == selected_student]
            if not student_bias.empty:
                bias_info = student_bias.iloc[0]
                st.write(f"**偏科等级**: {bias_info['偏科等级']}")
                bias_details = bias_dict.get(selected_student, {})
                index = bias_details.get('偏科指数')
                st.write(f"**本次偏科指数（A/B档位差距）**: {index:.3f}" if index is not None else "**本次偏科指数**: 暂不能判定")
                st.write(f"**本次等级**: {bias_details.get('本次偏科等级', '数据不足')}；**持续等级**: {bias_details.get('持续偏科等级', '待观察')}")
                st.write(f"**薄弱科目**: {'、'.join(bias_details.get('薄弱科目', [])) or '-'}")
                st.caption(bias_details.get('判定说明', ''))
                if bias_details.get('学科明细'):
                    st.dataframe(pd.DataFrame(bias_details['学科明细']), use_container_width=True, hide_index=True)
                if bias_details.get('持续学科明细'):
                    st.dataframe(pd.DataFrame(bias_details['持续学科明细']), use_container_width=True, hide_index=True)

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
                "A/B线奖励": student_score['A/B线奖励'],
                "集团排名加分": student_score['集团排名加分'],
            }
            if '总分奖励' in student_score.index:
                score_breakdown["总分奖励"] = student_score['总分奖励']
            if '东校状元奖' in student_score.index:
                score_breakdown["东校状元奖"] = student_score['东校状元奖']
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
    
    # 同一批成绩的下载文件只生成一次，筛选或切换学生时复用。
    export_key = st.session_state['_analysis_cache']['key'] + ':ab-history-v3:critical-v1'
    if st.session_state.get('_export_cache', {}).get('key') != export_key:
        st.session_state['_export_cache'] = {'key': export_key}
    export_cache = st.session_state['_export_cache']

    if 'raw' not in export_cache:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 新格式：每次考试单独保存为一个工作表
            # 从 df_all 中提取每次考试的数据
            import re

            # 考试顺序与评分一致，分数线列不被误识别为另一场考试。
            exam_labels_sorted = list(dict.fromkeys(get_exam_label(col) for col in progress_rank_cols))

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
        export_cache['raw'] = output.getvalue()

    st.download_button(
        label="📥 下载成绩总表（原始数据）",
        data=export_cache['raw'],
        file_name="成绩总表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("---")
    
    # 导出完整分析结果
    st.subheader("2. 导出完整分析结果")
    st.info("💡 此文件包含原始数据、得分明细和偏科分析，用于查看完整结果")
    
    if 'analysis' not in export_cache:
        output2 = BytesIO()
        with pd.ExcelWriter(output2, engine='openpyxl') as writer:
            df_final.to_excel(writer, sheet_name='完整结果', index=False)
            df_score.to_excel(writer, sheet_name='得分明细', index=False)
            tie_enabled, tie_limit = get_tie_progress_rule(st.session_state.config_params)
            pd.DataFrame([
                {"项目": "评分方案", "设置": SCHEME_LABELS[get_rank_basis(st.session_state.config_params)]},
                {"项目": "进步排名依据", "设置": f"总分{progress_basis}排名"},
                {"项目": "年级排名奖励", "设置": "开启" if st.session_state.config_params.get(GRADE_REWARD_ENABLED, True) else "关闭"},
                {"项目": "A/B线奖励", "设置": f"独立计算，按总分{rank_basis_label(st.session_state.config_params)}排名达标发放，两线取较高奖励"},
                {"项目": "集团排名奖励", "设置": "开启" if st.session_state.config_params.get(GROUP_REWARD_ENABLED, True) else "关闭"},
                {"项目": f"限定{progress_basis}排名内持平计入连续进步", "设置": "开启" if tie_enabled else "关闭"},
                {"项目": f"{progress_basis}排名上限（含）", "设置": tie_limit},
                {"项目": "连续进步规则", "设置": describe_progress_rule(st.session_state.config_params)},
                {"项目": "缺考处理", "设置": "跳过缺考；最新缺考保留此前连续次数，本次不增加"},
                {"项目": "持平区间进步得分", "设置": 0},
            ]).to_excel(writer, sheet_name='连续进步规则', index=False)
            parameter_rows = []
            for item in st.session_state.rank_intervals:
                parameter_rows.append({"类别": f"{progress_basis}区间权重", "条件": f"{item['start']}～{item['end']}名", "数值": item['weight']})
            for item in st.session_state.chain_bonuses:
                parameter_rows.append({"类别": "连续奖励", "条件": f"连续{item['times']}次", "数值": item['bonus']})
            for key, label in [('rank_bonuses', '年级排名奖励'), ('group_rank_bonuses', '集团排名奖励')]:
                for item in st.session_state[key]:
                    parameter_rows.append({"类别": label, "条件": f"前{item['threshold']}名", "数值": item['bonus']})
            for line in ['A', 'B']:
                parameter_rows.append({"类别": f"{line}线年级奖励", "条件": f"前{st.session_state.config_params[f'{line}线（排名）']}名", "数值": st.session_state.config_params[f'{line}线过线奖励']})
            pd.DataFrame(parameter_rows).to_excel(writer, sheet_name='当前方案参数', index=False)
            if has_subjects and df_bias is not None:
                df_bias.to_excel(writer, sheet_name='偏科检测', index=False)
                detail_rows = [dict(姓名=name, 分析考试=info['分析考试'], **detail)
                               for name, info in bias_dict.items() for detail in info['学科明细']]
                pd.DataFrame(detail_rows).to_excel(writer, sheet_name='偏科学科明细', index=False)
                for field, sheet in [('历史明细', '偏科历史明细'), ('持续学科明细', '持续偏科明细'),
                                     ('考试汇总', '偏科考试汇总')]:
                    rows = [dict(姓名=name, **record) for name, info in bias_dict.items() for record in info[field]]
                    pd.DataFrame(rows).to_excel(writer, sheet_name=sheet, index=False)
                pd.DataFrame(line_rows).to_excel(writer, sheet_name='偏科分数线', index=False)
                bias_rules = [{"项目": "算法", "设置": describe_bias_rule()},
                              {"项目": "参照范围", "设置": "各场物理类A/B分数线，不使用班级均分"},
                              {"项目": "选科线拆分", "设置": "按用户规则，化学、生物各取选科合计线的一半"},
                              {"项目": "缺少分数线", "设置": "该场不参与偏科判定；若本次缺少则本次不扣分"},
                              {"项目": "指数单位", "设置": "一个A/B档位即该科A线与B线之差；阈值和扣分属于教学规则"}]
                for level in BIAS_LEVELS:
                    bias_rules.extend([
                        {"项目": level + "差距阈值", "设置": st.session_state.config_params[level + '_AB档差距']},
                        {"项目": level + "扣分", "设置": st.session_state.config_params[level + '扣分']},
                    ])
                pd.DataFrame(bias_rules).to_excel(writer, sheet_name='偏科规则', index=False)
            if critical_analysis is not None:
                critical_summary = critical_analysis['summary']
                watchlist = (critical_summary[critical_summary['观察名单']]
                             if not critical_summary.empty else critical_summary)
                watchlist.to_excel(writer, sheet_name='临界生名单', index=False)
                critical_analysis['history'].to_excel(writer, sheet_name='临界生历史', index=False)
                critical_analysis['rules'].to_excel(writer, sheet_name='临界生规则', index=False)
        export_cache['analysis'] = output2.getvalue()

    st.download_button(
        label="📥 下载完整分析结果",
        data=export_cache['analysis'],
        file_name="完整分析结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
