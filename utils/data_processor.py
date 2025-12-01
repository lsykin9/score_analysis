"""
数据处理工具模块
负责处理文件上传、数据合并和分析计算
"""
import streamlit as st
import pandas as pd
import io
from score_analysis_v0_1 import (
    progress_score,
    ranking_bonus,
    group_ranking_bonus,
    chain_bonus_score,
    total_score_bonus,
    detect_subject_bias,
    bias_penalty_score
)


def _save_all_input_values():
    """从session_state的临时key中保存所有输入值"""
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
    rank_bonus = {item["threshold"]: item["bonus"] for item in st.session_state.rank_bonuses}
    
    # 从动态集团排名奖励构建group_rank_bonus
    group_rank_bonus = {item["threshold"]: item["bonus"] for item in st.session_state.group_rank_bonuses}
    
    # 从动态连续进步奖励构建chain_bonus
    chain_bonus = {item["times"]: item["bonus"] for item in st.session_state.chain_bonuses}
    
    # 从动态总分奖励构建score_bonus
    score_bonus = {item["threshold"]: item["bonus"] for item in st.session_state.score_bonuses}
    
    # 偏科扣分参数
    bias_penalty = {
        "轻微偏科": cfg.get("轻微偏科扣分", 10),
        "明显偏科": cfg.get("明显偏科扣分", 30),
        "严重偏科": cfg.get("严重偏科扣分", 60)
    }
    
    config = {
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
        # 偏科判定阈值
        "轻微偏科_标准差": cfg.get("轻微偏科_标准差", 15),
        "轻微偏科_最大差距": cfg.get("轻微偏科_最大差距", 50),
        "轻微偏科_相对离散度": cfg.get("轻微偏科_相对离散度", 80),
        "明显偏科_标准差": cfg.get("明显偏科_标准差", 30),
        "明显偏科_最大差距": cfg.get("明显偏科_最大差距", 100),
        "明显偏科_相对离散度": cfg.get("明显偏科_相对离散度", 150),
        "严重偏科_标准差": cfg.get("严重偏科_标准差", 60),
        "严重偏科_最大差距": cfg.get("严重偏科_最大差距", 200),
        "严重偏科_相对离散度": cfg.get("严重偏科_相对离散度", 300)
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
        elif col_count == 3:
            df.columns = ["姓名", "本次排名", "本次总分"]
        elif col_count == 9:
            df.columns = ["姓名", "本次排名", "本次总分"] + subjects
        elif col_count == 22:
            # 新格式：姓名 + 总分(分数、年级排名、集团排名) + 6科(每科3列)
            new_cols = ["姓名", "本次总分", "本次年级排名", "本次集团排名"]
            for subj in subjects:
                new_cols.extend([f"{subj}_分数", f"{subj}_年级排名", f"{subj}_集团排名"])
            df.columns = new_cols
        
        # 重命名为自定义标签
        if col_count == 22:
            # 新格式重命名
            rename_dict = {
                "本次年级排名": f"年级排名_{exam_label}",
                "本次集团排名": f"集团排名_{exam_label}",
                "本次总分": f"总分_{exam_label}"
            }
            for subj in subjects:
                rename_dict[f"{subj}_分数"] = f"{subj}_{exam_label}"
                rename_dict[f"{subj}_年级排名"] = f"{subj}_年级排名_{exam_label}"
                rename_dict[f"{subj}_集团排名"] = f"{subj}_集团排名_{exam_label}"
        else:
            # 旧格式重命名
            rename_dict = {"本次排名": f"排名_{exam_label}"}
            if has_score:
                rename_dict["本次总分"] = f"总分_{exam_label}"
        if has_subjects:
            for subj in subjects:
                rename_dict[subj] = f"{subj}_{exam_label}"
        
        df_renamed = df.rename(columns=rename_dict)
        
        # 合并数据
        if df_all is None:
            df_all = df_renamed
        else:
            # 检查是否有重复列名
            existing_cols = set(df_all.columns) - {"姓名"}
            new_cols = set(df_renamed.columns) - {"姓名"}
            duplicate_cols = existing_cols & new_cols
            
            if duplicate_cols:
                st.warning(f"⚠️ 警告: 检测到重复列名 {duplicate_cols}，请修改考试名称以避免冲突")
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
    
    # 分析得分
    results = []
    rank_cols = [col for col in df_all.columns if col.startswith("排名_") or col.startswith("年级排名_")]
    group_rank_cols = [col for col in df_all.columns if col.startswith("集团排名_")]
    score_cols = [col for col in df_all.columns if col.startswith("总分_")]
    
    # 如果有科目成绩，需要计算偏科扣分
    bias_dict = {}
    if has_subjects:
        subject_cols_dict = {}
        for subj in subjects:
            # 优先使用带"分数"的列，如果没有则使用旧格式
            subj_score_cols = [col for col in df_all.columns if col.startswith(f"{subj}_") and not ("年级排名" in col or "集团排名" in col)]
            if subj_score_cols:
                subject_cols_dict[subj] = subj_score_cols[-1]
    
    for _, row in df_all.iterrows():
        name = row["姓名"]
        
        # 检测缺考：检查最新一次考试是否有科目缺考
        is_absent = False
        if has_subjects:
            for subj, col in subject_cols_dict.items():
                latest_score = row[col]
                if pd.isna(latest_score) or latest_score == 0:
                    is_absent = True
                    break
        
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
        last_valid_rank_idx = -1  # 记录最后一个非缺考的排名位置

        # 计算连续进步次数（需要考虑缺考）
        # 如果当前缺考，需要找到上一次有效成绩
        if is_absent:
            # 当前缺考，从倒数第二次开始往前找有效成绩
            for i in range(len(ranks) - 2, -1, -1):
                if ranks[i] != 0:
                    last_valid_rank_idx = i
                    break
            
            # 如果找到了有效成绩，计算到该位置为止的连续进步次数
            if last_valid_rank_idx >= 0:
                for i in range(1, last_valid_rank_idx + 1):
                    before, now = ranks[i - 1], ranks[i]
                    if now != 0 and before != 0 and now < before:
                        chain_len += 1
                    elif now != 0 and before != 0:
                        # 退步则归零
                        chain_len = 0
        else:
            # 当前没有缺考，正常计算连续进步次数
            for i in range(1, len(ranks)):
                before, now = ranks[i - 1], ranks[i]
                if now != 0 and before != 0 and now < before:
                    chain_len += 1
                elif now != 0 and before != 0:
                    # 退步则归零
                    chain_len = 0
        
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
        if not is_absent:
            latest_rank = int(ranks[-1]) if ranks[-1] else 0
            # 找到上一次有效排名（跳过缺考）
            previous_rank = 9999
            for i in range(len(ranks) - 2, -1, -1):
                if ranks[i] != 0:
                    previous_rank = int(ranks[i])
                    break
            rank_add = ranking_bonus(latest_rank, previous_rank, config)
        
        # 集团排名加分 - 缺考时不加分
        group_rank_add = 0
        if not is_absent and group_rank_cols and len(group_rank_cols) > 0:
            latest_group_rank = row[group_rank_cols[-1]]
            if pd.notna(latest_group_rank) and latest_group_rank > 0:
                group_rank_add = group_ranking_bonus(int(latest_group_rank), config)
        
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
        
        # 偏科扣分 - 缺考时不扣分
        bias_deduct = 0
        bias_level = "均衡发展"
        if not is_absent and has_subjects:
            # 构建各科分数字典
            latest_scores = {"姓名": name}
            for subj, col in subject_cols_dict.items():
                latest_scores[subj] = row[col]
            
            # 构建各科排名字典（新格式）
            subject_ranks = {}
            for subj in subjects:
                # 查找该科目的年级排名列
                rank_col = f"{subj}_年级排名_{exam_labels.get(len(rank_cols), f'第{len(rank_cols)}次考试')}" if exam_labels else None
                if rank_col and rank_col in df_all.columns:
                    rank_val = row[rank_col]
                    if pd.notna(rank_val) and rank_val > 0:
                        subject_ranks[subj] = int(rank_val)
            
            # 调用偏科检测（传入排名和配置）
            bias_info = detect_subject_bias(latest_scores, subjects, subject_ranks, cfg)
            bias_level = bias_info["偏科等级"]
            bias_deduct = bias_penalty_score(bias_level, config)
            
            bias_dict[name] = bias_info
        elif is_absent:
            # 缺考时标记为"缺考"
            bias_level = "缺考"
            if name not in bias_dict:
                bias_dict[name] = {"偏科等级": "缺考"}
        
        # 总得分
        total = chain_progress + rank_add + group_rank_add + chain_add + score_add + bias_deduct

        if has_subjects:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, group_rank_add, score_add, bias_deduct, total])
        elif score_cols:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, group_rank_add, score_add, total])
        else:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, group_rank_add, total])

    # 生成结果DataFrame
    if has_subjects:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "年级排名加分", "集团排名加分", "总分奖励", "偏科扣分", "总得分"
        ])
    elif score_cols:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "年级排名加分", "集团排名加分", "总分奖励", "总得分"
        ])
    else:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "年级排名加分", "集团排名加分", "总得分"
        ])
    
    df_final = pd.merge(df_all, df_score, on="姓名")
    df_final = df_final.sort_values(by="总得分", ascending=False)
    
    # 偏科检测结果
    df_bias = None
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
    
    return df_all, df_score, df_final, df_bias, has_subjects, rank_cols, score_cols, subjects, bias_dict, exam_labels
