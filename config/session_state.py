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
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0  # 用于重置file_uploader

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
    if 'next_chain_bonus_id' not in st.session_state:
        st.session_state.next_chain_bonus_id = 0
    if 'next_score_bonus_id' not in st.session_state:
        st.session_state.next_score_bonus_id = 0

    # 动态区间权重列表
    if 'rank_intervals' not in st.session_state:
        st.session_state.rank_intervals = [
            {"id": 0, "start": 0, "end": 20, "weight": 4.0},
            {"id": 1, "start": 21, "end": 50, "weight": 2.5},
            {"id": 2, "start": 51, "end": 100, "weight": 1.4},
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
            {"id": 0, "threshold": 5, "bonus": 100},
            {"id": 1, "threshold": 10, "bonus": 70},
            {"id": 2, "threshold": 20, "bonus": 50},
            {"id": 3, "threshold": 30, "bonus": 35},
            {"id": 4, "threshold": 50, "bonus": 20},
            {"id": 5, "threshold": 100, "bonus": 10}
        ]
        st.session_state.next_bonus_id = 6

    # 动态集团排名奖励列表
    if 'group_rank_bonuses' not in st.session_state:
        st.session_state.group_rank_bonuses = [
            {"id": 0, "threshold": 20, "bonus": 200},
            {"id": 1, "threshold": 50, "bonus": 150},
            {"id": 2, "threshold": 100, "bonus": 100},
            {"id": 3, "threshold": 150, "bonus": 75},
            {"id": 4, "threshold": 200, "bonus": 50}
        ]
        st.session_state.next_group_bonus_id = 5

    # 动态连续进步奖励列表
    if 'chain_bonuses' not in st.session_state:
        st.session_state.chain_bonuses = [
            {"id": 0, "times": 1, "bonus": 20},
            {"id": 1, "times": 2, "bonus": 50},
            {"id": 2, "times": 3, "bonus": 90},
            {"id": 3, "times": 4, "bonus": 140},
            {"id": 4, "times": 5, "bonus": 200}
        ]
        st.session_state.next_chain_bonus_id = 5

    # 动态总分奖励列表
    if 'score_bonuses' not in st.session_state:
        st.session_state.score_bonuses = [
            {"id": 0, "threshold": 590, "bonus": 20},
            {"id": 1, "threshold": 600, "bonus": 40},
            {"id": 2, "threshold": 610, "bonus": 60},
            {"id": 3, "threshold": 620, "bonus": 80},
            {"id": 4, "threshold": 630, "bonus": 100},
            {"id": 5, "threshold": 640, "bonus": 120},
            {"id": 6, "threshold": 650, "bonus": 140},
            {"id": 7, "threshold": 660, "bonus": 160},
            {"id": 8, "threshold": 670, "bonus": 180}
        ]
        st.session_state.next_score_bonus_id = 9

    # 动态偏科扣分列表
    if 'bias_penalties' not in st.session_state:
        st.session_state.bias_penalties = [
            {"id": 0, "level": "轻微", "penalty": 20},
            {"id": 1, "level": "明显", "penalty": 40},
            {"id": 2, "level": "严重", "penalty": 70}
        ]

    # 默认参数配置
    if 'config_params' not in st.session_state:
        st.session_state.config_params = {
            "A线（排名）": 80,
            "A线过线奖励": 100,
            "B线（排名）": 430,
            "B线过线奖励": 0,
            "轻微偏科扣分": 20,
            "明显偏科扣分": 40,
            "严重偏科扣分": 70,
            # 偏科判定阈值（基于排名的混合法）
            "轻微偏科_标准差": 15,
            "轻微偏科_最大差距": 50,
            "轻微偏科_相对离散度": 80,
            "明显偏科_标准差": 30,
            "明显偏科_最大差距": 100,
            "明显偏科_相对离散度": 150,
            "严重偏科_标准差": 60,
            "严重偏科_最大差距": 200,
            "严重偏科_相对离散度": 300
        }
    
    # 东校状元奖（年级排名第1名的独立奖励）
    if 'champion_bonus' not in st.session_state:
        st.session_state.champion_bonus = 200

