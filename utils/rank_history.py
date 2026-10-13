"""评分和学生详情共用的总分年级排名、考试标签及缺考识别。"""
import math

from utils.progress_rules import normalize_rank


GRADE_RANK_PREFIXES = ("总分_年级排名_", "总分年级排名_", "年级排名_", "排名_")


def get_grade_rank_columns(columns):
    return [col for col in columns if col == "年级排名" or
            (isinstance(col, str) and col.startswith(GRADE_RANK_PREFIXES))]


def get_exam_label(column):
    for prefix in GRADE_RANK_PREFIXES:
        if column.startswith(prefix):
            return column[len(prefix):]
    return column


def get_rank_history(row, rank_columns, subjects):
    """返回有效年级排名序列；任一已有科目缺考则该次排名无效。"""
    ranks = []
    for column in rank_columns:
        label = get_exam_label(column)
        rank = normalize_rank(row.get(column, 0))
        for subject in subjects:
            score_column = f"{subject}_{label}"
            if score_column not in row:
                continue
            try:
                score = float(row[score_column])
                absent = not math.isfinite(score) or score == 0
            except (TypeError, ValueError, OverflowError):
                absent = True
            if absent:
                rank = 0
                break
        ranks.append(rank)
    return ranks
