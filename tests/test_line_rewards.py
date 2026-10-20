"""A/B 线独立于排名奖励开关，且评分、页面及导出一致。"""
from io import BytesIO
import unittest
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

import test_progress_integration as fixtures
from config.scoring_schemes import GRADE_REWARD_ENABLED, GROUP_REWARD_ENABLED
from score_analysis_v0_1 import line_bonus_score, ranking_bonus


class LineRewardTests(unittest.TestCase):
    def test_boundaries_choose_one_line_and_keep_rank_bonus_separate(self):
        config = {'line_a': 80, 'bonus_line_a': 100, 'line_b': 430,
                  'bonus_line_b': 30, 'rank_bonus': {50: 20, 100: 10}}
        for rank, expected in [(0, 0), (80, 100), (81, 30), (430, 30), (431, 0)]:
            with self.subTest(rank=rank):
                self.assertEqual(line_bonus_score(rank, config), expected)
        self.assertEqual(ranking_bonus(45, 46, config), 20)
        self.assertEqual(line_bonus_score(45, {**config, 'bonus_line_b': 150}), 150)
        self.assertEqual(line_bonus_score(50, {'line': 80, 'bonus_line': 5}), 5)


class LineRewardIntegrationTests(unittest.TestCase):
    setUp = fixtures.ProgressIntegrationTests.setUp
    tearDown = fixtures.ProgressIntegrationTests.tearDown
    assert_app_ok = fixtures.ProgressIntegrationTests.assert_app_ok

    def process(self, basis='grade', grade_enabled=False, group_enabled=False,
                rank=45, column_count=22, absent_exam=None):
        app = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
        app.session_state['scoring_scheme'] = basis
        app.session_state['score_files'] = fixtures.upload_files(
            [rank, rank], column_count, absent_exam=absent_exam, group_rank=[90, 90])
        app.session_state['test_rule'] = {GRADE_REWARD_ENABLED: grade_enabled,
                                          GROUP_REWARD_ENABLED: group_enabled,
                                          'B线过线奖励': 30}
        app.run()
        self.assert_app_ok(app)
        return app.session_state['results'][1].iloc[0]

    def test_both_schemes_and_all_reward_switch_combinations(self):
        for basis in ['grade', 'group']:
            for grade_enabled in [False, True]:
                for group_enabled in [False, True]:
                    with self.subTest(basis=basis, grade=grade_enabled, group=group_enabled):
                        row = self.process(basis, grade_enabled, group_enabled)
                        self.assertEqual(row['A/B线奖励'], 100)
                        self.assertEqual(row['年级排名加分'], 20 if grade_enabled else 0)
                        self.assertEqual(row['集团排名加分'], 100 if group_enabled else 0)
                        parts = ['区间进步得分', '连续进步加分', '年级排名加分',
                                 'A/B线奖励', '集团排名加分', '总分奖励', '东校状元奖', '偏科扣分']
                        self.assertAlmostEqual(row['总得分'], sum(row[col] for col in parts))

    def test_all_upload_formats_keep_lines_when_rank_rewards_are_off(self):
        for columns in [2, 3, 9, 22]:
            with self.subTest(columns=columns):
                row = self.process(column_count=columns)
                self.assertEqual(row['年级排名加分'], 0)
                self.assertEqual(row['A/B线奖励'], 100)

    def test_b_line_only_no_line_absence_and_invalid_grade(self):
        for basis in ['grade', 'group']:
            with self.subTest(basis=basis):
                self.assertEqual(self.process(basis, rank=81)['A/B线奖励'], 30)
                self.assertEqual(self.process(basis, rank=431)['A/B线奖励'], 0)
                self.assertEqual(self.process(basis, absent_exam=2)['A/B线奖励'], 0)
                self.assertEqual(self.process(basis, rank=0)['A/B线奖励'], 0)

    def test_pages_and_exports_show_independent_line_reward(self):
        app = AppTest.from_file(str(fixtures.ROOT / 'app.py'), default_timeout=30)
        app.session_state['scoring_scheme'] = 'group'
        app.session_state['score_files'] = fixtures.upload_files([46, 45], group_rank=[91, 90])
        app.session_state['analysis_started'] = True
        downloads = {}
        original = st.download_button

        def capture(*args, **kwargs):
            downloads[kwargs['file_name']] = kwargs['data']
            return original(*args, **kwargs)

        with patch('streamlit.download_button', side_effect=capture):
            app.run()
        self.assert_app_ok(app)
        self.assertEqual(app.session_state['df_score'].iloc[0]['年级排名加分'], 0)
        self.assertEqual(app.session_state['df_score'].iloc[0]['A/B线奖励'], 100)
        breakdown = next(table.value for table in app.table
                         if list(table.value.columns) == ['项目', '得分'])
        self.assertEqual(breakdown.set_index('项目').loc['A/B线奖励', '得分'], 100)
        self.assertAlmostEqual(breakdown['得分'].sum(), app.session_state['df_score'].iloc[0]['总得分'])
        workbook = pd.read_excel(BytesIO(downloads['完整分析结果.xlsx']), sheet_name=None)
        for sheet in ['完整结果', '得分明细']:
            self.assertEqual(workbook[sheet].iloc[0]['A/B线奖励'], 100)
            self.assertEqual(workbook[sheet].iloc[0]['年级排名加分'], 0)
        reimported = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
        reimported.session_state['scoring_scheme'] = 'group'
        reimported.session_state['history_file_content'] = downloads['成绩总表.xlsx']
        reimported.run()
        self.assert_app_ok(reimported)
        pd.testing.assert_frame_equal(app.session_state['df_score'], reimported.session_state['results'][1])


if __name__ == '__main__':
    unittest.main()
