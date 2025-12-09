"""
侧边栏组件
负责参数配置和文件上传界面
"""
import streamlit as st
import pandas as pd
import io
import time
import os
import glob
import json
from pathlib import Path
from streamlit.components.v1 import html


# 配置文件路径（作为备用）
CONFIG_FILE = Path("config/user_settings.json")


def _save_to_browser():
    """保存配置到浏览器 localStorage"""
    config = {
        "config_params": st.session_state.config_params,
        "rank_intervals": st.session_state.rank_intervals,
        "rank_bonuses": st.session_state.rank_bonuses,
        "group_rank_bonuses": st.session_state.group_rank_bonuses,
        "chain_bonuses": st.session_state.chain_bonuses,
        "score_bonuses": st.session_state.score_bonuses,
        "bias_penalties": st.session_state.bias_penalties,
        "subject_references": st.session_state.get("subject_references", {}),
    }
    
    config_json = json.dumps(config, ensure_ascii=False)
    
    # 使用 JavaScript 保存到 localStorage
    html(f"""
        <script>
            localStorage.setItem('score_analysis_config', {json.dumps(config_json)});
            window.parent.postMessage({{type: 'streamlit:setComponentValue', value: 'saved'}}, '*');
        </script>
    """, height=0)


def _load_from_browser():
    """从浏览器 localStorage 加载配置"""
    # 使用 JavaScript 读取 localStorage 并返回
    result = html("""
        <script>
            const config = localStorage.getItem('score_analysis_config');
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: config}, '*');
        </script>
    """, height=0)
    
    if result and result != 'null':
        try:
            config = json.loads(result)
            st.session_state.config_params = config.get("config_params", {})
            st.session_state.rank_intervals = config.get("rank_intervals", [])
            st.session_state.rank_bonuses = config.get("rank_bonuses", [])
            st.session_state.group_rank_bonuses = config.get("group_rank_bonuses", [])
            st.session_state.chain_bonuses = config.get("chain_bonuses", [])
            st.session_state.score_bonuses = config.get("score_bonuses", [])
            st.session_state.bias_penalties = config.get("bias_penalties", [])
            st.session_state.subject_references = config.get("subject_references", {})
            return True
        except:
            return False
    return False


def _save_config():
    """保存当前配置"""
    try:
        # 同时保存到浏览器和服务器
        _save_to_browser()
        
        # 备用：也保存到服务器文件（如果可写）
        try:
            CONFIG_FILE.parent.mkdir(exist_ok=True)
            config = {
                "config_params": st.session_state.config_params,
                "rank_intervals": st.session_state.rank_intervals,
                "rank_bonuses": st.session_state.rank_bonuses,
                "group_rank_bonuses": st.session_state.group_rank_bonuses,
                "chain_bonuses": st.session_state.chain_bonuses,
                "score_bonuses": st.session_state.score_bonuses,
                "bias_penalties": st.session_state.bias_penalties,
                "subject_references": st.session_state.get("subject_references", {}),
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass  # 服务器文件保存失败不影响浏览器保存
        
        st.success("✅ 配置已保存到浏览器！下次打开将自动加载")
    except Exception as e:
        st.error(f"❌ 保存配置失败: {str(e)}")


def _load_config():
    """手动加载配置"""
    # 先尝试从浏览器加载
    if _load_from_browser():
        st.success("✅ 已从浏览器加载配置！")
        st.rerun()
        return
    
    # 如果浏览器没有，尝试从服务器文件加载
    try:
        if not CONFIG_FILE.exists():
            st.warning("⚠️ 未找到保存的配置")
            return False
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        st.session_state.config_params = config.get("config_params", {})
        st.session_state.rank_intervals = config.get("rank_intervals", [])
        st.session_state.rank_bonuses = config.get("rank_bonuses", [])
        st.session_state.group_rank_bonuses = config.get("group_rank_bonuses", [])
        st.session_state.chain_bonuses = config.get("chain_bonuses", [])
        st.session_state.score_bonuses = config.get("score_bonuses", [])
        st.session_state.bias_penalties = config.get("bias_penalties", [])
        st.session_state.subject_references = config.get("subject_references", {})
        
        st.success("✅ 已从服务器加载配置！")
        st.rerun()
        return True
    except Exception as e:
        st.error(f"❌ 加载配置失败: {str(e)}")
        return False


def auto_load_config():
    """自动加载保存的配置（在应用启动时调用）"""
    if 'config_loaded' not in st.session_state:
        # 先尝试从浏览器加载
        loaded = _try_load_from_browser_silent()
        
        # 如果浏览器没有，尝试从服务器文件加载
        if not loaded and CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                st.session_state.config_params = config.get("config_params", {})
                st.session_state.rank_intervals = config.get("rank_intervals", [])
                st.session_state.rank_bonuses = config.get("rank_bonuses", [])
                st.session_state.group_rank_bonuses = config.get("group_rank_bonuses", [])
                st.session_state.chain_bonuses = config.get("chain_bonuses", [])
                st.session_state.score_bonuses = config.get("score_bonuses", [])
                st.session_state.bias_penalties = config.get("bias_penalties", [])
                st.session_state.subject_references = config.get("subject_references", {})
            except:
                pass
        
        st.session_state.config_loaded = True


def _try_load_from_browser_silent():
    """静默尝试从浏览器加载配置（用于自动加载，不显示消息）"""
    try:
        # 注入 JavaScript 代码来读取 localStorage
        result = html("""
            <script>
                const config = localStorage.getItem('score_analysis_config');
                if (config) {
                    window.parent.postMessage({type: 'streamlit:setComponentValue', value: config}, '*');
                }
            </script>
        """, height=0)
        
        if result and result != 'null':
            config = json.loads(result)
            st.session_state.config_params = config.get("config_params", {})
            st.session_state.rank_intervals = config.get("rank_intervals", [])
            st.session_state.rank_bonuses = config.get("rank_bonuses", [])
            st.session_state.group_rank_bonuses = config.get("group_rank_bonuses", [])
            st.session_state.chain_bonuses = config.get("chain_bonuses", [])
            st.session_state.score_bonuses = config.get("score_bonuses", [])
            st.session_state.bias_penalties = config.get("bias_penalties", [])
            return True
    except:
        pass
    return False


def _reset_to_default():
    """重置为默认配置"""
    # 重置所有配置为默认值
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
    
    st.session_state.rank_bonuses = [
        {"id": 0, "threshold": 10, "bonus": 30},
        {"id": 1, "threshold": 20, "bonus": 25},
        {"id": 2, "threshold": 30, "bonus": 20},
        {"id": 3, "threshold": 50, "bonus": 15},
        {"id": 4, "threshold": 100, "bonus": 10}
    ]
    
    st.session_state.group_rank_bonuses = [
        {"id": 0, "threshold": 50, "bonus": 20},
        {"id": 1, "threshold": 100, "bonus": 15},
        {"id": 2, "threshold": 200, "bonus": 10},
        {"id": 3, "threshold": 300, "bonus": 5}
    ]
    
    st.session_state.chain_bonuses = [
        {"id": 0, "times": 1, "bonus": 5},
        {"id": 1, "times": 2, "bonus": 8},
        {"id": 2, "times": 3, "bonus": 12},
        {"id": 3, "times": 4, "bonus": 18},
        {"id": 4, "times": 5, "bonus": 25}
    ]
    
    st.session_state.score_bonuses = [
        {"id": 0, "threshold": 580, "bonus": 5},
        {"id": 1, "threshold": 590, "bonus": 8},
        {"id": 2, "threshold": 600, "bonus": 10},
        {"id": 3, "threshold": 610, "bonus": 12},
        {"id": 4, "threshold": 620, "bonus": 15},
        {"id": 5, "threshold": 630, "bonus": 18},
        {"id": 6, "threshold": 640, "bonus": 20}
    ]
    
    st.session_state.bias_penalties = [
        {"id": 0, "level": "轻微", "penalty": 5},
        {"id": 1, "level": "明显", "penalty": 15},
        {"id": 2, "level": "严重", "penalty": 30}
    ]
    
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
        "总分大于580奖励": 5,
        "总分大于590奖励": 8,
        "总分大于600奖励": 10,
        "总分大于610奖励": 12,
        "总分大于620奖励": 15,
        "总分大于630奖励": 18,
        "总分大于640奖励": 20,
        "轻微偏科扣分": 5,
        "明显偏科扣分": 15,
        "严重偏科扣分": 30,
        "轻微偏科_标准差": 5,
        "明显偏科_标准差": 10,
        "严重偏科_标准差": 15
    }
    
    # 各科成绩参考线（默认值，实际分数形式）
    st.session_state.subject_references = {
        "语文": 105,
        "数学": 105,
        "英语": 105,
        "物理": 70,
        "选科": 140,  # 选科 = 化学 + 生物
        "政治": 70,
        "历史": 70,
        "地理": 70
    }
    
    st.success("✅ 已恢复默认配置！")
    st.rerun()


@st.fragment
def _render_param_settings():
    """渲染参数设置区域（使用fragment避免刷新主页面）"""
    # 初始化expander状态
    if 'param_expander_expanded' not in st.session_state:
        st.session_state.param_expander_expanded = False
    
    # 创建可折叠的参数设置区域
    expander = st.expander("📊 评分参数设置", expanded=st.session_state.param_expander_expanded)
    
    with expander:
        # 添加保存/加载配置按钮
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 保存配置", use_container_width=True):
                _save_config()
        with col2:
            if st.button("📂 加载配置", use_container_width=True):
                _load_config()
        with col3:
            if st.button("🔄 恢复默认", use_container_width=True):
                _reset_to_default()
        
        st.markdown("---")
        
        _render_interval_settings()
        _render_line_and_bonus_settings()
        _render_rank_bonus_settings()
        _render_group_rank_bonus_settings()
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
    """从session_state的临时key中保存区间值到rank_intervals（即时保存）"""
    for idx, interval in enumerate(st.session_state.rank_intervals):
        interval_id = interval["id"]
        start_key = f"start_{interval_id}"
        end_key = f"end_{interval_id}"
        weight_key = f"weight_{interval_id}"
        
        if start_key in st.session_state:
            new_val = st.session_state[start_key]
            if new_val != st.session_state.rank_intervals[idx]["start"]:
                st.session_state.rank_intervals[idx]["start"] = new_val
        if end_key in st.session_state:
            new_val = st.session_state[end_key]
            if new_val != st.session_state.rank_intervals[idx]["end"]:
                st.session_state.rank_intervals[idx]["end"] = new_val
        if weight_key in st.session_state:
            new_val = st.session_state[weight_key]
            if new_val != st.session_state.rank_intervals[idx]["weight"]:
                st.session_state.rank_intervals[idx]["weight"] = new_val


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


def _save_group_bonus_values():
    """从session_state的临时key中保存集团排名奖励值到group_rank_bonuses"""
    for idx, bonus in enumerate(st.session_state.group_rank_bonuses):
        bonus_id = bonus["id"]
        thresh_key = f"group_bonus_thresh_{bonus_id}"
        val_key = f"group_bonus_val_{bonus_id}"
        
        if thresh_key in st.session_state:
            st.session_state.group_rank_bonuses[idx]["threshold"] = st.session_state[thresh_key]
        if val_key in st.session_state:
            st.session_state.group_rank_bonuses[idx]["bonus"] = st.session_state[val_key]


def _save_chain_bonus_values():
    """从session_state的临时key中保存连续进步奖励值到chain_bonuses"""
    for idx, bonus in enumerate(st.session_state.chain_bonuses):
        bonus_id = bonus["id"]
        times_key = f"chain_times_{bonus_id}"
        val_key = f"chain_val_{bonus_id}"
        
        if times_key in st.session_state:
            st.session_state.chain_bonuses[idx]["times"] = st.session_state[times_key]
        if val_key in st.session_state:
            st.session_state.chain_bonuses[idx]["bonus"] = st.session_state[val_key]


def _save_score_bonus_values():
    """从session_state的临时key中保存总分奖励值到score_bonuses"""
    for idx, bonus in enumerate(st.session_state.score_bonuses):
        bonus_id = bonus["id"]
        thresh_key = f"score_thresh_{bonus_id}"
        val_key = f"score_val_{bonus_id}"
        
        if thresh_key in st.session_state:
            st.session_state.score_bonuses[idx]["threshold"] = st.session_state[thresh_key]
        if val_key in st.session_state:
            st.session_state.score_bonuses[idx]["bonus"] = st.session_state[val_key]


def _render_interval_settings():
    """渲染区间权重设置"""
    st.subheader("区间权重")
    
    # 显示当前所有区间
    for idx, interval in enumerate(st.session_state.rank_intervals):
        interval_id = interval["id"]
        # 区间标题 - 从session_state读取实际保存的值
        actual_start = interval["start"]
        actual_end = interval["end"]
        actual_weight = interval["weight"]
        st.markdown(f"**区间 {idx + 1}**: `({actual_start}-{actual_end}) 权重:{actual_weight}`")
        
        # 使用与排名奖励一致的列宽比例
        col1, col2, col3, col4 = st.columns([2.8, 2.8, 2.8, 1.3])
        
        with col1:
            st.number_input("起始", value=int(interval["start"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"start_{interval_id}", on_change=_save_interval_values)
        
        with col2:
            st.number_input("结束", value=int(interval["end"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"end_{interval_id}", on_change=_save_interval_values)
        
        with col3:
            st.number_input("权重", value=float(interval["weight"]), step=0.1, min_value=0.0, disabled=st.session_state.analysis_started, key=f"weight_{interval_id}", on_change=_save_interval_values)
        
        with col4:
            # 使用label占位实现对齐
            st.markdown("###### 　")  # 透明占位符
            # 删除按钮(保留至少1个区间)
            can_delete = len(st.session_state.rank_intervals) > 1
            if st.button("🗑️", key=f"del_{interval_id}", disabled=st.session_state.analysis_started or not can_delete, use_container_width=True, type="secondary"):
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
        st.markdown("")
        if st.button("➕ 添加区间", key="add_interval", use_container_width=True, type="primary"):
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
    
    # A线设置
    st.markdown("**A线**")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.config_params["A线（排名）"] = st.number_input(
            "A线排名", 
            value=st.session_state.config_params.get("A线（排名）", st.session_state.config_params.get("线（排名）", 430)), 
            step=1, 
            min_value=1,
            disabled=st.session_state.analysis_started
        )
    with col2:
        st.session_state.config_params["A线过线奖励"] = st.number_input(
            "A线过线奖励", 
            value=st.session_state.config_params.get("A线过线奖励", st.session_state.config_params.get("过线奖励", 5)), 
            step=1, 
            min_value=0,
            disabled=st.session_state.analysis_started
        )
    
    # B线设置
    st.markdown("**B线**")
    col3, col4 = st.columns(2)
    with col3:
        st.session_state.config_params["B线（排名）"] = st.number_input(
            "B线排名", 
            value=st.session_state.config_params.get("B线（排名）", 500), 
            step=1, 
            min_value=1,
            disabled=st.session_state.analysis_started
        )
    with col4:
        st.session_state.config_params["B线过线奖励"] = st.number_input(
            "B线过线奖励", 
            value=st.session_state.config_params.get("B线过线奖励", 3), 
            step=1, 
            min_value=0,
            disabled=st.session_state.analysis_started
        )


def _render_rank_bonus_settings():
    """渲染年级排名奖励设置"""
    st.markdown("---")
    st.subheader("年级排名奖励")
    
    # 显示当前所有年级排名奖励
    for idx, bonus in enumerate(st.session_state.rank_bonuses):
        bonus_id = bonus["id"]
        # 奖励标题
        st.markdown(f"**奖励档位 {idx + 1}**: `前 {bonus['threshold']} 名 → {bonus['bonus']} 分`")
        
        col1, col2, col3 = st.columns([2.8, 2.8, 1.3])
        
        with col1:
            st.number_input("前N名", value=int(bonus["threshold"]), step=1, min_value=1, disabled=st.session_state.analysis_started, key=f"bonus_thresh_{bonus_id}", on_change=_save_bonus_values)
        
        with col2:
            st.number_input("奖励分", value=int(bonus["bonus"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"bonus_val_{bonus_id}", on_change=_save_bonus_values)
        
        with col3:
            # 使用label占位实现对齐
            st.markdown("###### 　")  # 透明占位符
            # 删除按钮(保留至少1个奖励)
            if st.button("🗑️", key=f"del_bonus_{bonus_id}", disabled=st.session_state.analysis_started or len(st.session_state.rank_bonuses) <= 1, use_container_width=True, type="secondary"):
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
        st.markdown("")
        if st.button("➕ 添加年级排名奖励", key="add_bonus", use_container_width=True, type="primary"):
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


def _render_group_rank_bonus_settings():
    """渲染集团排名奖励设置"""
    st.markdown("---")
    st.subheader("集团排名奖励")
    
    # 显示当前所有集团排名奖励
    for idx, bonus in enumerate(st.session_state.group_rank_bonuses):
        bonus_id = bonus["id"]
        # 奖励标题
        st.markdown(f"**奖励档位 {idx + 1}**: `前 {bonus['threshold']} 名 → {bonus['bonus']} 分`")
        
        col1, col2, col3 = st.columns([2.8, 2.8, 1.3])
        
        with col1:
            st.number_input("前N名", value=int(bonus["threshold"]), step=1, min_value=1, disabled=st.session_state.analysis_started, key=f"group_bonus_thresh_{bonus_id}", on_change=_save_group_bonus_values)
        
        with col2:
            st.number_input("奖励分", value=int(bonus["bonus"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"group_bonus_val_{bonus_id}", on_change=_save_group_bonus_values)
        
        with col3:
            # 使用label占位实现对齐
            st.markdown("###### 　")  # 透明占位符
            # 删除按钮(保留至少1个奖励)
            if st.button("🗑️", key=f"del_group_bonus_{bonus_id}", disabled=st.session_state.analysis_started or len(st.session_state.group_rank_bonuses) <= 1, use_container_width=True, type="secondary"):
                # 操作锁避免重复
                if not st.session_state.get('_operation_lock', False):
                    st.session_state._operation_lock = True
                    _save_group_bonus_values()  # 先保存其他奖励的值
                    # 立即删除
                    st.session_state.group_rank_bonuses = [
                        b for b in st.session_state.group_rank_bonuses if b["id"] != bonus_id
                    ]
                    # 清理废弃的key
                    keys_to_delete = [k for k in st.session_state.keys() 
                                     if k.startswith(f"group_bonus_thresh_{bonus_id}") or 
                                        k.startswith(f"group_bonus_val_{bonus_id}") or 
                                        k.startswith(f"del_group_bonus_{bonus_id}")]
                    for key in keys_to_delete:
                        del st.session_state[key]
                    st.session_state.param_expander_expanded = True
                    time.sleep(0.15)  # 延迟配合CSS过渡动画
                    st.session_state._operation_lock = False
                    st.rerun(scope="fragment")
    
    # 添加新集团排名奖励按钮
    if not st.session_state.analysis_started:
        st.markdown("")
        if st.button("➕ 添加集团排名奖励", key="add_group_bonus", use_container_width=True, type="primary"):
            # 操作锁避免重复
            if not st.session_state.get('_operation_lock', False):
                st.session_state._operation_lock = True
                # 先保存当前所有输入框的值
                _save_group_bonus_values()
                
                # 默认新奖励阈值为最后一个+50
                last_threshold = st.session_state.group_rank_bonuses[-1]["threshold"] if st.session_state.group_rank_bonuses else 0
                
                new_id = st.session_state.next_group_bonus_id
                st.session_state.next_group_bonus_id += 1
                
                st.session_state.group_rank_bonuses.append({
                    "id": new_id,
                    "threshold": last_threshold + 50,
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
    
    # 显示当前所有连续进步奖励
    for idx, bonus in enumerate(st.session_state.chain_bonuses):
        bonus_id = bonus["id"]
        # 奖励标题
        st.markdown(f"**奖励档位 {idx + 1}**: `连续 {bonus['times']} 次 → {bonus['bonus']} 分`")
        
        col1, col2, col3 = st.columns([2.8, 2.8, 1.3])
        
        with col1:
            st.number_input("连续次数", value=int(bonus["times"]), step=1, min_value=1, disabled=st.session_state.analysis_started, key=f"chain_times_{bonus_id}", on_change=_save_chain_bonus_values)
        
        with col2:
            st.number_input("奖励分", value=int(bonus["bonus"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"chain_val_{bonus_id}", on_change=_save_chain_bonus_values)
        
        with col3:
            # 使用label占位实现对齐
            st.markdown("###### 　")  # 透明占位符
            # 删除按钮(保留至少1个奖励)
            if st.button("🗑️", key=f"del_chain_{bonus_id}", disabled=st.session_state.analysis_started or len(st.session_state.chain_bonuses) <= 1, use_container_width=True, type="secondary"):
                # 操作锁避免重复
                if not st.session_state.get('_operation_lock', False):
                    st.session_state._operation_lock = True
                    _save_chain_bonus_values()  # 先保存其他奖励的值
                    # 立即删除
                    st.session_state.chain_bonuses = [
                        b for b in st.session_state.chain_bonuses if b["id"] != bonus_id
                    ]
                    # 清理废弃的key
                    keys_to_delete = [k for k in st.session_state.keys() 
                                     if k.startswith(f"chain_times_{bonus_id}") or 
                                        k.startswith(f"chain_val_{bonus_id}") or 
                                        k.startswith(f"del_chain_{bonus_id}")]
                    for key in keys_to_delete:
                        del st.session_state[key]
                    st.session_state.param_expander_expanded = True
                    time.sleep(0.15)  # 延迟配合CSS过渡动画
                    st.session_state._operation_lock = False
                    st.rerun(scope="fragment")
    
    # 添加新连续进步奖励按钮
    if not st.session_state.analysis_started:
        st.markdown("")
        if st.button("➕ 添加连续进步奖励", key="add_chain_bonus", use_container_width=True, type="primary"):
            # 操作锁避免重复
            if not st.session_state.get('_operation_lock', False):
                st.session_state._operation_lock = True
                # 先保存当前所有输入框的值
                _save_chain_bonus_values()
                
                # 默认新奖励次数为最后一个+1
                last_times = st.session_state.chain_bonuses[-1]["times"] if st.session_state.chain_bonuses else 0
                
                new_id = st.session_state.next_chain_bonus_id
                st.session_state.next_chain_bonus_id += 1
                
                st.session_state.chain_bonuses.append({
                    "id": new_id,
                    "times": last_times + 1,
                    "bonus": 5
                })
                st.session_state.param_expander_expanded = True
                time.sleep(0.15)  # 延迟配合CSS过渡动画
                st.session_state._operation_lock = False
                st.rerun(scope="fragment")


def _render_score_bonus_settings():
    """渲染总分奖励设置"""
    st.markdown("---")
    st.subheader("总分奖励")
    
    # 显示当前所有总分奖励
    for idx, bonus in enumerate(st.session_state.score_bonuses):
        bonus_id = bonus["id"]
        # 奖励标题
        st.markdown(f"**奖励档位 {idx + 1}**: `总分 > {bonus['threshold']} → {bonus['bonus']} 分`")
        
        col1, col2, col3 = st.columns([2.8, 2.8, 1.3])
        
        with col1:
            st.number_input("总分阈值", value=int(bonus["threshold"]), step=10, min_value=0, disabled=st.session_state.analysis_started, key=f"score_thresh_{bonus_id}", on_change=_save_score_bonus_values)
        
        with col2:
            st.number_input("奖励分", value=int(bonus["bonus"]), step=1, min_value=0, disabled=st.session_state.analysis_started, key=f"score_val_{bonus_id}", on_change=_save_score_bonus_values)
        
        with col3:
            # 使用label占位实现对齐
            st.markdown("###### 　")  # 透明占位符
            # 删除按钮(保留至少1个奖励)
            if st.button("🗑️", key=f"del_score_{bonus_id}", disabled=st.session_state.analysis_started or len(st.session_state.score_bonuses) <= 1, use_container_width=True, type="secondary"):
                # 操作锁避免重复
                if not st.session_state.get('_operation_lock', False):
                    st.session_state._operation_lock = True
                    _save_score_bonus_values()  # 先保存其他奖励的值
                    # 立即删除
                    st.session_state.score_bonuses = [
                        b for b in st.session_state.score_bonuses if b["id"] != bonus_id
                    ]
                    # 清理废弃的key
                    keys_to_delete = [k for k in st.session_state.keys() 
                                     if k.startswith(f"score_thresh_{bonus_id}") or 
                                        k.startswith(f"score_val_{bonus_id}") or 
                                        k.startswith(f"del_score_{bonus_id}")]
                    for key in keys_to_delete:
                        del st.session_state[key]
                    st.session_state.param_expander_expanded = True
                    time.sleep(0.15)  # 延迟配合CSS过渡动画
                    st.session_state._operation_lock = False
                    st.rerun(scope="fragment")
    
    # 添加新总分奖励按钮
    if not st.session_state.analysis_started:
        st.markdown("")
        if st.button("➕ 添加总分奖励", key="add_score_bonus", use_container_width=True, type="primary"):
            # 操作锁避免重复
            if not st.session_state.get('_operation_lock', False):
                st.session_state._operation_lock = True
                # 先保存当前所有输入框的值
                _save_score_bonus_values()
                
                # 默认新奖励阈值为最后一个+50
                last_threshold = st.session_state.score_bonuses[-1]["threshold"] if st.session_state.score_bonuses else 600
                
                new_id = st.session_state.next_score_bonus_id
                st.session_state.next_score_bonus_id += 1
                
                st.session_state.score_bonuses.append({
                    "id": new_id,
                    "threshold": last_threshold + 50,
                    "bonus": 5
                })
                st.session_state.param_expander_expanded = True
                time.sleep(0.15)  # 延迟配合CSS过渡动画
                st.session_state._operation_lock = False
                st.rerun(scope="fragment")


def _render_bias_penalty_settings():
    """渲染偏科扣分设置"""
    st.markdown("---")
    st.subheader("偏科判定与扣分")
    
    # 各科成绩参考线设置
    st.markdown("**📏 各科成绩参考线（实际分数）**")
    st.caption("设置各科目的分数参考线，用于判定学生是否偏科（基于各科得分率与参考线的差值）")
    st.info("💡 注意：偏科分析时，化学和生物会合并为'选科'整体分析。请输入实际分数，程序会自动转换为得分率进行比较")
    
    # 初始化subject_references（实际分数形式，内部会转换为百分比）
    if 'subject_references' not in st.session_state:
        st.session_state.subject_references = {
            "语文": 105, "数学": 105, "英语": 105,
            "物理": 70, "选科": 140,  # 选科 = 化学 + 生物
            "政治": 70, "历史": 70, "地理": 70
        }
    
    # 根据当前数据中的科目显示参考线设置
    current_subjects = st.session_state.get('subjects', [])
    
    if current_subjects:
        # 检查是否同时有化学和生物
        has_chem = "化学" in current_subjects
        has_bio = "生物" in current_subjects
        
        # 动态显示当前数据中的科目（化学和生物合并为选科）
        display_subjects = []
        for subj in current_subjects:
            if subj not in ["化学", "生物"]:
                display_subjects.append(subj)
        
        # 如果有化学或生物，添加"选科"
        if has_chem or has_bio:
            display_subjects.append("选科")
        
        cols = st.columns(3)
        for idx, subject in enumerate(display_subjects):
            with cols[idx % 3]:
                if subject == "选科":
                    default_val = st.session_state.subject_references.get("选科", 140)
                    score_input = st.number_input(
                        "选科参考线",
                        value=default_val,
                        min_value=0,
                        max_value=200,
                        step=1,
                        disabled=st.session_state.analysis_started,
                        help="选科（化学+生物）的总分参考线，满分200分"
                    )
                    # 转换为百分比存储（内部使用）
                    st.session_state.subject_references["选科"] = score_input
                else:
                    # 根据科目确定满分
                    if subject in ["语文", "数学", "英语"]:
                        max_score = 150
                        default_val = st.session_state.subject_references.get(subject, 105)
                    else:  # 物理、政治、历史、地理等
                        max_score = 100
                        default_val = st.session_state.subject_references.get(subject, 70)
                    
                    score_input = st.number_input(
                        f"{subject}参考线",
                        value=default_val,
                        min_value=0,
                        max_value=max_score,
                        step=1,
                        disabled=st.session_state.analysis_started,
                        help=f"{subject}科目的分数参考线，满分{max_score}分"
                    )
                    # 直接存储分数（内部使用时会转换为百分比）
                    st.session_state.subject_references[subject] = score_input
    else:
        # 如果还没有上传数据，显示常见科目（化学生物合并为选科）
        st.info("上传成绩数据后，将显示对应科目的参考线设置")
        common_subjects = ["语文", "数学", "英语", "物理", "选科"]
        cols = st.columns(3)
        for idx, subject in enumerate(common_subjects):
            with cols[idx % 3]:
                if subject == "选科":
                    default_val = st.session_state.subject_references.get("选科", 140)
                    score_input = st.number_input(
                        "选科参考线",
                        value=default_val,
                        min_value=0,
                        max_value=200,
                        step=1,
                        disabled=st.session_state.analysis_started,
                        help="选科（化学+生物）的总分参考线，满分200分"
                    )
                    st.session_state.subject_references["选科"] = score_input
                else:
                    # 根据科目确定满分和默认值
                    if subject in ["语文", "数学", "英语"]:
                        max_score = 150
                        default_val = st.session_state.subject_references.get(subject, 105)
                    else:  # 物理
                        max_score = 100
                        default_val = st.session_state.subject_references.get(subject, 70)
                    
                    score_input = st.number_input(
                        f"{subject}参考线",
                        value=default_val,
                        min_value=0,
                        max_value=max_score,
                        step=1,
                        disabled=st.session_state.analysis_started,
                        help=f"{subject}科目的分数参考线，满分{max_score}分"
                    )
                    st.session_state.subject_references[subject] = score_input
    
    st.markdown("---")
    
    # 偏科判定标准
    st.markdown("**📊 偏科判定标准**")
    st.caption("基于各科得分率与参考线百分比差值的标准差进行判定")
    
    st.markdown("""
    **判定逻辑：**
    1. 将各科成绩转换为得分率（百分比）
    2. 计算各科差值 = 实际得分率 - 参考线百分比
    3. 计算差值的标准差（反映各科表现的离散程度）
    4. 根据标准差判定偏科等级
    
    **示例：** 标准差越大，说明各科成绩相对参考线的表现越不均衡
    """)
    
    # 偏科阈值设置
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**轻微偏科**")
        st.session_state.config_params["轻微偏科_标准差"] = st.number_input(
            "差值标准差阈值",
            value=float(st.session_state.config_params.get("轻微偏科_标准差", 7.5)),
            min_value=0.0,
            step=0.1,
            format="%.1f",
            disabled=st.session_state.analysis_started,
            help="各科得分率差值标准差 > 此阈值判定为轻微偏科（百分比单位）"
        )
    with col2:
        st.markdown("**明显偏科**")
        st.session_state.config_params["明显偏科_标准差"] = st.number_input(
            "差值标准差阈值 ",
            value=float(st.session_state.config_params.get("明显偏科_标准差", 8.5)),
            min_value=0.0,
            step=0.1,
            format="%.1f",
            disabled=st.session_state.analysis_started,
            help="各科得分率差值标准差 > 此阈值判定为明显偏科（百分比单位）"
        )
    with col3:
        st.markdown("**严重偏科**")
        st.session_state.config_params["严重偏科_标准差"] = st.number_input(
            "差值标准差阈值  ",
            value=float(st.session_state.config_params.get("严重偏科_标准差", 10.0)),
            min_value=0.0,
            step=0.1,
            format="%.1f",
            disabled=st.session_state.analysis_started,
            help="各科得分率差值标准差 > 此阈值判定为严重偏科（百分比单位）"
        )
    
    # 扣分设置
    st.markdown("---")
    st.markdown("**💰 偏科扣分**")
    col10, col11, col12 = st.columns(3)
    with col10:
        st.session_state.config_params["轻微偏科扣分"] = st.number_input("轻微扣分", value=st.session_state.config_params["轻微偏科扣分"], step=1, disabled=st.session_state.analysis_started)
    with col11:
        st.session_state.config_params["明显偏科扣分"] = st.number_input("明显扣分", value=st.session_state.config_params["明显偏科扣分"], step=1, disabled=st.session_state.analysis_started)
    with col12:
        st.session_state.config_params["严重偏科扣分"] = st.number_input("严重扣分", value=st.session_state.config_params["严重偏科扣分"], step=1, disabled=st.session_state.analysis_started)


def _render_file_upload():
    """渲染文件上传区域"""
    st.header("📁 文件上传")
    
    # 历史总表上传
    history_file = st.file_uploader(
        "1️⃣ 上传历史成绩总表（可选）",
        type=['xlsx'],
        help="如果已有历史数据，可以上传成绩总表.xlsx，新成绩将接续在后面",
        key=f"history_uploader_{st.session_state.uploader_key}"
    )
    
    # 保存历史文件到 session state 并分析次数
    if history_file is not None and not st.session_state.analysis_started:
        st.session_state.history_file_content = history_file.getvalue()
        # 分析历史文件有多少次考试
        try:
            # 检查是否有说明行需要跳过
            df_temp = pd.read_excel(io.BytesIO(history_file.getvalue()), nrows=1)
            if df_temp.iloc[0, 0] and isinstance(df_temp.iloc[0, 0], str) and "说明" in str(df_temp.iloc[0, 0]):
                df_history = pd.read_excel(io.BytesIO(history_file.getvalue()), skiprows=1)
            else:
                df_history = pd.read_excel(io.BytesIO(history_file.getvalue()))
            
            # 检查是否为多工作表格式
            excel_file = pd.ExcelFile(io.BytesIO(history_file.getvalue()))
            sheet_names = excel_file.sheet_names
            
            # 如果有多个工作表，每个工作表（除了'完整总表'等）代表一次考试
            if len(sheet_names) > 1:
                exam_count = len([s for s in sheet_names if s not in ['成绩总表', '完整总表']])
                st.session_state.history_exam_count = exam_count
                st.success(f"✅ 历史总表已上传 (多工作表格式，包含 {exam_count} 次考试)")
            else:
                # 旧格式：单工作表，需要从列名推断考试次数
                # 检测考试次数：匹配最后一个下划线后的考试标签
                import re
                exam_labels_found = set()
                
                for col in df_history.columns:
                    # 匹配最后一个下划线后的内容作为考试标签
                    if '_' in col and col != '姓名':
                        # 提取最后一个下划线后的部分
                        exam_label = col.rsplit('_', 1)[-1]
                        if exam_label:  # 只要有内容就算一次考试
                            exam_labels_found.add(exam_label)
                
                st.session_state.history_exam_count = len(exam_labels_found)
                st.success(f"✅ 历史总表已上传 (单工作表格式，包含 {len(exam_labels_found)} 次考试)")
        except Exception as e:
            st.error(f"❌ 历史文件读取失败: {str(e)}")
            st.session_state.history_file_content = None
            st.session_state.history_exam_count = 0
    elif history_file is None and st.session_state.history_file_content is not None and not st.session_state.analysis_started:
        # 用户删除了历史总表，清除相关数据和缓存
        st.session_state.history_file_content = None
        st.session_state.history_exam_count = 0
        
        # 同时清除已分析的数据缓存，避免残留
        for key in ['df_all', 'df_score', 'df_final', 'df_bias', 'has_subjects', 
                   'rank_cols', 'score_cols', 'group_rank_cols', 'subjects', 'bias_dict', 'exam_labels']:
            if key in st.session_state:
                del st.session_state[key]
        
        st.info("ℹ️ 已删除历史总表")
    
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
            if st.session_state.analysis_started:
                st.caption("⚠️ 分析进行中，考试名称已锁定。如需修改，请先点击「重置」")
            else:
                st.caption("💡 提示：可以修改考试名称，修改后点击「开始分析」生效")
        
        for idx, file_info in enumerate(st.session_state.score_files):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # 可编辑的考试名称
                current_label = file_info.get('exam_label', f"第{file_info['exam_num']}次考试")
                new_label = st.text_input(
                    f"考试{idx+1}名称",
                    value=current_label,
                    key=f"label_{idx}_{file_info['exam_num']}",
                    disabled=st.session_state.analysis_started,
                    label_visibility="collapsed",
                    placeholder="例如: 期中考试、期末考试、月考"
                )
                # 实时更新标签
                if new_label and new_label != current_label:
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
            # 清理临时文件
            import glob
            temp_files = glob.glob("*_temp.xlsx")
            for f in temp_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except:
                    pass
            
            # 清理session state
            st.session_state.score_files = []
            st.session_state.analysis_started = False
            st.session_state.history_file_content = None
            st.session_state.history_exam_count = 0
            st.session_state.uploader_key += 1  # 增加key值以重置file_uploader
            
            # 清理分析结果缓存
            for key in ['df_all', 'df_score', 'df_final', 'df_bias', 'has_subjects', 
                       'rank_cols', 'score_cols', 'group_rank_cols', 'subjects', 'bias_dict', 'exam_labels']:
                if key in st.session_state:
                    del st.session_state[key]
            
            # 注意: 不清除 config_params，保留用户的参数设置
            st.success("✅ 已清理所有临时文件和缓存")
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
    - 点击「💾 保存配置」将配置保存到浏览器
    - 下次用同一浏览器访问会自动加载配置
    - 如果上传了历史总表，新成绩将接续在后面
    - 文件顺序会自动标记（第N次）
    - 可以随时删除已上传的文件重新上传
    """)
