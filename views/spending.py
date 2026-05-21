"""Per-pupil spending — Lincoln vs the Burlingame elementaries (ESSA PPE).

Source: CDE ESSA Per-Pupil Expenditure files. Amounts are per-pupil current
expenditures, split into School (specific to each school) and Central (the
district-wide allocation, identical across schools in the district), each by
Federal vs State/Local fund source. ESSA PPE excludes capital outlay, debt
service, and a few federal programs by definition, so it is not total spending.
"""
import pandas as pd
import altair as alt
import streamlit as st

from shared import data as D
from shared.theme import LINCOLN_COLOR, PEER_COLOR, GRAY, WARN, DANGER, configure

LATEST = 2024

# CA statewide ESSA per-pupil expenditure for ELEMENTARY (K-6) schools, 2023-24 —
# enrollment-weighted across ~4,600 GS_K6 schools (2.2M students), computed from the
# CDE ESSA PPE workbook joined to CDE staffing grade-spans, after dropping data-entry
# outliers. Apples-to-apples with the K-6 schools shown here. (The all-grades figure is
# nearly identical at ~$19,200 — CA elementaries do not spend less than secondary.)
CA_AVG_PPE = 19450


def _ordinal(n):
    n = int(n)
    suf = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suf}'


spend = D.load_spending()

st.title(':material/payments: Per-Pupil Spending — Burlingame Elementaries')
st.caption(
    'CDE ESSA per-pupil expenditure data. **Total = School + Central**, where *Central* is the '
    'district-wide allocation (identical across schools) and *School* is what is spent at each '
    'site — so school-to-school differences come entirely from the School portion. '
    'Federal dollars flow disproportionately to higher-poverty schools (Title I). '
    'ESSA PPE excludes capital, debt service, and some federal programs, so it is *not* total spending.'
)

if spend.empty:
    st.warning('Spending data not found. Run `python seda_app/fetch_spending.py`.')
    st.stop()

spend = spend.copy()
spend['is_lincoln'] = spend['school_code'] == D.LINCOLN_SCHOOL_CODE
spend['School'] = spend['school_name']
spend['federal_total'] = spend['school_federal'] + spend['central_federal']
spend['state_local_total'] = spend['school_state_local'] + spend['central_state_local']

latest = spend[spend['school_year_end'] == LATEST].sort_values('total_ppe')
lincoln_now = latest[latest['is_lincoln']]
lincoln_now = lincoln_now.iloc[0] if not lincoln_now.empty else None


# ── Lincoln headline cards ────────────────────────────────────────────────────

if lincoln_now is not None:
    peers = latest[~latest['is_lincoln']]
    med = peers['total_ppe'].median()
    n = len(latest)
    rank = int((latest['total_ppe'] > lincoln_now['total_ppe']).sum()) + 1  # 1 = highest-spending
    fed_share = 100 * lincoln_now['federal_total'] / lincoln_now['total_ppe']

    ppe_spark = (spend[spend['is_lincoln']].dropna(subset=['total_ppe'])
                 .sort_values('school_year_end')['total_ppe'].tolist())

    st.markdown(f'### :material/school: Lincoln Elementary — {LATEST-1}-{str(LATEST)[2:]}')
    c1, c2, c3 = st.columns(3)
    c1.metric(
        ':material/payments: Total per-pupil spending',
        f"${lincoln_now['total_ppe']:,.0f}",
        delta=f"${lincoln_now['total_ppe'] - med:+,.0f} vs peer median",
        border=True,
        chart_data=ppe_spark,
        chart_type='line',
        help=f"Other Burlingame elementaries' median is ${med:,.0f}. "
             f"Sparkline = Lincoln's per-pupil spending over time.",
    )
    c2.metric(
        ':material/leaderboard: Rank among peers',
        f"{_ordinal(rank)} of {n}",
        border=True,
        help='1st = highest per-pupil spending among the Burlingame elementaries.',
    )
    c3.metric(
        ':material/account_balance: Federally funded share',
        f"{fed_share:.1f}%",
        border=True,
        help='Share of per-pupil spending from federal sources (Title I, etc.). '
             'Higher-poverty schools typically draw more.',
    )

st.html('<div style="height:10px"></div>')


tab_compare, tab_composition, tab_trend = st.tabs([
    ':material/bar_chart: Latest-Year Comparison',
    ':material/stacked_bar_chart: Funding Composition',
    ':material/trending_up: Trend Over Time',
])


with tab_compare:
    plot = latest.sort_values('total_ppe', ascending=False)
    bars = alt.Chart(plot).mark_bar().encode(
        x=alt.X('total_ppe:Q', title='Total per-pupil spending ($)', axis=alt.Axis(format='$,.0f')),
        y=alt.Y('School:N', sort=plot['School'].tolist(), title=None),
        color=alt.condition(alt.datum.is_lincoln, alt.value(LINCOLN_COLOR), alt.value(GRAY)),
        tooltip=[alt.Tooltip('School:N'),
                 alt.Tooltip('total_ppe:Q', title='Total PPE', format='$,.0f'),
                 alt.Tooltip('federal_total:Q', title='Federal', format='$,.0f'),
                 alt.Tooltip('state_local_total:Q', title='State & Local', format='$,.0f')],
    )
    labels = alt.Chart(plot).mark_text(align='left', dx=4, color='#374151').encode(
        x='total_ppe:Q', y=alt.Y('School:N', sort=plot['School'].tolist()),
        text=alt.Text('total_ppe:Q', format='$,.0f'),
    )
    ref = pd.DataFrame({'x': [CA_AVG_PPE]})
    ca_rule = alt.Chart(ref).mark_rule(color=DANGER, strokeDash=[5, 4], strokeWidth=2).encode(
        x='x:Q', tooltip=alt.value(f'CA state average (2023-24): ${CA_AVG_PPE:,}'))
    ca_text = alt.Chart(ref).mark_text(color=DANGER, align='center', baseline='bottom',
        dy=-4, fontSize=10, fontWeight='bold', text=f'CA elem avg ${CA_AVG_PPE:,}').encode(
        x='x:Q', y=alt.value(0))
    chart = (bars + labels + ca_rule + ca_text).properties(
        width=620, height=300,
        title=alt.TitleParams(f'Total per-pupil spending — {LATEST-1}-{str(LATEST)[2:]}', dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 70},
    )
    st.altair_chart(configure(chart), width='stretch')
    with st.expander(':material/insights: Analysis', expanded=True):
        hi = plot.iloc[0]
        lo = plot.iloc[-1]
        st.markdown(
            f'- **Blue = Lincoln.** Spending ranges from **${lo["total_ppe"]:,.0f}** ({lo["School"]}) '
            f'to **${hi["total_ppe"]:,.0f}** ({hi["School"]}) per pupil.\n'
            f'- **Red dashed line = CA average for elementary (K-6) schools (~${CA_AVG_PPE:,}, '
            f'2023-24).** Every Burlingame elementary spends *below* it — because California routes '
            f'extra money (LCFF supplemental/concentration + federal Title I) to higher-poverty '
            f'students, and Burlingame is low-poverty. (This is an elementary-only benchmark, so '
            f'it is apples-to-apples; CA elementaries do not spend less than secondary schools.)\n'
            f'- Smaller schools often show higher per-pupil spending — fixed costs '
            f'(a principal, an office) spread over fewer students.'
        )


with tab_composition:
    src = latest.melt(
        id_vars=['School', 'is_lincoln', 'total_ppe'],
        value_vars=['school_state_local', 'school_federal', 'central_state_local', 'central_federal'],
        var_name='component', value_name='amount')
    LABELS = {
        'school_state_local': 'School · State & Local',
        'school_federal': 'School · Federal',
        'central_state_local': 'Central · State & Local',
        'central_federal': 'Central · Federal',
    }
    COMP_COLORS = {
        'School · State & Local': LINCOLN_COLOR,
        'School · Federal': PEER_COLOR,
        'Central · State & Local': GRAY,
        'Central · Federal': WARN,
    }
    src['Component'] = src['component'].map(LABELS)
    order = latest.sort_values('total_ppe', ascending=False)['School'].tolist()

    chart = alt.Chart(src).mark_bar().encode(
        x=alt.X('amount:Q', title='Per-pupil spending ($)', stack='zero', axis=alt.Axis(format='$,.0f')),
        y=alt.Y('School:N', sort=order, title=None),
        color=alt.Color('Component:N',
            scale=alt.Scale(domain=list(COMP_COLORS.keys()), range=list(COMP_COLORS.values())),
            legend=alt.Legend(orient='bottom', columns=2, title=None)),
        order=alt.Order('Component:N'),
        tooltip=[alt.Tooltip('School:N'), alt.Tooltip('Component:N'),
                 alt.Tooltip('amount:Q', title='Amount', format='$,.0f')],
    ).properties(
        width=620, height=320,
        title=alt.TitleParams(f'Funding composition — {LATEST-1}-{str(LATEST)[2:]}', dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 20},
    )
    st.altair_chart(configure(chart), width='stretch')
    with st.expander(':material/insights: Analysis', expanded=True):
        cen = latest.iloc[0]
        st.markdown(
            f'- **Central allocation (gray + orange) is identical across all schools** '
            f'(~${cen["central_state_local"] + cen["central_federal"]:,.0f}/pupil) — it is the '
            f'district-wide share. All school-to-school variation lives in the *School* bars.\n'
            f'- The **School · Federal** slice is the clearest poverty signal: it concentrates at '
            f'the Title I schools and is near zero elsewhere.'
        )


with tab_trend:
    plot = spend.dropna(subset=['total_ppe'])
    base = alt.Chart(plot).encode(
        x=alt.X('school_year_end:O', title='School year (spring)'),
        y=alt.Y('total_ppe:Q', title='Total per-pupil spending ($)',
                scale=alt.Scale(zero=False), axis=alt.Axis(format='$,.0f')),
        detail='School:N',
        tooltip=[alt.Tooltip('School:N'), alt.Tooltip('school_year_end:O', title='Year'),
                 alt.Tooltip('total_ppe:Q', title='Total PPE', format='$,.0f')],
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
        x='school_year_end:O', y='total_ppe:Q', text='School:N',
        color=alt.Color('is_lincoln:N', scale=alt.Scale(domain=[True, False],
                        range=[LINCOLN_COLOR, GRAY]), legend=None),
    )
    ref = pd.DataFrame({'y': [CA_AVG_PPE]})
    ca_rule = alt.Chart(ref).mark_rule(color=DANGER, strokeDash=[5, 4], strokeWidth=2).encode(
        y='y:Q', tooltip=alt.value(f'CA state average (2023-24): ${CA_AVG_PPE:,}'))
    ca_text = alt.Chart(ref).mark_text(color=DANGER, align='left', baseline='bottom',
        dx=5, dy=-3, fontSize=10, fontWeight='bold', text=f'CA elem avg ${CA_AVG_PPE:,} (2023-24)').encode(
        x=alt.value(0), y='y:Q')
    chart = (lines + points + labels + ca_rule + ca_text).properties(
        width=720, height=400,
        title=alt.TitleParams('Total per-pupil spending by school', dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 80},
    )
    st.altair_chart(configure(chart), width='stretch')
    with st.expander(':material/insights: Analysis', expanded=True):
        lin = spend[spend['is_lincoln']].dropna(subset=['total_ppe']).sort_values('school_year_end')
        if len(lin) >= 2:
            first, last_r = lin.iloc[0], lin.iloc[-1]
            pct = 100 * (last_r['total_ppe'] - first['total_ppe']) / first['total_ppe']
            st.markdown(
                f"- **Lincoln (blue):** ${first['total_ppe']:,.0f} in {int(first['school_year_end'])} → "
                f"${last_r['total_ppe']:,.0f} in {int(last_r['school_year_end'])} "
                f"(+{pct:.0f}% nominal, not inflation-adjusted).\n"
                f"- The 2020-2022 bump across schools largely reflects one-time federal COVID relief "
                f"(ESSER) flowing through per-pupil figures."
            )
