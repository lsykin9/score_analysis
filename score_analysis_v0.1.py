import pandas as pd
import numpy as np
import os
import re
from utils.progress_rules import (
    TIE_ENABLED, TIE_RANK_LIMIT, get_tie_progress_rule, calculate_progress_chain,
    RANK_BASIS, get_rank_basis,
)

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

    from config.bias_rules import BIAS_DEFAULTS, normalize_bias_params
    cfg = normalize_bias_params(cfg)
    bias_penalty = {level: cfg[level + '扣分']
                    for level in ('轻微偏科', '明显偏科', '重度偏科')}

    tie_enabled, tie_limit = get_tie_progress_rule(cfg)
    return {
        **{key: cfg[key] for key in BIAS_DEFAULTS},
        RANK_BASIS: get_rank_basis(cfg),
        TIE_ENABLED: tie_enabled,
        TIE_RANK_LIMIT: tie_limit,
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
    """仅计算年级排名档位奖励；A/B 线奖励独立计算。"""
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
    
    return bonus


def line_bonus_score(now, config):
    """按当前年级排名计算 A/B 线奖励，两线同时达标时取较高奖励。"""
    if pd.isna(now) or now <= 0:
        return 0
    line_bonus = 0
    if "line_a" in config and "bonus_line_a" in config and "line_b" in config and "bonus_line_b" in config:
        # 新版本：同时有A线和B线
        if now <= config["line_a"]:
            line_bonus = max(line_bonus, config["bonus_line_a"])
        if now <= config["line_b"]:
            line_bonus = max(line_bonus, config["bonus_line_b"])
    elif "line" in config and "bonus_line" in config:
        # 兼容旧版本单线配置
        if now <= config["line"]:
            line_bonus = max(0, config["bonus_line"])
    
    return line_bonus

# === 集团排名奖励加分 ===
def group_ranking_bonus(group_rank, config):
    """根据集团排名计算奖励"""
    if group_rank == 0 or pd.isna(group_rank):
        return 0
    if "group_rank_bonus" not in config:
        return 0
    
    # 找到最小的满足条件的阈值（即最接近但大于等于排名的阈值）
    # 例如：排名54，应该匹配100而不是50（因为54>50，不满足<=50的条件）
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

# === 偏科检测：与网页共用 A/B 目标线及历史持续性算法 ===
def detect_subject_bias(row, subjects, subject_ranks=None, config=None):
    # 排名参数保留接口兼容；判定使用各场学科成绩及 A/B 分数线。
    from utils.subject_bias import detect_relative_bias
    return detect_relative_bias(row, subjects, config)


# === 偏科扣分 ===
def bias_penalty_score(bias_level, config):
    """
    根据偏科等级计算扣分
    
    参数:
        bias_level: 偏科等级（均衡发展/轻微偏科/明显偏科/重度偏科）
        config: 配置参数
    
    返回:
        float: 扣分值（负数）
    """
    if bias_level in ("均衡发展", "未达偏科阈值", "数据不足", "缺考", "待观察"):
        return 0
    
    penalties = config["bias_penalty"]
    penalty = penalties.get(bias_level, penalties.get("严重偏科", 0) if bias_level == "重度偏科" else 0)
    return -max(0, float(penalty))  # 返回负数表示扣分



# === 主流程 ===
def main():
    print("🚀 启动评分系统（支持灵活排名和连续进步加分）")

    config = read_config()
    if get_rank_basis(config) == 'group':
        raise ValueError("旧命令行流程不支持集团输入，请使用 Streamlit 网页中的集团排名方案。")
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

    # 无同场 A/B 分数线的旧命令行输入，仅显示数据不足，不回退班级均分算法。

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
        chain_progress = 0.0

        # 与网页共用限定年级排名的持平规则；保留命令行原有缺考中断行为。
        chain_len, _ = calculate_progress_chain(ranks, config, skip_absent=False)
        
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
        line_add = line_bonus_score(latest_rank, config)
        
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
            bias_info = detect_subject_bias(latest_scores, subjects, config=config)
            bias_level = bias_info["偏科等级"]
            bias_deduct = bias_penalty_score(bias_level, config)
            
            # 保存偏科信息供后续使用
            bias_dict[name] = bias_info
        
        # 总得分（包含偏科扣分）
        total = chain_progress + rank_add + line_add + chain_add + score_add + bias_deduct

        if has_subjects:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, line_add, score_add, bias_deduct, total])
        elif score_cols:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, line_add, score_add, total])
        else:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, line_add, total])

    # 根据是否有总分列和科目列，生成不同的DataFrame
    if has_subjects:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "排名加分", "A/B线奖励", "总分奖励", "偏科扣分", "总得分"
        ])
    elif score_cols:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "排名加分", "A/B线奖励", "总分奖励", "总得分"
        ])
    else:
        df_score = pd.DataFrame(results, columns=[
            "姓名", "连续进步次数", "区间进步得分", "连续进步加分", "排名加分", "A/B线奖励", "总得分"
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
                "偏科指数": bias_info["偏科指数"],
                "偏科等级": bias_info["偏科等级"],
                "薄弱科目": "、".join(bias_info["薄弱科目"]),
                "最强科目": bias_info["最强科目"],
                "最弱科目": bias_info["最弱科目"],
                "扣分": penalty
            })
        
        df_bias = pd.DataFrame(bias_results)
        df_bias = df_bias.sort_values(by="偏科指数", ascending=False)
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
