"""Staffing & class-size comparison across Burlingame elementary schools.

Source: CDE Student/Staff Ratio downloadable files (Census Day, first Wednesday in
October). Note: student/teacher ratio counts ALL teacher FTE at a school (including
specialists, intervention, and pull-out staff), so it runs LOWER than average
classroom size — it's a comparable proxy, not a literal class count.
"""
import pandas as pd
import altair as alt
import streamlit as st

from shared import data as D
from shared.theme import LINCOLN_COLOR, PEER_COLOR, GRAY, WARN, configure

ELEM_SPAN = 'GS_K6'
LATEST = 2025

# CA statewide students per teacher FTE, 2024-25 (CDE Certificated Staff Reports /
# DataQuest). All-grades; CDE does not publish an elementary-only cut. NOT class size.
CA_STATE_RATIO = 20.8


def _ordinal(n):
    n = int(n)
    suf = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suf}'


# ── Data ────────────────────────────────────────────────────────────────────

staff = D.load_staffing()


st.title(':material/groups: Burlingame Elementaries — Staffing & Class Size')
st.caption(
    'CDE Student/Staff Ratio data (Census Day enrollment + certificated teacher FTE). '
    'Lincoln is highlighted against the other Burlingame elementary schools. '
    '**Student/teacher ratio is a class-size *proxy*** — it includes all teacher FTE '
    '(specialists, intervention, pull-out), so it reads lower than a typical homeroom count.'
)

if staff.empty:
    st.warning('Staffing data not found. Run `python seda_app/fetch_staffing.py` to generate it.')
    st.stop()

elem = staff[staff['grade_span'] == ELEM_SPAN].copy()
elem['is_lincoln'] = elem['school_code'] == D.LINCOLN_SCHOOL_CODE
elem['School'] = elem['school_name'].str.replace(' Elementary', '', regex=False)

latest = elem[elem['school_year_end'] == LATEST].sort_values('stu_tch_ratio')
lincoln_now = latest[latest['is_lincoln']].iloc[0] if latest['is_lincoln'].any() else None


# ── Lincoln headline cards ────────────────────────────────────────────────────

if lincoln_now is not None:
    peers = latest[~latest['is_lincoln']]
    med_ratio = peers['stu_tch_ratio'].median()
    n = len(latest)
    rank = int((latest['stu_tch_ratio'] < lincoln_now['stu_tch_ratio']).sum()) + 1

    with st.container(border=True):
        st.markdown(f'### :material/school: Lincoln Elementary — {LATEST-1}-{str(LATEST)[2:]}')
        c1, c2, c3 = st.columns(3)
        c1.metric(
            ':material/groups: Students per teacher',
            f"{lincoln_now['stu_tch_ratio']:.1f}",
            delta=f"{lincoln_now['stu_tch_ratio'] - med_ratio:+.1f} vs peer median",
            delta_color='inverse',
            help=f"Peer (other elementaries) median is {med_ratio:.1f}. "
                 f"Lower = fewer students per teacher FTE.",
        )
        c2.metric(
            ':material/person: Enrollment',
            f"{int(lincoln_now['enrollment']):,}",
        )
        c3.metric(
            ':material/co_present: Teacher FTE',
            f"{lincoln_now['teacher_fte']:.1f}",
            help='Full-time-equivalent certificated teaching staff on Census Day.',
        )
        st.caption(
            f':material/leaderboard: Lincoln has the **{_ordinal(rank)}-smallest** '
            f'student/teacher ratio of the {n} Burlingame elementaries this year '
            f'(1st = smallest ratio = most teachers per student).'
        )

st.html('<div style="height:10px"></div>')


# ── Comparison tabs ────────────────────────────────────────────────────────────

tab_compare, tab_trend = st.tabs([
    ':material/bar_chart: Latest-Year Comparison',
    ':material/trending_up: Trends Over Time',
])


def lincoln_color(field):
    return alt.condition(
        alt.datum.is_lincoln, alt.value(LINCOLN_COLOR), alt.value(GRAY))


with tab_compare:
    metric = st.segmented_control(
        'Metric',
        ['Students per teacher', 'Enrollment', 'Teacher FTE'],
        default='Students per teacher', key='cmp_metric',
    )
    col_map = {
        'Students per teacher': ('stu_tch_ratio', '.1f', 'Students per teacher FTE'),
        'Enrollment': ('enrollment', ',.0f', 'Students enrolled'),
        'Teacher FTE': ('teacher_fte', '.1f', 'Teacher FTE'),
    }
    col, fmt, axis_title = col_map[metric]
    asc = metric == 'Students per teacher'  # smallest ratio first; biggest school first otherwise
    plot = latest.sort_values(col, ascending=asc)

    bars = alt.Chart(plot).mark_bar().encode(
        x=alt.X(f'{col}:Q', title=axis_title),
        y=alt.Y('School:N', sort=plot['School'].tolist(), title=None),
        color=lincoln_color(col),
        tooltip=[
            alt.Tooltip('school_name:N', title='School'),
            alt.Tooltip('stu_tch_ratio:Q', title='Students/teacher', format='.1f'),
            alt.Tooltip('enrollment:Q', title='Enrollment', format=','),
            alt.Tooltip('teacher_fte:Q', title='Teacher FTE', format='.1f'),
        ],
    )
    labels = alt.Chart(plot).mark_text(align='left', dx=4, color='#374151').encode(
        x=f'{col}:Q', y=alt.Y('School:N', sort=plot['School'].tolist()),
        text=alt.Text(f'{col}:Q', format=fmt),
    )
    layers = [bars, labels]
    if metric == 'Students per teacher':
        ref = pd.DataFrame({'x': [CA_STATE_RATIO]})
        layers.append(alt.Chart(ref).mark_rule(color=WARN, strokeDash=[5, 4], strokeWidth=2).encode(
            x='x:Q', tooltip=alt.value(f'CA state average: {CA_STATE_RATIO}')))
        layers.append(alt.Chart(ref).mark_text(
            color=WARN, align='center', baseline='bottom', dy=-4, fontSize=10,
            text=f'CA avg {CA_STATE_RATIO}').encode(
            x='x:Q', y=alt.value(0)))
    chart = alt.layer(*layers).properties(
        width=620, height=300,
        title=alt.TitleParams(f'{metric} by school — {LATEST-1}-{str(LATEST)[2:]}', dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 40},
    )
    st.altair_chart(configure(chart), width='stretch')

    with st.expander(':material/insights: Analysis', expanded=True):
        st.markdown(
            f'- **Blue = Lincoln.** Lower student/teacher ratio means more teaching staff '
            f'relative to enrollment.\n'
            f'- **Orange dashed line = California state average ({CA_STATE_RATIO} students per '
            f'teacher FTE, 2024-25).** CA runs among the highest (least favorable) ratios in the '
            f'US; bars to the left of the line beat the state norm.\n'
            f'- Ratios here ({latest["stu_tch_ratio"].min():.0f}–{latest["stu_tch_ratio"].max():.0f}) '
            f'sit below typical homeroom class sizes because every teacher FTE — including '
            f'specialists and intervention staff — is counted.\n'
            f'- Enrollment differences are large (smallest to largest school is roughly '
            f'{int(latest["enrollment"].min())}–{int(latest["enrollment"].max())} students), '
            f'which drives much of the staffing variation.'
        )


with tab_trend:
    metric_t = st.segmented_control(
        'Metric',
        ['Students per teacher', 'Enrollment', 'Teacher FTE'],
        default='Students per teacher', key='trend_metric',
    )
    col_t, fmt_t, axis_t = col_map[metric_t]

    base = alt.Chart(elem).encode(
        x=alt.X('school_year_end:O', title='School year (spring)'),
        y=alt.Y(f'{col_t}:Q', title=axis_t, scale=alt.Scale(zero=False)),
        detail='School:N',
        tooltip=[
            alt.Tooltip('school_name:N', title='School'),
            alt.Tooltip('school_year_end:O', title='Year'),
            alt.Tooltip(f'{col_t}:Q', title=metric_t, format=fmt_t),
        ],
    )
    # Lincoln drawn bold/blue, peers thin/gray via color+size conditions.
    lines = base.mark_line().encode(
        color=alt.Color('is_lincoln:N',
            scale=alt.Scale(domain=[True, False], range=[LINCOLN_COLOR, GRAY]),
            legend=None),
        size=alt.condition(alt.datum.is_lincoln, alt.value(3), alt.value(1.5)),
        opacity=alt.condition(alt.datum.is_lincoln, alt.value(1.0), alt.value(0.55)),
    )
    points = base.mark_point(filled=True, size=55).encode(
        color=alt.Color('is_lincoln:N',
            scale=alt.Scale(domain=[True, False], range=[LINCOLN_COLOR, GRAY]),
            legend=None),
        opacity=alt.condition(alt.datum.is_lincoln, alt.value(1.0), alt.value(0.55)),
    )
    # Text labels at the last year so peers are identifiable without a legend.
    last_pts = elem[elem['school_year_end'] == elem['school_year_end'].max()]
    labels_t = alt.Chart(last_pts).mark_text(align='left', dx=6, fontSize=10).encode(
        x=alt.X('school_year_end:O'),
        y=alt.Y(f'{col_t}:Q'),
        text='School:N',
        color=alt.Color('is_lincoln:N',
            scale=alt.Scale(domain=[True, False], range=[LINCOLN_COLOR, GRAY]), legend=None),
    )
    t_layers = [lines, points, labels_t]
    if metric_t == 'Students per teacher':
        ref = pd.DataFrame({'y': [CA_STATE_RATIO]})
        t_layers.append(alt.Chart(ref).mark_rule(color=WARN, strokeDash=[5, 4], strokeWidth=2).encode(
            y='y:Q', tooltip=alt.value(f'CA state average: {CA_STATE_RATIO}')))
        t_layers.append(alt.Chart(ref).mark_text(
            color=WARN, align='left', baseline='bottom', dx=5, dy=-3, fontSize=10,
            text=f'CA avg {CA_STATE_RATIO}').encode(
            x=alt.value(0), y='y:Q'))
    chart_t = alt.layer(*t_layers).properties(
        width=720, height=380,
        title=alt.TitleParams(f'{metric_t}, {elem["school_year_end"].min()}–{LATEST}', dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 70},
    )
    st.altair_chart(configure(chart_t), width='stretch')

    with st.expander(':material/insights: Analysis', expanded=True):
        lin_series = elem[elem['is_lincoln']].sort_values('school_year_end')
        if len(lin_series) >= 2:
            first, last = lin_series.iloc[0], lin_series.iloc[-1]
            d_ratio = last['stu_tch_ratio'] - first['stu_tch_ratio']
            st.markdown(
                f"- **Lincoln (blue):** student/teacher ratio went from "
                f"{first['stu_tch_ratio']:.1f} in {int(first['school_year_end'])} to "
                f"{last['stu_tch_ratio']:.1f} in {int(last['school_year_end'])} "
                f"({d_ratio:+.1f}).\n"
                f"- Ratios shift with both staffing decisions and enrollment — a rising ratio "
                f"can mean fewer teachers OR more students. Compare against the Enrollment and "
                f"Teacher FTE tabs to see which.\n"
                f"- This is Census-Day staffing, not a curriculum or class-schedule measure."
            )
