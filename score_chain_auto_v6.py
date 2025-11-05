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
    print("weights")
    # 排名加分（自动识别“前N奖励”）
    rank_bonus = {
        int(re.findall(r"\d+", k)[0]): v
        for k, v in cfg.items()
        if k.startswith("前") and "奖励" in k and "连续" not in k
    }

    # 连续进步加分（自动识别“连续进步第N次奖励”）
    chain_bonus = {
        int(re.findall(r"\d+", k)[0]): v
        for k, v in cfg.items()
        if k.startswith("连续进步第") and "奖励" in k
    }

    return {
        "weights": weights,
        "rank_bonus": rank_bonus,
        "chain_bonus": chain_bonus,
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

# === 主流程 ===
def main():
    print("🚀 启动评分系统（支持灵活排名和连续进步加分）")

    config = read_config()
    df_new = pd.read_excel("最新成绩.xlsx")
    df_new.columns = ["姓名", "本次考试"]

    if os.path.exists("成绩总表.xlsx"):
        df_all = pd.read_excel("成绩总表.xlsx")
    else:
        df_all = pd.DataFrame()

    if df_all.empty:
        df_all = df_new.rename(columns={"本次考试": "第1次"})
    else:
        next_col = f"第{df_all.shape[1]}次"
        df_all = pd.merge(df_all, df_new, on="姓名", how="outer").fillna(0)
        df_all = df_all.rename(columns={"本次考试": next_col})

    df_all.to_excel("成绩总表.xlsx", index=False)
    print("✅ 成绩总表已更新")

    # 分析得分
    results = []
    cols = df_all.columns[1:]
    for _, row in df_all.iterrows():
        name = row["姓名"]
        scores = list(row[1:])
        chain_len = 0
        chain_progress = 0.0

##############################################
        for i in range(1, len(scores)):
            before, now = scores[i - 1], scores[i]
            if now != 0 and before != 0 and now <= before:
                chain_len += 1
            else:
                ##
                chain_len = 0
                #break  # 连续进步断了
        _cur = scores[len(scores)-1]
        _pre = scores[len(scores)-2]
        if _cur and _pre and _cur < _pre:
            chain_progress = progress_score(_pre, _cur, config["weights"])
        else:
            chain_progress = 0.0

        latest = scores[-1]
        previous = scores[-2] if len(scores) > 1 else 9999
        rank_add = ranking_bonus(latest, previous, config)
        chain_add = chain_bonus_score(chain_len, config)
        total = chain_progress + rank_add + chain_add

        results.append([name, chain_len, chain_progress, chain_add, rank_add, total])

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
