"""以每场 A/B 分数线为参照的偏科规则。"""
import math

BIAS_VERSION = 3
BIAS_LEVELS = ('轻微偏科', '明显偏科', '重度偏科')
BIAS_BALANCED = '未达偏科阈值'
BIAS_WINDOW = 5
BIAS_ALPHA = 0.4
BIAS_MIN_HISTORY = 3
BIAS_FREQUENCY = 0.6
BIAS_DEFAULTS = {
    '偏科算法版本': BIAS_VERSION,
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
            '持续判定看最近5场，至少3场有效且其中60%出现短板，近期指数权重0.4。'
            '最近1次低于轻微阈值，历史计分降一档；最近2次有效考试均低于阈值，停止历史扣分。'
            '缺考或本次分数线不足不扣分，不使用班级均分。')
