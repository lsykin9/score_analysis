import json
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

import test_progress_integration as fixtures
from config.scoring_schemes import GRADE_REWARD_ENABLED, GROUP_REWARD_ENABLED
from utils.progress_rules import RANK_BASIS, TIE_RANK_LIMIT, TIE_ENABLED


class ScoringSchemeTests(unittest.TestCase):
    setUp = fixtures.ProgressIntegrationTests.setUp
    tearDown = fixtures.ProgressIntegrationTests.tearDown
    assert_app_ok = fixtures.ProgressIntegrationTests.assert_app_ok

    def process(self, grade, group, mode='group', rule=None, absent_exam=None):
        app = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
        app.session_state['scoring_scheme'] = mode
        app.session_state['score_files'] = fixtures.upload_files(grade, absent_exam=absent_exam, group_rank=group)
        app.session_state['test_rule'] = rule or {}
        app.run()
        self.assert_app_ok(app)
        return app.session_state['results'][1].iloc[0]

    def sidebar(self):
        app = AppTest.from_string(fixtures.SIDEBAR_SCRIPT, default_timeout=20).run()
        self.assert_app_ok(app)
        return app

    def switch(self, app, mode):
        app.radio(key='scoring_scheme_selector').set_value(mode).run()
        self.assert_app_ok(app)

    def test_grade_progress_does_not_override_group_regression(self):
        grade = self.process([120, 100, 80], [700, 500, 600], 'grade')
        group = self.process([120, 100, 80], [700, 500, 600])
        self.assertEqual(grade['连续进步次数'], 2)
        self.assertAlmostEqual(grade['区间进步得分'], 28)
        self.assertEqual(group['连续进步次数'], 0)
        self.assertEqual(group['区间进步得分'], 0)
        self.assertEqual(group['年级排名加分'], 0)
        self.assertEqual(group['年级进步名次'], 20)
        self.assertEqual(group['集团进步名次'], -100)
        self.assertEqual(group['双排名对照'], '校内位置提升，集团位置下降')

    def test_group_progress_does_not_use_grade_chain_or_weights(self):
        row = self.process([120, 80, 100], [700, 600, 500])
        self.assertEqual(row['连续进步次数'], 2)
        self.assertAlmostEqual(row['区间进步得分'], 60)
        self.assertEqual(row['连续进步加分'], 50)
        self.assertEqual(row['双排名对照'], '集团位置提升，校内位置下降')

    def test_group_tie_boundary_disabled_and_custom_scope(self):
        for rank, rule, count in [(200, {}, 1), (201, {}, 0),
                                  (500, {TIE_RANK_LIMIT: 500}, 1),
                                  (100, {TIE_ENABLED: False}, 0)]:
            with self.subTest(rank=rank, rule=rule):
                row = self.process([5, 5], [rank, rank], rule=rule)
                self.assertEqual(row['连续进步次数'], count)
                self.assertEqual(row['区间进步得分'], 0)

    def test_champion_and_total_score_are_independent_of_progress_scheme(self):
        row = self.process([1, 1], [80, 70])
        self.assertEqual(row['年级排名加分'], 0)
        self.assertEqual(row['东校状元奖'], 200)
        self.assertEqual(row['总分奖励'], 120)
        self.assertEqual(row['集团排名加分'], 100)
        disabled = self.process([1, 1], [80, 70], rule={GROUP_REWARD_ENABLED: False})
        self.assertEqual(disabled['集团排名加分'], 0)
        self.assertEqual(disabled['东校状元奖'], 200)
        enabled_grade = self.process([1, 1], [80, 70], rule={GRADE_REWARD_ENABLED: True})
        self.assertEqual(enabled_grade['年级排名加分'], 100)
        self.assertEqual(enabled_grade['A/B线奖励'], 100)

    def test_switch_preserves_independent_weights_chains_ties_and_reward_flags(self):
        app = self.sidebar()
        app.number_input(key='weight_2').set_value(2.7).run()
        app.number_input(key='chain_val_0').set_value(33).run()
        app.number_input(key='tie_progress_grade_rank_limit').set_value(75).run()
        self.switch(app, 'group')
        self.assertEqual(app.number_input(key='weight_2').value, .6)
        self.assertEqual(app.number_input(key='chain_val_0').value, 20)
        self.assertEqual(app.number_input(key='tie_progress_grade_rank_limit').value, 200)
        self.assertFalse(app.checkbox(key='grade_rank_reward_enabled').value)
        app.number_input(key='weight_2').set_value(1.1).run()
        app.number_input(key='chain_val_0').set_value(44).run()
        app.number_input(key='tie_progress_grade_rank_limit').set_value(500).run()
        app.checkbox(key='group_rank_reward_enabled').uncheck().run()
        self.switch(app, 'grade')
        self.assertEqual(app.number_input(key='weight_2').value, 2.7)
        self.assertEqual(app.number_input(key='chain_val_0').value, 33)
        self.assertEqual(app.number_input(key='tie_progress_grade_rank_limit').value, 75)
        self.assertTrue(app.checkbox(key='group_rank_reward_enabled').value)
        self.switch(app, 'group')
        self.assertEqual(app.number_input(key='weight_2').value, 1.1)
        self.assertEqual(app.number_input(key='chain_val_0').value, 44)
        self.assertEqual(app.number_input(key='tie_progress_grade_rank_limit').value, 500)
        self.assertFalse(app.checkbox(key='group_rank_reward_enabled').value)

    def test_two_profiles_save_restore_and_reset_without_stale_widgets(self):
        app = self.sidebar()
        app.number_input(key='tie_progress_grade_rank_limit').set_value(60).run()
        self.switch(app, 'group')
        app.number_input(key='tie_progress_grade_rank_limit').set_value(300).run()
        next(b for b in app.button if b.label == '💾 保存配置').click().run()
        self.assert_app_ok(app)
        saved = json.loads(Path('config/user_settings.json').read_text())
        self.assertEqual(saved['scheme_profiles']['grade']['params'][TIE_RANK_LIMIT], 60)
        self.assertEqual(saved['scheme_profiles']['group']['params'][TIE_RANK_LIMIT], 300)
        restored = self.sidebar()
        self.assertEqual(restored.radio(key='scoring_scheme_selector').value, 'group')
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 300)
        self.switch(restored, 'grade')
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 60)
        next(b for b in restored.button if b.label == '📂 加载配置').click().run()
        self.assert_app_ok(restored)
        self.assertEqual(restored.radio(key='scoring_scheme_selector').value, 'group')
        next(b for b in restored.button if b.label == '🔄 恢复默认').click().run()
        self.assert_app_ok(restored)
        self.assertEqual(restored.radio(key='scoring_scheme_selector').value, 'group')
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 200)
        self.switch(restored, 'grade')
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 100)

    def test_legacy_configuration_migrates_only_into_grade_profile(self):
        app = self.sidebar()
        app.number_input(key='tie_progress_grade_rank_limit').set_value(65).run()
        app.number_input(key='weight_2').set_value(3.7).run()
        next(b for b in app.button if b.label == '💾 保存配置').click().run()
        file = Path('config/user_settings.json')
        saved = json.loads(file.read_text())
        saved.pop('scheme_profiles')
        saved.pop('scoring_scheme')
        saved['config_params']['持平计入年级排名上限'] = saved['config_params'].pop(TIE_RANK_LIMIT)
        file.write_text(json.dumps(saved))
        restored = self.sidebar()
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 65)
        self.assertEqual(restored.number_input(key='weight_2').value, 3.7)
        self.switch(restored, 'group')
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 200)
        self.assertEqual(restored.number_input(key='weight_2').value, .6)

    def test_missing_current_group_column_or_value_is_reported(self):
        for files in [fixtures.upload_files([120, 100], 9),
                      fixtures.upload_files([120, 100], group_rank=[500, 0])]:
            with self.subTest(columns=files[0]['name']):
                app = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
                app.session_state['scoring_scheme'] = 'group'
                app.session_state['score_files'] = files
                app.run()
                self.assertTrue(app.exception)
                self.assertIn('集团排名', app.exception[0].message)
        # 年级方案允许缺少集团数据，但不能把上一次的集团排名当成本次奖励。
        grade = self.process([120, 100], [50, 0], mode='grade')
        self.assertEqual(grade['集团排名加分'], 0)
        self.assertIsNone(grade['集团进步名次'])

    def test_old_exams_without_group_are_skipped_and_not_mixed_with_grade(self):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for i, (grade, group) in enumerate([(120, 0), (100, 0), (90, 150), (80, 150)], 1):
                df = fixtures.exam_dataframe(grade, group_rank=group)
                if i <= 2:
                    df = df.drop(columns=['总分集团排名'])
                df.to_excel(writer, sheet_name=f'月考{i}', index=False)
        app = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
        app.session_state['scoring_scheme'] = 'group'
        app.session_state['history_file_content'] = output.getvalue()
        app.run()
        self.assert_app_ok(app)
        row = app.session_state['results'][1].iloc[0]
        self.assertEqual(row['连续进步次数'], 1)
        self.assertEqual(row['区间进步得分'], 0)
        self.assertTrue(any('已跳过' in info.value for info in app.info))

    def test_group_absence_skips_exam_and_does_not_gain_an_extra_step(self):
        middle = self.process([120, 100, 90, 80], [600, 400, 150, 150], absent_exam=2)
        self.assertEqual(middle['连续进步次数'], 2)
        latest = self.process([120, 100, 90, 80], [600, 400, 150, 150], absent_exam=4)
        self.assertEqual(latest['连续进步次数'], 2)
        self.assertEqual(latest['总得分'], 50)

    def test_group_all_pages_and_exports_follow_primary_basis(self):
        app = AppTest.from_file(str(fixtures.ROOT / 'app.py'), default_timeout=30)
        app.session_state['scoring_scheme'] = 'group'
        app.session_state['score_files'] = fixtures.upload_files([120, 100, 80], group_rank=[700, 500, 600])
        app.session_state['analysis_started'] = True
        captured = {}
        original = st.download_button
        def capture(*args, **kwargs):
            captured[kwargs['file_name']] = kwargs['data']
            return original(*args, **kwargs)
        with patch('streamlit.download_button', side_effect=capture):
            app.run()
        self.assert_app_ok(app)
        self.assertEqual(len(app.tabs), 7)
        self.assertTrue(app.radio(key='scoring_scheme_selector').disabled)
        self.assertEqual(next(m for m in app.metric if m.label == '进步人数').value, '0')
        charts = [json.loads(chart.proto.spec) for chart in app.get('plotly_chart')]
        lines = [trace for chart in charts for trace in chart['data']
                 if trace.get('mode', '').startswith('lines+markers')]
        self.assertEqual(len(lines), 2)
        for trace in lines:
            self.assertEqual(trace['y'], [700, 500, 600])
        details = [t.value for t in app.table if '判定' in t.value.columns]
        self.assertIn('本次集团排名', details[0].columns)
        self.assertEqual(details[0].iloc[-1]['连续进步次数'], 0)
        workbook = pd.read_excel(BytesIO(captured['完整分析结果.xlsx']), sheet_name=None)
        rules = workbook['连续进步规则'].set_index('项目')['设置']
        self.assertEqual(rules['进步排名依据'], '总分集团排名')
        self.assertEqual(rules['集团排名上限（含）'], 200)
        self.assertEqual(rules['年级排名奖励'], '关闭')
        self.assertIn('独立计算', rules['A/B线奖励'])
        self.assertIn('当前方案参数', workbook)
        self.assertEqual(workbook['得分明细'].iloc[0]['集团进步名次'], -100)
        self.assertEqual(workbook['得分明细'].iloc[0]['连续进步次数'], 0)
        reimported = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
        reimported.session_state['scoring_scheme'] = 'group'
        reimported.session_state['history_file_content'] = captured['成绩总表.xlsx']
        reimported.run()
        self.assert_app_ok(reimported)
        self.assertEqual(reimported.session_state['results'][1].iloc[0]['总得分'], workbook['得分明细'].iloc[0]['总得分'])


if __name__ == '__main__':
    unittest.main()
