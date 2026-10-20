"""
数据处理工具模块
负责处理文件上传、数据合并和分析计算
"""
import streamlit as st
import pandas as pd
import io
import os
from utils.progress_rules import (
    TIE_ENABLED, TIE_RANK_LIMIT, get_tie_progress_rule, calculate_progress_chain,
    RANK_BASIS, get_rank_basis,
)
from utils.rank_history import (
    get_grade_rank_columns, get_group_rank_columns, get_progress_rank_columns,
    get_rank_history, get_exam_label, latest_rank_change, compare_rank_changes,
    correct_tied_score_ranks,
)
from config.scoring_schemes import GRADE_REWARD_ENABLED, GROUP_REWARD_ENABLED, SCHEME_LABELS
from score_analysis_v0_1 import (
    progress_score,
    ranking_bonus,
    line_bonus_score,
    group_ranking_bonus,
    chain_bonus_score,
    total_score_bonus,
    detect_subject_bias,
    bias_penalty_score
)


def _save_all_input_values():
    """从session_state的临时key中保存所有输入值"""
    if 'tie_progress_enabled' in st.session_state:
        st.session_state.config_params[TIE_ENABLED] = st.session_state.tie_progress_enabled
    if 'tie_progress_grade_rank_limit' in st.session_state:
        st.session_state.config_params[TIE_RANK_LIMIT] = st.session_state.tie_progress_grade_rank_limit
    for widget, param in [('line_a_rank', 'A线（排名）'), ('line_a_bonus', 'A线过线奖励'),
                          ('line_b_rank', 'B线（排名）'), ('line_b_bonus', 'B线过线奖励'),
                          ('grade_rank_reward_enabled', GRADE_REWARD_ENABLED),
                          ('group_rank_reward_enabled', GROUP_REWARD_ENABLED)]:
        if widget in st.session_state:
            st.session_state.config_params[param] = st.session_state[widget]
    # 保存区间值
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
    
    # 保存年级排名奖励值
    for idx, bonus in enumerate(st.session_state.rank_bonuses):
        bonus_id = bonus["id"]
        thresh_key = f"bonus_thresh_{bonus_id}"
        val_key = f"bonus_val_{bonus_id}"
        
        if thresh_key in st.session_state:
            st.session_state.rank_bonuses[idx]["threshold"] = st.session_state[thresh_key]
        if val_key in st.session_state:
            st.session_state.rank_bonuses[idx]["bonus"] = st.session_state[val_key]
    
    # 保存集团排名奖励值
    for idx, bonus in enumerate(st.session_state.group_rank_bonuses):
        bonus_id = bonus["id"]
        thresh_key = f"group_bonus_thresh_{bonus_id}"
        val_key = f"group_bonus_val_{bonus_id}"
        
        if thresh_key in st.session_state:
            st.session_state.group_rank_bonuses[idx]["threshold"] = st.session_state[thresh_key]
        if val_key in st.session_state:
            st.session_state.group_rank_bonuses[idx]["bonus"] = st.session_state[val_key]
    
    # 保存连续进步奖励值
    for idx, bonus in enumerate(st.session_state.chain_bonuses):
        bonus_id = bonus["id"]
        times_key = f"chain_times_{bonus_id}"
        val_key = f"chain_val_{bonus_id}"
        
        if times_key in st.session_state:
            st.session_state.chain_bonuses[idx]["times"] = st.session_state[times_key]
        if val_key in st.session_state:
            st.session_state.chain_bonuses[idx]["bonus"] = st.session_state[val_key]
    
    # 保存总分奖励值
    for idx, bonus in enumerate(st.session_state.score_bonuses):
        bonus_id = bonus["id"]
        thresh_key = f"score_thresh_{bonus_id}"
        val_key = f"score_val_{bonus_id}"
        
        if thresh_key in st.session_state:
            st.session_state.score_bonuses[idx]["threshold"] = st.session_state[thresh_key]
        if val_key in st.session_state:
            st.session_state.score_bonuses[idx]["bonus"] = st.session_state[val_key]


def process_data():
    """
    处理上传的文件并进行数据分析
    返回: (df_all, df_score, df_final, df_bias, has_subjects, rank_cols, score_cols, subjects, bias_dict, exam_labels)
    """
    # 先从session_state的临时key中保存所有用户输入的值
    _save_all_input_values()
    
    # 从 session state 构建配置
    cfg = st.session_state.config_params
    
    # 直接从动态区间构建weights
    weights = []
    for interval in st.session_state.rank_intervals:
        start = int(interval["start"])
        end = int(interval["end"])
        weight = float(interval["weight"])
        weights.append((start, end, weight))
    
    # 从动态排名奖励构建rank_bonus
    rank_bonus = {int(item["threshold"]): float(item["bonus"]) for item in st.session_state.rank_bonuses}
    
    # 从动态集团排名奖励构建group_rank_bonus
    group_rank_bonus = {int(item["threshold"]): float(item["bonus"]) for item in st.session_state.group_rank_bonuses}
    
    # 从动态连续进步奖励构建chain_bonus
    chain_bonus = {int(item["times"]): float(item["bonus"]) for item in st.session_state.chain_bonuses}
    
    # 从动态总分奖励构建score_bonus
    score_bonus = {int(item["threshold"]): float(item["bonus"]) for item in st.session_state.score_bonuses}
    
    # 偏科扣分参数
    bias_penalty = {
        "轻微偏科": cfg.get("轻微偏科扣分", 10),
        "明显偏科": cfg.get("明显偏科扣分", 30),
        "严重偏科": cfg.get("严重偏科扣分", 60)
    }
    
    tie_enabled, tie_limit = get_tie_progress_rule(cfg)
    config = {
        RANK_BASIS: get_rank_basis(cfg),
        TIE_ENABLED: tie_enabled,
        TIE_RANK_LIMIT: tie_limit,
        "weights": weights,
        "rank_bonus": rank_bonus,
        "group_rank_bonus": group_rank_bonus,
        "chain_bonus": chain_bonus,
        "score_bonus": score_bonus,
        "bias_penalty": bias_penalty,
        # 支持A线和B线
        "line_a": int(cfg.get("A线（排名）", cfg.get("线（排名）", 430))),
        "bonus_line_a": cfg.get("A线过线奖励", cfg.get("过线奖励", 5)),
        "line_b": int(cfg.get("B线（排名）", 500)),
        "bonus_line_b": cfg.get("B线过线奖励", 3),
        # 偏科判定阈值（新方法：基于差值标准差，百分比单位）
        "轻微偏科_标准差": cfg.get("轻微偏科_标准差", 5),
        "明显偏科_标准差": cfg.get("明显偏科_标准差", 10),
        "严重偏科_标准差": cfg.get("严重偏科_标准差", 15),
        # 各科成绩参考线（实际分数形式，注意：偏科分析时化学+生物会合并为"选科"）
        "subject_references": st.session_state.get("subject_references", {
            "语文": 105, "数学": 105, "英语": 105,
            "物理": 70, "选科": 140,  # 选科 = 化学 + 生物
            "政治": 70, "历史": 70, "地理": 70
        })
    }
    
    # 定义科目
    subjects = ["语文", "数学", "英语", "物理", "化学", "生物"]
    
    # 处理历史总表（如果有）
    df_all = None
    has_subjects = False
    has_score = False
    
    if st.session_state.history_file_content is not None:
        with open("成绩总表_temp.xlsx", "wb") as f:
            f.write(st.session_state.history_file_content)
        
        # 读取所有工作表
        excel_file = pd.ExcelFile("成绩总表_temp.xlsx")
        sheet_names = excel_file.sheet_names
        
        # 如果有多个工作表，说明是新格式（每次考试一个工作表）
        if len(sheet_names) > 1:
            st.info(f"📊 检测到多工作表格式，共 {len(sheet_names)} 个工作表")
            # 读取除'成绩总表'和'完整总表'外的所有工作表（每个工作表对应一次考试）
            history_dfs = []
            import re
            
            for sheet_name in sheet_names:
                if sheet_name in ['成绩总表', '完整总表']:  # 跳过总表工作表
                    continue
                
                # 跳过默认工作表名
                if re.match(r'^Sheet\d+$', sheet_name):
                    st.warning(f"⚠️ 工作表 '{sheet_name}' 使用了默认名称，已跳过。请将工作表重命名为考试名称（如：期中考试、期末考试）")
                    continue
                
                df_sheet = pd.read_excel("成绩总表_temp.xlsx", sheet_name=sheet_name)
                
                # 直接使用工作表名称作为考试标识
                # 为所有列（除了"姓名"）添加考试标识后缀
                rename_dict = {}
                for col in df_sheet.columns:
                    if col != "姓名":
                        # 先去掉可能存在的尾部下划线（兼容旧模板）
                        clean_col = col.rstrip('_') if col.endswith('_') else col
                        # 检查列名是否已经有后缀（避免重复添加）
                        if not clean_col.endswith(f"_{sheet_name}"):
                            rename_dict[col] = f"{clean_col}_{sheet_name}"
                
                if rename_dict:
                    df_sheet = df_sheet.rename(columns=rename_dict)
                if rename_dict:
                    df_sheet = df_sheet.rename(columns=rename_dict)
                
                history_dfs.append((sheet_name, df_sheet))
                st.success(f"✅ 读取工作表: {sheet_name}")
            
            # 合并所有工作表的数据
            if history_dfs:
                df_all = history_dfs[0][1]
                for exam_label, df_sheet in history_dfs[1:]:
                    df_all = pd.merge(df_all, df_sheet, on="姓名", how="outer", suffixes=('', '_重复')).fillna(0)
                    # 删除重复列
                    duplicate_cols = [col for col in df_all.columns if col.endswith('_重复')]
                    if duplicate_cols:
                        df_all = df_all.drop(columns=duplicate_cols)
        else:
            # 旧格式：单工作表，所有考试堆叠在一起
            # 检查是否有说明行需要跳过
            df_temp = pd.read_excel("成绩总表_temp.xlsx", nrows=1)
            if df_temp.iloc[0, 0] and isinstance(df_temp.iloc[0, 0], str) and "说明" in str(df_temp.iloc[0, 0]):
                df_all = pd.read_excel("成绩总表_temp.xlsx", skiprows=1)
            else:
                df_all = pd.read_excel("成绩总表_temp.xlsx")
        
        # 检查历史总表的格式
        rank_cols_history = [col for col in df_all.columns if col.startswith("排名_") or col.startswith("年级排名_")]
        score_cols_history = [col for col in df_all.columns if col.startswith("总分_")]
        
        # 推断格式
        if len(score_cols_history) > 0:
            has_score = True
            # 检查是否有科目列（排除年级排名和集团排名列）
            subject_cols_check = [col for col in df_all.columns 
                                 if any(col.startswith(f"{subj}_") for subj in subjects)
                                 and "年级排名" not in col
                                 and "集团排名" not in col]
            if len(subject_cols_check) > 0:
                has_subjects = True
            else:
                has_subjects = False
        else:
            has_subjects = False
            has_score = False
    
    # 处理新上传的成绩文件
    all_dfs = []
    exam_labels = {}  # 存储考试编号到标签的映射
    
    # 优先从 session_state 读取用户自定义的考试标签
    if len(st.session_state.score_files) > 0:
        for idx, file_info in enumerate(st.session_state.score_files):
            exam_num = file_info['exam_num']
            exam_label = file_info.get('exam_label', f"第{exam_num}次考试")
            exam_labels[exam_num] = exam_label
    
    # 如果有历史总表，从列名中提取考试标签（仅用于未在 session_state 中定义的考试）
    if df_all is not None:
        # 从成绩列名中提取考试标签（格式：科目_考试X 或 总分_考试X）
        import re
        for col in df_all.columns:
            # 匹配 "科目_考试X" 或 "总分_考试X" 或 "年级排名_考试X" 等格式
            match = re.search(r'_(.+)$', col)
            if match:
                exam_label = match.group(1)
                # 尝试提取考试编号（如果是"考试1"、"考试2"这样的格式）
                exam_num_match = re.search(r'考试(\d+)', exam_label)
                if exam_num_match:
                    exam_num = int(exam_num_match.group(1))
                    # 只有当该考试编号未在 session_state 中定义时才使用历史总表的标签
                    if exam_num not in exam_labels:
                        exam_labels[exam_num] = exam_label
    
    # 更新历史总表的列名（如果用户修改了考试标签）
    if df_all is not None and len(exam_labels) > 0:
        rename_dict = {}
        import re
        for col in df_all.columns:
            if col == "姓名":
                continue
            # 匹配列名格式：科目_旧标签 或 总分_旧标签
            match = re.search(r'^(.+)_(.+)$', col)
            if match:
                prefix = match.group(1)  # 如：总分、语文、化学年级排名
                old_label = match.group(2)  # 旧的考试标签
                
                # 尝试从旧标签中提取考试编号
                exam_num_match = re.search(r'考试(\d+)', old_label)
                if exam_num_match:
                    exam_num = int(exam_num_match.group(1))
                    # 如果该考试有新标签，更新列名
                    if exam_num in exam_labels:
                        new_label = exam_labels[exam_num]
                        if new_label != old_label:
                            new_col = f"{prefix}_{new_label}"
                            rename_dict[col] = new_col
        
        if rename_dict:
            df_all = df_all.rename(columns=rename_dict)
    
    if len(st.session_state.score_files) > 0:
        for idx, file_info in enumerate(st.session_state.score_files):
            exam_num = file_info['exam_num']
            exam_label = file_info.get('exam_label', f"第{exam_num}次考试")
            exam_labels[exam_num] = exam_label
            
            # 保存临时文件
            temp_filename = f"成绩_第{exam_num}次_temp.xlsx"
            with open(temp_filename, "wb") as f:
                f.write(file_info['content'])
            
            # 读取成绩 - 检查是否有说明行需要跳过
            df_temp = pd.read_excel(temp_filename, nrows=1)
            # 如果第一行第一列包含"说明"字样，则跳过第一行
            if df_temp.iloc[0, 0] and isinstance(df_temp.iloc[0, 0], str) and "说明" in str(df_temp.iloc[0, 0]):
                df = pd.read_excel(temp_filename, skiprows=1)
            else:
                df = pd.read_excel(temp_filename)
            
            # 智能处理列名：
            # - 如果列名以 _ 结尾，说明需要添加考试标识，先去掉 _ 再重命名
            # - 如果列名不以 _ 结尾，保持原样（如"姓名"）
            # 这样 Excel 模板可以用 _ 来标记哪些列需要添加考试标识
            cleaned_columns = []
            for col in df.columns:
                if col == '姓名':
                    cleaned_columns.append(col)
                elif col.endswith('_'):
                    # 去掉尾部下划线，后续会添加考试标签
                    cleaned_columns.append(col.rstrip('_'))
                else:
                    cleaned_columns.append(col)
            
            df.columns = cleaned_columns
            all_dfs.append((exam_num, exam_label, df))
    
    # 如果没有历史总表,需要从新文件推断格式
    if df_all is None and len(all_dfs) > 0:
        # 检查第一个文件的格式
        first_df = all_dfs[0][2]
        col_count = first_df.shape[1]
        
        # 新格式：姓名 + 总分(3列) + 6科(每科3列) = 1 + 3 + 18 = 22列
        # 旧格式：
        # - 2列（姓名、排名）
        # - 3列（姓名、排名、总分）
        # - 9列（姓名、排名、总分、6科成绩）
        if col_count == 2:
            has_score = False
            has_subjects = False
        elif col_count == 3:
            has_score = True
            has_subjects = False
        elif col_count == 9:
            has_score = True
            has_subjects = True
        elif col_count == 22:
            # 新格式：包含分数、年级排名、集团排名
            has_score = True
            has_subjects = True
        else:
            st.error(f"❌ 数据格式错误！当前列数：{col_count}\\n\\n支持格式：\\n- 2列（姓名、排名）\\n- 3列（姓名、排名、总分）\\n- 9列（姓名、排名、总分、6科成绩）\\n- 22列（姓名、总分+年级排名+集团排名、6科各3列）")
            st.stop()
        
        # 创建空的df_all作为基础
        df_all = pd.DataFrame(columns=["姓名"])
    elif df_all is not None and len(all_dfs) > 0:
        # 如果有历史总表，新文件格式应该与历史总表一致
        # has_subjects和has_score已经从历史总表推断过了，保持不变
        pass
    
    # 检查所有新文件格式是否一致
    if len(all_dfs) > 0:
        expected_col_count = all_dfs[0][2].shape[1]
        for exam_num, exam_label, df in all_dfs:
            if df.shape[1] != expected_col_count:
                st.error(f"❌ {exam_label} 成绩格式不一致！\\n第1次新增：{expected_col_count}列\\n{exam_label}：{df.shape[1]}列\\n\\n请确保所有成绩使用相同格式")
                st.stop()
    
    # 合并新上传的成绩到历史总表
    for exam_num, exam_label, df in all_dfs:
        # 设置基础列名
        col_count = df.shape[1]
        
        if col_count == 2:
            df.columns = ["姓名", "本次排名"]
            rename_dict = {"本次排名": f"排名_{exam_label}"}
            
        elif col_count == 3:
            df.columns = ["姓名", "本次排名", "本次总分"]
            rename_dict = {
                "本次排名": f"排名_{exam_label}",
                "本次总分": f"总分_{exam_label}"
            }
            
        elif col_count == 9:
            df.columns = ["姓名", "本次排名", "本次总分"] + subjects
            rename_dict = {
                "本次排名": f"排名_{exam_label}",
                "本次总分": f"总分_{exam_label}"
            }
            for subj in subjects:
                rename_dict[subj] = f"{subj}_{exam_label}"
                
        elif col_count == 22:
            # 新格式：姓名 + 总分(分数、年级排名、集团排名) + 6科(每科3列)
            # 原始列名：姓名、总分、总分年级排名、总分集团排名、语文、语文年级排名、语文集团排名...
            # 目标列名：姓名、总分_考试1、总分年级排名_考试1、总分集团排名_考试1、语文_考试1、语文年级排名_考试1...
            expected_cols = ["姓名", "总分", "总分年级排名", "总分集团排名"]
            for subj in subjects:
                expected_cols.extend([subj, f"{subj}年级排名", f"{subj}集团排名"])
            
            # 重命名为带考试标签的格式（只有一个下划线）
            rename_dict = {
                "总分": f"总分_{exam_label}",
                "总分年级排名": f"总分年级排名_{exam_label}",
                "总分集团排名": f"总分集团排名_{exam_label}"
            }
            for subj in subjects:
                rename_dict[subj] = f"{subj}_{exam_label}"
                rename_dict[f"{subj}年级排名"] = f"{subj}年级排名_{exam_label}"
                rename_dict[f"{subj}集团排名"] = f"{subj}集团排名_{exam_label}"
        
        df_renamed = df.rename(columns=rename_dict)
        
        # 合并数据
        if df_all is None or df_all.empty or len(df_all.columns) == 1:
            # df_all为空或只有姓名列，直接使用新数据
            df_all = df_renamed
        else:
            # 检查是否有重复列名
            existing_cols = set(df_all.columns) - {"姓名"}
            new_cols = set(df_renamed.columns) - {"姓名"}
            duplicate_cols = existing_cols & new_cols
            
            if duplicate_cols:
                st.error(f"❌ 检测到重复考试: **{exam_label}**")
                st.info("💡 该考试已存在于历史总表中。如需更新数据，请先删除历史总表中对应的工作表，或将新文件重命名为其他考试名称。")
                st.warning(f"⚠️ 已自动跳过重复数据，保留历史总表中的原始数据")
                # 跳过重复的列，不覆盖历史数据
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
            base_col = col.rsplit('_', 1)[0]
            st.warning(f"⚠️ 检测到异常列名: {col}，已重命名为: {base_col}")
            cols_to_rename[col] = base_col
    
    if cols_to_rename:
        df_all = df_all.rename(columns=cols_to_rename)
        df_all = df_all.loc[:, ~df_all.columns.duplicated()]
    
    # 确保至少有一些数据
    if df_all is None or df_all.empty:
        st.error("❌ 没有可用的数据进行分析")
        st.stop()

    # 学校年级排名可能拆分同分学生；评分前按总分统一其年级名次。
    corrected_rank_count = correct_tied_score_ranks(df_all)
    if corrected_rank_count:
        st.info(f"已自动校正 {corrected_rank_count} 处总分年级排名：同一考试总分相同的学生统一采用最靠前的已有年级名次。")
    
    # 分析得分
    results = []
    # 识别排名列：支持多种格式
    # 1. 旧格式：排名_xxx 或 年级排名_xxx
    # 2. 新格式：总分年级排名_xxx 或 总分_年级排名_xxx
    # 只保留总分的年级排名列，排除单科排名
    rank_cols = get_grade_rank_columns(df_all.columns)
    progress_rank_cols = get_progress_rank_columns(df_all.columns, config)
    if get_rank_basis(config) == 'group':
        if not progress_rank_cols or progress_rank_cols[-1] not in df_all.columns:
            raise ValueError("集团排名方案需要本次总分集团排名，请补齐数据或切换年级方案；不会自动用年级排名代替。")
        missing_exams = [get_exam_label(col) for col in progress_rank_cols[:-1] if col not in df_all.columns]
        if missing_exams:
            st.info(f"以下历史考试未提供集团排名，已跳过：{'、'.join(missing_exams)}。连续次数仅比较有效集团排名。")
    
    # 集团排名列：支持多种格式（必须带考试标识）
    group_rank_cols = get_group_rank_columns(df_all.columns)
    
    # 总分列（排除年级排名和集团排名列）
    score_cols = []
    for col in df_all.columns:
        if col.startswith("总分_") and "年级排名" not in col and "集团排名" not in col:
            score_cols.append(col)
    
    # 如果有科目成绩，需要计算偏科扣分
    bias_dict = {}
    if has_subjects:
        subject_cols_dict = {}
        for subj in subjects:
            # 查找该科目的分数列（排除年级排名和集团排名列）
            subj_score_cols = [col for col in df_all.columns 
                              if col.startswith(f"{subj}_") 
                              and "年级排名" not in col 
                              and "集团排名" not in col]
            if subj_score_cols:
                subject_cols_dict[subj] = subj_score_cols[-1]
    
    
    comparison_results = []
    for idx, row in df_all.iterrows():
        name = row["姓名"]
        
        # 跳过非字符串姓名（可能是表头残留）
        if not isinstance(name, str) or pd.isna(name):
            continue
        
        # 与学生详情共用排名和缺考识别，保留每次考试的位置。
        grade_ranks = get_rank_history(row, rank_cols, subjects if has_subjects else [])
        group_ranks = get_rank_history(row, get_progress_rank_columns(df_all.columns, {RANK_BASIS: 'group'}),
                                       subjects if has_subjects else [])
        ranks = get_rank_history(row, progress_rank_cols, subjects if has_subjects else [])
        grade_change, group_change = latest_rank_change(grade_ranks), latest_rank_change(group_ranks)
        comparison_results.append({
            "评分方案": SCHEME_LABELS[get_rank_basis(config)],
            "年级进步名次": grade_change, "集团进步名次": group_change,
            "双排名对照": compare_rank_changes(grade_change, group_change),
        })

        # 检测最新一次考试是否缺考
        # 优先检查科目成绩，如果有科目成绩且任一科为0或空则算缺考
        # 否则看总分排名是否为0
        is_absent = False
        if has_subjects and subject_cols_dict:
            # 检查最新一次考试的各科成绩
            for subj, col in subject_cols_dict.items():
                score = row[col]
                if pd.isna(score) or score == 0:
                    is_absent = True
                    break
        else:
            # 没有科目成绩时，根据排名判断
            is_absent = (ranks[-1] == 0) if ranks else False
        
        if get_rank_basis(config) == 'group' and not is_absent and not ranks[-1]:
            raise ValueError(f"学生 {name} 本次参试但缺少有效总分集团排名，请补齐后再使用集团方案。")

        # 最新缺考时保留此前连续次数；中间缺考跳过。
        chain_ranks = ranks[:-1] if is_absent else ranks
        chain_len, _ = calculate_progress_chain(chain_ranks, config)
        chain_progress = 0.0

        # 计算最近一次进步得分
        if not is_absent and len(ranks) >= 2:
            _cur = ranks[-1]
            # 找到上一次有效排名（跳过缺考）
            _pre = None
            for i in range(len(ranks) - 2, -1, -1):
                if ranks[i] != 0:
                    _pre = ranks[i]
                    break
            
            if _cur and _pre and _cur < _pre:
                chain_progress = progress_score(int(_pre), int(_cur), config["weights"])
            else:
                chain_progress = 0.0
        else:
            chain_progress = 0.0

        # 排名加分（年级排名）- 缺考时不加分
        rank_add = 0
        if not is_absent and grade_ranks and cfg.get(GRADE_REWARD_ENABLED, True):
            latest_rank = grade_ranks[-1]
            # 找到上一次有效排名（跳过缺考）
            previous_rank = 9999
            for i in range(len(grade_ranks) - 2, -1, -1):
                if grade_ranks[i] != 0:
                    previous_rank = grade_ranks[i]
                    break
            rank_add = ranking_bonus(latest_rank, previous_rank, config)

        # A/B 线奖励始终按年级排名独立计算，不受两个排名奖励开关影响。
        line_add = 0
        if not is_absent and grade_ranks:
            line_add = line_bonus_score(grade_ranks[-1], config)
        
        # 集团排名加分 - 缺考时不加分
        group_rank_add = 0
        if not is_absent and group_ranks and cfg.get(GROUP_REWARD_ENABLED, True):
            latest_group_rank = group_ranks[-1]
            if latest_group_rank:
                group_rank_add = group_ranking_bonus(latest_group_rank, config)

        # 连续进步加分
        chain_add = chain_bonus_score(chain_len, config)
        
        # 总分奖励加分 - 缺考时不加分
        score_add = 0
        if not is_absent and score_cols and len(score_cols) > 0:
            latest_total_score = row[score_cols[-1]]
            if pd.notna(latest_total_score):
                score_add = total_score_bonus(float(latest_total_score), config)
            else:
                score_add = 0
        
        # 东校状元奖 - 年级排名第1名的独立奖励
        champion_add = 0
        if not is_absent and grade_ranks:
            latest_rank = grade_ranks[-1]
            if latest_rank == 1:
                champion_add = st.session_state.get('champion_bonus', 200)
        
        # 偏科扣分 - 缺考时不扣分
        bias_deduct = 0
        bias_level = "均衡发展"
        if not is_absent and has_subjects:
            # 构建各科分数字典
            latest_scores = {"_name": name}
            for subj, col in subject_cols_dict.items():
                latest_scores[subj] = row[col]
            
            # 构建各科排名字典（查找最新一次考试的年级排名）
            subject_ranks = {}
            for subj in subjects:
                # 查找该科目的所有年级排名列
                # 新格式：语文年级排名_考试1 或 旧格式：语文_年级排名_考试1
                subj_rank_cols = [col for col in df_all.columns 
                                 if col.startswith(f"{subj}年级排名_") 
                                 or col.startswith(f"{subj}_年级排名_")]
                if subj_rank_cols:
                    # 取最后一次（最新）的排名
                    latest_rank_col = subj_rank_cols[-1]
                    rank_val = row[latest_rank_col]
                    if pd.notna(rank_val) and rank_val > 0:
                        subject_ranks[subj] = int(rank_val)
            
            # 调用偏科检测（传入成绩、排名和配置）
            bias_info = detect_subject_bias(latest_scores, subjects, subject_ranks, config)
            bias_level = bias_info["偏科等级"]
            bias_deduct = bias_penalty_score(bias_level, config)
            
            bias_dict[name] = bias_info
        elif is_absent:
            # 缺考时标记为"缺考"，并设置完整的字段
            bias_level = "缺考"
            if name not in bias_dict:
                bias_dict[name] = {
                    "偏科等级": "缺考",
                    "最强科目": "-",
                    "最弱科目": "-",
                    "差值标准差": 0,
                    "平均差值": 0,
                    "最强科差值": 0,
                    "最弱科差值": 0
                }
        else:
            # 其他情况（没有科目成绩或数据不完整）
            if has_subjects and name not in bias_dict:
                bias_dict[name] = {
                    "偏科等级": "数据不足",
                    "最强科目": "-",
                    "最弱科目": "-",
                    "差值标准差": 0,
                    "平均差值": 0,
                    "最强科差值": 0,
                    "最弱科差值": 0
                }
        
        # 总得分
        total = chain_progress + rank_add + line_add + group_rank_add + chain_add + score_add + champion_add + bias_deduct

        if has_subjects:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, line_add, group_rank_add, score_add, champion_add, bias_deduct, total])
        elif score_cols:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, line_add, group_rank_add, score_add, champion_add, total])
        else:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, line_add, group_rank_add, champion_add, total])

    # 生成结果DataFrame
    if has_subjects:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "年级排名加分", "A/B线奖励", "集团排名加分", "总分奖励", "东校状元奖", "偏科扣分", "总得分"
        ])
    elif score_cols:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "年级排名加分", "A/B线奖励", "集团排名加分", "总分奖励", "东校状元奖", "总得分"
        ])
    else:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "年级排名加分", "A/B线奖励", "集团排名加分", "东校状元奖", "总得分"
        ])
    
    df_score = pd.concat([df_score, pd.DataFrame(comparison_results)], axis=1)
    df_final = pd.merge(df_all, df_score, on="姓名")
    df_final = df_final.sort_values(by="总得分", ascending=False)
    
    # 偏科检测结果
    df_bias = None
    if has_subjects:
        bias_results = []
        for name, bias_info in bias_dict.items():
            # 检查bias_info是否完整
            required_keys = ["偏科等级", "最强科目", "最弱科目", "差值标准差", "平均差值", "最强科差值", "最弱科差值"]
            missing_keys = [key for key in required_keys if key not in bias_info]
            
            if missing_keys:
                st.error(f"⚠️ 学生 {name} 的偏科检测数据不完整，缺少字段: {missing_keys}")
                st.error(f"实际返回的数据: {bias_info}")
                continue
            
            penalty = bias_penalty_score(bias_info["偏科等级"], config)
            bias_results.append({
                "姓名": name,
                "差值标准差": bias_info.get("差值标准差", 0),
                "平均差值": bias_info.get("平均差值", 0),
                "偏科等级": bias_info["偏科等级"],
                "最强科目": bias_info["最强科目"],
                "最强科差值": bias_info.get("最强科差值", 0),
                "最弱科目": bias_info["最弱科目"],
                "最弱科差值": bias_info.get("最弱科差值", 0),
                "扣分": penalty
            })
        df_bias = pd.DataFrame(bias_results)
        df_bias = df_bias.sort_values(by="差值标准差", ascending=False)
    
    # 清理临时文件（在数据处理完成后）
    import glob
    temp_files = glob.glob("*_temp.xlsx")
    for f in temp_files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass  # 忽略删除失败的情况
    
    return df_all, df_score, df_final, df_bias, has_subjects, rank_cols, score_cols, subjects, bias_dict, exam_labels
