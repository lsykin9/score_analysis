"""两套进步评分参数的初始化、快照和切换，不依赖界面控件。"""
from copy import deepcopy

from utils.progress_rules import (
    RANK_BASIS, TIE_ENABLED, TIE_RANK_LIMIT,
)

SCHEME_LABELS = {"grade": "年级排名方案", "group": "集团排名方案"}
GRADE_REWARD_ENABLED = "启用年级排名奖励"
GROUP_REWARD_ENABLED = "启用集团排名奖励"
PROFILE_LISTS = ("rank_intervals", "rank_bonuses", "group_rank_bonuses", "chain_bonuses")
PROFILE_PARAMS = (TIE_ENABLED, TIE_RANK_LIMIT, "A线（排名）", "A线过线奖励",
                  "B线（排名）", "B线过线奖励", GRADE_REWARD_ENABLED, GROUP_REWARD_ENABLED)
WIDGET_PREFIXES = ("start_", "end_", "weight_", "bonus_thresh_", "bonus_val_",
                   "group_bonus_thresh_", "group_bonus_val_", "chain_times_", "chain_val_")
WIDGET_KEYS = ("line_a_rank", "line_a_bonus", "line_b_rank", "line_b_bonus",
               "tie_progress_enabled", "tie_progress_grade_rank_limit",
               "grade_rank_reward_enabled", "group_rank_reward_enabled")

GRADE_INTERVALS = (
    (0, 20, 4), (21, 50, 2.5), (51, 100, 1.4), (101, 150, 1.2),
    (151, 200, 1), (201, 300, .8), (301, 430, .6), (431, 99999, .5),
)

# 旧的集团方案仅用于识别并迁移从前一版本保存的默认配置。
LEGACY_GROUP_INTERVALS = (
    (0, 200, 4), (201, 500, 1.4), (501, 1000, .6), (1001, 99999, .3),
)

# 前段名次竞争更密集，保留较高的每名权重；从第 51 名起平滑递减，
# 同时避免 200、500、1000 名处出现突变。1000 名后仍保留正向反馈。
GROUP_INTERVALS = (
    (1, 50, 4.0), (51, 100, 3.2), (101, 200, 2.4),
    (201, 300, 1.7), (301, 400, 1.4), (401, 500, 1.2),
    (501, 600, 1.0), (601, 700, .9), (701, 800, .8),
    (801, 900, .7), (901, 1000, .6), (1001, 99999, .5),
)

GRADE_LINE_PARAMS = {
    "A线（排名）": 80,
    "A线过线奖励": 100,
    "B线（排名）": 430,
    "B线过线奖励": 20,
}
GROUP_LINE_PARAMS = {
    "A线（排名）": 565,
    "A线过线奖励": 100,
    "B线（排名）": 1180,
    "B线过线奖励": 20,
}
LEGACY_LINE_PARAMS = {
    "A线（排名）": 80,
    "A线过线奖励": 100,
    "B线（排名）": 430,
    "B线过线奖励": 0,
}

RANK_BONUSES = (
    (5, 200), (10, 160), (20, 120), (30, 90),
    (50, 60), (80, 40), (100, 20),
)
GROUP_RANK_BONUSES = (
    (20, 220), (50, 180), (100, 140), (200, 90),
    (300, 60), (500, 35), (565, 25),
)
CHAIN_BONUSES = ((1, 25), (2, 60), (3, 110), (4, 170), (5, 240))
SCORE_BONUSES = (
    (590, 20), (600, 40), (610, 60), (620, 80), (630, 100),
    (640, 120), (650, 140), (660, 160), (670, 180),
)
LEGACY_RANK_BONUSES = ((5, 100), (10, 70), (20, 50), (30, 35), (50, 20), (100, 10))
LEGACY_GROUP_RANK_BONUSES = ((20, 200), (50, 150), (100, 100), (150, 75), (200, 50))
LEGACY_CHAIN_BONUSES = ((1, 20), (2, 50), (3, 90), (4, 140), (5, 200))


def _interval_records(intervals):
    return [{"id": i, "start": start, "end": end, "weight": float(weight)}
            for i, (start, end, weight) in enumerate(intervals)]


def _matches_intervals(items, intervals):
    """只迁移完整保留旧默认值的方案，不覆盖用户自行调过的参数。"""
    if not isinstance(items, list) or len(items) != len(intervals):
        return False
    try:
        actual = [(int(item["start"]), int(item["end"]), float(item["weight"]))
                  for item in items]
    except (KeyError, TypeError, ValueError):
        return False
    expected = [(start, end, float(weight)) for start, end, weight in intervals]
    return actual == expected


def _migrate_group_intervals(profile):
    """将旧的四档默认集团权重升级为新的十二档平滑权重。"""
    if _matches_intervals(profile.get("rank_intervals"), LEGACY_GROUP_INTERVALS):
        profile["rank_intervals"] = _interval_records(GROUP_INTERVALS)
        return True
    return False


def _migrate_line_params(profile, defaults):
    """仅替换旧默认 A/B 线，不改变教师保存过的自定义设置。"""
    params = profile.setdefault("params", {})
    if all(params.get(key) == value for key, value in LEGACY_LINE_PARAMS.items()):
        params.update(defaults)
        return True
    return False


def _matches_bonus_items(items, intervals, threshold_key):
    if not isinstance(items, list) or len(items) != len(intervals):
        return False
    try:
        actual = [(int(item[threshold_key]), float(item["bonus"])) for item in items]
    except (KeyError, TypeError, ValueError):
        return False
    return actual == [(threshold, float(bonus)) for threshold, bonus in intervals]


def _migrate_reward_defaults(profile):
    """升级完整保留旧默认值的奖励档位，已编辑过的档位原样保留。"""
    changed = False
    if _matches_bonus_items(profile.get("rank_bonuses"), LEGACY_RANK_BONUSES, "threshold"):
        profile["rank_bonuses"] = [
            {"id": index, "threshold": threshold, "bonus": bonus}
            for index, (threshold, bonus) in enumerate(RANK_BONUSES)
        ]
        changed = True
    if _matches_bonus_items(profile.get("group_rank_bonuses"), LEGACY_GROUP_RANK_BONUSES, "threshold"):
        profile["group_rank_bonuses"] = [
            {"id": index, "threshold": threshold, "bonus": bonus}
            for index, (threshold, bonus) in enumerate(GROUP_RANK_BONUSES)
        ]
        changed = True
    if _matches_bonus_items(profile.get("chain_bonuses"), LEGACY_CHAIN_BONUSES, "times"):
        profile["chain_bonuses"] = [
            {"id": index, "times": times, "bonus": bonus}
            for index, (times, bonus) in enumerate(CHAIN_BONUSES)
        ]
        changed = True
    return changed


def default_profile(basis):
    intervals = GRADE_INTERVALS if basis == "grade" else GROUP_INTERVALS
    line_params = GRADE_LINE_PARAMS if basis == "grade" else GROUP_LINE_PARAMS
    return {
        "rank_intervals": _interval_records(intervals),
        "rank_bonuses": [{"id": i, "threshold": n, "bonus": b} for i, (n, b) in
                         enumerate(RANK_BONUSES)],
        "group_rank_bonuses": [{"id": i, "threshold": n, "bonus": b} for i, (n, b) in
                               enumerate(GROUP_RANK_BONUSES)],
        "chain_bonuses": [{"id": i, "times": n, "bonus": b} for i, (n, b) in
                         enumerate(CHAIN_BONUSES)],
        "params": {TIE_ENABLED: True, TIE_RANK_LIMIT: 100 if basis == "grade" else 200,
                   **line_params, GRADE_REWARD_ENABLED: basis == "grade",
                   GROUP_REWARD_ENABLED: True},
    }


def capture_active_profile(state):
    basis = state.get("scoring_scheme", "grade")
    params = state["config_params"]
    profile = {key: deepcopy(state[key]) for key in PROFILE_LISTS}
    profile["params"] = {key: deepcopy(params[key]) for key in PROFILE_PARAMS if key in params}
    state["scheme_profiles"][basis] = profile


def activate_scheme(state, basis, *, capture=True):
    if basis not in SCHEME_LABELS:
        raise ValueError("未知评分方案")
    if capture:
        capture_active_profile(state)
    profile = state["scheme_profiles"][basis]
    defaults = default_profile(basis)
    state["scoring_scheme"] = basis
    state["config_params"].update(defaults["params"])
    state["config_params"].update(profile.get("params", {}))
    state["config_params"][RANK_BASIS] = basis
    for key in PROFILE_LISTS:
        state[key] = deepcopy(profile.get(key, defaults[key]))
    for list_key, counter_key in [("rank_intervals", "next_interval_id"),
                                  ("rank_bonuses", "next_bonus_id"),
                                  ("group_rank_bonuses", "next_group_bonus_id"),
                                  ("chain_bonuses", "next_chain_bonus_id")]:
        state[counter_key] = max((item["id"] for item in state[list_key]), default=-1) + 1
    for key in list(state.keys()):
        if key in WIDGET_KEYS or key.startswith(WIDGET_PREFIXES):
            del state[key]


def initialize_scheme_state(state):
    if "scheme_profiles" not in state:
        requested = state.get("scoring_scheme", "grade")
        state["scheme_profiles"] = {basis: default_profile(basis) for basis in SCHEME_LABELS}
        # 旧配置/会话中已修改的参数归入年级方案，集团采用独立初始值。
        state["scoring_scheme"] = "grade"
        for key, value in default_profile("grade")["params"].items():
            state["config_params"].setdefault(key, value)
        capture_active_profile(state)
        activate_scheme(state, requested, capture=False)
    else:
        group_profile = state["scheme_profiles"].get("group", {})
        grade_profile = state["scheme_profiles"].get("grade", {})
        migrated = _migrate_group_intervals(group_profile)
        migrated = _migrate_line_params(grade_profile, GRADE_LINE_PARAMS) or migrated
        migrated = _migrate_line_params(group_profile, GROUP_LINE_PARAMS) or migrated
        for profile in state["scheme_profiles"].values():
            migrated = _migrate_reward_defaults(profile) or migrated
        # 已打开方案的活动参数和控件缓存，也应同步到迁移后的方案。
        if migrated:
            activate_scheme(state, state.get("scoring_scheme", "grade"), capture=False)
        state["config_params"][RANK_BASIS] = state.get("scoring_scheme", "grade")


def restore_scheme_profiles(state, saved):
    basis = saved.get("scoring_scheme", "grade")
    if basis not in SCHEME_LABELS:
        basis = "grade"
    state["scheme_profiles"] = {key: default_profile(key) for key in SCHEME_LABELS}
    stored_profiles = saved.get("scheme_profiles")
    if isinstance(stored_profiles, dict):
        for key in SCHEME_LABELS:
            if isinstance(stored_profiles.get(key), dict):
                state["scheme_profiles"][key].update(deepcopy(stored_profiles[key]))
    else:
        # 兼容此前仅存储一套参数的配置。
        state["scoring_scheme"] = "grade"
        capture_active_profile(state)
    _migrate_group_intervals(state["scheme_profiles"]["group"])
    _migrate_line_params(state["scheme_profiles"]["grade"], GRADE_LINE_PARAMS)
    _migrate_line_params(state["scheme_profiles"]["group"], GROUP_LINE_PARAMS)
    for profile in state["scheme_profiles"].values():
        _migrate_reward_defaults(profile)
    activate_scheme(state, basis, capture=False)
    state["scoring_scheme_selector"] = basis
