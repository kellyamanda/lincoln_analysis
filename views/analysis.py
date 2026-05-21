"""Lincoln Elementary — detailed analysis with three tabs:
  - Lincoln overall performance
  - Lincoln compared to other schools
  - Lincoln to BIS transition
+ permanent footer with data caveats.

For the one-glance summary, see views/overview.py.
"""
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

from shared import data as D
from shared.theme import (
    LINCOLN_COLOR, PEER_COLOR, GRAY, WARN,
    PCT_COLORS, GRADE_COLORS, configure,
)


# ── Header ────────────────────────────────────────────────────────────────────

st.title(':material/analytics: Lincoln Elementary — Detailed Analysis')
st.caption(
    'Three lenses on Lincoln K-5 academic performance. Switch between the tabs below. '
    'Sources: California CAASPP 2014-15 through 2024-25 · Stanford SEDA 2025.1.'
)


# ── Load data ─────────────────────────────────────────────────────────────────

caaspp = D.load_caaspp()
lincoln_full = D.load_lincoln_full()
bis = D.load_bis()


# ── Helpers ───────────────────────────────────────────────────────────────────

PRE_YEARS = [2015, 2016, 2017, 2018, 2019]
POST_YEARS = [2022, 2023, 2024, 2025]


def prop_z(p1, n1, p2, n2):
    p1, p2 = p1 / 100, p2 / 100
    pool = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = np.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    return (p2 - p1) / se if se > 0 else np.nan


def lincoln_pooled(subject, metric_col):
    df = lincoln_full[lincoln_full['Subject'] == subject].dropna(
        subset=[metric_col, 'Students with Scores'])
    pre = df[df['Year'].isin(PRE_YEARS)]
    post = df[df['Year'].isin(POST_YEARS)]
    pre_n = pre['Students with Scores'].sum()
    post_n = post['Students with Scores'].sum()
    if pre_n == 0 or post_n == 0:
        return None
    pre_w = (pre[metric_col] * pre['Students with Scores']).sum() / pre_n
    post_w = (post[metric_col] * post['Students with Scores']).sum() / post_n
    return dict(
        pre=pre_w, post=post_w,
        pre_n=int(pre_n), post_n=int(post_n),
        diff=post_w - pre_w, z=prop_z(pre_w, pre_n, post_w, post_n),
    )


@st.cache_data(show_spinner=False)
def lincoln_yearly(subject):
    df = lincoln_full[lincoln_full['Subject'] == subject].dropna(
        subset=['Percentage Standard Met and Above',
                'Percentage Standard Exceeded',
                'Students with Scores'])
    df = df[df['Students with Scores'] > 0]
    out = df.groupby('Year').apply(
        lambda g: pd.Series({
            '% Met & Above': (g['Percentage Standard Met and Above'] * g['Students with Scores']).sum() / g['Students with Scores'].sum(),
            '% Exceeded':    (g['Percentage Standard Exceeded']      * g['Students with Scores']).sum() / g['Students with Scores'].sum(),
            'N': g['Students with Scores'].sum(),
        }),
        include_groups=False,
    ).reset_index()
    return out


@st.cache_data(show_spinner=False)
def burl_school_yearly(subject):
    sub = D.burl_caaspp(caaspp)
    sub = sub[sub['Subject'] == subject]
    sub = sub[sub['School Code'].isin(D.BURL_ELEMENTARIES.keys())]
    sub = sub.dropna(subset=['Pct Met Above'])
    sub['Name'] = sub['School Code'].map(D.BURL_ELEMENTARIES)
    out = sub.groupby(['Year', 'Name'])['Pct Met Above'].mean().reset_index()
    return out


@st.cache_data(show_spinner=False)
def ca_percentile_for_lincoln(subject):
    school_yr = caaspp.groupby(
        ['School Code', 'District Code', 'Year', 'Subject']
    )['Pct Met Above'].mean().reset_index()
    school_yr = school_yr[school_yr['Subject'] == subject]
    rows = []
    for yr, g in school_yr.groupby('Year'):
        lin = g[(g['School Code'] == D.LINCOLN_SCHOOL_CODE) &
                (g['District Code'] == D.CAASPP_DISTRICT_CODE)]['Pct Met Above']
        if lin.empty or pd.isna(lin.iloc[0]):
            continue
        lv = lin.iloc[0]
        pool = g['Pct Met Above'].dropna()
        rank = (pool < lv).mean() * 100
        rows.append({'Year': int(yr), 'Lincoln': lv,
                     'CA percentile': rank, 'CA median': pool.median()})
    return pd.DataFrame(rows)


# ── Pre-compute headline numbers (referenced by analysis paragraphs) ─────────

ela_pool  = lincoln_pooled('ELA',  'Percentage Standard Met and Above')
ela_exc   = lincoln_pooled('ELA',  'Percentage Standard Exceeded')
math_pool = lincoln_pooled('Math', 'Percentage Standard Met and Above')
math_exc  = lincoln_pooled('Math', 'Percentage Standard Exceeded')


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_overall, tab_compare, tab_bis = st.tabs([
    ':material/home: Lincoln overall performance',
    ':material/compare: Lincoln compared to other schools',
    ':material/swap_horiz: Lincoln to BIS transition',
])


# ── TAB 1: Lincoln overall performance ────────────────────────────────────────

with tab_overall:
    st.markdown(
        'Both the share of students meeting standards (% Met & Above) and the share '
        'performing at the top achievement level (% Exceeded). Charts show grade 3-5 '
        'weighted means at Lincoln, year by year.'
    )

    ela_yr = lincoln_yearly('ELA')
    math_yr = lincoln_yearly('Math')

    def lincoln_two_metric_chart(yearly_df, subject):
        long_df = yearly_df.melt(
            id_vars=['Year'],
            value_vars=['% Met & Above', '% Exceeded'],
            var_name='Metric', value_name='Value',
        )
        base = alt.Chart(long_df).encode(
            x=alt.X('Year:O', title='School Year'),
            y=alt.Y('Value:Q', title='% of students',
                    scale=alt.Scale(domain=[40, 95])),
            color=alt.Color('Metric:N',
                scale=alt.Scale(domain=['% Met & Above', '% Exceeded'],
                                range=[LINCOLN_COLOR, '#F59E0B']),
                legend=alt.Legend(orient='bottom', title=None)),
            tooltip=['Year:O', 'Metric:N', alt.Tooltip('Value:Q', format='.1f')],
        )
        return alt.layer(
            base.mark_line(strokeWidth=2.5),
            base.mark_point(size=70, filled=True),
        ).properties(
            width=520, height=320,
            title=alt.TitleParams(f'{subject} — Lincoln grade 3-5 weighted mean',
                                  dy=-8, fontSize=13, anchor='start'),
            padding={'top': 35, 'bottom': 10, 'left': 5, 'right': 10},
        )

    ela_col, math_col = st.columns(2)
    with ela_col:
        st.altair_chart(configure(lincoln_two_metric_chart(ela_yr, 'ELA')), width='stretch')
    with math_col:
        st.altair_chart(configure(lincoln_two_metric_chart(math_yr, 'Math')), width='stretch')

    def section1_analysis():
        def fmt_change(diff, z):
            d = 'improved' if diff > 0 else 'declined'
            sig = 'statistically meaningful' if abs(z) > 2 else 'within the margin of error'
            return d, abs(diff), sig

        e_d, e_abs, e_sig = fmt_change(ela_pool['diff'], ela_pool['z'])
        m_d, m_abs, m_sig = fmt_change(math_pool['diff'], math_pool['z'])
        ee_d, ee_abs, ee_sig = fmt_change(ela_exc['diff'], ela_exc['z'])
        me_d, me_abs, me_sig = fmt_change(math_exc['diff'], math_exc['z'])

        return (
            f'**Analysis.** '
            f"Lincoln's ELA % Met & Above {e_d} by **{e_abs:.1f}pp** from pre-COVID "
            f"({ela_pool['pre']:.1f}%) to post-COVID ({ela_pool['post']:.1f}%), which is **{e_sig}** "
            f"(z = {ela_pool['z']:.2f}). Math {m_d} by **{m_abs:.1f}pp** "
            f"({math_pool['pre']:.1f}% → {math_pool['post']:.1f}%), also **{m_sig}** "
            f"(z = {math_pool['z']:.2f}).\n\n"
            f'The high-achiever measure (% Exceeded) tells a more positive story: '
            f"ELA {ee_d} by **{ee_abs:.1f}pp** ({ela_exc['pre']:.1f}% → {ela_exc['post']:.1f}%, "
            f"z = {ela_exc['z']:.2f}, {ee_sig}), and **math % Exceeded improved by "
            f"{me_abs:.1f}pp** ({math_exc['pre']:.1f}% → {math_exc['post']:.1f}%, "
            f"z = {math_exc['z']:.2f}, **{me_sig}**). In plain English: the share of "
            f"Lincoln students scoring at the very top of the state's achievement scale in "
            f'math is *higher* now than before the pandemic.\n\n'
            f'**Read the chart.** A widening gap between the blue line (% Met & Above) '
            f'and the orange line (% Exceeded) means more of Lincoln\'s passing students '
            f'are clustered in the "Met" band rather than the "Exceeded" band; a narrowing '
            f'gap means more are reaching the top tier.'
        )

    with st.container(border=True):
        st.markdown(section1_analysis())


# ── TAB 2: Lincoln compared to other schools ──────────────────────────────────

with tab_compare:
    st.markdown(
        'Two comparisons: against the five other elementary schools in Burlingame School '
        'District, and against every elementary school in California.'
    )

    st.markdown('### Within Burlingame School District')

    def burl_chart(subject):
        df_b = burl_school_yearly(subject)
        base = alt.Chart(df_b).encode(
            x=alt.X('Year:O', title='School Year'),
            y=alt.Y('Pct Met Above:Q', title='% Met & Above (grade 3-5 mean)',
                    scale=alt.Scale(domain=[55, 95])),
            color=alt.Color('Name:N',
                scale=alt.Scale(
                    domain=['Lincoln', 'Franklin', 'Hoover', 'McKinley', 'Roosevelt', 'Washington'],
                    range=[LINCOLN_COLOR, '#10B981', '#0891B2', '#9CA3AF', '#F87171', '#F59E0B'],
                ),
                legend=alt.Legend(orient='bottom', columns=3, title=None)),
            strokeWidth=alt.condition(alt.datum.Name == 'Lincoln', alt.value(3.5), alt.value(1.5)),
            opacity=alt.condition(alt.datum.Name == 'Lincoln', alt.value(1.0), alt.value(0.7)),
            tooltip=['Year:O', 'Name:N', alt.Tooltip('Pct Met Above:Q', format='.1f', title='% Met+Above')],
        )
        return alt.layer(
            base.mark_line(),
            base.mark_point(size=55, filled=True),
        ).properties(
            width=520, height=340,
            title=alt.TitleParams(f'{subject} — Burlingame elementaries (Lincoln bolded)',
                                  dy=-8, fontSize=13, anchor='start'),
            padding={'top': 35, 'bottom': 10, 'left': 5, 'right': 10},
        )

    ela_col, math_col = st.columns(2)
    with ela_col:
        st.altair_chart(configure(burl_chart('ELA')), width='stretch')
    with math_col:
        st.altair_chart(configure(burl_chart('Math')), width='stretch')

    st.markdown('### Within California (percentile rank of all elementary schools)')

    def ca_rank_chart(subject):
        rank_df = ca_percentile_for_lincoln(subject)
        y_scale = alt.Scale(domain=[85, 100])
        rule_95 = alt.Chart(pd.DataFrame({'y': [95]})).mark_rule(
            color=PCT_COLORS[95], strokeDash=[4, 3], opacity=0.6,
        ).encode(y=alt.Y('y:Q', scale=y_scale))
        rule_90 = alt.Chart(pd.DataFrame({'y': [90]})).mark_rule(
            color=PCT_COLORS[90], strokeDash=[4, 3], opacity=0.6,
        ).encode(y=alt.Y('y:Q', scale=y_scale))
        base = alt.Chart(rank_df).encode(
            x=alt.X('Year:O', title='School Year'),
            y=alt.Y('CA percentile:Q',
                    title='Lincoln CA percentile rank',
                    scale=y_scale),
            tooltip=['Year:O',
                     alt.Tooltip('CA percentile:Q', format='.1f', title='CA percentile'),
                     alt.Tooltip('Lincoln:Q', format='.1f', title='Lincoln % Met+Above')],
        )
        return alt.layer(
            rule_95, rule_90,
            base.mark_line(color=LINCOLN_COLOR, strokeWidth=2.5),
            base.mark_point(color=LINCOLN_COLOR, size=70, filled=True),
        ).properties(
            width=520, height=320,
            title=alt.TitleParams(f'{subject} — Lincoln rank among CA elementaries',
                                  dy=-8, fontSize=13, anchor='start'),
            padding={'top': 35, 'bottom': 10, 'left': 5, 'right': 10},
        ), rank_df

    ela_col, math_col = st.columns(2)
    ela_chart, ela_rank_df = ca_rank_chart('ELA')
    math_chart, math_rank_df = ca_rank_chart('Math')
    with ela_col:
        st.altair_chart(configure(ela_chart), width='stretch')
    with math_col:
        st.altair_chart(configure(math_chart), width='stretch')

    ela_latest = ela_rank_df.sort_values('Year').iloc[-1]
    math_latest = math_rank_df.sort_values('Year').iloc[-1]

    with st.container(border=True):
        st.markdown(
            f'**Analysis.** Within Burlingame School District, Lincoln sits in the '
            f'**upper-middle of six elementaries** — typically 3rd-best behind Franklin and '
            f'Hoover, and above McKinley, Roosevelt, and Washington. Franklin and Hoover have '
            f'higher percentages meeting standards, but they are also smaller schools serving '
            f'more affluent attendance areas; the three schools below Lincoln serve higher-FRPM '
            f'populations. The **district-wide "decline" reported in many SEDA summaries is '
            f'largely driven by McKinley, Roosevelt, and Washington — not by Lincoln**.\n\n'
            f'Within California, Lincoln is **in the top 5%** every single year of available '
            f'data. In 2025, Lincoln scored **{ela_latest["Lincoln"]:.1f}%** Met+Above in ELA '
            f'(**{ela_latest["CA percentile"]:.0f}th percentile**) and '
            f'**{math_latest["Lincoln"]:.1f}%** in Math '
            f'(**{math_latest["CA percentile"]:.0f}th percentile**). Math dropped from roughly '
            f'the 97th to the 95th percentile between 2019 and 2022 — a small relative slide '
            f'that has since stabilized.\n\n'
            f'**Read the chart.** In the Burlingame chart, look at how the spread between '
            f"schools opens up after 2019 — that's the district-level \"decline\" story being "
            f'driven entirely by the lower three schools, while Lincoln, Franklin, and Hoover '
            f'stay close to their pre-COVID levels.'
        )


# ── TAB 3: Lincoln to BIS transition ──────────────────────────────────────────

with tab_bis:
    st.markdown(
        'After 5th grade, every Lincoln student moves to **Burlingame Intermediate (BIS)** '
        'for grades 6-8. BIS is the *single most important* downstream context for any K-5 '
        'Lincoln parent — it is where the entire district consolidates.'
    )

    def bis_chart(subject, metric_col, label, y_domain):
        sub = bis[bis['Subject'] == subject].dropna(subset=[metric_col]).copy()
        sub['Grade'] = 'Grade ' + sub['Grade'].astype(str)
        base = alt.Chart(sub).encode(
            x=alt.X('Year:O', title='School Year'),
            y=alt.Y(f'{metric_col}:Q', title=label, scale=alt.Scale(domain=y_domain)),
            color=alt.Color('Grade:N',
                scale=alt.Scale(
                    domain=['Grade 6', 'Grade 7', 'Grade 8'],
                    range=[GRADE_COLORS['Grade 6'], GRADE_COLORS['Grade 7'], GRADE_COLORS['Grade 8']],
                ),
                legend=alt.Legend(orient='bottom', title=None)),
            tooltip=['Year:O', 'Grade:N', alt.Tooltip(f'{metric_col}:Q', format='.1f', title=label)],
        )
        return alt.layer(
            base.mark_line(strokeWidth=2.5),
            base.mark_point(size=55, filled=True),
        ).properties(
            width=520, height=320,
            title=alt.TitleParams(f'{subject} — BIS {label}', dy=-8, fontSize=13, anchor='start'),
            padding={'top': 35, 'bottom': 10, 'left': 5, 'right': 10},
        )

    st.markdown('#### % Exceeded by grade (the high-achiever measure)')
    ela_col, math_col = st.columns(2)
    with ela_col:
        st.altair_chart(configure(
            bis_chart('ELA', 'Percentage Standard Exceeded', '% Exceeded', [30, 55])
        ), width='stretch')
    with math_col:
        st.altair_chart(configure(
            bis_chart('Math', 'Percentage Standard Exceeded', '% Exceeded', [35, 65])
        ), width='stretch')

    st.markdown('#### % Met & Above by grade')
    ela_col, math_col = st.columns(2)
    with ela_col:
        st.altair_chart(configure(
            bis_chart('ELA', 'Percentage Standard Met and Above', '% Met & Above', [65, 90])
        ), width='stretch')
    with math_col:
        st.altair_chart(configure(
            bis_chart('Math', 'Percentage Standard Met and Above', '% Met & Above', [55, 85])
        ), width='stretch')

    @st.cache_data(show_spinner=False)
    def bis_pre_post_table():
        rows = []
        for subj in ['ELA', 'Math']:
            for g in ['6', '7', '8']:
                sub = bis[(bis['Subject'] == subj) & (bis['Grade'] == g)]
                pre = sub[sub['Year'].isin(PRE_YEARS)].dropna(
                    subset=['Percentage Standard Exceeded', 'Students with Scores'])
                post = sub[sub['Year'].isin(POST_YEARS)].dropna(
                    subset=['Percentage Standard Exceeded', 'Students with Scores'])
                if pre.empty or post.empty:
                    continue
                pre_n = pre['Students with Scores'].sum()
                post_n = post['Students with Scores'].sum()
                pre_w = (pre['Percentage Standard Exceeded'] * pre['Students with Scores']).sum() / pre_n
                post_w = (post['Percentage Standard Exceeded'] * post['Students with Scores']).sum() / post_n
                z = prop_z(pre_w, pre_n, post_w, post_n)
                rows.append({
                    'Subject': subj,
                    'Grade': f'Grade {g}',
                    'Pre-COVID': f'{pre_w:.1f}%',
                    'Post-COVID': f'{post_w:.1f}%',
                    'Change': f'{post_w - pre_w:+.1f}pp',
                    'z': f'{z:.2f}',
                    'Meaningful?': 'Yes' if abs(z) > 2 else 'No',
                })
        return pd.DataFrame(rows)

    st.markdown('#### Pre-COVID vs post-COVID at BIS — high-achiever share (% Exceeded)')
    st.dataframe(bis_pre_post_table(), hide_index=True, width='stretch')

    with st.container(border=True):
        st.markdown(
            '**Analysis.** Unlike Lincoln K-5, **BIS shows real post-COVID weakness** in two '
            'specific places: **grade 6 and grade 7**. High-achiever share in ELA dropped by '
            'roughly **10 percentage points** in both 6th and 7th grade, and grade 7 math also '
            'lost roughly **9 percentage points**. Both changes exceed the 2-standard-error '
            'threshold with N ≈ 370 students per grade — they are not noise.\n\n'
            'Grade 8 numbers are **flat or slightly improved**, which is consistent with one of '
            'two stories: either the dip is "transition shock" that cohorts grow out of by 8th '
            'grade, or the 8th-grade tested population is different (different students elected '
            'to test or are placed in different tracks). The data cannot distinguish between '
            'those two possibilities.\n\n'
            ':material/lightbulb: **What this means for a Lincoln parent of a high-achieving '
            'child:** the K-5 years at Lincoln look fine and the data does not support '
            'transferring schools for elementary. But the **6th- and 7th-grade transition into '
            'BIS is where a real signal lives**. Worth investigating: what changed at BIS '
            'post-2019? Curriculum? Math placement practices? Staffing? Those questions are '
            '*not* answerable from CAASPP scores alone — they require talking to current BIS '
            "families and looking at BIS's GATE/acceleration pathways."
        )


# ── FOOTER: What this can / cannot tell you ───────────────────────────────────

st.divider()
st.markdown('#### :material/help_outline: What this analysis can and cannot tell you')

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.markdown(
            '<div style="font-size:0.88rem; line-height:1.5">'
            '<div style="margin-bottom:0.4rem; color:#16A34A; font-weight:600">'
            '✓ The data does support:</div>'
            '<ul style="margin:0; padding-left:1.1rem">'
            '<li>Lincoln K-5 % Met+Above is stable pre vs post-COVID (no statistical decline).</li>'
            f'<li>Lincoln K-5 % Exceeded in math has <i>increased</i> '
            f'({math_exc["pre"]:.1f}% → {math_exc["post"]:.1f}%, z = {math_exc["z"]:.2f}).</li>'
            '<li>Lincoln is in the top 5% of California elementaries every year since 2015.</li>'
            '<li>The district-level decline is concentrated in Roosevelt, Washington, and McKinley.</li>'
            '<li>BIS high-achiever shares in 6th and 7th grade ELA dropped ~10pp post-COVID.</li>'
            '</ul></div>',
            unsafe_allow_html=True,
        )
with c2:
    with st.container(border=True):
        st.markdown(
            '<div style="font-size:0.88rem; line-height:1.5">'
            '<div style="margin-bottom:0.4rem; color:#D97706; font-weight:600">'
            '⚠ The data cannot tell you:</div>'
            '<ul style="margin:0; padding-left:1.1rem">'
            "<li>Whether your specific child's learning has changed.</li>"
            '<li>Whether high-achievers at Lincoln are being adequately challenged '
            '(no within-school distributional data).</li>'
            '<li>Whether subgroup-level changes are happening at Lincoln '
            '(subgroup cells suppressed below n=11).</li>'
            '<li>What is causing the BIS dip (curriculum? staffing? remote-era cohorts?).</li>'
            '<li>How Lincoln teachers or principals are performing.</li>'
            '</ul></div>',
            unsafe_allow_html=True,
        )

st.caption(
    'Sources: California CAASPP (Smarter Balanced) school-level results, 2014-15 through '
    '2024-25 · Stanford Education Data Archive (SEDA) 2025.1, district-level. '
    'See the "School (CAASPP)" and "District (SEDA)" pages for the underlying data.'
)
