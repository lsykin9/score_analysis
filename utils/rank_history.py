"""评分和学生详情共用的总分年级排名、考试标签及缺考识别。"""
import math
import pandas as pd

from utils.progress_rules import normalize_rank, get_rank_basis


GRADE_RANK_PREFIXES = ("总分_年级排名_", "总分年级排名_", "年级排名_", "排名_")
GROUP_RANK_PREFIXES = ("总分_集团排名_", "总分集团排名_", "集团排名_")


def correct_tied_score_ranks(dataframe):
    """按每次考试的总分，将同分学生的总分年级排名统一为最优已有名次。

    保留集团排名、单科排名和其他学生的名次，不根据上传名单重新排名。
    缺少总分或有效年级排名的记录不参与校正。
    """
    corrected_count = 0
    for rank_column in get_grade_rank_columns(dataframe.columns):
        score_column = "总分" if rank_column == "年级排名" else f"总分_{get_exam_label(rank_column)}"
        if score_column not in dataframe.columns:
            continue

        scores = pd.to_numeric(dataframe[score_column], errors="coerce")
        ranks = pd.to_numeric(dataframe[rank_column], errors="coerce")
        valid = (scores > 0) & (scores < float('inf')) & (ranks >= 1) & (ranks < float('inf'))
        if not valid.any():
            continue

        tied = pd.DataFrame({"score": scores[valid], "rank": ranks[valid]})
        corrected = tied.groupby("score", sort=False)["rank"].transform("min")
        changed = corrected != ranks[valid]
        corrected_count += int(changed.sum())
        dataframe.loc[corrected.index[changed], rank_column] = corrected[changed].to_numpy()

    return corrected_count


def get_grade_rank_columns(columns):
    return [col for col in columns if col == "年级排名" or
            (isinstance(col, str) and col.startswith(GRADE_RANK_PREFIXES))]


def get_group_rank_columns(columns):
    return [col for col in columns if isinstance(col, str) and col.startswith(GROUP_RANK_PREFIXES)]


def get_progress_rank_columns(columns, config):
    if get_rank_basis(config) == "grade":
        return get_grade_rank_columns(columns)
    grade = get_grade_rank_columns(columns)
    group = get_group_rank_columns(columns)
    labels = list(dict.fromkeys(get_exam_label(col) for col in columns if col in grade or col in group))
    group_by_label = {get_exam_label(col): col for col in group}
    # 缺少集团排名的旧考试保留为无效位置，连续计算只比较有效集团排名。
    return [group_by_label.get(label, f"集团排名_{label}") for label in labels]


def get_exam_label(column):
    for prefix in GRADE_RANK_PREFIXES + GROUP_RANK_PREFIXES:
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


def latest_rank_change(ranks):
    if not ranks or not ranks[-1]:
        return None
    previous = next((rank for rank in reversed(ranks[:-1]) if rank), 0)
    return previous - ranks[-1] if previous else None


def compare_rank_changes(grade_change, group_change):
    if grade_change is None or group_change is None:
        return "排名对照数据不足"
    if grade_change > 0 and group_change < 0:
        return "校内位置提升，集团位置下降"
    if grade_change < 0 and group_change > 0:
        return "集团位置提升，校内位置下降"
    def describe(change):
        return "提升" if change > 0 else "下降" if change < 0 else "持平"
    return f"年级{describe(grade_change)}，集团{describe(group_change)}"
