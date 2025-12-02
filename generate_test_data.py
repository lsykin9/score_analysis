"""
生成测试用的成绩总表
包含4次考试数据，涵盖各种测试场景：
1. 缺考后进步的学生
2. 缺考后退步的学生
3. 偏科的学生
4. 不偏科的学生
5. 排名波动的学生
"""

import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

# 读取原始数据
df_source = pd.read_excel('学生成绩_转换后.xlsx')
print(f"读取到 {len(df_source)} 个学生的数据")

# 获取学生姓名（保持原始顺序）
students = df_source['姓名'].tolist()
print(f"前6个学生: {students[:6]}")

# 科目列表
subjects = ['语文', '数学', '英语', '物理', '化学', '生物']

# 生成4次考试的数据
def generate_exam_data(exam_num, students):
    """生成一次考试的数据"""
    n_students = len(students)
    data = {'姓名': students}
    
    # 为每个学生生成成绩
    scores = []
    for i, student in enumerate(students):
        student_scores = {}
        
        # 根据学生编号决定特殊情况
        student_idx = i
        
        # === 第一次考试：基准考试 ===
        if exam_num == 1:
            # 正常分数分布
            base_scores = {
                '语文': np.random.randint(95, 125),
                '数学': np.random.randint(90, 130),
                '英语': np.random.randint(95, 125),
                '物理': np.random.randint(70, 95),
                '化学': np.random.randint(70, 95),
                '生物': np.random.randint(65, 90)
            }
            student_scores = base_scores
            
        # === 第二次考试：引入缺考和偏科 ===
        elif exam_num == 2:
            if student_idx == 0:  # 学生1：数学缺考（下次会进步）
                student_scores = {
                    '语文': np.random.randint(100, 120),
                    '数学': 0,  # 缺考
                    '英语': np.random.randint(100, 120),
                    '物理': np.random.randint(75, 90),
                    '化学': np.random.randint(75, 90),
                    '生物': np.random.randint(70, 85)
                }
            elif student_idx == 1:  # 学生2：英语缺考（下次会退步）
                student_scores = {
                    '语文': np.random.randint(110, 125),
                    '数学': np.random.randint(110, 125),
                    '英语': 0,  # 缺考
                    '物理': np.random.randint(80, 92),
                    '化学': np.random.randint(80, 92),
                    '生物': np.random.randint(75, 88)
                }
            elif student_idx == 2:  # 学生3：偏科（数学特别好，语文较弱）
                student_scores = {
                    '语文': np.random.randint(85, 100),
                    '数学': np.random.randint(125, 135),
                    '英语': np.random.randint(105, 118),
                    '物理': np.random.randint(88, 95),
                    '化学': np.random.randint(88, 95),
                    '生物': np.random.randint(82, 90)
                }
            elif student_idx == 3:  # 学生4：不偏科（各科均衡）
                avg = np.random.randint(105, 115)
                student_scores = {
                    '语文': avg + np.random.randint(-5, 5),
                    '数学': avg + np.random.randint(-5, 5),
                    '英语': avg + np.random.randint(-5, 5),
                    '物理': int((avg + np.random.randint(-5, 5)) * 0.75),
                    '化学': int((avg + np.random.randint(-5, 5)) * 0.75),
                    '生物': int((avg + np.random.randint(-5, 5)) * 0.72)
                }
            else:
                # 其他学生正常分数
                student_scores = {
                    '语文': np.random.randint(95, 125),
                    '数学': np.random.randint(90, 130),
                    '英语': np.random.randint(95, 125),
                    '物理': np.random.randint(70, 95),
                    '化学': np.random.randint(70, 95),
                    '生物': np.random.randint(65, 90)
                }
                
        # === 第三次考试：缺考后的表现 ===
        elif exam_num == 3:
            if student_idx == 0:  # 学生1：数学进步（从缺考到高分）
                student_scores = {
                    '语文': np.random.randint(100, 120),
                    '数学': np.random.randint(125, 135),  # 进步
                    '英语': np.random.randint(100, 120),
                    '物理': np.random.randint(78, 92),
                    '化学': np.random.randint(78, 92),
                    '生物': np.random.randint(72, 87)
                }
            elif student_idx == 1:  # 学生2：英语退步（从缺考到低分）
                student_scores = {
                    '语文': np.random.randint(110, 125),
                    '数学': np.random.randint(110, 125),
                    '英语': np.random.randint(80, 95),  # 退步
                    '物理': np.random.randint(80, 92),
                    '化学': np.random.randint(80, 92),
                    '生物': np.random.randint(75, 88)
                }
            elif student_idx == 2:  # 学生3：继续偏科
                student_scores = {
                    '语文': np.random.randint(82, 98),
                    '数学': np.random.randint(128, 138),
                    '英语': np.random.randint(103, 120),
                    '物理': np.random.randint(86, 95),
                    '化学': np.random.randint(86, 95),
                    '生物': np.random.randint(80, 90)
                }
            elif student_idx == 3:  # 学生4：继续均衡
                avg = np.random.randint(108, 118)
                student_scores = {
                    '语文': avg + np.random.randint(-5, 5),
                    '数学': avg + np.random.randint(-5, 5),
                    '英语': avg + np.random.randint(-5, 5),
                    '物理': int((avg + np.random.randint(-5, 5)) * 0.75),
                    '化学': int((avg + np.random.randint(-5, 5)) * 0.75),
                    '生物': int((avg + np.random.randint(-5, 5)) * 0.72)
                }
            elif student_idx == 4:  # 学生5：缺考化学
                student_scores = {
                    '语文': np.random.randint(105, 120),
                    '数学': np.random.randint(100, 120),
                    '英语': np.random.randint(105, 120),
                    '物理': np.random.randint(75, 90),
                    '化学': 0,  # 缺考
                    '生物': np.random.randint(70, 85)
                }
            else:
                # 其他学生正常分数
                student_scores = {
                    '语文': np.random.randint(95, 125),
                    '数学': np.random.randint(90, 130),
                    '英语': np.random.randint(95, 125),
                    '物理': np.random.randint(70, 95),
                    '化学': np.random.randint(70, 95),
                    '生物': np.random.randint(65, 90)
                }
                
        # === 第四次考试：最终测试 ===
        elif exam_num == 4:
            if student_idx == 0:  # 学生1：继续保持进步
                student_scores = {
                    '语文': np.random.randint(105, 122),
                    '数学': np.random.randint(128, 138),
                    '英语': np.random.randint(105, 122),
                    '物理': np.random.randint(80, 94),
                    '化学': np.random.randint(80, 94),
                    '生物': np.random.randint(74, 89)
                }
            elif student_idx == 1:  # 学生2：英语继续低迷
                student_scores = {
                    '语文': np.random.randint(112, 127),
                    '数学': np.random.randint(112, 127),
                    '英语': np.random.randint(75, 92),
                    '物理': np.random.randint(82, 94),
                    '化学': np.random.randint(82, 94),
                    '生物': np.random.randint(77, 90)
                }
            elif student_idx == 2:  # 学生3：偏科更明显
                student_scores = {
                    '语文': np.random.randint(80, 95),
                    '数学': np.random.randint(130, 140),
                    '英语': np.random.randint(100, 118),
                    '物理': np.random.randint(84, 95),
                    '化学': np.random.randint(84, 95),
                    '生物': np.random.randint(78, 90)
                }
            elif student_idx == 3:  # 学生4：继续均衡
                avg = np.random.randint(110, 120)
                student_scores = {
                    '语文': avg + np.random.randint(-5, 5),
                    '数学': avg + np.random.randint(-5, 5),
                    '英语': avg + np.random.randint(-5, 5),
                    '物理': int((avg + np.random.randint(-5, 5)) * 0.75),
                    '化学': int((avg + np.random.randint(-5, 5)) * 0.75),
                    '生物': int((avg + np.random.randint(-5, 5)) * 0.72)
                }
            elif student_idx == 4:  # 学生5：化学进步
                student_scores = {
                    '语文': np.random.randint(108, 122),
                    '数学': np.random.randint(103, 122),
                    '英语': np.random.randint(108, 122),
                    '物理': np.random.randint(78, 92),
                    '化学': np.random.randint(85, 95),  # 从缺考恢复并进步
                    '生物': np.random.randint(73, 87)
                }
            elif student_idx == 5:  # 学生6：新偏科（物理特别差）
                student_scores = {
                    '语文': np.random.randint(110, 125),
                    '数学': np.random.randint(110, 125),
                    '英语': np.random.randint(110, 125),
                    '物理': np.random.randint(55, 70),  # 明显弱项
                    '化学': np.random.randint(85, 95),
                    '生物': np.random.randint(80, 90)
                }
            else:
                # 其他学生正常分数
                student_scores = {
                    '语文': np.random.randint(95, 125),
                    '数学': np.random.randint(90, 130),
                    '英语': np.random.randint(95, 125),
                    '物理': np.random.randint(70, 95),
                    '化学': np.random.randint(70, 95),
                    '生物': np.random.randint(65, 90)
                }
        
        scores.append(student_scores)
    
    # 计算总分
    total_scores = []
    for student_score in scores:
        total = sum(student_score.values())
        total_scores.append(total)
    
    # 计算年级排名（总分）
    total_ranks = pd.Series(total_scores).rank(method='min', ascending=False).astype(int).tolist()
    
    # 计算集团排名（模拟，基于年级排名加随机偏移）
    group_ranks = [min(1500, max(1, rank + np.random.randint(-50, 100))) for rank in total_ranks]
    
    # 添加总分列
    data['总分'] = total_scores
    data[f'总分_年级排名_考试{exam_num}'] = total_ranks
    data[f'总分_集团排名_考试{exam_num}'] = group_ranks
    
    # 添加各科成绩和排名
    for subject in subjects:
        subject_scores = [s[subject] for s in scores]
        data[f'{subject}_考试{exam_num}'] = subject_scores
        
        # 计算年级排名（只对非0分数排名）
        subject_series = pd.Series(subject_scores)
        valid_mask = subject_series > 0
        ranks = pd.Series([0] * len(subject_scores))
        if valid_mask.any():
            ranks[valid_mask] = subject_series[valid_mask].rank(method='min', ascending=False).astype(int)
        data[f'{subject}_年级排名_考试{exam_num}'] = ranks.tolist()
        
        # 集团排名
        group_subject_ranks = [min(1500, max(1, r + np.random.randint(-50, 100))) if r > 0 else 0 for r in ranks]
        data[f'{subject}_集团排名_考试{exam_num}'] = group_subject_ranks
    
    return pd.DataFrame(data)

# 生成4次考试数据
print("正在生成4次考试数据...")

# 初始化最终DataFrame
df_final = pd.DataFrame({'姓名': students})

# 为每次考试生成数据并直接添加列
for exam_num in range(1, 5):
    print(f"生成第{exam_num}次考试数据...")
    
    # 生成这次考试的所有学生成绩
    scores = []
    for i, student in enumerate(students):
        student_scores = {}
        student_idx = i
        
        # === 第一次考试：基准考试 ===
        if exam_num == 1:
            # 正常分数分布
            base_scores = {
                '语文': np.random.randint(95, 125),
                '数学': np.random.randint(90, 130),
                '英语': np.random.randint(95, 125),
                '物理': np.random.randint(70, 95),
                '化学': np.random.randint(70, 95),
                '生物': np.random.randint(65, 90)
            }
            student_scores = base_scores

# 重新排列列顺序：姓名 + 每次考试的(总分排名 + 各科成绩和排名)
columns_order = ['姓名']
for exam_num in range(1, 5):
    columns_order.append(f'总分_年级排名_考试{exam_num}')
    columns_order.append(f'总分_集团排名_考试{exam_num}')
    for subject in subjects:
        columns_order.append(f'{subject}_考试{exam_num}')
        columns_order.append(f'{subject}_年级排名_考试{exam_num}')
        columns_order.append(f'{subject}_集团排名_考试{exam_num}')

df_final = df_final[columns_order]

# 保存到Excel并设置格式
print("保存到Excel文件...")
wb = Workbook()
ws = wb.active
ws.title = "成绩总表"

# 写入数据
for r_idx, row in enumerate(dataframe_to_rows(df_final, index=False, header=True), 1):
    ws.append(row)

# 设置表头样式
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
header_font = Font(bold=True, color="FFFFFF", size=11)
header_alignment = Alignment(horizontal='center', vertical='center')

for cell in ws[1]:
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = header_alignment

# 设置边框
thin_border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
    for cell in row:
        cell.border = thin_border
        if cell.row > 1:  # 非表头居中
            cell.alignment = Alignment(horizontal='center', vertical='center')

# 设置列宽
ws.column_dimensions['A'].width = 12  # 姓名
for col_idx in range(2, ws.max_column + 1):
    ws.column_dimensions[ws.cell(1, col_idx).column_letter].width = 15

# 冻结首行和首列
ws.freeze_panes = 'B2'

# 保存文件
output_file = '测试成绩总表_4次考试.xlsx'
wb.save(output_file)

print(f"\n✅ 测试数据生成完成！")
print(f"文件保存为: {output_file}")
print(f"总学生数: {len(students)}")
print(f"考试次数: 4")
print(f"总列数: {len(df_final.columns)}")
print(f"\n测试场景包括:")
print(f"  - 学生1: 第2次考试数学缺考 → 第3、4次进步")
print(f"  - 学生2: 第2次考试英语缺考 → 第3、4次退步")
print(f"  - 学生3: 明显偏科（数学强，语文弱）")
print(f"  - 学生4: 各科均衡，不偏科")
print(f"  - 学生5: 第3次化学缺考 → 第4次进步")
print(f"  - 学生6: 第4次物理明显偏弱")
print(f"  - 其他学生: 正常分数分布")
