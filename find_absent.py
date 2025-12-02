import pandas as pd

# 读取测试数据
df = pd.read_excel('测试成绩总表_4次考试.xlsx')

# 定义科目
subjects = ["语文", "数学", "英语", "物理", "化学", "生物"]

print("=" * 80)
print("有缺考情况的学生：")
print("=" * 80)

absent_info = []

for idx, row in df.iterrows():
    name = row['姓名']
    if pd.isna(name) or not isinstance(name, str):
        continue
    
    # 检查每次考试
    for exam_num in range(1, 5):
        exam_label = f"考试{exam_num}"
        absent_subjects = []
        
        for subj in subjects:
            col = f"{subj}_{exam_label}"
            if col in df.columns:
                score = row[col]
                if pd.isna(score) or score == 0:
                    absent_subjects.append(subj)
        
        if absent_subjects:
            rank_col = f"总分_年级排名_{exam_label}"
            rank = row[rank_col] if rank_col in df.columns else "N/A"
            print(f"{name} - {exam_label}: 缺考科目={', '.join(absent_subjects)}, 总分排名={int(rank) if pd.notna(rank) else 'N/A'}")
            absent_info.append(name)

# 去重统计
unique_students = list(set(absent_info))
print(f"\n总计 {len(unique_students)} 名学生有缺考情况：")
print(', '.join(sorted(unique_students)))
