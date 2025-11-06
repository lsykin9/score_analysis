import pandas as pd
import os
import re

# === 读取配置 ===
def read_config(path="参数配置.xlsx"):
    df = pd.read_excel(path)
    cfg = df.set_index("区间")["参数"].to_dict()

    # 提取区间权重
    weights = [
        (1, 20, cfg.get("A_前20", 4.0)),
        (21, 50, cfg.get("B_21-50", 3.5)),
        (51, 100, cfg.get("C_51-100", 3.0)),
        (101, 150, cfg.get("D_101-150", 2.5)),
        (151, 200, cfg.get("E_151-200", 2.0)),
        (201, 300, cfg.get("F_201-300", 1.5)),
        (301, int(cfg.get("line", 430)), cfg.get("G_301-线", 1.0)),
        (int(cfg.get("line", 430)) + 1, float("inf"), cfg.get("H_线下", 0.8))
    ]
    # 排名加分（自动识别“前N奖励”）
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

    return {
        "weights": weights,
        "rank_bonus": rank_bonus,
        "chain_bonus": chain_bonus,
        "score_bonus": score_bonus,
        "line": int(cfg.get("line", 430)),
        "bonus_line": cfg.get("过线奖励", 0)
    }

# === 区间加权进步得分 ===
def progress_score(before, now, weights):
    if before == 0 or now == 0 or now > before:
        return 0.0
    score = 0.0
    for r in range(now, before + 1):
        for start, end, w in weights:
            if start <= r <= end:
                score += w
                break
    return score

# === 排名奖励加分 ===
def ranking_bonus(now, before, config):
    if now == 0:
        return 0
    min_threshold = float("inf")
    bonus = 0
    for threshold, b in config["rank_bonus"].items():
        if now <= threshold and threshold < min_threshold:
            min_threshold = threshold
            bonus = b
    if now <= config["line"]:
        bonus += config["bonus_line"]
    return bonus

# === 连续进步加分（基于进步次数） ===
def chain_bonus_score(chain_length, config):
    return sum([config["chain_bonus"].get(i, 0) for i in range(1, chain_length + 1)])

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

# === 主流程 ===
def main():
    print("🚀 启动评分系统（支持灵活排名和连续进步加分）")

    config = read_config()
    df_new = pd.read_excel("最新成绩.xlsx")
    
    # 检查列数，判断是否包含总分
    if df_new.shape[1] == 2:
        # 只有姓名和排名
        df_new.columns = ["姓名", "本次排名"]
        has_score = False
    elif df_new.shape[1] == 3:
        # 包含姓名、排名和总分
        df_new.columns = ["姓名", "本次排名", "本次总分"]
        has_score = True
    else:
        raise ValueError("最新成绩.xlsx格式错误！应包含2列（姓名、排名）或3列（姓名、排名、总分）")

    if os.path.exists("成绩总表.xlsx"):
        df_all = pd.read_excel("成绩总表.xlsx")
    else:
        df_all = pd.DataFrame()

    if df_all.empty:
        if has_score:
            df_all = df_new.rename(columns={"本次排名": "排名_第1次", "本次总分": "总分_第1次"})
        else:
            df_all = df_new.rename(columns={"本次排名": "排名_第1次"})
    else:
        # 计算当前是第几次考试
        rank_cols = [col for col in df_all.columns if col.startswith("排名_")]
        next_num = len(rank_cols) + 1
        next_rank_col = f"排名_第{next_num}次"
        next_score_col = f"总分_第{next_num}次"
        
        if has_score:
            df_new_renamed = df_new.rename(columns={"本次排名": next_rank_col, "本次总分": next_score_col})
        else:
            df_new_renamed = df_new.rename(columns={"本次排名": next_rank_col})
        
        df_all = pd.merge(df_all, df_new_renamed, on="姓名", how="outer").fillna(0)

    df_all.to_excel("成绩总表.xlsx", index=False)
    print("✅ 成绩总表已更新")

    # 分析得分
    results = []
    rank_cols = [col for col in df_all.columns if col.startswith("排名_")]
    score_cols = [col for col in df_all.columns if col.startswith("总分_")]
    
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
        
        # 总得分
        total = chain_progress + rank_add + chain_add + score_add

        if score_cols:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, score_add, total])
        else:
            results.append([name, chain_len, chain_progress, chain_add, rank_add, total])

    # 根据是否有总分列，生成不同的DataFrame
    if score_cols:
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

    input("按回车退出...")

if __name__ == "__main__":
    main()
