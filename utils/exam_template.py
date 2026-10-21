"""拆分学生成绩与物理类 A/B 线，兼容右侧表格及系统导出的线列。"""
import math
import re

import pandas as pd

SUBJECTS = ('语文', '数学', '英语', '物理', '化学', '生物')
LINE_SOURCE = '偏科线来源'
RESERVED_SHEETS = {'成绩总表', '完整总表', '偏科分数线', '偏科规则', '偏科检测',
                   '偏科学科明细', '偏科历史明细', '持续偏科明细', '偏科考试汇总',
                   '完整结果', '得分明细', '连续进步规则', '当前方案参数',
                   '临界生名单', '临界生历史', '临界生规则'}


def _text(value):
    return re.sub(r'\s+', '', str(value)).rstrip('_')


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def split_exam_sheet(frame):
    """选科合计线按用户约定平分；历史类扩展区域不参与当前解析。"""
    frame = frame.copy()
    frame.columns = [str(column).strip().rstrip('_') for column in frame.columns]
    lines = {'A': {}, 'B': {}, '来源': ''}

    # 系统导出的分数线按列保存，不依赖学生行号和右侧排版。
    for subject in SUBJECTS:
        for kind in ('A', 'B'):
            column = subject + kind + '线'
            if column in frame:
                values = frame[column].dropna().map(_number).dropna().unique()
                if len(values) > 1:
                    raise ValueError(f'{column}在同一场考试中存在不同设置，请检查模板。')
                if len(values):
                    lines[kind][subject] = float(values[0])
    if LINE_SOURCE in frame:
        sources = frame[LINE_SOURCE].dropna().astype(str).unique()
        lines['来源'] = sources[0] if len(sources) else ''

    columns = list(frame.columns)
    physical = next((i for i, col in enumerate(columns) if _text(col) == '物理类'), None)
    if physical is not None:
        end = next((i for i in range(physical + 1, len(columns))
                    if _text(columns[i]) in ('历史类', '物理类')), len(columns))
        block = frame.iloc[:, physical:end]
        # 新模板的历史类也可能纵向放在物理类下面。
        next_category = next((i for i in range(len(block))
                              if _text(block.iloc[i, 0]) in ('历史类', '物理类')), len(block))
        block = block.iloc[:next_category]
        header = next((i for i in range(min(10, len(block)))
                       if sum(_text(value) in (*SUBJECTS, '选科', '选科合计')
                              for value in block.iloc[i]) >= 4), None)
        if header is not None:
            positions = {_text(value): j for j, value in enumerate(block.iloc[header])
                         if _text(value) in (*SUBJECTS, '选科', '选科合计')}
            for kind in ('A', 'B'):
                indices = [i for i in range(len(block)) if _text(block.iloc[i, 0]) == kind + '线']
                if len(indices) > 1:
                    raise ValueError(f'物理类存在多行{kind}线，无法确定本场分数线。')
                if not indices:
                    continue
                line_row = block.iloc[indices[0]]
                for subject in SUBJECTS:
                    if subject in positions:
                        value = _number(line_row.iloc[positions[subject]])
                        if value is not None:
                            lines[kind][subject] = value
                combined = positions.get('选科', positions.get('选科合计'))
                if combined is not None:
                    value = _number(line_row.iloc[combined])
                    if value is not None:
                        for subject in ('化学', '生物'):
                            if subject not in positions:
                                lines[kind][subject] = value / 2
            lines['来源'] = ('物理类；化学、生物分数线按选科合计÷2'
                           if '选科' in positions or '选科合计' in positions else '物理类各科分数线')

    standard = ['姓名', '总分', '总分年级排名', '总分集团排名']
    for subject in SUBJECTS:
        standard.extend([subject, subject + '年级排名', subject + '集团排名'])
    if all(column in frame for column in standard):
        scores = frame[standard].copy()
    else:
        removable = {LINE_SOURCE, '总分A线', '总分B线'} | {
            subject + kind + '线' for subject in SUBJECTS for kind in ('A', 'B')}
        scores = frame[[column for column in frame if column not in removable]].copy()
        if physical is not None:
            scores = scores.iloc[:, :physical].dropna(axis=1, how='all')
        else:
            scores = scores.dropna(axis=1, how='all')
    if '姓名' in scores:
        names = scores['姓名']
        scores = scores.loc[names.map(lambda x: isinstance(x, str) and bool(x.strip())
                                     and _text(x) not in ('姓名', 'A线', 'B线'))].copy()
    return scores, lines


def attach_exam_lines(frame, label, lines):
    for subject in SUBJECTS:
        for kind in ('A', 'B'):
            frame[f'{subject}{kind}线_{label}'] = lines[kind].get(subject, float('nan'))
    for kind in ('A', 'B'):
        values = [lines[kind].get(subject) for subject in SUBJECTS]
        frame[f'总分{kind}线_{label}'] = sum(values) if all(v is not None for v in values) else float('nan')
    frame[f'{LINE_SOURCE}_{label}'] = lines.get('来源', '')
    return frame


def read_exam_lines(frame, label):
    lines = {'A': {}, 'B': {}, '来源': ''}
    for subject in SUBJECTS:
        for kind in ('A', 'B'):
            column = f'{subject}{kind}线_{label}'
            if column in frame:
                values = frame[column].dropna().map(_number).dropna().unique()
                if len(values) > 1:
                    raise ValueError(f'{label}的{subject}{kind}线存在不同设置。')
                if len(values):
                    lines[kind][subject] = float(values[0])
    source_column = f'{LINE_SOURCE}_{label}'
    if source_column in frame:
        sources = [value for value in frame[source_column].dropna().unique()
                   if isinstance(value, str) and value]
        lines['来源'] = sources[0] if sources else ''
    return lines
