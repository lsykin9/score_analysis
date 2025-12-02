import pandas as pd

# 读取测试数据
df_all = pd.read_excel('测试成绩总表_4次考试.xlsx')

# 定义科目
subjects = ["语文", "数学", "英语", "物理", "化学", "生物"]

# 年级排名列（只保留总分排名，不包括单科排名）
rank_cols = []
for col in df_all.columns:
    # 只处理总分的年级排名列
    if col.startswith("总分_年级排名_") or col == "年级排名" or col.startswith("年级排名_"):
        # 排除科目排名列
        is_subject_rank = any(col.startswith(f"{subj}_年级排名_") for subj in subjects)
        if not is_subject_rank:
            rank_cols.append(col)

print(f"rank_cols: {rank_cols}")
print(f"\n科目相关列:")
for col in df_all.columns:
    if "考试2" in col and any(subj in col for subj in subjects):
        print(f"  {col}")

# 找林子桓
student = df_all[df_all['姓名'] == '林子桓'].iloc[0]

print(f"\n林子桓 考试2 相关数据:")
for col in df_all.columns:
    if "考试2" in col:
        print(f"  {col}: {student[col]}")

# 模拟缺考检测逻辑
print("\n\n=== 模拟缺考检测 ===")
ranks = []
has_subjects = True

for col in rank_cols:
    val = student[col]
    
    # 从列名提取考试标识
    exam_label = None
    if "_年级排名_" in col:
        exam_label = col.split("_年级排名_")[-1]
    elif col.startswith("年级排名_"):
        exam_label = col.replace("年级排名_", "")
    
    print(f"\n处理列: {col}")
    print(f"  exam_label: {exam_label}")
    print(f"  原始排名: {val}")
    
    # 检查该次考试是否有科目缺考
    is_exam_absent = False
    if has_subjects and exam_label:
        for subj in subjects:
            subj_col = f"{subj}_{exam_label}"
            if subj_col in df_all.columns:
                score_val = student[subj_col]
                print(f"  检查 {subj_col}: {score_val}")
                if pd.isna(score_val) or score_val == 0:
                    is_exam_absent = True
                    print(f"    -> 发现缺考！")
                    break
    
    # 如果该次考试有科目缺考，排名设为0
    if is_exam_absent:
        print(f"  最终排名: 0 (缺考)")
        ranks.append(0)
    else:
        print(f"  最终排名: {int(val)}")
        ranks.append(int(val))

print(f"\n最终ranks: {ranks}")
