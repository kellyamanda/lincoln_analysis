"""Lincoln Overview — the hero summary page.

Just the bottom line and four headline metric cards.
Drill-down lives on the "Lincoln Analysis" page.
"""
import numpy as np
import pandas as pd
import streamlit as st

from shared import data as D


# ── Header ────────────────────────────────────────────────────────────────────

st.title(':material/insights: Lincoln Elementary — Overview')
st.caption(
    'A one-glance summary of Lincoln Elementary K-5 academic performance. '
    'For trend charts, peer comparisons, and the BIS transition deep-dive, see "Lincoln Analysis".'
)


# ── Data + helpers ────────────────────────────────────────────────────────────

lincoln_full = D.load_lincoln_full()
caaspp = D.load_caaspp()

PRE_YEARS = [2015, 2016, 2017, 2018, 2019]
POST_YEARS = [2022, 2023, 2024, 2025]
LATEST_YEAR = 2025
COMPARE_YEAR = 2019  # baseline for "Lincoln in California" delta


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
def ca_percentile_for_lincoln(subject):
    """Lincoln's CA percentile rank each year (grade 3-5 mean of % Met+Above)."""
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
                     'CA percentile': rank, 'N schools': len(pool)})
    return pd.DataFrame(rows)


ela_pool  = lincoln_pooled('ELA',  'Percentage Standard Met and Above')
ela_exc   = lincoln_pooled('ELA',  'Percentage Standard Exceeded')
math_pool = lincoln_pooled('Math', 'Percentage Standard Met and Above')
math_exc  = lincoln_pooled('Math', 'Percentage Standard Exceeded')

ela_rank = ca_percentile_for_lincoln('ELA')
math_rank = ca_percentile_for_lincoln('Math')


def rank_row(rank_df, year):
    row = rank_df[rank_df['Year'] == year]
    return row.iloc[0] if not row.empty else None


def ordinal(n):
    n = int(round(n))
    if 10 <= n % 100 <= 20:
        suf = 'th'
    else:
        suf = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suf}'


# ── Hero card: plain-English bottom line ──────────────────────────────────────

with st.container(border=True):
    st.markdown(
        '### :material/insights: The bottom line for Lincoln Elementary, K-5\n'
        '**Lincoln students are doing well.** Performance is essentially flat through the '
        'COVID era — neither subject shows a statistically meaningful change pre- vs. '
        'post-COVID. Lincoln consistently ranks in the **top 5% of California elementary '
        'schools** in both ELA and Math. The share of *high-achieving* students '
        '(% Exceeded Standards) in **math has actually increased** since pre-COVID.\n\n'
        ':material/warning: **The bigger question for parents** is what happens at '
        '**Burlingame Intermediate (BIS)** after 5th grade — that is the part of the '
        'district where high-achiever performance has dipped post-COVID, especially in '
        'grades 6-7 ELA. See "Lincoln Analysis" → "Lincoln to BIS transition".'
    )

st.html('<div style="height:14px"></div>')


# ── Side-by-side: K-5 performance | Where Lincoln sits in California ─────────

ela_latest = rank_row(ela_rank, LATEST_YEAR)
ela_baseline = rank_row(ela_rank, COMPARE_YEAR)
math_latest = rank_row(math_rank, LATEST_YEAR)
math_baseline = rank_row(math_rank, COMPARE_YEAR)

ela_lo, ela_hi = ela_rank['CA percentile'].min(), ela_rank['CA percentile'].max()
math_lo, math_hi = math_rank['CA percentile'].min(), math_rank['CA percentile'].max()

left_col, right_col = st.columns(2)

# --- LEFT: Lincoln K-5 academic performance ---
with left_col:
    with st.container(border=True):
        st.markdown('### :material/school: Lincoln K-5 academic performance')

        r1c1, r1c2 = st.columns(2)
        r1c1.metric(
            ':material/menu_book: ELA — % Met & Above',
            f"{ela_pool['post']:.1f}%",
            delta=f"{ela_pool['diff']:+.1f}pp vs pre-COVID",
            help=f"Pre={ela_pool['pre']:.1f}%, post={ela_pool['post']:.1f}%, z={ela_pool['z']:.2f}",
        )
        r1c2.metric(
            ':material/menu_book: ELA — % Exceeded (top tier)',
            f"{ela_exc['post']:.1f}%",
            delta=f"{ela_exc['diff']:+.1f}pp vs pre-COVID",
            help=f"z={ela_exc['z']:.2f}",
        )
        r2c1, r2c2 = st.columns(2)
        r2c1.metric(
            ':material/calculate: Math — % Met & Above',
            f"{math_pool['post']:.1f}%",
            delta=f"{math_pool['diff']:+.1f}pp vs pre-COVID",
            help=f"z={math_pool['z']:.2f}",
        )
        r2c2.metric(
            ':material/calculate: Math — % Exceeded (top tier)',
            f"{math_exc['post']:.1f}%",
            delta=f"{math_exc['diff']:+.1f}pp vs pre-COVID",
            help=f"z={math_exc['z']:.2f}",
        )

        st.caption(
            ':material/info: Cards compare 2014-15 to 2018-19 weighted mean '
            '("pre-COVID") against 2021-22 to 2024-25 ("post-COVID"). '
            'z > 2 = change exceeds the 95% confidence band. Hover for full numbers. '
            'Source: California CAASPP school-level data.'
        )

# --- RIGHT: Where Lincoln sits in California ---
with right_col:
    with st.container(border=True):
        st.markdown('### :material/leaderboard: Where Lincoln sits in California')

        rc1, rc2 = st.columns(2)
        if ela_latest is not None:
            rc1.metric(
                ':material/menu_book: ELA — CA percentile rank (2024-25)',
                ordinal(ela_latest['CA percentile']),
                delta=(f"{ela_latest['CA percentile'] - ela_baseline['CA percentile']:+.0f} pts vs {COMPARE_YEAR}"
                       if ela_baseline is not None else None),
                help=(f"Lincoln scored {ela_latest['Lincoln']:.1f}% Met+Above in 2024-25. "
                      f"Among {int(ela_latest['N schools']):,} CA elementaries with reported "
                      f"grade 3-5 ELA data, Lincoln ranks at the "
                      f"{ordinal(ela_latest['CA percentile'])} percentile."),
            )
        if math_latest is not None:
            rc2.metric(
                ':material/calculate: Math — CA percentile rank (2024-25)',
                ordinal(math_latest['CA percentile']),
                delta=(f"{math_latest['CA percentile'] - math_baseline['CA percentile']:+.0f} pts vs {COMPARE_YEAR}"
                       if math_baseline is not None else None),
                help=(f"Lincoln scored {math_latest['Lincoln']:.1f}% Met+Above in 2024-25. "
                      f"Among {int(math_latest['N schools']):,} CA elementaries with reported "
                      f"grade 3-5 Math data, Lincoln ranks at the "
                      f"{ordinal(math_latest['CA percentile'])} percentile."),
            )

        # Spacer the height of one metric row, so this 2-card container matches
        # the 4-card container's overall height and the captions line up at the bottom.
        st.html('<div style="height:75px"></div>')

        st.caption(
            f':material/info: Among all California elementary schools with reported '
            f'grade 3-5 data. Across every year on record (2015-2025), Lincoln has '
            f'ranked between the **{ordinal(ela_lo)}–{ordinal(ela_hi)} percentile** in '
            f'ELA and the **{ordinal(math_lo)}–{ordinal(math_hi)} percentile** in Math '
            f'— top 5% of California elementary schools every single year.'
        )


# ── Beyond test scores: staffing, attendance, spending ────────────────────────
# CA benchmarks (see the detail pages for sourcing): student/teacher ratio from CDE
# 2024-25 Certificated Staff Reports; elementary per-pupil from CDE ESSA PPE 2023-24.
CA_RATIO = 20.8
CA_PPE_ELEM = 19450

staff = D.load_staffing()
absent = D.load_absenteeism()
spend = D.load_spending()

if not staff.empty and not absent.empty and not spend.empty:
    st.html('<div style="height:14px"></div>')

    elem_staff = staff[staff['grade_span'] == 'GS_K6']
    s_latest = elem_staff[elem_staff['school_year_end'] == elem_staff['school_year_end'].max()]
    lin_ratio = s_latest[s_latest['school_code'] == D.LINCOLN_SCHOOL_CODE]['stu_tch_ratio'].iloc[0]
    ratio_rank = int((s_latest['stu_tch_ratio'] < lin_ratio).sum()) + 1
    n_elem = len(s_latest)

    ab_tot = absent[(absent['category_code'] == 'TA') & (absent['level'] == 'school')]
    ab_latest = ab_tot[ab_tot['school_year_end'] == ab_tot['school_year_end'].max()]
    lin_abs = ab_latest[ab_latest['school_code'] == D.LINCOLN_SCHOOL_CODE]['chronic_rate'].iloc[0]
    abs_rank = int((ab_latest['chronic_rate'] < lin_abs).sum()) + 1
    ca_abs = absent[absent['level'] == 'state']
    ca_abs = ca_abs[ca_abs['school_year_end'] == ca_abs['school_year_end'].max()]['chronic_rate'].iloc[0]

    sp_latest = spend[spend['school_year_end'] == spend['school_year_end'].max()]
    lin_ppe = sp_latest[sp_latest['school_code'] == D.LINCOLN_SCHOOL_CODE]['total_ppe'].iloc[0]
    ppe_rank = int((sp_latest['total_ppe'] > lin_ppe).sum()) + 1

    with st.container(border=True):
        st.markdown(
            '### :material/dashboard: Beyond test scores: the fuller picture\n'
            'Three more dimensions of how Lincoln operates, each compared against its 5 sister '
            'Burlingame elementaries and the California average. See the dedicated pages for detail.'
        )

        b1, b2, b3 = st.columns(3)
        b1.metric(
            ':material/groups: Class size (students per teacher)',
            f'{lin_ratio:.1f}',
            delta=f'{lin_ratio - CA_RATIO:+.1f} vs CA avg ({CA_RATIO})',
            delta_color='inverse',
            help=f'CDE staffing ratio (a class-size proxy — counts all teacher FTE). '
                 f'Lincoln is {ordinal(ratio_rank)}-smallest of {n_elem} Burlingame elementaries; '
                 f'slightly above the CA average.',
        )
        b2.metric(
            ':material/event_busy: Chronic absenteeism',
            f'{lin_abs:.1f}%',
            delta=f'{lin_abs - ca_abs:+.1f} pp vs CA ({ca_abs:.1f}%)',
            delta_color='inverse',
            help=f'Lincoln has the {ordinal(abs_rank)}-lowest chronic absenteeism of '
                 f'{n_elem} Burlingame elementaries, and a fraction of the statewide rate.',
        )
        b3.metric(
            ':material/payments: Per-pupil spending',
            f'${lin_ppe:,.0f}',
            help=f'CA elementary average is \\${CA_PPE_ELEM:,}; Lincoln is '
                 f'{ordinal(ppe_rank)}-highest of {n_elem} locally. Spending largely tracks '
                 f'student need (low-poverty districts draw less LCFF/Title I), so higher or '
                 f'lower is not inherently better.',
        )

        st.caption(
            ':material/lightbulb: **Takeaway:** Lincoln pairs top-5% academics with the '
            'district\'s lowest chronic absenteeism, on below-average per-pupil funding — while '
            'carrying slightly larger-than-average class sizes. Spending and class size reflect '
            'its low-poverty enrollment more than school decisions.'
        )
