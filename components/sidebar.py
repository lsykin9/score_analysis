"""
侧边栏组件
负责参数配置和文件上传界面
"""
import streamlit as st
import pandas as pd
import io
import time


@st.fragment
def _render_param_settings():
    """渲染参数设置区域（使用fragment避免刷新主页面）"""
    # 初始化expander状态
    if 'param_expander_expanded' not in st.session_state:
        st.session_state.param_expander_expanded = False
    
    # 创建可折叠的参数设置区域
    expander = st.expander("📊 评分参数设置", expanded=st.session_state.param_expander_expanded)
    
    with expander:
        _render_interval_settings()
        _render_line_and_bonus_settings()
        _render_rank_bonus_settings()
        _render_chain_bonus_settings()
        _render_score_bonus_settings()
        _render_bias_penalty_settings()


def render_sidebar():
    """渲染侧边栏 - 参数配置和文件上传"""
    
    with st.sidebar:
        st.header("⚙️ 参数配置")
        
        # 使用fragment渲染参数设置，避免全页刷新
        _render_param_settings()
        
        st.markdown("---")
        _render_file_upload()
        
        st.markdown("---")
        _render_control_buttons()
        
        st.markdown("---")
        _render_usage_info()


def _save_interval_values():
    """从session_state的临时key中保存区间值到rank_intervals"""
    for idx, interval in enumerate(st.session_state.rank_intervals):
        interval_id = interval["id"]
        start_key = f"start_{interval_id}"
        end_key = f"end_{interval_id}"
        weight_key = f"weight_{interval_id}"
        
        if start_key in st.session_state:
            st.session_state.rank_intervals[idx]["start"] = st.session_state[start_key]
        if end_key in st.session_state:
            st.session_state.rank_intervals[idx]["end"] = st.session_state[end_key]
        if weight_key in st.session_state:
            st.session_state.rank_intervals[idx]["weight"] = st.session_state[weight_key]


def _save_bonus_values():
    """从session_state的临时key中保存奖励值到rank_bonuses"""
    for idx, bonus in enumerate(st.session_state.rank_bonuses):
        bonus_id = bonus["id"]
        thresh_key = f"bonus_thresh_{bonus_id}"
        val_key = f"bonus_val_{bonus_id}"
        
        if thresh_key in st.session_state:
            st.session_state.rank_bonuses[idx]["threshold"] = st.session_state[thresh_key]
        if val_key in st.session_state:
            st.session_state.rank_bonuses[idx]["bonus"] = st.session_state[val_key]


def _render_interval_settings():
    """渲染区间权重设置"""
    st.subheader("区间权重")
    
    # 显示当前所有区间
    for idx, interval in enumerate(st.session_state.rank_intervals):
        interval_id = interval["id"]
        # 区间标题
        st.markdown(f"**区间 {idx + 1}**: `({interval['start']}-{interval['end']})`")
        
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            st.number_input("起始", value=int(interval["start"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"start_{interval_id}", label_visibility="visible")
        
        with col2:
            st.number_input("结束", value=int(interval["end"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"end_{interval_id}", label_visibility="visible")
        
        with col3:
            st.number_input("权重", value=float(interval["weight"]), step=0.1, min_value=0.0, disabled=st.session_state.analysis_started, key=f"weight_{interval_id}", label_visibility="visible")
        
        with col4:
            st.write("")  # 空行对齐
            # 删除按钮(保留至少1个区间)
            can_delete = len(st.session_state.rank_intervals) > 1
            if st.button("🗑️", key=f"del_{interval_id}", disabled=st.session_state.analysis_started or not can_delete):
                # 操作锁避免重复
                if not st.session_state.get('_operation_lock', False):
                    st.session_state._operation_lock = True
                    _save_interval_values()  # 先保存其他区间的值
                    # 立即删除
                    st.session_state.rank_intervals = [
                        iv for iv in st.session_state.rank_intervals if iv["id"] != interval_id
                    ]
                    # 清理废弃的key
                    keys_to_delete = [k for k in st.session_state.keys() 
                                     if k.startswith(f"start_{interval_id}") or 
                                        k.startswith(f"end_{interval_id}") or 
                                        k.startswith(f"weight_{interval_id}") or 
                                        k.startswith(f"del_{interval_id}")]
                    for key in keys_to_delete:
                        del st.session_state[key]
                    st.session_state.param_expander_expanded = True
                    time.sleep(0.15)  # 延迟配合CSS过渡动画
                    st.session_state._operation_lock = False
                    st.rerun(scope="fragment")
    
    # 添加新区间按钮
    if not st.session_state.analysis_started:
        if st.button("➕ 添加区间", key="add_interval"):
            # 操作锁避免重复
            if not st.session_state.get('_operation_lock', False):
                st.session_state._operation_lock = True
                # 先保存当前所有输入框的值到区间数据
                _save_interval_values()
                
                # 在末尾添加新区间
                if len(st.session_state.rank_intervals) > 0:
                    last_interval = st.session_state.rank_intervals[-1]
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
                st.session_state.param_expander_expanded = True
                time.sleep(0.15)  # 延迟配合CSS过渡动画
                st.session_state._operation_lock = False
                st.rerun(scope="fragment")


def _render_line_and_bonus_settings():
    """渲染排名线和过线奖励设置"""
    st.markdown("---")
    st.subheader("排名线和过线奖励")
    st.session_state.config_params["线（排名）"] = st.number_input("线（排名）", value=st.session_state.config_params["线（排名）"], step=1, disabled=st.session_state.analysis_started)
    st.session_state.config_params["过线奖励"] = st.number_input("过线奖励", value=st.session_state.config_params["过线奖励"], step=1, disabled=st.session_state.analysis_started)


def _render_rank_bonus_settings():
    """渲染排名奖励设置"""
    st.markdown("---")
    st.subheader("排名奖励")
    
    # 显示当前所有排名奖励
    for idx, bonus in enumerate(st.session_state.rank_bonuses):
        bonus_id = bonus["id"]
        # 奖励标题
        st.markdown(f"**奖励档位 {idx + 1}**: `前 {bonus['threshold']} 名 → {bonus['bonus']} 分`")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.number_input("前N名", value=int(bonus["threshold"]), step=1, min_value=1, disabled=st.session_state.analysis_started, key=f"bonus_thresh_{bonus_id}")
        
        with col2:
            st.number_input("奖励分", value=int(bonus["bonus"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"bonus_val_{bonus_id}")
        
        with col3:
            st.write("")  # 空行对齐
            # 删除按钮(保留至少1个奖励)
            if st.button("🗑️", key=f"del_bonus_{bonus_id}", disabled=st.session_state.analysis_started or len(st.session_state.rank_bonuses) <= 1):
                # 操作锁避免重复
                if not st.session_state.get('_operation_lock', False):
                    st.session_state._operation_lock = True
                    _save_bonus_values()  # 先保存其他奖励的值
                    # 立即删除
                    st.session_state.rank_bonuses = [
                        b for b in st.session_state.rank_bonuses if b["id"] != bonus_id
                    ]
                    # 清理废弃的key
                    keys_to_delete = [k for k in st.session_state.keys() 
                                     if k.startswith(f"bonus_thresh_{bonus_id}") or 
                                        k.startswith(f"bonus_val_{bonus_id}") or 
                                        k.startswith(f"del_bonus_{bonus_id}")]
                    for key in keys_to_delete:
                        del st.session_state[key]
                    st.session_state.param_expander_expanded = True
                    time.sleep(0.15)  # 延迟配合CSS过渡动画
                    st.session_state._operation_lock = False
                    st.rerun(scope="fragment")
    
    # 添加新排名奖励按钮
    if not st.session_state.analysis_started:
        if st.button("➕ 添加排名奖励", key="add_bonus"):
            # 操作锁避免重复
            if not st.session_state.get('_operation_lock', False):
                st.session_state._operation_lock = True
                # 先保存当前所有输入框的值
                _save_bonus_values()
                
                # 默认新奖励阈值为最后一个+10
                last_threshold = st.session_state.rank_bonuses[-1]["threshold"] if st.session_state.rank_bonuses else 0
                
                new_id = st.session_state.next_bonus_id
                st.session_state.next_bonus_id += 1
                
                st.session_state.rank_bonuses.append({
                    "id": new_id,
                    "threshold": last_threshold + 10,
                    "bonus": 5
                })
                st.session_state.param_expander_expanded = True
                time.sleep(0.15)  # 延迟配合CSS过渡动画
                st.session_state._operation_lock = False
                st.rerun(scope="fragment")


def _render_chain_bonus_settings():
    """渲染连续进步奖励设置"""
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


def _render_score_bonus_settings():
    """渲染总分奖励设置"""
    st.markdown("---")
    st.subheader("总分奖励")
    st.session_state.config_params["总分大于600奖励"] = st.number_input("总分>600", value=st.session_state.config_params["总分大于600奖励"], step=1, disabled=st.session_state.analysis_started)
    st.session_state.config_params["总分大于650奖励"] = st.number_input("总分>650", value=st.session_state.config_params["总分大于650奖励"], step=1, disabled=st.session_state.analysis_started)
    st.session_state.config_params["总分大于700奖励"] = st.number_input("总分>700", value=st.session_state.config_params["总分大于700奖励"], step=1, disabled=st.session_state.analysis_started)


def _render_bias_penalty_settings():
    """渲染偏科扣分设置"""
    st.markdown("---")
    st.subheader("偏科扣分")
    st.session_state.config_params["轻微偏科扣分"] = st.number_input("轻微偏科", value=st.session_state.config_params["轻微偏科扣分"], step=1, disabled=st.session_state.analysis_started)
    st.session_state.config_params["明显偏科扣分"] = st.number_input("明显偏科", value=st.session_state.config_params["明显偏科扣分"], step=1, disabled=st.session_state.analysis_started)
    st.session_state.config_params["严重偏科扣分"] = st.number_input("严重偏科", value=st.session_state.config_params["严重偏科扣分"], step=1, disabled=st.session_state.analysis_started)


def _render_file_upload():
    """渲染文件上传区域"""
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


def _render_control_buttons():
    """渲染控制按钮"""
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


def _render_usage_info():
    """渲染使用说明"""
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
