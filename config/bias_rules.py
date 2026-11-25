"""以每场 A/B 分数线为参照的偏科规则。"""
import math

BIAS_VERSION = 4
BIAS_LEVELS = ('轻微偏科', '明显偏科', '重度偏科')
BIAS_BALANCED = '未达偏科阈值'
BIAS_WINDOW = 5
BIAS_ALPHA = 0.4
BIAS_MIN_HISTORY = 3
BIAS_FREQUENCY = 0.6
BIAS_DEFAULTS = {
    '偏科算法版本': BIAS_VERSION,
    '轻微偏科_AB档差距': 0.4,
    '明显偏科_AB档差距': 0.9,
    '重度偏科_AB档差距': 1.4,
    '轻微偏科扣分': 20,
    '明显偏科扣分': 50,
    '重度偏科扣分': 100,
}

LEGACY_BIAS_DEFAULTS = {
    '轻微偏科_AB档差距': 0.5,
    '明显偏科_AB档差距': 1.0,
    '重度偏科_AB档差距': 1.5,
    '轻微偏科扣分': 10,
    '明显偏科扣分': 25,
    '重度偏科扣分': 45,
}


def normalize_bias_params(params):
    """旧标准分阈值不转换成 A/B 档位；保留用户自定义扣分。"""
    result = dict(params)
    # 完整保留 v2/v3 初始扣分的配置升级为新默认值，保留教师自行调过的数值。
    # v2 仍含“标准差”旧字段，不能因为版本号被兼容而一直覆盖新版默认值。
    legacy_penalties = all(
        result.get(key) == value
        for key, value in LEGACY_BIAS_DEFAULTS.items() if key.endswith('扣分')
    )
    version = result.get('偏科算法版本')
    if version == 2 and legacy_penalties:
        # v2 只有旧的标准差规则；整套切换为 A/B 档位默认值。
        result.update(BIAS_DEFAULTS)
    elif version in (3, BIAS_VERSION) and legacy_penalties:
        # 已有 A/B 档位的配置只替换旧的扣分默认值，保留教师自行调整过的
        # 阈值。此前 v3→v4 迁移只识别 0.5/1.0/1.5，导致 0.4/0.9/1.4
        # 配合 10/25/45 的半迁移配置漏网，页面便一直显示旧扣分。
        for level in BIAS_LEVELS:
            result[level + '扣分'] = BIAS_DEFAULTS[level + '扣分']
    if result.get('偏科算法版本') not in (2, BIAS_VERSION):
        old = tuple(result.get(key) for key in
                    ('轻微偏科扣分', '明显偏科扣分', '严重偏科扣分'))
        if old in {(20, 40, 70), (10, 30, 60)}:
            for level in BIAS_LEVELS:
                result[level + '扣分'] = BIAS_DEFAULTS[level + '扣分']
        elif '重度偏科扣分' not in result and '严重偏科扣分' in result:
            result['重度偏科扣分'] = result['严重偏科扣分']
    for key in list(result):
        if key.endswith(('_标准分差距', '_标准差')):
            del result[key]
    for key, value in BIAS_DEFAULTS.items():
        result.setdefault(key, value)
    result['偏科算法版本'] = BIAS_VERSION
    return result


def validate_bias_params(params):
    thresholds = [float(params[level + '_AB档差距']) for level in BIAS_LEVELS]
    penalties = [float(params[level + '扣分']) for level in BIAS_LEVELS]
    if not all(math.isfinite(x) for x in thresholds + penalties):
        raise ValueError('偏科阈值和扣分必须是有限数值。')
    if not 0 < thresholds[0] < thresholds[1] < thresholds[2]:
        raise ValueError('偏科档位差距须满足：0 < 轻微 < 明显 < 重度。')
    if not 0 <= penalties[0] < penalties[1] < penalties[2]:
        raise ValueError('偏科扣分须满足：0 ≤ 轻微 < 明显 < 重度。')


def describe_bias_rule():
    return ('各科目标位置＝（成绩－B线）÷（A线－B线）；'
            '短板差距＝其他五科目标位置的中位数－该科目标位置。'
            '本次与持续偏科分别判定，每人按较高的计分档位扣一次。'
            '0.4／0.9／1.4 档分别为轻微、明显、重度；持续判定看最近5场，至少3场有效且其中60%出现短板，近期指数权重0.4。'
            '最近1次低于轻微阈值，历史计分降一档；最近2次有效考试均低于阈值，停止历史扣分。'
            '缺考或本次分数线不足不扣分，不使用班级均分。')
