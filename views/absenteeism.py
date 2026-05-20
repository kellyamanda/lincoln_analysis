"""Chronic absenteeism — Lincoln vs the Burlingame elementaries, over time and by subgroup.

Source: CDE Chronic Absenteeism downloadable files. A student is "chronically absent"
if absent (excused or unexcused) for >=10% of enrolled days. 2019-20 is not published;
2020-21 reflects distance learning and is not comparable to in-person years.
"""
import pandas as pd
import altair as alt
import streamlit as st

from shared import data as D
from shared.theme import LINCOLN_COLOR, GRAY, WARN, configure

LATEST = 2025
COVID_YEAR = 2021  # distance-learning year — flagged, not comparable


def _ordinal(n):
    n = int(n)
    suf = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suf}'


abs_df = D.load_absenteeism()

st.title(':material/event_busy: Chronic Absenteeism — Burlingame Elementaries')
st.caption(
    'CDE chronic absenteeism data. A student is **chronically absent** when absent '
    '(excused or unexcused) for **10% or more** of enrolled days — research links it to '
    'lower early-grade reading and weaker long-run outcomes. Lincoln is highlighted in blue. '
    f'**{COVID_YEAR-1}-{str(COVID_YEAR)[2:]} (distance learning) is not comparable** to in-person years; '
    f'{COVID_YEAR-2}-{str(COVID_YEAR-1)[2:]} is not published.'
)

if abs_df.empty:
    st.warning('Absenteeism data not found. Run `python seda_app/fetch_absenteeism.py`.')
    st.stop()

abs_df = abs_df.copy()
abs_df['is_lincoln'] = abs_df['school_code'] == D.LINCOLN_SCHOOL_CODE
abs_df['School'] = abs_df['school_name']

total = abs_df[abs_df['category_code'] == 'TA'].copy()
latest_total = total[total['school_year_end'] == LATEST].sort_values('chronic_rate')
lincoln_now = latest_total[latest_total['is_lincoln']]
lincoln_now = lincoln_now.iloc[0] if not lincoln_now.empty else None


# ── Lincoln headline cards ────────────────────────────────────────────────────

if lincoln_now is not None:
    peers = latest_total[~latest_total['is_lincoln']]
    med = peers['chronic_rate'].median()
    n = len(latest_total)
    rank = int((latest_total['chronic_rate'] < lincoln_now['chronic_rate']).sum()) + 1

    with st.container(border=True):
        st.markdown(f'### :material/school: Lincoln Elementary — {LATEST-1}-{str(LATEST)[2:]}')
        c1, c2, c3 = st.columns(3)
        c1.metric(
            ':material/event_busy: Chronic absenteeism rate',
            f"{lincoln_now['chronic_rate']:.1f}%",
            delta=f"{lincoln_now['chronic_rate'] - med:+.1f} pp vs peer median",
            delta_color='inverse',
            help=f"Other Burlingame elementaries' median is {med:.1f}%. Lower is better.",
        )
        c2.metric(
            ':material/groups: Chronically absent students',
            f"{int(lincoln_now['chronic_count'])}",
            help=f"Out of {int(lincoln_now['eligible_enrollment'])} eligible students.",
        )
        c3.metric(
            ':material/trending_down: Rank among peers',
            f"{_ordinal(rank)} of {n}",
            help='1st = lowest (best) chronic absenteeism rate among the Burlingame elementaries.',
        )

st.html('<div style="height:10px"></div>')


tab_trend, tab_compare, tab_subgroup = st.tabs([
    ':material/trending_up: Trend Over Time',
    ':material/bar_chart: Latest-Year Comparison',
    ':material/groups: Lincoln by Subgroup',
])


with tab_trend:
    hide_covid = st.toggle('Hide distance-learning year (2020-21)', value=True, key='hide_covid')
    plot = total.dropna(subset=['chronic_rate']).copy()
    if hide_covid:
        plot = plot[plot['school_year_end'] != COVID_YEAR]

    dist_avg = plot.groupby('school_year_end', as_index=False)['chronic_rate'].mean()
    dist_avg['School'] = 'Elementary avg'

    base = alt.Chart(plot).encode(
        x=alt.X('school_year_end:O', title='School year (spring)'),
        y=alt.Y('chronic_rate:Q', title='Chronic absenteeism rate (%)'),
        detail='School:N',
        tooltip=[alt.Tooltip('School:N'), alt.Tooltip('school_year_end:O', title='Year'),
                 alt.Tooltip('chronic_rate:Q', title='Rate %', format='.1f'),
                 alt.Tooltip('chronic_count:Q', title='Count', format='.0f')],
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
    avg_line = alt.Chart(dist_avg).mark_line(strokeDash=[5, 4], color=WARN, strokeWidth=2).encode(
        x='school_year_end:O', y='chronic_rate:Q',
        tooltip=[alt.Tooltip('school_year_end:O', title='Year'),
                 alt.Tooltip('chronic_rate:Q', title='Elem avg %', format='.1f')],
    )
    last = plot[plot['school_year_end'] == plot['school_year_end'].max()]
    labels = alt.Chart(last).mark_text(align='left', dx=6, fontSize=10).encode(
        x='school_year_end:O', y='chronic_rate:Q', text='School:N',
        color=alt.Color('is_lincoln:N', scale=alt.Scale(domain=[True, False],
                        range=[LINCOLN_COLOR, GRAY]), legend=None),
    )
    chart = (avg_line + lines + points + labels).properties(
        width=720, height=400,
        title=alt.TitleParams('Chronic absenteeism rate by school', dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 80},
    )
    st.altair_chart(configure(chart))

    with st.expander(':material/insights: Analysis', expanded=True):
        lin = total[(total['is_lincoln']) & (total['school_year_end'] != COVID_YEAR)].dropna(
            subset=['chronic_rate']).sort_values('school_year_end')
        pre = lin[lin['school_year_end'] <= 2019]['chronic_rate'].mean()
        peak_row = lin.loc[lin['chronic_rate'].idxmax()] if not lin.empty else None
        now_rate = lin[lin['school_year_end'] == LATEST]['chronic_rate']
        lines_md = []
        if pd.notna(pre) and peak_row is not None and not now_rate.empty:
            lines_md.append(
                f"- **Lincoln (blue):** averaged ~{pre:.1f}% pre-COVID, peaked at "
                f"{peak_row['chronic_rate']:.1f}% in {int(peak_row['school_year_end'])}, and is back to "
                f"{now_rate.iloc[0]:.1f}% in {LATEST-1}-{str(LATEST)[2:]} — essentially at its pre-pandemic baseline."
            )
        lines_md.append(
            '- **Orange dashed line** = average across the Burlingame elementaries. '
            'Chronic absenteeism spiked district-wide (and statewide) after schools reopened in 2021-22.'
        )
        lines_md.append(
            '- A low rate means most students attend regularly; it does not capture *why* the '
            'chronically-absent students are missing school (illness, anxiety, family circumstance).'
        )
        st.markdown('\n'.join(lines_md))


with tab_compare:
    plot = latest_total.dropna(subset=['chronic_rate']).sort_values('chronic_rate')
    bars = alt.Chart(plot).mark_bar().encode(
        x=alt.X('chronic_rate:Q', title='Chronic absenteeism rate (%)'),
        y=alt.Y('School:N', sort=plot['School'].tolist(), title=None),
        color=alt.condition(alt.datum.is_lincoln, alt.value(LINCOLN_COLOR), alt.value(GRAY)),
        tooltip=[alt.Tooltip('School:N'), alt.Tooltip('chronic_rate:Q', title='Rate %', format='.1f'),
                 alt.Tooltip('chronic_count:Q', title='Count', format='.0f'),
                 alt.Tooltip('eligible_enrollment:Q', title='Eligible', format='.0f')],
    )
    labels = alt.Chart(plot).mark_text(align='left', dx=4, color='#374151').encode(
        x='chronic_rate:Q', y=alt.Y('School:N', sort=plot['School'].tolist()),
        text=alt.Text('chronic_rate:Q', format='.1f'),
    )
    chart = (bars + labels).properties(
        width=620, height=300,
        title=alt.TitleParams(f'Chronic absenteeism by school — {LATEST-1}-{str(LATEST)[2:]}', dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 40},
    )
    st.altair_chart(configure(chart))
    with st.expander(':material/insights: Analysis', expanded=True):
        st.markdown(
            f'- **Blue = Lincoln.** Range across the elementaries is '
            f'{plot["chronic_rate"].min():.1f}%–{plot["chronic_rate"].max():.1f}%.\n'
            f'- Small schools swing more year-to-year: a handful of students moves the rate '
            f'by a full percentage point when eligible enrollment is only ~200-500.'
        )


with tab_subgroup:
    st.caption('Lincoln chronic absenteeism by subgroup. Cells with very few students are '
               'suppressed by CDE (shown as gaps).')
    cat_type = st.segmented_control(
        'Breakdown', ['Race', 'Program', 'Gender', 'Grade'],
        default='Race', key='sg_type')
    lin_sg = abs_df[
        (abs_df['is_lincoln'])
        & (abs_df['school_year_end'] == LATEST)
        & (abs_df['category_type'] == cat_type)
    ].dropna(subset=['chronic_rate']).sort_values('chronic_rate', ascending=False)

    if lin_sg.empty:
        st.info('No reportable subgroup data for this breakdown in the latest year.')
    else:
        bars = alt.Chart(lin_sg).mark_bar(color=LINCOLN_COLOR).encode(
            x=alt.X('chronic_rate:Q', title='Chronic absenteeism rate (%)'),
            y=alt.Y('subgroup:N', sort=lin_sg['subgroup'].tolist(), title=None),
            tooltip=[alt.Tooltip('subgroup:N', title='Subgroup'),
                     alt.Tooltip('chronic_rate:Q', title='Rate %', format='.1f'),
                     alt.Tooltip('chronic_count:Q', title='Count', format='.0f'),
                     alt.Tooltip('eligible_enrollment:Q', title='Eligible', format='.0f')],
        )
        labels = alt.Chart(lin_sg).mark_text(align='left', dx=4, color='#374151').encode(
            x='chronic_rate:Q', y=alt.Y('subgroup:N', sort=lin_sg['subgroup'].tolist()),
            text=alt.Text('chronic_rate:Q', format='.1f'),
        )
        chart = (bars + labels).properties(
            width=620, height=max(180, 42 * len(lin_sg)),
            title=alt.TitleParams(f'Lincoln by {cat_type.lower()} — {LATEST-1}-{str(LATEST)[2:]}', dy=-4),
            padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 40},
        )
        st.altair_chart(configure(chart))
        with st.expander(':material/insights: Analysis', expanded=True):
            st.markdown(
                '- Subgroup rates at a single small school rest on very few students — '
                'a subgroup of 30 with 6 absent reads as 18%, so read these as directional, not precise.\n'
                '- Socioeconomically disadvantaged and English-learner students tend to show higher '
                'chronic absenteeism nationally; check whether that pattern holds at Lincoln here.'
            )
