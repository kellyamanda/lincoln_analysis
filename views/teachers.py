"""Teacher experience across the Burlingame elementary schools.

Source: CDE Staff Experience files (Census Day). Shows average years of teaching
experience and the share of "inexperienced" teachers (<=2 years total). Research
note: teacher *effectiveness* is what matters for students; experience is only a
rough proxy — it helps most in the first few years and then largely plateaus, so
read this as a stability signal, not a quality ranking.
"""
import pandas as pd
import altair as alt
import streamlit as st

from shared import data as D
from shared.theme import LINCOLN_COLOR, GRAY, WARN, configure

LATEST = 2025

# CA statewide average total years of teacher experience, 2024-25 (CDE Staff
# Experience file, Staff Type = TCH, all grade spans). Context, not a target.
CA_AVG_EXP = 14.0


def _ordinal(n):
    n = int(n)
    suf = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suf}'


teach = D.load_teachers()

st.title(':material/co_present: Teacher Experience — Burlingame Elementaries')
st.caption(
    'CDE Staff Experience data (certificated teachers, Census Day). **Average years of '
    'experience** and the **share of novice teachers** (≤2 years total experience). '
    'Experience is a rough proxy for stability, not quality — its biggest effect is in a '
    "teacher's first few years, then it largely plateaus."
)

if teach.empty:
    st.warning('Teacher data not found. Run `python seda_app/fetch_teachers.py`.')
    st.stop()

teach = teach.copy()
teach['is_lincoln'] = teach['school_code'] == D.LINCOLN_SCHOOL_CODE
teach['School'] = teach['school_name']

latest = teach[teach['school_year_end'] == LATEST].sort_values('avg_years_exp', ascending=False)
lincoln_now = latest[latest['is_lincoln']]
lincoln_now = lincoln_now.iloc[0] if not lincoln_now.empty else None


# ── Lincoln headline card ─────────────────────────────────────────────────────

if lincoln_now is not None:
    peers = latest[~latest['is_lincoln']]
    med_exp = peers['avg_years_exp'].median()

    with st.container(border=True):
        st.markdown(f'### :material/school: Lincoln Elementary — {LATEST-1}-{str(LATEST)[2:]}')
        c1, c2, c3 = st.columns(3)
        c1.metric(
            ':material/co_present: Avg years of experience',
            f"{lincoln_now['avg_years_exp']:.1f}",
            delta=f"{lincoln_now['avg_years_exp'] - med_exp:+.1f} vs peer median",
            delta_color='off',
            help=f"Peer (other elementaries) median is {med_exp:.1f} yrs; CA average is "
                 f"{CA_AVG_EXP:.0f} yrs. More experience isn't strictly better — shown for context.",
        )
        c2.metric(
            ':material/fiber_new: Novice teachers (≤2 yrs)',
            f"{lincoln_now['pct_inexperienced']:.0f}%",
            help=f"{int(lincoln_now['inexperienced'])} of {int(lincoln_now['teachers'])} teachers have "
                 f"≤2 years of experience. A high novice share can signal turnover/instability.",
        )
        c3.metric(
            ':material/groups: Teachers',
            f"{int(lincoln_now['teachers'])}",
        )

st.html('<div style="height:10px"></div>')


tab_compare, tab_trend = st.tabs([
    ':material/bar_chart: Comparison',
    ':material/trending_up: Trend Over Time',
])


with tab_compare:
    metric = st.segmented_control(
        'Metric', ['Avg years experience', '% novice teachers'],
        default='Avg years experience', key='te_metric')
    col, fmt, axis_title, show_ca = (
        ('avg_years_exp', '.1f', 'Average years of experience', True)
        if metric == 'Avg years experience'
        else ('pct_inexperienced', '.0f', '% novice teachers (≤2 yrs)', False))
    plot = latest.sort_values(col, ascending=False)

    bars = alt.Chart(plot).mark_bar().encode(
        x=alt.X(f'{col}:Q', title=axis_title),
        y=alt.Y('School:N', sort=plot['School'].tolist(), title=None),
        color=alt.condition(alt.datum.is_lincoln, alt.value(LINCOLN_COLOR), alt.value(GRAY)),
        tooltip=[alt.Tooltip('School:N'),
                 alt.Tooltip('avg_years_exp:Q', title='Avg years', format='.1f'),
                 alt.Tooltip('pct_inexperienced:Q', title='% novice', format='.0f'),
                 alt.Tooltip('teachers:Q', title='Teachers', format='.0f')],
    )
    labels = alt.Chart(plot).mark_text(align='left', dx=4, color='#374151').encode(
        x=f'{col}:Q', y=alt.Y('School:N', sort=plot['School'].tolist()),
        text=alt.Text(f'{col}:Q', format=fmt),
    )
    layers = [bars, labels]
    if show_ca:
        ref = pd.DataFrame({'x': [CA_AVG_EXP]})
        layers.append(alt.Chart(ref).mark_rule(color=WARN, strokeDash=[5, 4], strokeWidth=2).encode(
            x='x:Q', tooltip=alt.value(f'CA average: {CA_AVG_EXP} yrs')))
        layers.append(alt.Chart(ref).mark_text(color=WARN, align='center', baseline='bottom',
            dy=-4, fontSize=10, fontWeight='bold', text=f'CA avg {CA_AVG_EXP:.0f} yrs').encode(
            x='x:Q', y=alt.value(0)))
    chart = alt.layer(*layers).properties(
        width=620, height=300,
        title=alt.TitleParams(f'{metric} by school — {LATEST-1}-{str(LATEST)[2:]}',
                              anchor='start', limit=0),
        padding={'top': 34, 'bottom': 10, 'left': 5, 'right': 40},
    )
    st.altair_chart(configure(chart), width='stretch')

    with st.expander(':material/insights: Analysis', expanded=True):
        st.markdown(
            f'- **Blue = Lincoln.** Its teachers average '
            f'{lincoln_now["avg_years_exp"]:.1f} years of experience '
            f'(orange line = CA average, {CA_AVG_EXP:.0f} yrs).\n'
            f'- **Novice share is the more actionable number:** a school with many ≤2-year teachers '
            f'may be experiencing turnover, which research links to lower achievement — '
            f'independent of any individual teacher\'s skill.\n'
            f'- Beyond the first few years, more experience shows **diminishing returns**, so a '
            f'higher average is not automatically "better." This counts years of service, not '
            f'teaching quality (which the data cannot measure).'
        )


with tab_trend:
    metric_t = st.segmented_control(
        'Metric', ['Avg years experience', '% novice teachers'],
        default='Avg years experience', key='te_trend_metric')
    col_t, fmt_t, axis_t = (
        ('avg_years_exp', '.1f', 'Average years of experience')
        if metric_t == 'Avg years experience'
        else ('pct_inexperienced', '.0f', '% novice teachers (≤2 yrs)'))

    plot = teach.dropna(subset=[col_t])
    base = alt.Chart(plot).encode(
        x=alt.X('school_year_end:O', title='School year (spring)'),
        y=alt.Y(f'{col_t}:Q', title=axis_t, scale=alt.Scale(zero=False)),
        detail='School:N',
        tooltip=[alt.Tooltip('School:N'), alt.Tooltip('school_year_end:O', title='Year'),
                 alt.Tooltip(f'{col_t}:Q', title=metric_t, format=fmt_t)],
    )
    lines = base.mark_line().encode(
        color=alt.Color('is_lincoln:N', scale=alt.Scale(domain=[True, False],
                        range=[LINCOLN_COLOR, GRAY]), legend=None),
        size=alt.condition(alt.datum.is_lincoln, alt.value(3), alt.value(1.5)),
        opacity=alt.condition(alt.datum.is_lincoln, alt.value(1.0), alt.value(0.5)),
    )
    points = base.mark_point(filled=True, size=55).encode(
        color=alt.Color('is_lincoln:N', scale=alt.Scale(domain=[True, False],
                        range=[LINCOLN_COLOR, GRAY]), legend=None),
        opacity=alt.condition(alt.datum.is_lincoln, alt.value(1.0), alt.value(0.5)),
    )
    last = plot[plot['school_year_end'] == plot['school_year_end'].max()]
    labels = alt.Chart(last).mark_text(align='left', dx=6, fontSize=10).encode(
        x='school_year_end:O', y=f'{col_t}:Q', text='School:N',
        color=alt.Color('is_lincoln:N', scale=alt.Scale(domain=[True, False],
                        range=[LINCOLN_COLOR, GRAY]), legend=None),
    )
    chart_t = (lines + points + labels).properties(
        width=720, height=380,
        title=alt.TitleParams(f'{metric_t}, {plot["school_year_end"].min()}–{LATEST}',
                              anchor='start', limit=0),
        padding={'top': 34, 'bottom': 10, 'left': 5, 'right': 80},
    )
    st.altair_chart(configure(chart_t), width='stretch')
