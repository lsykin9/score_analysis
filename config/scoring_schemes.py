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


def default_profile(basis):
    intervals = ([(0, 20, 4), (21, 50, 2.5), (51, 100, 1.4), (101, 150, 1.2),
                  (151, 200, 1), (201, 300, .8), (301, 430, .6), (431, 99999, .5)]
                 if basis == "grade" else
                 [(0, 200, 4), (201, 500, 1.4), (501, 1000, .6), (1001, 99999, .3)])
    return {
        "rank_intervals": [{"id": i, "start": a, "end": b, "weight": float(w)}
                           for i, (a, b, w) in enumerate(intervals)],
        "rank_bonuses": [{"id": i, "threshold": n, "bonus": b} for i, (n, b) in
                         enumerate([(5, 100), (10, 70), (20, 50), (30, 35), (50, 20), (100, 10)])],
        "group_rank_bonuses": [{"id": i, "threshold": n, "bonus": b} for i, (n, b) in
                               enumerate([(20, 200), (50, 150), (100, 100), (150, 75), (200, 50)])],
        "chain_bonuses": [{"id": i, "times": n, "bonus": b} for i, (n, b) in
                         enumerate([(1, 20), (2, 50), (3, 90), (4, 140), (5, 200)])],
        "params": {TIE_ENABLED: True, TIE_RANK_LIMIT: 100 if basis == "grade" else 200,
                   "A线（排名）": 80, "A线过线奖励": 100, "B线（排名）": 430,
                   "B线过线奖励": 0, GRADE_REWARD_ENABLED: basis == "grade",
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
    activate_scheme(state, basis, capture=False)
    state["scoring_scheme_selector"] = basis
