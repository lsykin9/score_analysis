import pandas as pd
import numpy as np
import os
import re

# === 读取配置 ===
def read_config(path="参数配置.xlsx", config_dict=None):
    """
    读取配置参数
    参数:
        path: Excel配置文件路径(可选)
        config_dict: 字典格式的配置(可选,包含rank_intervals和rank_bonuses)
    """
    if config_dict is not None:
        # 使用传入的字典配置
        cfg = config_dict
        
        # 从rank_intervals构建weights
        weights = []
        for interval in cfg.get("rank_intervals", []):
            start = int(interval["start"])
            end = int(interval["end"])
            weight = float(interval["weight"])
            weights.append((start, end, weight))
        
        # 从rank_bonuses构建rank_bonus字典
        rank_bonus = {item["threshold"]: item["bonus"] for item in cfg.get("rank_bonuses", [])}
        
    else:
        # 从Excel读取配置
        df = pd.read_excel(path)
        cfg = df.set_index("参数")["数值"].to_dict()

        # 提取区间权重
        weights = [
            (1, 20, cfg.get("排名前20", 4.0)),
            (21, 50, cfg.get("排名21-50", 3.5)),
            (51, 100, cfg.get("排名51-100", 3.0)),
            (101, 150, cfg.get("排名101-150", 2.5)),
            (151, 200, cfg.get("排名151-200", 2.0)),
            (201, 300, cfg.get("排名201-300", 1.5)),
            (301, int(cfg.get("线（排名）", 430)), cfg.get("排名301-线", 1.0)),
            (int(cfg.get("线（排名）", 430)) + 1, float("inf"), cfg.get("排名线下", 0.8))
        ]
        # 排名加分（自动识别"前N奖励"）
        rank_bonus = {
            int(re.findall(r"\d+", k)[0]): v
            for k, v in cfg.items()
            if k.startswith("前") and "奖励" in k and "连续" not in k
        }

    # 连续进步加分（自动识别"连续进步第N次奖励"）
    chain_bonus = {
        int(re.findall(r"\d+", k)[0]): v
        for k, v in cfg.items()
        if k.startswith("连续进步第") and "奖励" in k
    }

    # 总分奖励阈值（自动识别"总分大于N奖励"）
    score_bonus = {}
    for k, v in cfg.items():
        if k.startswith("总分大于") and "奖励" in k:
            threshold = int(re.findall(r"\d+", k)[0])
            score_bonus[threshold] = v

    # 偏科扣分参数
    bias_penalty = {
        "轻微偏科": cfg.get("轻微偏科扣分", 10),
        "明显偏科": cfg.get("明显偏科扣分", 30),
        "严重偏科": cfg.get("严重偏科扣分", 60)
    }

    return {
        "weights": weights,
        "rank_bonus": rank_bonus,
        "chain_bonus": chain_bonus,
        "score_bonus": score_bonus,
        "bias_penalty": bias_penalty,
        "line": int(cfg.get("线（排名）", 430)),
        "bonus_line": cfg.get("过线奖励", 5)
    }

# === 区间加权进步得分 ===
def progress_score(before, now, weights):
    """
    计算区间进步得分
    before: 之前的排名
    now: 现在的排名
    weights: 区间权重配置 [(start, end, weight), ...]
    
    进步得分 = 进步跨越的每个排名的权重之和
    注意：不包括当前排名，只计算进步的部分
    例如：44→34 进步10名，计算 35-44 共10个排名
    """
    if before == 0 or now == 0 or now >= before:
        return 0.0
    score = 0.0
    # 从 now+1 开始，不包括当前排名now
    for r in range(now + 1, before + 1):
        for start, end, w in weights:
            if start <= r <= end:
                score += w
                break
    return score

# === 排名奖励加分 ===
def ranking_bonus(now, before, config):
    if now == 0:
        return 0
    
    # 找到最小的满足条件的阈值（当前排名必须<=阈值才能拿奖励）
    # 例如：排名4，可以拿10、20、30、50、100的奖励，应该拿最小阈值10对应的奖励
    min_threshold = float("inf")
    bonus = 0
    for threshold, b in config["rank_bonus"].items():
        if now <= threshold and threshold < min_threshold:
            min_threshold = threshold
            bonus = b
    
    # AB线过线奖励（只加一个，取奖励更高的）
    line_bonus = 0
    if "line_a" in config and "bonus_line_a" in config and "line_b" in config and "bonus_line_b" in config:
        # 新版本：同时有A线和B线
        if now <= config["line_a"]:
            line_bonus = max(line_bonus, config["bonus_line_a"])
        if now <= config["line_b"]:
            line_bonus = max(line_bonus, config["bonus_line_b"])
        bonus += line_bonus
    elif "line" in config and "bonus_line" in config:
        # 兼容旧版本单线配置
        if now <= config["line"]:
            bonus += config["bonus_line"]
    
    return bonus

# === 集团排名奖励加分 ===
def group_ranking_bonus(group_rank, config):
    """根据集团排名计算奖励"""
    if group_rank == 0 or pd.isna(group_rank):
        return 0
    if "group_rank_bonus" not in config:
        return 0
    
    # 找到最小的满足条件的阈值
    min_threshold = float("inf")
    bonus = 0
    for threshold, b in config["group_rank_bonus"].items():
        if group_rank <= threshold and threshold < min_threshold:
            min_threshold = threshold
            bonus = b
    return bonus

# === 连续进步加分（基于进步次数） ===
def chain_bonus_score(chain_length, config):
    """
    根据连续进步次数计算加分
    只返回当前连续次数对应的奖励，不累加之前的
    
    例如：连续进步2次，只加2次对应的8分，不加1次的5分
    """
    if chain_length == 0:
        return 0
    
    # 找到连续次数对应的奖励
    # 如果超过最大配置次数，使用最大次数的奖励
    bonus = 0
    max_times = 0
    for times, b in config["chain_bonus"].items():
        if chain_length >= times and times > max_times:
            max_times = times
            bonus = b
    
    return bonus

# === 总分奖励加分 ===
def total_score_bonus(total_score, config):
    """根据总分计算奖励"""
    if total_score == 0:
        return 0
    bonus = 0
    # 找到所有满足条件的阈值，取最大奖励
    for threshold, b in config["score_bonus"].items():
        if total_score > threshold and b > bonus:
            bonus = b
    return bonus

# === 偏科检测（基于排名的混合法） ===
def detect_subject_bias(row, subjects, subject_ranks=None, config=None):
    """
    检测学生是否偏科（新方法：基于成绩与参考线差值的标准差）
    
    参数:
        row: 学生成绩数据行（包含各科分数）
        subjects: 科目列表
        subject_ranks: 各科排名字典 {科目: 排名}（用于辅助信息，非主要判定依据）
        config: 配置参数（包含偏科判定阈值和各科参考线）
    
    返回:
        dict: 包含偏科等级、最强科目、最弱科目、差值标准差等信息
    """
    if not config:
        return {
            "偏科等级": "配置错误",
            "最强科目": "-",
            "最弱科目": "-",
            "差值标准差": 0,
            "平均差值": 0
        }
    
    # 获取各科参考线
    subject_references = config.get("subject_references", {})
    
    # 计算各科差值（成绩 - 参考线）
    differences = []
    diff_dict = {}
    
    for subj in subjects:
        # 获取该科成绩
        score = row.get(subj, 0)
        if pd.isna(score) or score <= 0:
            continue  # 跳过缺考或无效成绩
        
        # 获取该科参考线
        reference = subject_references.get(subj, 100)  # 默认100分
        
        # 计算差值
        diff = score - reference
        differences.append(diff)
        diff_dict[subj] = diff
    
    # 如果没有足够的有效数据
    if len(differences) < 2:
        return {
            "偏科等级": "数据不足",
            "最强科目": "-",
            "最弱科目": "-",
            "差值标准差": 0,
            "平均差值": 0,
            "最强科差值": 0,
            "最弱科差值": 0
        }
    
    # 计算统计指标
    diff_array = np.array(differences)
    mean_diff = np.mean(diff_array)  # 平均差值（反映整体水平）
    std_diff = np.std(diff_array, ddof=1) if len(differences) > 1 else 0  # 标准差（反映离散程度）
    max_diff = np.max(diff_array)  # 最大差值
    min_diff = np.min(diff_array)  # 最小差值
    range_diff = max_diff - min_diff  # 极差（最强科比最弱科高多少）
    
    # 找到最强和最弱科目
    best_subject = max(diff_dict, key=diff_dict.get) if diff_dict else "-"
    worst_subject = min(diff_dict, key=diff_dict.get) if diff_dict else "-"
    best_diff = diff_dict.get(best_subject, 0)
    worst_diff = diff_dict.get(worst_subject, 0)
    
    # 判定偏科等级（基于标准差）
    bias_level = "均衡发展"
    
    severe_std = config.get("严重偏科_标准差", 30)
    obvious_std = config.get("明显偏科_标准差", 20)
    mild_std = config.get("轻微偏科_标准差", 10)
    
    if std_diff >= severe_std:
        bias_level = "严重偏科"
    elif std_diff >= obvious_std:
        bias_level = "明显偏科"
    elif std_diff >= mild_std:
        bias_level = "轻微偏科"
    
    return {
        "偏科等级": bias_level,
        "最强科目": best_subject,
        "最弱科目": worst_subject,
        "差值标准差": round(std_diff, 2),
        "平均差值": round(mean_diff, 2),
        "最强科差值": round(best_diff, 2),
        "最弱科差值": round(worst_diff, 2),
        "各科差值": diff_dict
    }


# === 旧的基于分数的偏科检测（备用） ===
def _detect_subject_bias_by_score(row, subjects):
    """
    基于分数的偏科检测（旧方法，作为备用）
    """
    # 定义各科满分
    full_scores = {
        "语文": 150, "数学": 150, "英语": 150,
        "物理": 100, "化学": 100, "生物": 100
    }
    
    # 提取各科成绩并标准化为百分制
    normalized_scores = []
    subject_scores = {}
    
    for subj in subjects:
        score = row.get(subj, 0)
        if score > 0:  # 只处理有效成绩
            full_score = full_scores.get(subj, 100)
            normalized = (score / full_score) * 100
            normalized_scores.append(normalized)
            subject_scores[subj] = {
                "原始分": score,
                "标准化分": round(normalized, 2)
            }
    
    # 如果没有有效成绩，返回空结果
    if len(normalized_scores) < 2:
        return {
            "偏科等级": "数据不足",
            "最强科目": "-",
            "最弱科目": "-"
        }
    
    # 计算标准差
    std_dev = np.std(normalized_scores, ddof=1)  # 使用样本标准差
    mean_score = np.mean(normalized_scores)
    
    # 判定偏科等级（简单判定）
    if std_dev < 10:
        bias_level = "均衡发展"
    elif std_dev < 15:
        bias_level = "轻微偏科"
    elif std_dev < 20:
        bias_level = "明显偏科"
    else:
        bias_level = "严重偏科"
    
    # 找出最强和最弱科目
    max_subj = max(subject_scores.items(), key=lambda x: x[1]["标准化分"])
    min_subj = min(subject_scores.items(), key=lambda x: x[1]["标准化分"])
    
    return {
        "偏科等级": bias_level,
        "最强科目": f"{max_subj[0]}({max_subj[1]['标准化分']}%)",
        "最弱科目": f"{min_subj[0]}({min_subj[1]['标准化分']}%)",
        "标准差": round(std_dev, 2),
        "平均标准化分": round(mean_score, 2),
        "科目详情": subject_scores
    }

# === 偏科扣分 ===
def bias_penalty_score(bias_level, config):
    """
    根据偏科等级计算扣分
    
    参数:
        bias_level: 偏科等级（均衡发展/轻微偏科/明显偏科/严重偏科）
        config: 配置参数
    
    返回:
        float: 扣分值（负数）
    """
    if bias_level == "均衡发展" or bias_level == "数据不足":
        return 0
    
    penalty = config["bias_penalty"].get(bias_level, 0)
    return -penalty  # 返回负数表示扣分



# === 主流程 ===
def main():
    print("🚀 启动评分系统（支持灵活排名和连续进步加分）")

    config = read_config()
    df_new = pd.read_excel("最新成绩.xlsx")
    
    # 定义各科科目
    subjects = ["语文", "数学", "英语", "物理", "化学", "生物"]
    
    # 检查列数，判断数据格式
    col_count = df_new.shape[1]
    
    if col_count == 2:
        # 格式1: 姓名、排名
        df_new.columns = ["姓名", "本次排名"]
        has_score = False
        has_subjects = False
    elif col_count == 3:
        # 格式2: 姓名、排名、总分
        df_new.columns = ["姓名", "本次排名", "本次总分"]
        has_score = True
        has_subjects = False
    elif col_count == 9:
        # 格式3: 姓名、排名、总分、6科成绩
        df_new.columns = ["姓名", "本次排名", "本次总分"] + subjects
        has_score = True
        has_subjects = True
    else:
        raise ValueError(f"最新成绩.xlsx格式错误！当前列数：{col_count}\n支持格式：\n- 2列（姓名、排名）\n- 3列（姓名、排名、总分）\n- 9列（姓名、排名、总分、语文、数学、英语、物理、化学、生物）")

    if os.path.exists("成绩总表.xlsx"):
        df_all = pd.read_excel("成绩总表.xlsx")
    else:
        df_all = pd.DataFrame()

    if df_all.empty:
        if has_subjects:
            # 包含各科成绩
            rename_dict = {"本次排名": "排名_第1次", "本次总分": "总分_第1次"}
            for subj in subjects:
                rename_dict[subj] = f"{subj}_第1次"
            df_all = df_new.rename(columns=rename_dict)
        elif has_score:
            # 只有总分
            df_all = df_new.rename(columns={"本次排名": "排名_第1次", "本次总分": "总分_第1次"})
        else:
            # 只有排名
            df_all = df_new.rename(columns={"本次排名": "排名_第1次"})
    else:
        # 计算当前是第几次考试
        rank_cols = [col for col in df_all.columns if col.startswith("排名_")]
        next_num = len(rank_cols) + 1
        
        # 构建重命名字典
        rename_dict = {
            "本次排名": f"排名_第{next_num}次"
        }
        
        if has_score:
            rename_dict["本次总分"] = f"总分_第{next_num}次"
        
        if has_subjects:
            for subj in subjects:
                rename_dict[subj] = f"{subj}_第{next_num}次"
        
        df_new_renamed = df_new.rename(columns=rename_dict)
        df_all = pd.merge(df_all, df_new_renamed, on="姓名", how="outer").fillna(0)

    df_all.to_excel("成绩总表.xlsx", index=False)
    print("✅ 成绩总表已更新")

    # 分析得分
    results = []
    rank_cols = [col for col in df_all.columns if col.startswith("排名_")]
    score_cols = [col for col in df_all.columns if col.startswith("总分_")]
    
    # 如果有科目成绩，需要计算偏科扣分
    bias_dict = {}  # 存储每个学生的偏科信息
    if has_subjects:
        # 获取最新一次的科目成绩列
        subject_cols_dict = {}
        for subj in subjects:
            subj_cols = [col for col in df_all.columns if col.startswith(f"{subj}_")]
            if subj_cols:
                subject_cols_dict[subj] = subj_cols[-1]  # 取最新一次
    
    for _, row in df_all.iterrows():
        name = row["姓名"]
        ranks = [row[col] for col in rank_cols]
        chain_len = 0
        chain_progress = 0.0

        # 计算连续进步次数
        for i in range(1, len(ranks)):
            before, now = ranks[i - 1], ranks[i]
            if now != 0 and before != 0 and now <= before:
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
            # 提取最新一次的各科成绩
            latest_scores = {"姓名": name}
            for subj, col in subject_cols_dict.items():
                latest_scores[subj] = row[col]
            
            # 检测偏科
            bias_info = detect_subject_bias(latest_scores, subjects)
            bias_level = bias_info["偏科等级"]
            bias_deduct = bias_penalty_score(bias_level, config)
            
            # 保存偏科信息供后续使用
            bias_dict[name] = bias_info
        
        # 总得分（包含偏科扣分）
        total = chain_progress + rank_add + chain_add + score_add + bias_deduct

        if has_subjects:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, score_add, bias_deduct, total])
        elif score_cols:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, score_add, total])
        else:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, total])

    # 根据是否有总分列和科目列，生成不同的DataFrame
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
    df_score.to_excel("进步链分析结果.xlsx", index=False)
    print("✅ 已生成进步链分析结果.xlsx")

    df_final = pd.merge(df_all, df_score, on="姓名")
    df_final = df_final.sort_values(by="总得分", ascending=False)
    df_final.to_excel("最终得分结果.xlsx", index=False)
    print("✅ 已生成最终得分结果.xlsx")

    # 偏科检测（仅在有科目成绩时执行）
    if has_subjects:
        print("\n📊 正在进行偏科检测...")
        bias_results = []
        
        # 使用之前计算好的偏科信息
        for name, bias_info in bias_dict.items():
            # 计算该学生的扣分
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
        df_bias.to_excel("偏科检测报告.xlsx", index=False)
        print("✅ 已生成偏科检测报告.xlsx")
        
        # 统计偏科情况
        bias_stats = df_bias["偏科等级"].value_counts()
        print("\n📈 偏科情况统计:")
        for level, count in bias_stats.items():
            print(f"   {level}: {count}人")
        
        # 统计扣分情况
        total_penalty = df_bias[df_bias["扣分"] < 0]["扣分"].sum()
        penalty_count = len(df_bias[df_bias["扣分"] < 0])
        if penalty_count > 0:
            print(f"\n⚠️  偏科扣分统计:")
            print(f"   共{penalty_count}人被扣分，累计扣除{abs(total_penalty):.1f}分")

    input("\n按回车退出...")


if __name__ == "__main__":
    main()
