"""
Session State 初始化模块
负责初始化所有 Streamlit session state 变量
"""
import streamlit as st


def initialize_session_state():
    """初始化所有session state变量"""
    
    # 文件上传相关
    if 'score_files' not in st.session_state:
        st.session_state.score_files = []
    if 'analysis_started' not in st.session_state:
        st.session_state.analysis_started = False
    if 'history_file_content' not in st.session_state:
        st.session_state.history_file_content = None
    if 'history_exam_count' not in st.session_state:
        st.session_state.history_exam_count = 0

    # 删除标记
    if 'interval_to_delete' not in st.session_state:
        st.session_state.interval_to_delete = None
    if 'bonus_to_delete' not in st.session_state:
        st.session_state.bonus_to_delete = None

    # ID计数器(用于生成唯一ID)
    if 'next_interval_id' not in st.session_state:
        st.session_state.next_interval_id = 0
    if 'next_bonus_id' not in st.session_state:
        st.session_state.next_bonus_id = 0
    if 'next_group_bonus_id' not in st.session_state:
        st.session_state.next_group_bonus_id = 0

    # 动态区间权重列表
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

    # 动态年级排名奖励列表
    if 'rank_bonuses' not in st.session_state:
        st.session_state.rank_bonuses = [
            {"id": 0, "threshold": 10, "bonus": 30},
            {"id": 1, "threshold": 20, "bonus": 25},
            {"id": 2, "threshold": 30, "bonus": 20},
            {"id": 3, "threshold": 50, "bonus": 15},
            {"id": 4, "threshold": 100, "bonus": 10}
        ]
        st.session_state.next_bonus_id = 5

    # 动态集团排名奖励列表
    if 'group_rank_bonuses' not in st.session_state:
        st.session_state.group_rank_bonuses = [
            {"id": 0, "threshold": 50, "bonus": 20},
            {"id": 1, "threshold": 100, "bonus": 15},
            {"id": 2, "threshold": 200, "bonus": 10},
            {"id": 3, "threshold": 300, "bonus": 5}
        ]
        st.session_state.next_group_bonus_id = 4

    # 默认参数配置
    if 'config_params' not in st.session_state:
        st.session_state.config_params = {
            "A线（排名）": 430,
            "A线过线奖励": 5,
            "B线（排名）": 500,
            "B线过线奖励": 3,
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
