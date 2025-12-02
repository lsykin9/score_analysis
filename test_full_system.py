"""
全面系统测试脚本
测试成绩进步评分系统的所有核心计算逻辑
"""
import pandas as pd
import sys
from utils.data_processor import process_data
from score_analysis_v0_1 import (
    progress_score, ranking_bonus, group_ranking_bonus,
    chain_bonus_score, total_score_bonus, detect_subject_bias, bias_penalty_score
)

# 模拟 streamlit session_state
class MockSessionState:
    def __init__(self):
        self.history_file_content = None
        self.score_files = []
        self.config_params = {
            "rank_bonus": {4: 100, 10: 50, 20: 30, 50: 20, 100: 10},
            "line_a": 300,
            "line_b": 600,
            "bonus_line_a": 50,
            "bonus_line_b": 20,
            "max_continuous_bonus": 50,
            "bias_penalty_ratio": 0.5,
            "bias_threshold": 50,
            "weights": [(1, 10, 1.0), (11, 30, 0.8), (31, 100, 0.5), (101, 300, 0.3)],
            "chain_bonus": [
                {"times": 1, "bonus": 5},
                {"times": 2, "bonus": 10},
                {"times": 3, "bonus": 20}
            ],
            "score_bonuses": [
                {"threshold": 580, "bonus": 5},
                {"threshold": 590, "bonus": 8},
                {"threshold": 600, "bonus": 10},
                {"threshold": 610, "bonus": 12},
                {"threshold": 620, "bonus": 15},
                {"threshold": 630, "bonus": 18},
                {"threshold": 640, "bonus": 20}
            ],
            "group_rank_bonuses": [
                {"threshold": 10, "bonus": 30},
                {"threshold": 30, "bonus": 20},
                {"threshold": 50, "bonus": 15},
                {"threshold": 100, "bonus": 10}
            ],
            "轻微偏科_排名标准差": 50,
            "中度偏科_排名标准差": 100,
            "严重偏科_排名标准差": 150,
            "轻微偏科_最大排名差": 100,
            "中度偏科_最大排名差": 150,
            "严重偏科_最大排名差": 200,
            "轻微偏科_相对离散度": 100,
            "中度偏科_相对离散度": 200,
            "严重偏科_相对离散度": 300
        }
        self.rank_intervals = [
            {"id": 0, "start": 1, "end": 10, "weight": 1.0},
            {"id": 1, "start": 11, "end": 30, "weight": 0.8},
            {"id": 2, "start": 31, "end": 100, "weight": 0.5},
            {"id": 3, "start": 101, "end": 300, "weight": 0.3}
        ]
        self.group_rank_bonuses = [
            {"id": 0, "threshold": 10, "bonus": 30},
            {"id": 1, "threshold": 30, "bonus": 20},
            {"id": 2, "threshold": 50, "bonus": 15},
            {"id": 3, "threshold": 100, "bonus": 10}
        ]

# 设置模拟的 session_state
import streamlit as st
if not hasattr(st, 'session_state'):
    st.session_state = MockSessionState()
else:
    for key, value in MockSessionState().__dict__.items():
        if key not in st.session_state:
            setattr(st.session_state, key, value)

print("=" * 100)
print("学生成绩进步评分系统 - 全面测试")
print("=" * 100)

# 读取测试数据
with open('测试成绩总表_4次考试.xlsx', 'rb') as f:
    st.session_state.history_file_content = f.read()

# 处理数据
print("\n📊 正在处理数据...")
df_all, df_score, df_final, df_bias, has_subjects, rank_cols, score_cols, subjects, bias_dict, exam_labels = process_data()
print(f"✅ 数据处理完成: {len(df_final)} 名学生")

# 测试用例定义
test_cases = [
    {
        "name": "林子桓",
        "description": "考试2数学缺考",
        "expected": {
            "ranks": [27, 0, 9, 4],
            "连续进步次数": 2,
            "缺考处理": "考试2应标记为缺考，跳过该次考试的比较"
        }
    },
    {
        "name": "张泽轩",
        "description": "考试2英语缺考",
        "expected": {
            "ranks_has_zero": True,
            "缺考处理": "考试2应标记为缺考"
        }
    },
    {
        "name": "庄曼丽",
        "description": "考试3化学缺考",
        "expected": {
            "ranks_has_zero": True,
            "缺考处理": "考试3应标记为缺考"
        }
    }
]

# 测试 1: 缺考学生
print("\n" + "=" * 100)
print("测试 1: 缺考处理")
print("=" * 100)

for test in test_cases:
    name = test["name"]
    student = df_final[df_final["姓名"] == name].iloc[0]
    
    print(f"\n🔍 {name} - {test['description']}")
    print("-" * 100)
    
    # 提取ranks
    ranks = []
    for col in rank_cols:
        val = student[col]
        
        # 提取考试标识
        exam_label = None
        if "_年级排名_" in col:
            exam_label = col.split("_年级排名_")[-1]
        elif col.startswith("年级排名_"):
            exam_label = col.replace("年级排名_", "")
        
        # 检查缺考
        is_absent = False
        if subjects and exam_label:
            for subj in subjects:
                subj_col = f"{subj}_{exam_label}"
                if subj_col in student.index:
                    score_val = student[subj_col]
                    if pd.isna(score_val) or score_val == 0:
                        is_absent = True
                        break
        
        if is_absent or pd.isna(val) or val == 0:
            ranks.append(0)
        else:
            ranks.append(int(val))
    
    print(f"  排名序列: {ranks}")
    print(f"  连续进步次数: {student['连续进步次数']}")
    print(f"  区间进步得分: {student['区间进步得分']:.1f}")
    print(f"  连续进步加分: {student['连续进步加分']:.1f}")
    
    # 验证
    if "ranks" in test["expected"]:
        if ranks == test["expected"]["ranks"]:
            print(f"  ✅ 排名序列正确")
        else:
            print(f"  ❌ 排名序列错误！期望: {test['expected']['ranks']}, 实际: {ranks}")
    
    if "连续进步次数" in test["expected"]:
        if student['连续进步次数'] == test["expected"]["连续进步次数"]:
            print(f"  ✅ 连续进步次数正确")
        else:
            print(f"  ❌ 连续进步次数错误！期望: {test['expected']['连续进步次数']}, 实际: {student['连续进步次数']}")
    
    if "ranks_has_zero" in test["expected"]:
        if 0 in ranks:
            print(f"  ✅ 缺考已标记（排名包含0）")
        else:
            print(f"  ❌ 缺考未标记！排名序列: {ranks}")

# 测试 2: 进步/退步情况
print("\n" + "=" * 100)
print("测试 2: 进步/退步/稳定情况")
print("=" * 100)

# 找出不同情况的学生
continuous_progress = []  # 连续进步
has_regression = []  # 有退步
stable = []  # 排名稳定

for idx, student in df_final.iterrows():
    name = student['姓名']
    if pd.isna(name):
        continue
    
    # 提取有效排名
    ranks = []
    for col in rank_cols:
        val = student[col]
        if pd.notna(val) and val > 0:
            ranks.append(int(val))
    
    if len(ranks) >= 2:
        # 检查是否连续进步
        is_continuous = all(ranks[i] < ranks[i-1] for i in range(1, len(ranks)))
        if is_continuous:
            continuous_progress.append((name, ranks, student['连续进步次数']))
        
        # 检查是否有退步
        has_regress = any(ranks[i] > ranks[i-1] for i in range(1, len(ranks)))
        if has_regress:
            has_regression.append((name, ranks, student['连续进步次数']))

print(f"\n📈 连续进步的学生（前5名）:")
for i, (name, ranks, chain) in enumerate(continuous_progress[:5], 1):
    print(f"  {i}. {name}: {ranks} → 连续进步{chain}次")

print(f"\n📉 有退步的学生（前5名）:")
for i, (name, ranks, chain) in enumerate(has_regression[:5], 1):
    print(f"  {i}. {name}: {ranks} → 连续进步{chain}次")

# 测试 3: 各项加分
print("\n" + "=" * 100)
print("测试 3: 各项加分/扣分")
print("=" * 100)

# 选择排名最好的学生
top_student = df_final.iloc[0]
print(f"\n🏆 总得分第一名: {top_student['姓名']}")
print(f"  总得分: {top_student['总得分']:.1f}")
print(f"  区间进步得分: {top_student['区间进步得分']:.1f}")
print(f"  连续进步加分: {top_student['连续进步加分']:.1f}")
print(f"  年级排名加分: {top_student['年级排名加分']:.1f}")
print(f"  集团排名加分: {top_student['集团排名加分']:.1f}")
print(f"  总分奖励: {top_student['总分奖励']:.1f}")
if '偏科扣分' in top_student.index:
    print(f"  偏科扣分: {top_student['偏科扣分']:.1f}")

# 测试 4: 偏科检测
if df_bias is not None and len(df_bias) > 0:
    print("\n" + "=" * 100)
    print("测试 4: 偏科检测")
    print("=" * 100)
    
    print(f"\n🔍 偏科学生统计:")
    bias_stats = df_bias['偏科等级'].value_counts()
    for level, count in bias_stats.items():
        print(f"  {level}: {count}人")
    
    # 显示偏科最严重的学生
    severe_bias = df_bias[df_bias['偏科等级'] == '严重偏科']
    if len(severe_bias) > 0:
        print(f"\n⚠️  严重偏科学生（前3名）:")
        for idx, student in severe_bias.head(3).iterrows():
            print(f"  - {student['姓名']}: 最强{student['最强科目']}, 最弱{student['最弱科目']}, "
                  f"标准差={student['排名标准差']:.1f}, 扣分={student['扣分']:.1f}")

# 测试 5: 数据一致性
print("\n" + "=" * 100)
print("测试 5: 数据一致性检查")
print("=" * 100)

issues = []

# 检查总得分计算
for idx, student in df_final.iterrows():
    name = student['姓名']
    if pd.isna(name):
        continue
    
    # 计算总得分
    calculated_total = (
        student['区间进步得分'] + 
        student['连续进步加分'] + 
        student['年级排名加分'] + 
        student['集团排名加分'] + 
        student['总分奖励']
    )
    
    if '偏科扣分' in student.index:
        calculated_total -= student['偏科扣分']
    
    # 允许0.1的误差
    if abs(calculated_total - student['总得分']) > 0.1:
        issues.append(f"{name}: 总分不一致 (计算={calculated_total:.1f}, 记录={student['总得分']:.1f})")

if issues:
    print("❌ 发现以下数据一致性问题:")
    for issue in issues[:10]:  # 只显示前10个
        print(f"  - {issue}")
else:
    print("✅ 所有学生的总得分计算一致")

# 总结
print("\n" + "=" * 100)
print("测试总结")
print("=" * 100)
print(f"✅ 测试完成")
print(f"  - 学生总数: {len(df_final)}")
print(f"  - 缺考学生: 3人（林子桓、张泽轩、庄曼丽）")
print(f"  - 连续进步: {len(continuous_progress)}人")
print(f"  - 有退步: {len(has_regression)}人")
if df_bias is not None:
    print(f"  - 偏科学生: {len(df_bias)}人")
print(f"  - 数据一致性问题: {len(issues)}个")
