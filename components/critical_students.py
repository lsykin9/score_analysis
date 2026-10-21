"""临界生页面：宽范围观察、历史线差和解释性标记。"""
import plotly.express as px
import streamlit as st


def render_critical_students(analysis):
    st.header('🎓 临界生')
    st.caption('观察范围：总分A线差在－20至＋15分之间，包含端点及恰好压线。'
               '使用物理类六科总分及六科A线之和，不设置上下10分的硬性核心层。')
    st.caption('单次离开区间仍延续观察；连续2次有效考试处于区间同一侧后，'
               '线上转常规跟踪，线下转基础提升支持。缺考或无线不作升降判断。')
    summary = analysis['summary']
    if summary.empty:
        st.info('请上传包含六科成绩和物理类A线的考试数据。')
        return
    current = summary['观察名单']
    inside = summary['当期区间内']
    pending = summary['本次A线差'].isna()
    columns = st.columns(4)
    columns[0].metric('观察名单人数', int(current.sum()))
    columns[1].metric('本次区间内', int(inside.sum()))
    columns[2].metric('区间外延续观察', int((current & ~inside & ~pending).sum()))
    columns[3].metric('在册待核实', int((current & pending).sum()))

    references = analysis['references']
    missing = references[references['A线'].isna()]
    if not missing.empty:
        st.info('以下考试缺少有效A线，不参与临界判断：' + '、'.join(missing['考试']) + '。不借用其他场次分数线。')
    if pending.all():
        st.warning('本次没有可判定的A线差；历史在册学生仅保留为待核实，不使用旧成绩代替本次。')
    elif pending.any():
        st.info(f'本次共{int(pending.sum())}人资料待核实，其中{int((current & pending).sum())}人在历史观察名单中。')
    st.caption('关注标记是对最近3次有效考试的描述，不是上线概率或测量误差估计。'
               '短期小幅变化需结合批改、试卷和课堂表现核实。临界生跟踪不改变评分。')

    left, right = st.columns(2)
    scope = left.selectbox('名单范围', ['当前观察名单', '本次区间内', '全部学生'], key='critical_scope')
    position = right.selectbox('线上线下', ['全部', '线上（含压线）', '线下', '本次待核实'], key='critical_position')
    options = sorted({tag for text in summary['关注标记'] for tag in text.split('、')})
    selected_tags = st.multiselect('按关注标记筛选（任选其一）', options, key='critical_tags')
    display = summary.copy()
    if scope == '当前观察名单':
        display = display[display['观察名单']]
    elif scope == '本次区间内':
        display = display[display['当期区间内']]
    if position != '全部':
        display = display[display['线上线下'] == position]
    if selected_tags:
        selected = set(selected_tags)
        display = display[display['关注标记'].map(lambda text: bool(selected.intersection(text.split('、'))))]
    columns = ['姓名', '本次总分', '本次A线', '本次A线差', '线上线下', '跟踪状态', '关注标记',
               '最近有效场数', '最近区间内次数', '最近跨线次数', '最近线差变化', '最近线差极差',
               '持续偏科等级', '持续薄弱科目', '偏科改善科目', '本次资料说明']
    formats = {name: st.column_config.NumberColumn(format='%.1f') for name in
               ('本次总分', '本次A线', '本次A线差', '最近线差变化', '最近线差极差')}
    st.subheader(f'学生名单（{len(display)}人）')
    if display.empty:
        st.info('当前筛选条件下没有学生，可切换到“全部学生”查看历史跟踪记录。')
    st.dataframe(display[columns], column_config=formats, use_container_width=True, hide_index=True)

    with st.expander('查看区间外及转出后的跟踪'):
        st.dataframe(summary.loc[~current, columns], column_config=formats,
                     use_container_width=True, hide_index=True)

    st.subheader('个人线差历史')
    students = display['姓名'].tolist() if not display.empty else summary['姓名'].tolist()
    student = st.selectbox('选择临界生跟踪学生', students, key='critical_student')
    history = analysis['history']
    history = history[history['姓名'] == student].copy()
    details = summary[summary['姓名'] == student].iloc[0]
    st.write(f"**跟踪状态**：{details['跟踪状态']}　**关注标记**：{details['关注标记']}")
    st.caption('最近有效考试：' + (details['最近有效考试'] or '暂无') + '。缺失场次在图中保留断点。')
    if history['资料有效'].any():
        figure = px.line(history, x='考试', y='A线差', category_orders={'考试': history['考试'].tolist()},
                         hover_data=['六科总分', '总分A线'])
        figure.update_traces(mode='lines+markers', connectgaps=False)
        figure.add_hrect(y0=-20, y1=15, fillcolor='#f6bd16', opacity=0.12, line_width=0)
        figure.add_hline(y=0, line_dash='dash', annotation_text='A线')
        figure.add_hline(y=-20, line_dash='dot', annotation_text='线下20分')
        figure.add_hline(y=15, line_dash='dot', annotation_text='线上15分')
        st.plotly_chart(figure, use_container_width=True)
    st.dataframe(history[['考试', '六科总分', '总分A线', 'A线差', '当期区间内',
                          '观察名单', '跟踪状态', '资料说明']],
                 column_config={'A线差': st.column_config.NumberColumn(format='%.1f')},
                 use_container_width=True, hide_index=True)
    with st.expander('查看判断规则和分数线'):
        st.dataframe(analysis['rules'], use_container_width=True, hide_index=True)
        st.dataframe(references, use_container_width=True, hide_index=True)
