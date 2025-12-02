"""调试排名加分和总分奖励计算问题"""
import pandas as pd
from score_analysis_v0_1 import ranking_bonus, total_score_bonus

# 模拟配置
config = {
    "rank_bonus": {10: 15, 20: 10, 50: 5},  # 前10奖励15分，前20奖励10分，前50奖励5分
    "score_bonus": {600: 10, 650: 15, 700: 20},  # 总分>600奖励10分，>650奖励15分，>700奖励20分
    "line_a": 430,
    "bonus_line_a": 5,
    "line_b": 500,
    "bonus_line_b": 3
}

print("=== 测试排名加分 ===")
print(f"配置: {config['rank_bonus']}")
print(f"A线: {config['line_a']}, 奖励: {config['bonus_line_a']}")
print(f"B线: {config['line_b']}, 奖励: {config['bonus_line_b']}")

# 测试几个排名
test_ranks = [
    (4, 9, "从9进步到4"),
    (27, 50, "从50进步到27"),
    (100, 150, "从150进步到100"),
    (430, 500, "从500进步到430（过A线）"),
]

for now, before, desc in test_ranks:
    bonus = ranking_bonus(now, before, config)
    print(f"{desc}: now={now}, before={before} -> 加分={bonus}")

print("\n=== 测试总分奖励 ===")
print(f"配置: {config['score_bonus']}")

test_scores = [550, 605, 655, 705]
for score in test_scores:
    bonus = total_score_bonus(score, config)
    print(f"总分={score} -> 奖励={bonus}")

# 读取实际数据测试
print("\n=== 实际数据测试 ===")
df = pd.read_excel('测试成绩总表_4次考试.xlsx')

# 找到排名列和总分列
rank_cols = [col for col in df.columns if col.startswith('总分_年级排名_')]
score_cols = [col for col in df.columns if col.startswith('总分_考试')]

print(f"排名列: {rank_cols}")
print(f"总分列: {score_cols}")

# 测试前3个学生
for idx in range(min(3, len(df))):
    student = df.iloc[idx]
    name = student['姓名']
    
    # 获取最新排名
    if len(rank_cols) > 0:
        latest_rank = student[rank_cols[-1]]
        previous_rank = student[rank_cols[-2]] if len(rank_cols) > 1 else 9999
        rank_bonus_val = ranking_bonus(int(latest_rank), int(previous_rank), config)
        print(f"\n{name}: 排名 {previous_rank} -> {latest_rank}, 加分={rank_bonus_val}")
    
    # 获取最新总分
    if len(score_cols) > 0:
        latest_score = student[score_cols[-1]]
        score_bonus_val = total_score_bonus(float(latest_score), config)
        print(f"  总分={latest_score}, 奖励={score_bonus_val}")
