"""School-level enrollment & demographics for the Burlingame elementaries.

Source: CDE Census Day Enrollment files (first Wednesday in October). This is
SCHOOL-level (Lincoln-specific) racial/ethnic composition, English-learner share,
and enrollment by grade — complementing the district-level SEDA demographics.
Only 2023-24 onward is published in this file.
"""
import pandas as pd
import altair as alt
import streamlit as st

from shared import data as D
from shared.theme import LINCOLN_COLOR, GRAY, configure

LATEST = 2026

RACE_COLORS = {
    'White': '#16A34A', 'Asian': '#7C3AED', 'Hispanic': '#D97706', 'Black': '#DC2626',
    'Filipino': '#0891B2', 'Two or More': '#2563EB', 'Pacific Islander': '#DB2777',
    'American Indian': '#65A30D', 'Not Reported': '#9CA3AF',
}


enr = D.load_enrollment()

st.title(':material/diversity_3: Enrollment & Demographics — Burlingame Elementaries')
st.caption(
    'CDE Census Day enrollment (school-level). Lincoln-specific racial/ethnic composition, '
    'English-learner share, and enrollment by grade — complements the district-wide SEDA '
    'demographics on the SEDA page. Published from 2023-24 onward only.'
)

if enr.empty:
    st.warning('Enrollment data not found. Run `python seda_app/fetch_enrollment.py`.')
    st.stop()

enr = enr.copy()
enr['is_lincoln'] = enr['school_code'] == D.LINCOLN_SCHOOL_CODE
enr['School'] = enr['school_name']

latest = enr[enr['school_year_end'] == LATEST]
lincoln_latest = latest[latest['is_lincoln']]


def cat_count(df, ctype, label):
    s = df[(df['category_type'] == ctype) & (df['label'] == label)]['count']
    return float(s.iloc[0]) if not s.empty else 0.0


# ── Lincoln headline card ─────────────────────────────────────────────────────

if not lincoln_latest.empty:
    total = cat_count(lincoln_latest, 'Total', 'All Students')
    el = cat_count(lincoln_latest, 'EL', 'English Learners')
    races = lincoln_latest[lincoln_latest['category_type'] == 'Race'].sort_values('count', ascending=False)
    top_race = races.iloc[0] if not races.empty else None

    with st.container(border=True):
        st.markdown(f'### :material/school: Lincoln Elementary — {LATEST-1}-{str(LATEST)[2:]}')
        c1, c2, c3 = st.columns(3)
        c1.metric(':material/groups: Total enrollment', f"{int(total):,}")
        c2.metric(
            ':material/translate: English learners',
            f"{el / total * 100:.0f}%" if total else "—",
            help=f"{int(el)} of {int(total)} students are classified English learners.",
        )
        if top_race is not None:
            c3.metric(
                ':material/diversity_3: Largest group',
                f"{top_race['label']}",
                help=f"{top_race['label']} students are the largest group "
                     f"({top_race['count'] / total * 100:.0f}%). No single group is a majority.",
            )

st.html('<div style="height:10px"></div>')


tab_race, tab_grade, tab_trend = st.tabs([
    ':material/diversity_3: Racial / Ethnic Composition',
    ':material/school: Enrollment by Grade',
    ':material/trending_up: Enrollment Trend',
])


with tab_race:
    race = latest[latest['category_type'] == 'Race'].copy()
    totals = latest[latest['category_type'] == 'Total'][['school_name', 'count']].rename(
        columns={'count': 'school_total'})
    race = race.merge(totals, on='school_name', how='left')
    race['pct'] = race['count'] / race['school_total'] * 100
    order = ['Lincoln'] + sorted(s for s in race['School'].unique() if s != 'Lincoln')
    race_order = [r for r in RACE_COLORS if r in race['label'].unique()]

    chart = alt.Chart(race).mark_bar().encode(
        x=alt.X('pct:Q', title='% of students', stack='normalize', axis=alt.Axis(format='%')),
        y=alt.Y('School:N', sort=order, title=None),
        color=alt.Color('label:N', sort=race_order,
            scale=alt.Scale(domain=race_order, range=[RACE_COLORS[r] for r in race_order]),
            legend=alt.Legend(orient='right', title='Race / Ethnicity')),
        order=alt.Order('label:N'),
        tooltip=[alt.Tooltip('School:N'), alt.Tooltip('label:N', title='Group'),
                 alt.Tooltip('count:Q', title='Students', format='.0f'),
                 alt.Tooltip('pct:Q', title='% of school', format='.1f')],
    ).properties(
        width=620, height=300,
        title=alt.TitleParams(f'Racial / ethnic composition — {LATEST-1}-{str(LATEST)[2:]}',
                              anchor='start', limit=0),
        padding={'top': 34, 'bottom': 10, 'left': 5, 'right': 10},
    )
    st.altair_chart(configure(chart), width='stretch')
    with st.expander(':material/insights: Analysis', expanded=True):
        st.markdown(
            '- Bars are normalized to 100%, so they show each school\'s *mix*, not its size.\n'
            '- Lincoln (top) has no majority group — it is a plurality-White, heavily Asian school '
            'with a smaller Hispanic share than the district\'s higher-poverty sites.\n'
            '- This composition is the backdrop for the funding and absenteeism patterns elsewhere '
            'in the app: demographics, not school decisions, drive much of that variation.'
        )


with tab_grade:
    grades = lincoln_latest[lincoln_latest['category_type'] == 'Grade'].copy()
    grade_order = ['TK', 'K', '1', '2', '3', '4', '5', '6']
    grades = grades[grades['count'] > 0]
    bars = alt.Chart(grades).mark_bar(color=LINCOLN_COLOR).encode(
        x=alt.X('label:N', sort=grade_order, title='Grade'),
        y=alt.Y('count:Q', title='Students'),
        tooltip=[alt.Tooltip('label:N', title='Grade'), alt.Tooltip('count:Q', title='Students', format='.0f')],
    )
    labels = alt.Chart(grades).mark_text(dy=-6, color='#374151').encode(
        x=alt.X('label:N', sort=grade_order), y='count:Q',
        text=alt.Text('count:Q', format='.0f'),
    )
    chart = (bars + labels).properties(
        width=620, height=300,
        title=alt.TitleParams(f'Lincoln enrollment by grade — {LATEST-1}-{str(LATEST)[2:]}',
                              anchor='start', limit=0),
        padding={'top': 34, 'bottom': 10, 'left': 5, 'right': 10},
    )
    st.altair_chart(configure(chart), width='stretch')
    with st.expander(':material/insights: Analysis', expanded=True):
        st.markdown(
            '- Grade-to-grade size differences reflect cohort size and family in/out-migration, '
            'not capacity.\n'
            '- Lincoln runs TK-5; small per-grade counts (~50-90) mean subgroup test-score figures '
            'for any single grade carry wide margins of error.'
        )


with tab_trend:
    tot = enr[enr['category_type'] == 'Total'].copy()
    base = alt.Chart(tot).encode(
        x=alt.X('school_year_end:O', title='School year (spring)'),
        y=alt.Y('count:Q', title='Total enrollment', scale=alt.Scale(zero=False)),
        detail='School:N',
        tooltip=[alt.Tooltip('School:N'), alt.Tooltip('school_year_end:O', title='Year'),
                 alt.Tooltip('count:Q', title='Enrollment', format='.0f')],
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
    last = tot[tot['school_year_end'] == tot['school_year_end'].max()]
    labels = alt.Chart(last).mark_text(align='left', dx=6, fontSize=10).encode(
        x='school_year_end:O', y='count:Q', text='School:N',
        color=alt.Color('is_lincoln:N', scale=alt.Scale(domain=[True, False],
                        range=[LINCOLN_COLOR, GRAY]), legend=None),
    )
    chart = (lines + points + labels).properties(
        width=720, height=360,
        title=alt.TitleParams('Total enrollment by school', anchor='start', limit=0),
        padding={'top': 34, 'bottom': 10, 'left': 5, 'right': 80},
    )
    st.altair_chart(configure(chart), width='stretch')
    st.caption('Only three years are published in this file (2023-24 onward), so the trend is short.')
