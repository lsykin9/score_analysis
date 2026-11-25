"""同分年级排名校正及真实 Excel 导入评分回归。"""
from io import BytesIO
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

import test_progress_integration as fixtures
from utils.rank_history import correct_tied_score_ranks


class TiedRankTests(unittest.TestCase):
    def test_screenshot_ties_only_change_total_grade_ranks(self):
        df = pd.DataFrame({
            '总分_期中': [646, 619, 619, 614, 614, 609, 609, 608, 608],
            '总分年级排名_期中': [1, 13, 14, 18, 17, 26, 27, 28, 29],
            '总分集团排名_期中': [57, 228, 228, 265, 265, 315, 315, 325, 325],
            # 即使集团或单科排名也存在同分冲突，仍保留原值。
            '集团排名_期中': [57, 228, 229, 265, 266, 315, 316, 325, 326],
            '数学_期中': [100] * 9,
            '数学年级排名_期中': list(range(1, 10)),
        })
        before = df.copy(deep=True)
        self.assertEqual(correct_tied_score_ranks(df), 4)
        self.assertEqual(df['总分年级排名_期中'].tolist(), [1, 13, 13, 17, 17, 26, 26, 28, 28])
        other = before.columns.drop('总分年级排名_期中')
        pd.testing.assert_frame_equal(df[other], before[other])
        self.assertEqual(correct_tied_score_ranks(df), 0)

    def test_legacy_columns_and_exams_are_corrected_independently(self):
        df = pd.DataFrame({'姓名': ['甲', '乙']})
        for prefix, label, ranks in [
            ('排名_', '九月_月考', [21, 20]),
            ('年级排名_', '期中', [30, 31]),
            ('总分_年级排名_', '期末', [41, 40]),
        ]:
            df[f'总分_{label}'] = [500, 500]
            df[f'{prefix}{label}'] = ranks
        df['排名_无分数'] = [9, 10]
        self.assertEqual(correct_tied_score_ranks(df), 3)
        self.assertEqual(df['排名_九月_月考'].tolist(), [20, 20])
        self.assertEqual(df['年级排名_期中'].tolist(), [30, 30])
        self.assertEqual(df['总分_年级排名_期末'].tolist(), [40, 40])
        self.assertEqual(df['排名_无分数'].tolist(), [9, 10])

    def test_absent_and_missing_values_do_not_supply_a_better_rank(self):
        df = pd.DataFrame({
            '总分_考试': [0, 0, None, None, 500, 500, 500, 500, 500.1],
            '排名_考试': [5, 6, 7, 8, 0, None, 20, 21, 22],
        })
        self.assertEqual(correct_tied_score_ranks(df), 1)
        expected = pd.Series([5, 6, 7, 8, 0, None, 20, 20, 22], name='排名_考试')
        pd.testing.assert_series_equal(df['排名_考试'], expected)


class TiedRankIntegrationTests(unittest.TestCase):
    setUp = fixtures.ProgressIntegrationTests.setUp
    tearDown = fixtures.ProgressIntegrationTests.tearDown
    assert_app_ok = fixtures.ProgressIntegrationTests.assert_app_ok

    def test_new_and_historical_excel_use_corrected_ranks_for_scoring(self):
        exams = []
        for ranks in ([13, 14], [14, 13]):
            rows = []
            for name, rank, group_rank in zip(['甲', '乙'], ranks, [201, 199]):
                df = fixtures.exam_dataframe(rank, group_rank=group_rank)
                df['姓名'] = name
                df['总分'] = 619
                rows.append(df)
            exams.append(pd.concat(rows, ignore_index=True))

        for historical in [False, True]:
            with self.subTest(historical=historical):
                app = AppTest.from_string(fixtures.PROCESS_SCRIPT, default_timeout=20)
                if historical:
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        for index, df in enumerate(exams, 1):
                            df.to_excel(writer, sheet_name=f'月考{index}', index=False)
                    app.session_state['history_file_content'] = output.getvalue()
                else:
                    files = []
                    for index, df in enumerate(exams, 1):
                        output = BytesIO()
                        df.to_excel(output, index=False)
                        files.append({'name': f'{index}.xlsx', 'content': output.getvalue(),
                                      'exam_num': index, 'exam_label': f'月考{index}'})
                    app.session_state['score_files'] = files
                app.run()
                self.assert_app_ok(app)
                all_data, scores, final = app.session_state['results'][:3]
                all_data = all_data.set_index('姓名').loc[['甲', '乙']]
                scores = scores.set_index('姓名').loc[['甲', '乙']]
                for index in [1, 2]:
                    self.assertEqual(all_data[f'总分年级排名_月考{index}'].tolist(), [13, 13])
                    self.assertEqual(all_data[f'总分集团排名_月考{index}'].tolist(), [201, 199])
                self.assertEqual(scores['连续进步次数'].tolist(), [1, 1])
                self.assertEqual(scores['区间进步得分'].tolist(), [0, 0])
                self.assertEqual(scores['年级排名加分'].tolist(), [120, 120])
                self.assertEqual(scores['A/B线奖励'].tolist(), [100, 100])
                self.assertEqual(scores['集团排名加分'].tolist(), [60, 90])
                self.assertEqual(final['总分年级排名_月考2'].tolist(), [13, 13])


if __name__ == '__main__':
    unittest.main()
