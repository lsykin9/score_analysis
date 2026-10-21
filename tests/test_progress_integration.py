"""用真实 Excel 和 Streamlit AppTest 核对评分、设置、持久化及导出。"""
import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

# 在切换到临时工作目录前加载评分模块，隔离测试文件及配置。
from score_analysis_v0_1 import read_config
from utils.progress_rules import TIE_ENABLED, TIE_RANK_LIMIT


ROOT = Path(__file__).resolve().parents[1]
SUBJECTS = ['语文', '数学', '英语', '物理', '化学', '生物']
PROCESS_SCRIPT = '''
import streamlit as st
from config.session_state import initialize_session_state
from utils.data_processor import process_data
initialize_session_state()
st.session_state.config_params.update(st.session_state.get('test_rule', {}))
st.session_state['results'] = process_data()
'''
SIDEBAR_SCRIPT = '''
import streamlit as st
from config.session_state import initialize_session_state
from components.sidebar import render_sidebar, auto_load_config
initialize_session_state()
auto_load_config()
render_sidebar()
'''


def exam_dataframe(rank, column_count=22, absent_subject=None, group_rank=50):
    if column_count == 22:
        data = {'姓名': ['测试学生'], '总分': [650],
                '总分年级排名': [rank], '总分集团排名': [group_rank]}
        for subject in SUBJECTS:
            data[subject] = [0 if subject == absent_subject else
                             (120 if subject in SUBJECTS[:3] else 80)]
            data[subject + '年级排名'] = [rank]
            data[subject + '集团排名'] = [group_rank]
    else:
        data = {'姓名': ['测试学生'], '排名': [rank]}
        if column_count >= 3:
            data['总分'] = [650]
        if column_count == 9:
            for subject in SUBJECTS:
                data[subject] = [0 if subject == absent_subject else
                                 (120 if subject in SUBJECTS[:3] else 80)]
    return pd.DataFrame(data)


def upload_files(ranks, column_count=22, absent_exam=None, group_rank=50):
    files = []
    for index, rank in enumerate(ranks, 1):
        output = BytesIO()
        exam_dataframe(rank, column_count, '数学' if index == absent_exam else None,
                       group_rank[index - 1] if isinstance(group_rank, list) else group_rank).to_excel(output, index=False)
        files.append({'name': f'考试{index}.xlsx', 'content': output.getvalue(),
                      'exam_num': index, 'exam_label': f'月考{index}'})
    return files


class ProgressIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path.cwd()
        self.temp = tempfile.TemporaryDirectory()
        os.chdir(self.temp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.temp.cleanup()

    def assert_app_ok(self, app):
        self.assertEqual([e.message for e in app.exception], [])

    def process(self, ranks, column_count=22, rule=None, absent_exam=None, group_rank=50):
        app = AppTest.from_string(PROCESS_SCRIPT, default_timeout=20)
        app.session_state['score_files'] = upload_files(ranks, column_count, absent_exam, group_rank)
        app.session_state['test_rule'] = rule or {}
        app.run()
        self.assert_app_ok(app)
        return app.session_state['results']

    def test_rule_applies_to_all_four_upload_formats(self):
        for columns in [2, 3, 9, 22]:
            with self.subTest(columns=columns):
                result = self.process([120, 100, 100, 90], columns)
                row = result[1].iloc[0]
                self.assertEqual(row['连续进步次数'], 3)
                self.assertEqual(row['连续进步加分'], 90)
                self.assertAlmostEqual(row['区间进步得分'], 14)

    def test_ties_change_chain_reward_but_not_progress_score(self):
        enabled = self.process([120, 100, 100])[1].iloc[0]
        disabled = self.process([120, 100, 100], rule={TIE_ENABLED: False})[1].iloc[0]
        self.assertEqual(enabled['连续进步次数'], 2)
        self.assertEqual(enabled['连续进步加分'], 50)
        self.assertEqual(disabled['连续进步次数'], 0)
        self.assertEqual(disabled['连续进步加分'], 0)
        self.assertEqual(enabled['区间进步得分'], 0)
        self.assertEqual(disabled['区间进步得分'], 0)
        self.assertEqual(enabled['总得分'] - disabled['总得分'], 50)

    def test_boundary_and_grade_scope_not_group_scope(self):
        for rank, limit, group_rank, expected in [
            (100, 100, 500, 1), (101, 100, 1, 0),
            (50, 50, 500, 1), (51, 50, 1, 0),
        ]:
            with self.subTest(rank=rank, limit=limit):
                row = self.process([rank, rank], rule={TIE_RANK_LIMIT: limit},
                                   group_rank=group_rank)[1].iloc[0]
                self.assertEqual(row['连续进步次数'], expected)

    def test_absences_do_not_count_as_ties(self):
        row = self.process([120, 100, 100], absent_exam=2)[1].iloc[0]
        self.assertEqual(row['连续进步次数'], 1)
        latest_absent = self.process([120, 100, 100, 90], absent_exam=4)[1].iloc[0]
        self.assertEqual(latest_absent['连续进步次数'], 2)
        self.assertEqual(latest_absent['连续进步加分'], 50)
        self.assertEqual(latest_absent['区间进步得分'], 0)
        self.assertEqual(latest_absent['总得分'], 50)

    def test_historical_multisheet_and_single_sheet(self):
        for multisheet in [True, False]:
            with self.subTest(multisheet=multisheet):
                output = BytesIO()
                dfs = []
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for index, rank in enumerate([120, 100, 100], 1):
                        df = exam_dataframe(rank)
                        label = f'月考{index}'
                        if multisheet:
                            df.to_excel(writer, sheet_name=label, index=False)
                        df = df.rename(columns={c: f'{c}_{label}' for c in df.columns if c != '姓名'})
                        dfs.append(df)
                    complete = dfs[0]
                    for df in dfs[1:]:
                        complete = complete.merge(df, on='姓名')
                    complete.to_excel(writer, sheet_name='完整总表', index=False)
                app = AppTest.from_string(PROCESS_SCRIPT, default_timeout=20)
                app.session_state['history_file_content'] = output.getvalue()
                app.run()
                self.assert_app_ok(app)
                row = app.session_state['results'][1].iloc[0]
                self.assertEqual(row['连续进步次数'], 2)
                self.assertEqual(row['连续进步加分'], 50)

    def test_widgets_callbacks_and_saved_config(self):
        app = AppTest.from_string(SIDEBAR_SCRIPT, default_timeout=20).run()
        self.assert_app_ok(app)
        self.assertTrue(app.checkbox(key='tie_progress_enabled').value)
        self.assertEqual(app.number_input(key='tie_progress_grade_rank_limit').value, 100)
        app.number_input(key='tie_progress_grade_rank_limit').set_value(50).run()
        self.assertEqual(app.session_state['config_params'][TIE_RANK_LIMIT], 50)
        app.checkbox(key='tie_progress_enabled').uncheck().run()
        self.assertFalse(app.session_state['config_params'][TIE_ENABLED])
        self.assertTrue(app.number_input(key='tie_progress_grade_rank_limit').disabled)
        next(b for b in app.button if b.label == '💾 保存配置').click().run()
        self.assert_app_ok(app)
        saved = json.loads(Path('config/user_settings.json').read_text())
        self.assertFalse(saved['config_params'][TIE_ENABLED])
        self.assertEqual(saved['config_params'][TIE_RANK_LIMIT], 50)
        restored = AppTest.from_string(SIDEBAR_SCRIPT, default_timeout=20).run()
        self.assert_app_ok(restored)
        self.assertFalse(restored.checkbox(key='tie_progress_enabled').value)
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 50)
        # 控件值被改变后，手动加载应恢复已保存值，而非被旧控件覆盖。
        restored.checkbox(key='tie_progress_enabled').check().run()
        restored.number_input(key='tie_progress_grade_rank_limit').set_value(30).run()
        next(b for b in restored.button if b.label == '📂 加载配置').click().run()
        self.assert_app_ok(restored)
        self.assertFalse(restored.checkbox(key='tie_progress_enabled').value)
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 50)
        next(b for b in restored.button if b.label == '🔄 恢复默认').click().run()
        self.assert_app_ok(restored)
        self.assertTrue(restored.checkbox(key='tie_progress_enabled').value)
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 100)

    def test_legacy_saved_config_and_core_config_are_upgraded(self):
        app = AppTest.from_string(SIDEBAR_SCRIPT, default_timeout=20).run()
        next(b for b in app.button if b.label == '💾 保存配置').click().run()
        file = Path('config/user_settings.json')
        saved = json.loads(file.read_text())
        saved['config_params'].pop(TIE_ENABLED)
        saved['config_params'].pop(TIE_RANK_LIMIT)
        file.write_text(json.dumps(saved))
        restored = AppTest.from_string(SIDEBAR_SCRIPT, default_timeout=20).run()
        self.assert_app_ok(restored)
        self.assertTrue(restored.checkbox(key='tie_progress_enabled').value)
        self.assertEqual(restored.number_input(key='tie_progress_grade_rank_limit').value, 100)
        cfg = read_config(config_dict={})
        self.assertTrue(cfg[TIE_ENABLED])
        self.assertEqual(cfg[TIE_RANK_LIMIT], 100)
        cfg = read_config(config_dict={TIE_ENABLED: False, TIE_RANK_LIMIT: 50})
        self.assertFalse(cfg[TIE_ENABLED])
        self.assertEqual(cfg[TIE_RANK_LIMIT], 50)

    def test_old_formats_show_consistent_grade_charts_and_details(self):
        for columns in [2, 3, 9]:
            with self.subTest(columns=columns):
                app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30)
                app.session_state['score_files'] = upload_files([120, 100, 100], columns)
                app.session_state['analysis_started'] = True
                app.run()
                self.assert_app_ok(app)
                charts = [json.loads(chart.proto.spec) for chart in app.get('plotly_chart')]
                lines = [trace for chart in charts for trace in chart['data']
                         if trace.get('mode', '').startswith('lines+markers')]
                self.assertEqual(len(lines), 2)
                for trace in lines:
                    self.assertEqual(trace['y'], [120, 100, 100])
                    self.assertEqual(trace['x'], ['月考1', '月考2', '月考3'])
                details = [table.value for table in app.table if '判定' in table.value.columns]
                self.assertEqual(details[0].iloc[-1]['连续进步次数'], 2)

    def test_latest_absence_keeps_chain_but_not_current_progress_count(self):
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30)
        app.session_state['score_files'] = upload_files([120, 100, 100, 90], absent_exam=4)
        app.session_state['analysis_started'] = True
        app.run()
        self.assert_app_ok(app)
        self.assertEqual(app.session_state['df_score'].iloc[0]['连续进步次数'], 2)
        self.assertEqual(next(m for m in app.metric if m.label == '进步人数').value, '0')
        charts = [json.loads(chart.proto.spec) for chart in app.get('plotly_chart')]
        grade_lines = [trace for chart in charts for trace in chart['data']
                       if trace.get('mode', '').startswith('lines+markers')]
        for trace in grade_lines:
            self.assertEqual(trace['y'], [120, 100, 100, None])

    def test_all_tabs_details_locking_and_real_excel_exports(self):
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30)
        app.session_state['score_files'] = upload_files([120, 100, 100])
        app.session_state['analysis_started'] = True
        downloads = {}
        original = st.download_button

        def capture_download(*args, **kwargs):
            downloads[kwargs['file_name']] = kwargs['data']
            return original(*args, **kwargs)

        with patch('streamlit.download_button', side_effect=capture_download):
            app.run()
        self.assert_app_ok(app)
        self.assertEqual(len(app.tabs), 7)
        self.assertEqual(next(m for m in app.metric if m.label == '进步人数').value, '1')
        self.assertTrue(app.checkbox(key='tie_progress_enabled').disabled)
        self.assertTrue(app.number_input(key='tie_progress_grade_rank_limit').disabled)
        for label in ['📂 加载配置', '🔄 恢复默认']:
            self.assertTrue(next(b for b in app.button if b.label == label).disabled)
        details = [t.value for t in app.table if '判定' in t.value.columns]
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0].iloc[-1]['连续进步次数'], 2)
        self.assertIn('持平', details[0].iloc[-1]['判定'])
        self.assertEqual(app.session_state['df_score'].iloc[0]['连续进步次数'], 2)
        exported = pd.read_excel(BytesIO(downloads['完整分析结果.xlsx']), sheet_name=None)
        self.assertEqual(exported['得分明细'].iloc[0]['连续进步次数'], 2)
        self.assertEqual(exported['得分明细'].iloc[0]['连续进步加分'], 50)
        self.assertEqual(exported['得分明细'].iloc[0]['区间进步得分'], 0)
        self.assertEqual(exported['完整结果'].iloc[0]['总得分'], app.session_state['df_score'].iloc[0]['总得分'])
        rules = exported['连续进步规则'].set_index('项目')['设置']
        self.assertEqual(rules['限定年级排名内持平计入连续进步'], '开启')
        self.assertEqual(rules['年级排名上限（含）'], 100)
        # 原始总表导出后，再导入应保持同样的连续次数和总分。
        reimported = AppTest.from_string(PROCESS_SCRIPT, default_timeout=20)
        reimported.session_state['history_file_content'] = downloads['成绩总表.xlsx']
        reimported.run()
        self.assert_app_ok(reimported)
        row = reimported.session_state['results'][1].iloc[0]
        self.assertEqual(row['连续进步次数'], 2)
        self.assertEqual(row['总得分'], exported['得分明细'].iloc[0]['总得分'])


if __name__ == '__main__':
    unittest.main()
