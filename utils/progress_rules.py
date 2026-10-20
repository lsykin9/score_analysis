"""年级/集团方案共用的进步判定与连续次数。"""
import math


TIE_ENABLED = "持平计入连续进步"
TIE_RANK_LIMIT = "持平计入排名上限"
LEGACY_TIE_RANK_LIMIT = "持平计入年级排名上限"
RANK_BASIS = "进步排名依据"
DEFAULT_TIE_RANK_LIMIT = 100


def get_rank_basis(config):
    return "group" if config.get(RANK_BASIS) == "group" else "grade"


def rank_basis_label(config):
    return "集团" if get_rank_basis(config) == "group" else "年级"


def get_tie_progress_rule(config):
    """兼容旧字段；缺省时年级前 100 名、集团前 200 名持平计入。"""
    enabled = config.get(TIE_ENABLED, True)
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() in {"true", "1", "是", "开启"}
    default = 200 if get_rank_basis(config) == "group" else DEFAULT_TIE_RANK_LIMIT
    try:
        limit = max(1, int(config.get(TIE_RANK_LIMIT, config.get(LEGACY_TIE_RANK_LIMIT, default))))
    except (TypeError, ValueError, OverflowError):
        limit = default
    return bool(enabled), limit


def normalize_rank(value):
    """将缺失、非数值或非正排名转为缺考标记 0。"""
    try:
        value = float(value)
        return int(value) if math.isfinite(value) and value >= 1 else 0
    except (TypeError, ValueError, OverflowError):
        return 0


def is_progress_step(before, now, config):
    before, now = normalize_rank(before), normalize_rank(now)
    if before == 0 or now == 0:
        return False
    enabled, limit = get_tie_progress_rule(config)
    return now < before or (enabled and now == before and now <= limit)


def is_current_progress(ranks, config):
    """本次是否计为进步；最新缺考不参与人数统计。"""
    if not ranks or normalize_rank(ranks[-1]) == 0:
        return False
    previous = next((normalize_rank(rank) for rank in reversed(ranks[:-1])
                     if normalize_rank(rank)), 0)
    return is_progress_step(previous, ranks[-1], config)


def calculate_progress_chain(ranks, config, *, skip_absent=True):
    """返回当前连续次数和逐次判定；网页跳过缺考，旧命令行可保留中断行为。"""
    enabled, limit = get_tie_progress_rule(config)
    label = rank_basis_label(config)
    chain_length = 0
    previous = 0
    details = []
    for value in ranks:
        current = normalize_rank(value)
        if current == 0:
            if not skip_absent:
                chain_length = 0
                previous = 0
            continue
        if previous:
            counted = is_progress_step(previous, current, config)
            if current < previous:
                reason = "排名提升"
            elif current > previous:
                reason = "退步，连续次数归零"
            elif not enabled:
                reason = "持平规则关闭，连续次数归零"
            elif current <= limit:
                reason = f"{label}前 {limit} 名内持平，计入一次进步"
            else:
                reason = f"{label}前 {limit} 名外持平，连续次数归零"
            chain_length = chain_length + 1 if counted else 0
            details.append({
                f"上次{label}排名": previous,
                f"本次{label}排名": current,
                "判定": reason,
                "连续进步次数": chain_length,
            })
        previous = current
    return chain_length, details


def describe_progress_rule(config):
    enabled, limit = get_tie_progress_rule(config)
    label = rank_basis_label(config)
    if enabled:
        return (f"{label}排名提升，或{label}前 {limit} 名（含第 {limit} 名）持平，"
                "均计入一次连续进步；范围外持平或退步归零。持平的区间进步分为 0。")
    return f"仅{label}排名严格提升计入连续进步；持平或退步归零。"
