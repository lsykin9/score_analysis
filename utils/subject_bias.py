"""基于外部 A/B 线及最近多场考试识别个人学科短板，不使用班级均分。"""
import math
from statistics import median

from config.bias_rules import (
    BIAS_LEVELS, BIAS_BALANCED, BIAS_WINDOW, BIAS_ALPHA, BIAS_MIN_HISTORY,
    BIAS_FREQUENCY, normalize_bias_params, validate_bias_params,
)
from utils.exam_template import read_exam_lines

FULL_SCORES = {'语文': 150, '数学': 150, '英语': 150,
               '物理': 100, '化学': 100, '生物': 100}


def valid_score(value, subject):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(value) or not 0 < value <= FULL_SCORES.get(subject, 100):
        return None
    return value


def level_number(gap, params):
    for number, level in reversed(list(enumerate(BIAS_LEVELS, 1))):
        if gap >= float(params[level + '_AB档差距']) - 1e-12:
            return number
    return 0


def level_name(number):
    return BIAS_LEVELS[number - 1] if number else BIAS_BALANCED


def empty_bias_result(level='数据不足', reason='缺少同场六科有效成绩或完整 A/B 分数线，本次不扣分。', exam=''):
    return {'偏科等级': level, '偏科指数': None, '本次偏科等级': level,
            '持续偏科等级': '待观察', '持续偏科指数': None,
            '最强科目': '-', '最弱科目': '-', '薄弱科目': [], '持续薄弱科目': [],
            '学科明细': [], '历史明细': [], '持续学科明细': [], '考试汇总': [],
            '判定说明': reason, '分析考试': exam}


def prepare_bias_exams(dataframe, labels, subjects):
    """分数线每场读取一次，绝不使用其他考试补齐。"""
    exams = []
    for label in labels:
        lines = read_exam_lines(dataframe, label)
        columns = {subject: f'{subject}_{label}' for subject in subjects
                   if f'{subject}_{label}' in dataframe}
        errors = []
        for subject in subjects:
            a, b = lines['A'].get(subject), lines['B'].get(subject)
            if a is None or b is None:
                errors.append(f'{subject}缺少A/B线')
            elif not (0 <= b < a <= FULL_SCORES[subject]):
                errors.append(f'{subject}须满足0≤B线<A线≤满分')
            if subject not in columns:
                errors.append(f'缺少{subject}成绩列')
        exams.append({'考试': label, '成绩列': columns, '分数线': lines,
                      '资料说明': '；'.join(errors)})
    return exams


def _analyze_exam(row, exam, subjects, params):
    label, lines = exam['考试'], exam['分数线']
    scores = {subject: valid_score(row.get(exam['成绩列'].get(subject)), subject)
              for subject in subjects}
    reason = exam.get('资料说明', '')
    if any(value is None for value in scores.values()):
        reason = '六科成绩缺失、缺考或超出有效范围'
    details = []
    result = {'考试': label, '有效': not bool(reason), '资料说明': reason,
              '总分': sum(scores.values()) if all(v is not None for v in scores.values()) else None,
              '总分A线': None, '总分B线': None, '总分A线差': None, '总分B线差': None,
              '总分目标位置': None, '本次偏科等级': '数据不足', '偏科指数': None,
              '学科明细': details}
    positions = {}
    if not reason:
        positions = {s: (scores[s] - lines['B'][s]) / (lines['A'][s] - lines['B'][s]) for s in subjects}
        for kind in ('A', 'B'):
            target = sum(lines[kind][s] for s in subjects)
            result['总分' + kind + '线'] = target
            result['总分' + kind + '线差'] = result['总分'] - target
        result['总分目标位置'] = (result['总分'] - result['总分B线']) / (result['总分A线'] - result['总分B线'])
    for subject in subjects:
        score = scores[subject]
        a, b = lines['A'].get(subject), lines['B'].get(subject)
        detail = {'考试': label, '科目': subject, '原始分': score, 'A线': a, 'B线': b,
                  'A线差': score - a if score is not None and a is not None else None,
                  'B线差': score - b if score is not None and b is not None else None,
                  '目标位置': None, '其他学科中位目标位置': None, '有向短板差距': None,
                  '短板差距': None, '个人参照目标分': None, '补齐个人短板所需分数': None,
                  '学科判定': '数据不足', '资料说明': reason, '分数线来源': lines.get('来源', '')}
        if not reason:
            baseline = median(value for key, value in positions.items() if key != subject)
            signed_gap = baseline - positions[subject]
            target = max(0.0, min(FULL_SCORES[subject], b + baseline * (a - b)))
            detail.update({'目标位置': positions[subject], '其他学科中位目标位置': baseline,
                           '有向短板差距': signed_gap, '短板差距': max(0.0, signed_gap),
                           '个人参照目标分': target, '补齐个人短板所需分数': max(0.0, target - score),
                           '学科判定': level_name(level_number(signed_gap, params))})
        details.append(detail)
    if not reason:
        result['偏科指数'] = max(detail['短板差距'] for detail in details)
        result['本次偏科等级'] = level_name(level_number(result['偏科指数'], params))
    return result


def analyze_student_history(row, subjects, config):
    params = normalize_bias_params(config)
    validate_bias_params(params)
    exams = config.get('bias_exams', [])
    if not exams:
        return empty_bias_result(exam=config.get('bias_exam_label', ''))
    records = [_analyze_exam(row, exam, subjects, params) for exam in exams]
    current = records[-1]
    result = empty_bias_result(reason=current['资料说明'], exam=current['考试'])
    result['学科明细'] = current['学科明细']
    result['历史明细'] = [detail for record in records for detail in record['学科明细']]
    result['考试汇总'] = [{key: value for key, value in record.items() if key != '学科明细'}
                          for record in records]
    window = records[-BIAS_WINDOW:]
    recent = [(index, record) for index, record in enumerate(window) if record['有效']]
    light = float(params['轻微偏科_AB档差距'])
    summaries = []
    for subject in subjects:
        gaps = [(index, next(detail['有向短板差距'] for detail in record['学科明细']
                            if detail['科目'] == subject)) for index, record in recent]
        weak_count = sum(gap >= light - 1e-12 for _, gap in gaps)
        streak = 0
        for _, gap in reversed(gaps):
            if gap < light - 1e-12:
                break
            streak += 1
        weights = [BIAS_ALPHA * (1 - BIAS_ALPHA) ** (len(window) - 1 - index) for index, _ in gaps]
        average = sum(weight * gap for weight, (_, gap) in zip(weights, gaps)) / sum(weights) if weights else None
        enough = len(gaps) >= BIAS_MIN_HISTORY
        persistent = (level_number(average, params) if enough and
                      weak_count >= math.ceil(BIAS_FREQUENCY * len(gaps)) else 0)
        effective = persistent
        status = '持续短板' if persistent else ('待观察' if not enough else '未达持续判定条件')
        if persistent and gaps[-1][1] < light - 1e-12:
            status = '改善中'
            effective = max(0, persistent - 1)
            if len(gaps) >= 2 and gaps[-2][1] < light - 1e-12:
                status = '近期连续改善，停止历史扣分'
                effective = 0
        summaries.append({'科目': subject, '最近窗口场数': len(window), '有效场数': len(gaps),
                          '短板场数': weak_count, '短板频率': weak_count / len(gaps) if gaps else None,
                          '连续有效考试短板次数': streak, '历史加权差距': average,
                          '持续偏科等级': level_name(persistent) if enough else '待观察',
                          '历史计分等级': level_name(effective), '当前状态': status,
                          '最新有向短板差距': current['学科明细'][subjects.index(subject)]['有向短板差距']})
    result['持续学科明细'] = summaries
    historical_index = max((max(0.0, s['历史加权差距']) for s in summaries
                            if s['历史加权差距'] is not None), default=None)
    raw_persistent = max((BIAS_LEVELS.index(s['持续偏科等级']) + 1 for s in summaries
                          if s['持续偏科等级'] in BIAS_LEVELS), default=0)
    result['持续偏科指数'] = historical_index
    result['持续偏科等级'] = level_name(raw_persistent) if len(recent) >= BIAS_MIN_HISTORY else '待观察'
    result['持续薄弱科目'] = [s['科目'] for s in summaries if s['持续偏科等级'] in BIAS_LEVELS]
    if not current['有效']:
        # 历史可展示，但本次资料不完整时不据历史扣分。
        result['判定说明'] = current['资料说明'] + '；本次不扣分，历史记录仅供查看。'
        return result

    details = current['学科明细']
    current_number = level_number(current['偏科指数'], params)
    effective_history = max((BIAS_LEVELS.index(s['历史计分等级']) + 1 for s in summaries
                             if s['历史计分等级'] in BIAS_LEVELS), default=0)
    score_number = max(current_number, effective_history)
    current_weak = [d['科目'] for d in sorted(details, key=lambda d: d['短板差距'], reverse=True)
                    if level_number(d['短板差距'], params)]
    historical_weak = [s['科目'] for s in summaries if s['历史计分等级'] in BIAS_LEVELS]
    result.update({'偏科等级': level_name(score_number), '本次偏科等级': current['本次偏科等级'],
                   '偏科指数': current['偏科指数'],
                   '最强科目': max(details, key=lambda d: d['目标位置'])['科目'],
                   '最弱科目': max(details, key=lambda d: d['短板差距'])['科目'],
                   '薄弱科目': list(dict.fromkeys(current_weak + historical_weak)),
                   '判定说明': ('按各场物理类A/B线识别个人短板，不使用班级均分；'
                            f'最近{len(window)}场中{len(recent)}场有效。'
                            '本次等级与改善调整后的历史等级取较高档，每人只扣一次。')})
    return result


def detect_relative_bias(row, subjects, config=None):
    """兼容原接口；直接成绩字典也必须显式提供同场 A/B 线。"""
    config = dict(config or {})
    if 'bias_exams' not in config:
        label = config.get('bias_exam_label', '本次')
        lines = config.get('bias_exam_lines', {'A': {}, 'B': {}, '来源': ''})
        errors = []
        for subject in subjects:
            a, b = lines.get('A', {}).get(subject), lines.get('B', {}).get(subject)
            if a is None or b is None or not 0 <= b < a <= FULL_SCORES[subject]:
                errors.append(f'{subject}缺少有效A/B线')
        config['bias_exams'] = [{'考试': label, '成绩列': {subject: subject for subject in subjects},
                                 '分数线': lines, '资料说明': '；'.join(errors)}]
    return analyze_student_history(row, list(subjects), config)
