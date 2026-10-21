"""偏科指标的边界、统计性质和页面评分导出回归。"""
from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

import test_progress_integration as fixtures
from config.bias_rules import BIAS_DEFAULTS, BIAS_BALANCED, normalize_bias_params, validate_bias_params
from score_analysis_v0_1 import detect_subject_bias, bias_penalty_score

SUBJECTS = fixtures.SUBJECTS


def known_config():
    return {**BIAS_DEFAULTS, 'bias_exam_label': '本次',
            'bias_exam_lines': {'A': dict.fromkeys(SUBJECTS, 85),
                                'B': dict.fromkeys(SUBJECTS, 75), '来源': '独立目标线'}}


def cohort_frame():
    rows = []
    for index in range(12):
        row = {'姓名': f'学生{index}', '总分年级排名': index + 1,
               '总分集团排名': (index + 1) * 10}
        for subject in SUBJECTS:
            row[subject] = 100 + (index - 5.5) * 2 if subject in SUBJECTS[:3] else 70 + index - 5.5
            row[subject + '年级排名'] = index + 1
            row[subject + '集团排名'] = (index + 1) * 10
        if index == 11:
            row['英语'] = 65
        row['总分'] = sum(row[s] for s in SUBJECTS)
        rows.append(row)
    return pd.DataFrame(rows)


def uploaded(frame, index=1):
    buffer = BytesIO()
    frame = frame.copy()
    for subject in SUBJECTS:
        frame[subject + 'A线'] = 110 if subject in SUBJECTS[:3] else 80
        frame[subject + 'B线'] = 90 if subject in SUBJECTS[:3] else 60
    frame.to_excel(buffer, index=False)
    return {'name': f'考试{index}.xlsx', 'content': buffer.getvalue(),
            'exam_num': index, 'exam_label': f'月考{index}'}


class SubjectBiasTests(unittest.TestCase):
    def test_boundary_severity_and_progressive_deductions(self):
        cfg = known_config()
        cfg['bias_penalty'] = {level: cfg[level + '扣分']
                               for level in ['轻微偏科', '明显偏科', '重度偏科']}
        for english, label, penalty in [(71, BIAS_BALANCED, 0), (70, '轻微偏科', -10),
                                        (65, '明显偏科', -25), (60, '重度偏科', -45)]:
            with self.subTest(english=english):
                result = detect_subject_bias({**dict.fromkeys(SUBJECTS, 75), '英语': english}, SUBJECTS, config=cfg)
                self.assertEqual(result['偏科等级'], label)
                self.assertEqual(bias_penalty_score(label, cfg), penalty)

    def test_uniform_low_scores_or_one_strong_subject_are_not_penalized(self):
        for scores in [dict.fromkeys(SUBJECTS, 55), dict.fromkeys(SUBJECTS, 90),
                       {**dict.fromkeys(SUBJECTS, 75), '数学': 110}]:
            self.assertEqual(detect_subject_bias(scores, SUBJECTS, config=known_config())['偏科等级'], BIAS_BALANCED)

    def test_multiple_weak_subjects_are_visible_but_do_not_multiply_the_penalty(self):
        result = detect_subject_bias({**dict.fromkeys(SUBJECTS, 75), '语文': 55, '英语': 55},
                                     SUBJECTS, config=known_config())
        self.assertEqual(set(result['薄弱科目']), {'语文', '英语'})
        self.assertEqual(result['偏科指数'], 2)
        self.assertEqual(result['偏科等级'], '重度偏科')

    def test_chemistry_and_biology_are_separate(self):
        result = detect_subject_bias({**dict.fromkeys(SUBJECTS, 75), '化学': 55, '生物': 95},
                                     SUBJECTS, config=known_config())
        self.assertIn('化学', result['薄弱科目'])
        self.assertEqual(result['最弱科目'], '化学')

    def test_affine_score_scale_does_not_change_the_result(self):
        scores = {**dict.fromkeys(SUBJECTS, 75), '英语': 60}
        cfg = known_config()
        before = detect_subject_bias(scores, SUBJECTS, config=cfg)
        scores['英语'] = scores['英语'] * 1.2 + 5
        for kind in ('A', 'B'):
            cfg['bias_exam_lines'][kind]['英语'] = cfg['bias_exam_lines'][kind]['英语'] * 1.2 + 5
        after = detect_subject_bias(scores, SUBJECTS, config=cfg)
        self.assertAlmostEqual(before['偏科指数'], after['偏科指数'])
        self.assertEqual(before['薄弱科目'], after['薄弱科目'])

    def test_missing_lines_and_invalid_scores_are_not_false_balance(self):
        row = dict.fromkeys(SUBJECTS, 75)
        self.assertEqual(detect_subject_bias(row, SUBJECTS, config=BIAS_DEFAULTS)['偏科等级'], '数据不足')
        for value in [0, None, float('nan'), float('inf'), -1, 151, '无成绩']:
            with self.subTest(value=value):
                result = detect_subject_bias({**row, '英语': value}, SUBJECTS, config=known_config())
                self.assertEqual(result['偏科等级'], '数据不足')
        self.assertEqual(detect_subject_bias(row, SUBJECTS, config=known_config())['偏科等级'], BIAS_BALANCED)

    def test_config_migration_preserves_custom_values_and_validates_order(self):
        old = {'轻微偏科_标准差': 15, '明显偏科_标准差': 30, '严重偏科_标准差': 60,
               '轻微偏科扣分': 20, '明显偏科扣分': 40, '严重偏科扣分': 70}
        migrated = normalize_bias_params(old)
        for key, value in BIAS_DEFAULTS.items():
            self.assertEqual(migrated[key], value)
        custom = normalize_bias_params({**old, '轻微偏科扣分': 3, '明显偏科扣分': 7, '严重偏科扣分': 12})
        self.assertEqual([custom[s + '扣分'] for s in ['轻微偏科', '明显偏科', '重度偏科']], [3, 7, 12])
        for override in [{'轻微偏科_AB档差距': 2}, {'重度偏科扣分': 5}, {'明显偏科扣分': -1}]:
            with self.assertRaises(ValueError):
                validate_bias_params({**BIAS_DEFAULTS, **override})


class SubjectBiasIntegrationTests(unittest.TestCase):
    setUp = fixtures.ProgressIntegrationTests.setUp
    tearDown = fixtures.ProgressIntegrationTests.tearDown
    assert_app_ok = fixtures.ProgressIntegrationTests.assert_app_ok

    def test_scoring_and_both_schemes_use_same_external_lines(self):
        frame = cohort_frame()
        for basis in ['grade', 'group']:
            for columns in [9, 22] if basis == 'grade' else [22]:
                with self.subTest(basis=basis, columns=columns):
                    data = frame if columns == 22 else frame[['姓名', '总分年级排名', '总分'] + SUBJECTS]
                    app = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
                    app.session_state['scoring_scheme'] = basis
                    app.session_state['score_files'] = [uploaded(data)]
                    app.run()
                    self.assert_app_ok(app)
                    row = app.session_state['results'][1].set_index('姓名').loc['学生11']
                    self.assertEqual(row['偏科等级'], '重度偏科')
                    self.assertEqual(row['薄弱科目'], '英语')
                    self.assertEqual(row['偏科扣分'], -45)
                    parts = ['区间进步得分', '连续进步加分', '年级排名加分', 'A/B线奖励',
                             '集团排名加分', '总分奖励', '东校状元奖', '偏科扣分']
                    self.assertAlmostEqual(row['总得分'], sum(row[col] for col in parts))

    def test_no_old_exam_subjects_are_used_to_fill_current_missing_columns(self):
        frame = cohort_frame()
        output = BytesIO()
        current = frame.drop(columns=[c for c in frame if c.startswith(('化学', '生物'))])
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            frame.to_excel(writer, sheet_name='历史', index=False)
            current.to_excel(writer, sheet_name='本次', index=False)
        app = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
        app.session_state['history_file_content'] = output.getvalue()
        app.run()
        self.assert_app_ok(app)
        details = app.session_state['results'][8]['学生11']['学科明细']
        self.assertEqual(app.session_state['results'][8]['学生11']['偏科等级'], '数据不足')
        self.assertTrue(all(d['原始分'] is None for d in details if d['科目'] in ('化学', '生物')))

    def test_pages_exports_and_reimport_keep_explainable_deductions(self):
        app = AppTest.from_file(str(fixtures.ROOT / 'app.py'), default_timeout=30)
        app.session_state['score_files'] = [uploaded(cohort_frame())]
        app.session_state['analysis_started'] = True
        downloads = {}
        original = st.download_button

        def capture(*args, **kwargs):
            downloads[kwargs['file_name']] = kwargs['data']
            return original(*args, **kwargs)

        with patch('streamlit.download_button', side_effect=capture):
            app.run()
        self.assert_app_ok(app)
        self.assertEqual(len(app.tabs), 7)
        book = pd.read_excel(BytesIO(downloads['完整分析结果.xlsx']), sheet_name=None)
        for sheet in ['完整结果', '得分明细', '偏科检测']:
            self.assertEqual(book[sheet].set_index('姓名').loc['学生11', '偏科等级'], '重度偏科')
        details = book['偏科学科明细']
        self.assertEqual(len(details[details['姓名'] == '学生11']), 6)
        self.assertEqual(book['偏科规则'].set_index('项目').loc['重度偏科扣分', '设置'], 45)
        again = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
        again.session_state['history_file_content'] = downloads['成绩总表.xlsx']
        again.run()
        self.assert_app_ok(again)
        pd.testing.assert_frame_equal(app.session_state['df_score'], again.session_state['results'][1])

    def test_configuration_save_load_and_restore_use_one_set_of_defaults(self):
        app = AppTest.from_string(fixtures.SIDEBAR_SCRIPT, default_timeout=20).run()
        self.assert_app_ok(app)
        app.number_input(key='bias_v3_轻微偏科扣分').set_value(12.0).run()
        next(b for b in app.button if b.label == '💾 保存配置').click().run()
        saved = json.loads(Path('config/user_settings.json').read_text())
        self.assertEqual(saved['config_params']['轻微偏科扣分'], 12)
        app.number_input(key='bias_v3_轻微偏科扣分').set_value(18.0).run()
        next(b for b in app.button if b.label == '📂 加载配置').click().run()
        self.assert_app_ok(app)
        self.assertEqual(app.number_input(key='bias_v3_轻微偏科扣分').value, 12)
        next(b for b in app.button if b.label == '🔄 恢复默认').click().run()
        self.assert_app_ok(app)
        for key, value in BIAS_DEFAULTS.items():
            self.assertEqual(app.session_state['config_params'][key], value)


if __name__ == '__main__':
    unittest.main()
