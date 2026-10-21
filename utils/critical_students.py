"""按总分 A 线差跟踪临界生，使用宽观察区间和描述性历史标记。"""
import pandas as pd

from config.bias_rules import BIAS_LEVELS
from utils.exam_template import SUBJECTS, read_exam_lines
from utils.subject_bias import FULL_SCORES, valid_score

LOWER_MARGIN = 20.0
UPPER_MARGIN = 15.0
RECENT_EXAMS = 3
EXIT_EXAMS = 2
EPSILON = 1e-9
RULES = [
    {'项目': '当期观察范围', '设置': '总分A线差在-20至+15分之间，包含两端及恰好压线'},
    {'项目': '总分及A线', '设置': '六科成绩求和；物理类六科A线求和，选科A线平分给化学和生物'},
    {'项目': '进入观察', '设置': '任一场进入观察区间，即进入观察名单；不设置硬性的核心层'},
    {'项目': '延续观察', '设置': '单次超出区间仍观察，连续2次有效考试处于区间同一侧才转出'},
    {'项目': '转出后的支持', '设置': '线上区外转常规跟踪；线下区外转基础提升支持，记录仍可查看'},
    {'项目': '本次资料不足', '设置': '缺考、成绩无效或A线不足不判断升降；历史在册者保留并标记待核实'},
    {'项目': '历史窗口', '设置': '最近3次有完整六科成绩及A线的有效考试，按工作表或上传顺序'},
    {'项目': '跨线', '设置': 'A线差>=0为线上；最近3次中1次跨线标记近期跨线，2次标记反复跨线'},
    {'项目': '趋势', '设置': '最近3次线差严格递减或递增，标记连续下降或上升，并展示变化幅度'},
    {'项目': '波动', '设置': '展示最近3次线差最大值减最小值，不将波动当作批改误差或上线概率'},
    {'项目': '关注标记', '设置': '结合跨线、连续变化、单次进入及持续偏科供老师判断，不计算风险总分'},
    {'项目': '评分', '设置': '临界生跟踪不参与进步、奖励或偏科扣分的计算'},
]


def _in_band(delta):
    return delta is not None and -LOWER_MARGIN - EPSILON <= delta <= UPPER_MARGIN + EPSILON


def _exam_reference(dataframe, label):
    lines = read_exam_lines(dataframe, label)['A']
    invalid = [subject for subject in SUBJECTS if subject not in lines or
               not 0 < lines[subject] <= FULL_SCORES[subject]]
    return {
        '考试': label,
        'A线': sum(lines[subject] for subject in SUBJECTS) if not invalid else None,
        '分数线说明': '缺少或无效A线：' + '、'.join(invalid) if invalid else '',
    }


def _exam_record(row, reference):
    label = reference['考试']
    scores = {subject: valid_score(row.get(f'{subject}_{label}'), subject) for subject in SUBJECTS}
    invalid = [subject for subject, value in scores.items() if value is None]
    reason = [reference['分数线说明']] if reference['分数线说明'] else []
    if invalid:
        reason.append('成绩缺失、缺考或无效：' + '、'.join(invalid))
    total = sum(scores.values()) if not invalid else None
    delta = total - reference['A线'] if not reason else None
    return {'考试': label, '资料有效': not reason, '六科总分': total,
            '总分A线': reference['A线'], 'A线差': delta,
            '当期区间内': _in_band(delta), '资料说明': '；'.join(reason)}


def build_critical_analysis(dataframe, labels, bias_dict=None):
    """状态从成绩历史重建，重新导入或切换排名方案不会改变分组依据。"""
    bias_dict = bias_dict or {}
    references = [_exam_reference(dataframe, label) for label in dict.fromkeys(labels)]
    summaries, histories = [], []
    for _, row in dataframe.iterrows():
        name = row.get('姓名')
        if not isinstance(name, str) or not name.strip() or not references:
            continue
        records = [_exam_record(row, reference) for reference in references]
        observing, previous_side, outside_streak = False, None, 0
        for record in records:
            if record['资料有效']:
                delta = record['A线差']
                if record['当期区间内']:
                    observing, previous_side, outside_streak = True, None, 0
                    status = '当期区间内'
                else:
                    side = '线上' if delta > UPPER_MARGIN else '线下'
                    outside_streak = outside_streak + 1 if previous_side == side else 1
                    previous_side = side
                    if observing and outside_streak < EXIT_EXAMS:
                        status = f'延续观察（{side}区外）'
                    else:
                        observing = False
                        status = '转常规跟踪（线上区外）' if side == '线上' else '转基础提升支持（线下区外）'
            else:
                status = '历史在册，本次待核实' if observing else '本次待核实'
            record.update({'姓名': name, '观察名单': observing, '跟踪状态': status})
            histories.append(record)

        current = records[-1]
        valid = [record for record in records if record['资料有效']]
        recent = valid[-RECENT_EXAMS:]
        deltas = [record['A线差'] for record in recent]
        changes = [right - left for left, right in zip(deltas[:-1], deltas[1:])]
        crossings = sum((left >= 0) != (right >= 0) for left, right in zip(deltas[:-1], deltas[1:]))
        tags = []
        if current['资料有效']:
            if crossings >= 2:
                tags.append('反复跨线')
            elif crossings:
                tags.append('近期跨线')
            if len(deltas) == RECENT_EXAMS:
                if all(change < -EPSILON for change in changes):
                    tags.append('线差连续下降')
                elif all(change > EPSILON for change in changes):
                    tags.append('线差连续上升')
            if len(valid) >= 2:
                previous = valid[-2]
                if previous['A线差'] >= 0 > current['A线差']:
                    tags.append('本次跌破A线')
                elif previous['A线差'] < 0 <= current['A线差']:
                    tags.append('本次升至A线')
                if current['当期区间内'] and not previous['当期区间内']:
                    side = '线上' if previous['A线差'] > UPPER_MARGIN else '线下'
                    tags.append(f'本次从{side}区外进入')
        else:
            tags.append('本次待核实')
        if len(recent) < RECENT_EXAMS:
            tags.append('有效历史不足3场')

        bias = bias_dict.get(name, {})
        persistent = bias.get('持续薄弱科目', [])
        if bias.get('持续偏科等级') in BIAS_LEVELS:
            tags.append('持续偏科')
        improving = [item['科目'] for item in bias.get('持续学科明细', []) if '改善' in item['当前状态']]
        if improving:
            tags.append('偏科改善中')
        delta = current['A线差']
        summaries.append({
            '姓名': name, '本次考试': current['考试'], '本次总分': current['六科总分'],
            '本次A线': current['总分A线'], '本次A线差': delta,
            '线上线下': ('线上（含压线）' if delta >= 0 else '线下') if delta is not None else '本次待核实',
            '当期区间内': current['当期区间内'], '观察名单': current['观察名单'],
            '跟踪状态': current['跟踪状态'], '关注标记': '、'.join(tags) or '常规观察',
            '最近有效场数': len(recent), '最近区间内次数': sum(record['当期区间内'] for record in recent),
            '最近跨线次数': crossings,
            '最近线差变化': changes[-1] if changes else None,
            '最近线差极差': max(deltas) - min(deltas) if deltas else None,
            '最近平均线差': sum(deltas) / len(deltas) if deltas else None,
            '最近有效考试': ' → '.join(record['考试'] for record in recent),
            '持续偏科等级': bias.get('持续偏科等级', '数据不足'),
            '持续薄弱科目': '、'.join(persistent) or '-', '偏科改善科目': '、'.join(improving) or '-',
            '本次资料说明': current['资料说明'],
        })

    summary = pd.DataFrame(summaries)
    if not summary.empty:
        summary = summary.sort_values(['本次A线差', '姓名'], na_position='last').reset_index(drop=True)
    return {'summary': summary, 'history': pd.DataFrame(histories),
            'references': pd.DataFrame(references), 'rules': pd.DataFrame(RULES)}
