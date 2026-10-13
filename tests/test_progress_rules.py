import unittest

from utils.progress_rules import (
    TIE_ENABLED, TIE_RANK_LIMIT, calculate_progress_chain,
    get_tie_progress_rule, is_progress_step, is_current_progress,
)
from utils.rank_history import get_exam_label, get_grade_rank_columns, get_rank_history


class ProgressRuleTests(unittest.TestCase):
    def test_default_rule_and_boundaries(self):
        self.assertEqual(get_tie_progress_rule({}), (True, 100))
        for before, now, expected in [
            (120, 110, True), (100, 100, True), (99, 99, True),
            (101, 101, False), (99, 100, False), (0, 0, False),
            (0, 50, False), (50, 0, False), (float('nan'), 50, False),
        ]:
            with self.subTest(before=before, now=now):
                self.assertEqual(is_progress_step(before, now, {}), expected)

    def test_disabled_and_custom_limit(self):
        self.assertFalse(is_progress_step(1, 1, {TIE_ENABLED: False}))
        self.assertTrue(is_progress_step(51, 50, {TIE_ENABLED: False}))
        self.assertTrue(is_progress_step(50, 50, {TIE_RANK_LIMIT: 50}))
        self.assertFalse(is_progress_step(51, 51, {TIE_RANK_LIMIT: 50}))

    def test_chains_increment_and_restart(self):
        for ranks, expected in [
            ([120, 100, 100, 90], 3), ([100, 100, 100], 2),
            ([120, 110, 110, 100], 1), ([100, 100, 101], 0),
            ([120, 100, 101, 100, 100], 2), ([100], 0), ([], 0),
            ([120, 0, 100, 100], 2), ([120, 100, 100, 0], 2),
        ]:
            with self.subTest(ranks=ranks):
                count, details = calculate_progress_chain(ranks, {})
                self.assertEqual(count, expected)
                if details:
                    self.assertEqual(details[-1]['连续进步次数'], expected)

    def test_disabled_rule_and_legacy_absence_behavior(self):
        self.assertEqual(calculate_progress_chain([120, 100, 100, 90], {TIE_ENABLED: False})[0], 1)
        self.assertEqual(calculate_progress_chain([120, 100, 0, 100], {}, skip_absent=False)[0], 0)
        self.assertTrue(is_current_progress([120, 100, 100], {}))
        self.assertFalse(is_current_progress([120, 100, 100, 0], {}))
        self.assertFalse(is_current_progress([100], {}))
        self.assertFalse(is_current_progress([120, 110, 110], {}))
        self.assertFalse(is_current_progress([100, 100], {TIE_ENABLED: False}))

    def test_grade_columns_exclude_subject_and_group_rankings(self):
        columns = ['姓名', '排名_甲', '年级排名_乙', '总分年级排名_丙',
                   '总分_年级排名_丁', '语文年级排名_甲', '总分集团排名_甲', '集团排名_甲']
        self.assertEqual(get_grade_rank_columns(columns), columns[1:5])

    def test_labels_and_absence_use_same_history(self):
        columns = ['总分年级排名_九月_月考', '总分年级排名_期中', '总分年级排名_期末']
        self.assertEqual(get_exam_label(columns[0]), '九月_月考')
        row = {columns[0]: 120, columns[1]: 100, columns[2]: 100,
               '数学_九月_月考': 100, '数学_期中': 0, '数学_期末': 100}
        ranks = get_rank_history(row, columns, ['数学'])
        self.assertEqual(ranks, [120, 0, 100])
        self.assertEqual(calculate_progress_chain(ranks, {})[0], 1)


if __name__ == '__main__':
    unittest.main()
