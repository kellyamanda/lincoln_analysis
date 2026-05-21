"""California School Dashboard — official accountability colors for Burlingame elementaries.

The Dashboard assigns each school a performance color per indicator by combining current
status with year-over-year change: Red (lowest) → Orange → Yellow → Green → Blue (highest).
This page shows the 2024-25 Dashboard for the 6 Burlingame elementaries, with Lincoln
highlighted. No Dashboard was issued for 2020 or 2021 (COVID).
"""
import pandas as pd
import altair as alt
import streamlit as st

from shared import data as D
from shared.theme import configure

LATEST = 2025

# Approximate CA School Dashboard performance-color palette.
COLOR_HEX = {
    'Red': '#E1442F', 'Orange': '#F0973B', 'Yellow': '#F6D330',
    'Green': '#5BB552', 'Blue': '#4C7FB8', 'Not rated': '#E5E7EB',
}
COLOR_ORDER = ['Red', 'Orange', 'Yellow', 'Green', 'Blue', 'Not rated']
# Map Dashboard color names to st.badge's supported color keywords.
BADGE_COLOR = {'Red': 'red', 'Orange': 'orange', 'Yellow': 'yellow',
               'Green': 'green', 'Blue': 'blue', 'Not rated': 'gray'}
INDICATOR_ORDER = ['ELA', 'Math', 'Chronic Absenteeism', 'Suspension', 'EL Progress']

# How to read currstatus, and whether higher is better.
UNITS = {
    'ELA': ('pts from standard', '+.1f'),
    'Math': ('pts from standard', '+.1f'),
    'Chronic Absenteeism': ('%', '.1f'),
    'Suspension': ('%', '.1f'),
    'EL Progress': ('% making progress', '.1f'),
}


def fmt_status(indicator, value):
    if pd.isna(value):
        return '—'
    unit, spec = UNITS.get(indicator, ('', '.1f'))
    num = format(value, spec)
    if indicator in ('ELA', 'Math'):
        return f'{num}'
    return f'{num}%' if unit == '%' else f'{num}'


dash = D.load_dashboard()

st.title(':material/dashboard: California School Dashboard')
st.caption(
    'The official state accountability colors (2024-25). Each indicator combines current '
    '**status** with year-over-year **change** into a performance level: '
    ':red[Red] → :orange[Orange] → :gray[Yellow] → :green[Green] → :blue[Blue] (highest). '
    'For ELA/Math, status is *distance from the "standard met" threshold* in points (higher is '
    'better); for absenteeism and suspension it is a rate (lower is better).'
)

if dash.empty:
    st.warning('Dashboard data not found. Run `python seda_app/fetch_dashboard.py`.')
    st.stop()

dash = dash.copy()
dash['color_name'] = dash['color_name'].fillna('Not rated')
latest = dash[dash['school_year_end'] == LATEST].copy()
lincoln = latest[latest['school_code'] == D.LINCOLN_SCHOOL_CODE]


# ── Lincoln color chips ───────────────────────────────────────────────────────

with st.container(border=True):
    st.markdown('### :material/school: Lincoln Elementary — 2024-25 Dashboard')
    cols = st.columns(len(INDICATOR_ORDER))
    for col, ind in zip(cols, INDICATOR_ORDER):
        row = lincoln[lincoln['indicator'] == ind]
        if row.empty:
            continue
        r = row.iloc[0]
        cname = r['color_name']
        status = fmt_status(ind, r['currstatus'])
        with col:
            st.markdown(f'**{ind}**')
            if cname == 'Not rated':
                st.badge('Not rated', color='gray', icon=':material/remove:')
            else:
                st.badge(f'{status} · {cname}', color=BADGE_COLOR[cname],
                         icon=':material/circle:')
    st.caption(
        ':material/info: Lincoln is Blue (highest) on ELA, Math, and Suspension, and Green on '
        'Chronic Absenteeism. EL Progress is unrated — too few English-learner students to assign '
        'a color (a small-population data limit, not a result).'
    )

st.html('<div style="height:12px"></div>')


# ── Full color grid: 6 elementaries × indicators ──────────────────────────────

st.markdown('#### :material/grid_view: All Burlingame elementaries')

grid = latest.copy()
grid['School'] = grid['school_name']
grid['ind_order'] = grid['indicator'].map({n: i for i, n in enumerate(INDICATOR_ORDER)})
grid['label'] = grid.apply(lambda r: fmt_status(r['indicator'], r['currstatus']), axis=1)
# Lincoln first, then alphabetical.
school_order = ['Lincoln'] + sorted(s for s in grid['School'].unique() if s != 'Lincoln')

heat = alt.Chart(grid).mark_rect(stroke='white', strokeWidth=3).encode(
    x=alt.X('indicator:N', sort=INDICATOR_ORDER, title=None,
            axis=alt.Axis(orient='top', labelAngle=0, labelLimit=200)),
    y=alt.Y('School:N', sort=school_order, title=None),
    color=alt.Color('color_name:N',
        scale=alt.Scale(domain=COLOR_ORDER, range=[COLOR_HEX[c] for c in COLOR_ORDER]),
        legend=alt.Legend(orient='bottom', title='Dashboard color', direction='horizontal')),
    tooltip=[alt.Tooltip('School:N'), alt.Tooltip('indicator:N', title='Indicator'),
             alt.Tooltip('color_name:N', title='Color'),
             alt.Tooltip('currstatus:Q', title='Status', format='.1f'),
             alt.Tooltip('change:Q', title='Change', format='+.1f')],
)
text = alt.Chart(grid).mark_text(fontSize=12, fontWeight='bold').encode(
    x=alt.X('indicator:N', sort=INDICATOR_ORDER),
    y=alt.Y('School:N', sort=school_order),
    text='label:N',
    color=alt.condition(
        alt.FieldOneOfPredicate(field='color_name', oneOf=['Yellow', 'Not rated']),
        alt.value('#1F2937'), alt.value('white')),
)
chart = (heat + text).properties(
    width=620, height=58 * len(school_order),
    padding={'top': 10, 'bottom': 10, 'left': 5, 'right': 5},
)
st.altair_chart(configure(chart), width='stretch')

with st.expander(':material/insights: Analysis', expanded=True):
    st.markdown(
        '- **Cell color is the official Dashboard rating; the number is the underlying status** '
        '(ELA/Math = points from the "standard met" line; absenteeism/suspension = rate %).\n'
        '- Lincoln and its sister schools cluster in **Green/Blue** on academics and suspension — '
        'the district is high-performing across the board.\n'
        '- **Suspension is 0% at every Burlingame elementary — this is real, not missing data.** '
        'California law (SB 419) bars suspending K-8 students for "willful defiance/disruption," '
        'the most common reason young children are suspended; the offenses still suspendable '
        '(violence, weapons, drugs) are rare at small, low-poverty K-6 schools. By contrast BIS '
        '(grades 6-8) shows ~1.8%, confirming suspensions are recorded where they occur. A 0% rate '
        'means no *out-of-school suspensions* — not zero discipline (schools still use conferences, '
        'in-class measures, restorative practices).\n'
        '- **EL Progress is mostly unrated** at these schools: their English-learner populations are '
        'too small to meet the Dashboard\'s minimum size for a color.\n'
        '- The Dashboard rewards *both* high status **and** improvement, so a high-scoring school that '
        'dipped slightly can land below a lower-scoring school that is climbing.'
    )
