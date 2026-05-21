"""School-level CAASPP view — ported from school_scores/app.py."""
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

from shared import data as D
from shared.theme import (
    LINCOLN_COLOR, PCT_COLORS, GRADE_COLORS, configure,
)

SUBGROUP_NAMES = {
    '1':   'All Students',
    '3':   'Male',
    '4':   'Female',
    '28':  'Hispanic or Latino',
    '74':  'Asian',
    '75':  'Black or African American',
    '76':  'Filipino',
    '78':  'White',
    '79':  'Two or More Races',
    '160': 'Economically Disadvantaged',
    '180': 'English Learners',
    '200': 'Students with Disabilities',
}

SUBCAT_GROUPS = {
    'Race / Ethnicity': ['All Students', 'Hispanic or Latino', 'Asian',
                         'Black or African American', 'Filipino', 'White',
                         'Two or More Races'],
    'Socioeconomic':    ['All Students', 'Economically Disadvantaged'],
    'Gender':           ['All Students', 'Male', 'Female'],
    'English Learners': ['All Students', 'English Learners'],
    'Disability':       ['All Students', 'Students with Disabilities'],
}

# Lincoln-blue + balanced palette for subgroup line colors (Altair will pick by index)
SUBGROUP_PALETTE = [
    '#2563EB',  # All Students — Lincoln blue
    '#16A34A',  # green
    '#D97706',  # amber
    '#7C3AED',  # purple
    '#DC2626',  # red
    '#0891B2',  # cyan
    '#DB2777',  # pink
    '#B45309',  # brown
]


df = D.load_caaspp()
sg_df = D.load_caaspp_subgroups()

years = sorted(df['Year'].unique())
grades = ['3', '4', '5']
subjects = ['ELA', 'Math']
GRADE_COLOR_PAIRS = {'Grade 3': '#2563EB', 'Grade 4': '#F59E0B', 'Grade 5': '#10B981'}


@st.cache_data(show_spinner=False)
def compute_percentiles(subject, grade):
    rows = []
    for year, grp in df[(df['Subject'] == subject) & (df['Grade'] == str(grade))].groupby('Year'):
        pool = grp['Pct Met Above'].dropna()
        if len(pool) < 10:
            continue
        for p in [25, 50, 75, 90, 95]:
            rows.append({'Year': year, 'Percentile': p, 'Value': float(np.percentile(pool, p))})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def compute_lincoln_rank(subject, grade):
    rows = []
    lincoln = df[df['is_lincoln'] & (df['Subject'] == subject) & (df['Grade'] == str(grade))]
    for year, grp in df[(df['Subject'] == subject) & (df['Grade'] == str(grade))].groupby('Year'):
        pool = grp['Pct Met Above'].dropna()
        lrow = lincoln[lincoln['Year'] == year]
        if len(lrow) == 0 or pool.empty:
            continue
        lv = lrow['Pct Met Above'].iloc[0]
        if pd.isna(lv):
            continue
        rank = float((pool < lv).mean() * 100)
        rows.append({'Year': year, 'Percentile Rank': rank, 'Pct Met Above': lv})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def compute_cohorts(subject):
    available_years = set(df['Year'].unique())
    grade_map = {'3': 0, '4': 1, '5': 2}
    rows = []
    for start_year in sorted(available_years):
        for grade, offset in grade_map.items():
            test_year = start_year + offset
            if test_year not in available_years:
                continue
            pool = df[(df['Year'] == test_year) & (df['Subject'] == subject) & (df['Grade'] == grade)]['Pct Met Above'].dropna()
            if len(pool) < 10:
                continue
            lincoln_row = df[df['is_lincoln'] & (df['Year'] == test_year) & (df['Subject'] == subject) & (df['Grade'] == grade)]['Pct Met Above']
            lincoln_val = float(lincoln_row.iloc[0]) if not lincoln_row.empty and pd.notna(lincoln_row.iloc[0]) else None
            lincoln_pct = float((pool < lincoln_val).mean() * 100) if lincoln_val is not None else None
            rows.append({
                'Cohort': str(start_year),
                'Grade': int(grade),
                'Test Year': test_year,
                'Lincoln %': lincoln_val,
                'Lincoln Pct Rank': lincoln_pct,
                **{f'p{p}': float(np.percentile(pool, p)) for p in [25, 50, 75, 90, 95]},
            })
    return pd.DataFrame(rows)


RANK_REF_PCTS = [50, 75, 90, 95]


def make_rank_chart(subject, grade):
    lincoln_df = compute_lincoln_rank(subject, grade)
    all_years = lincoln_df['Year'].tolist()

    rows = [{'Year': yr, 'Value': row['Percentile Rank'], 'Series': 'Lincoln',
             'tip': f"{row['Pct Met Above']:.1f}% Met Above"}
            for yr, (_, row) in zip(all_years, lincoln_df.iterrows())]
    for p in RANK_REF_PCTS:
        for yr in all_years:
            rows.append({'Year': yr, 'Value': p, 'Series': f'{p}th pct', 'tip': f'{p}th percentile threshold'})
    combined = pd.DataFrame(rows)

    domain = ['Lincoln'] + [f'{p}th pct' for p in RANK_REF_PCTS]
    range_colors = [LINCOLN_COLOR] + [PCT_COLORS[p] for p in RANK_REF_PCTS]

    base = alt.Chart(combined).encode(
        x=alt.X('Year:O', title='School Year'),
        y=alt.Y('Value:Q', title='CA Percentile Rank', scale=alt.Scale(domain=[45, 100])),
        color=alt.Color('Series:N',
                        scale=alt.Scale(domain=domain, range=range_colors),
                        legend=alt.Legend(title='Series', orient='bottom', columns=3)),
        strokeDash=alt.condition(alt.datum.Series == 'Lincoln', alt.value([1, 0]), alt.value([4, 3])),
        strokeWidth=alt.condition(alt.datum.Series == 'Lincoln', alt.value(2.5), alt.value(1.3)),
        opacity=alt.condition(alt.datum.Series == 'Lincoln', alt.value(1.0), alt.value(0.75)),
        tooltip=['Year:O', 'Series:N', alt.Tooltip('Value:Q', format='.0f', title='Value')],
    )

    return alt.layer(
        base.mark_line(),
        base.mark_point(filled=True, size=60).transform_filter(alt.datum.Series == 'Lincoln'),
    ).properties(
        width=560, height=280,
        title=alt.TitleParams(f'CA Percentile Rank — {subject} Grade {grade}', dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5},
    )


def make_score_chart(subject, grade, show_bands):
    pct_df = compute_percentiles(subject, grade)
    lincoln_df = compute_lincoln_rank(subject, grade)

    pct_filtered = pct_df[pct_df['Percentile'].isin(show_bands)].copy()
    pct_filtered['Label'] = pct_filtered['Percentile'].astype(str) + 'th pct'

    bands = alt.Chart(pct_filtered).mark_line(strokeDash=[4, 3], opacity=0.8).encode(
        x=alt.X('Year:O', title='School Year'),
        y=alt.Y('Value:Q', title='% Standard Met and Above',
                scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('Label:N', scale=alt.Scale(
            domain=[f'{p}th pct' for p in show_bands],
            range=[PCT_COLORS[p] for p in show_bands],
        ), legend=alt.Legend(title='CA Benchmarks', orient='bottom', columns=3)),
        strokeWidth=alt.value(1.5),
        tooltip=['Year:O', 'Label:N', alt.Tooltip('Value:Q', format='.1f', title='% Met Above')],
    )
    line = alt.Chart(lincoln_df).mark_line(color=LINCOLN_COLOR, strokeWidth=2.5).encode(
        x='Year:O',
        y=alt.Y('Pct Met Above:Q', scale=alt.Scale(domain=[0, 100])),
        tooltip=['Year:O', alt.Tooltip('Pct Met Above:Q', format='.1f', title='Lincoln % Met Above')],
    )
    points = alt.Chart(lincoln_df).mark_point(color=LINCOLN_COLOR, size=70, filled=True).encode(
        x='Year:O', y='Pct Met Above:Q')

    return alt.layer(bands, line, points).properties(
        width=560, height=280,
        title=alt.TitleParams(f'% Standard Met and Above — {subject} Grade {grade}', dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5},
    )


def make_trend_chart(subject, grade_sel):
    rows = []
    for g in grade_sel:
        ldf = compute_lincoln_rank(subject, g)
        ldf['Grade'] = f'Grade {g}'
        rows.append(ldf)
    if not rows:
        return None
    trend_df = pd.concat(rows)

    base = alt.Chart(trend_df).encode(
        x=alt.X('Year:O', title='School Year'),
        y=alt.Y('Percentile Rank:Q', title='CA Percentile Rank', scale=alt.Scale(domain=[50, 100])),
        color=alt.Color('Grade:N', scale=alt.Scale(
            domain=list(GRADE_COLOR_PAIRS.keys()),
            range=list(GRADE_COLOR_PAIRS.values()),
        )),
        tooltip=['Year:O', 'Grade:N',
                 alt.Tooltip('Percentile Rank:Q', format='.0f', title='Percentile Rank'),
                 alt.Tooltip('Pct Met Above:Q', format='.1f', title='% Met Above')],
    )

    rule_90 = alt.Chart(pd.DataFrame({'y': [90]})).mark_rule(
        color='#10B981', strokeDash=[4, 3], opacity=0.6).encode(y='y:Q')
    rule_95 = alt.Chart(pd.DataFrame({'y': [95]})).mark_rule(
        color='#F59E0B', strokeDash=[4, 3], opacity=0.6).encode(y='y:Q')

    return alt.layer(
        rule_90, rule_95,
        base.mark_line(strokeWidth=2.5),
        base.mark_point(size=70, filled=True),
    ).properties(width=560, height=380, title=f'Lincoln Percentile Rank — {subject}')


# ── Page ──────────────────────────────────────────────────────────────────────

st.title(':material/school: Lincoln Elementary — CAASPP School-Level Data')
st.caption('2014–15 through 2024–25 · Smarter Balanced · % Standard Met and Above')

tab_lincoln, tab_subgroup, tab_trends, tab_cohort = st.tabs([
    ':material/home: Lincoln Over Time',
    ':material/group: Subgroup Analysis',
    ':material/trending_up: Grade Comparison',
    ':material/timeline: Cohort Tracking',
])


with tab_lincoln:
    grade_l = st.segmented_control('Grade', options=grades, format_func=lambda g: f'Grade {g}',
                                   default=grades[0], key='grade_l')
    show_bands = [25, 50, 75, 90, 95]
    ela_col, math_col = st.columns(2)

    for col, subject in [(ela_col, 'ELA'), (math_col, 'Math')]:
        ldf = compute_lincoln_rank(subject, grade_l)
        pct_df_l = compute_percentiles(subject, grade_l)
        latest_year = max(years)
        latest = ldf[ldf['Year'] == latest_year].iloc[0] if not ldf[ldf['Year'] == latest_year].empty else None
        prev = ldf[ldf['Year'] == sorted(years)[-2]].iloc[0] if len(ldf) >= 2 else None
        latest_pcts = pct_df_l[pct_df_l['Year'] == latest_year].set_index('Percentile')['Value'].to_dict()

        with col:
            with st.container(border=True):
                st.markdown(f'<h2 style="font-size:1.7rem;font-weight:700;margin:0 0 0.6rem 0">{subject}</h2>',
                            unsafe_allow_html=True)
                st.altair_chart(configure(make_rank_chart(subject, grade_l)), width='stretch')
                st.altair_chart(configure(make_score_chart(subject, grade_l, show_bands)), width='stretch')

                st.markdown('**2024–25 Lincoln Results**')
                if latest is not None:
                    c1, c2 = st.columns(2)
                    c1.metric(
                        '% Standard Met & Above',
                        f"{latest['Pct Met Above']:.1f}%",
                        delta=f"{latest['Pct Met Above'] - prev['Pct Met Above']:.1f}pp vs prior year" if prev is not None else None,
                    )
                    c2.metric(
                        'CA Percentile Rank',
                        f"{latest['Percentile Rank']:.0f}th",
                        delta=f"{latest['Percentile Rank'] - prev['Percentile Rank']:.0f}pts vs prior year" if prev is not None else None,
                    )

                st.markdown('**CA Benchmark Values (2024–25)**')
                p_cols = st.columns(5)
                for pcol, p in zip(p_cols, [25, 50, 75, 90, 95]):
                    val = latest_pcts.get(p)
                    display = f'{val:.1f}%' if val else '—'
                    pcol.markdown(
                        f'<div style="font-size:0.72rem;color:#6B7280;margin-bottom:2px">{p}th pct</div>'
                        f'<div style="font-size:1rem;font-weight:600">{display}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown('<div style="height:5px"></div>', unsafe_allow_html=True)


with tab_subgroup:
    available_subgroups = sorted(sg_df['Subgroup'].dropna().unique())
    suppressed = [s for s in SUBGROUP_NAMES.values()
                  if s not in available_subgroups and s != 'All Students']

    group_by = st.segmented_control(
        'Compare by', list(SUBCAT_GROUPS.keys()),
        default='Race / Ethnicity', key='sg_groupby',
    )
    grade_sg = st.segmented_control(
        'Grade', options=grades, format_func=lambda g: f'Grade {g}',
        default=grades[0], key='grade_sg',
    )

    options_in_cat = [s for s in SUBCAT_GROUPS[group_by] if s in available_subgroups]
    selected_sgs = st.pills(
        'Subgroups', options_in_cat,
        selection_mode='multi',
        default=options_in_cat,        # all subgroups in category selected by default
        key=f'sg_pills_{group_by}',    # reset selection when category changes
    )
    if not selected_sgs:
        selected_sgs = options_in_cat

    if not selected_sgs:
        st.info('No reportable subgroups in this category for this grade.')
    else:
        ela_col, math_col = st.columns(2)
        for col, subject in [(ela_col, 'ELA'), (math_col, 'Math')]:
            filtered = sg_df[
                (sg_df['Subject'] == subject) &
                (sg_df['Grade'] == str(grade_sg)) &
                (sg_df['Subgroup'].isin(selected_sgs))
            ].dropna(subset=['Pct Met Above'])

            with col:
                st.markdown(f'### {subject}')
                if filtered.empty:
                    st.info('No data for this subject / grade / subgroup combination.')
                    continue
                y_min = max(0, int(filtered['Pct Met Above'].min()) - 10)
                color_domain = options_in_cat
                color_range = SUBGROUP_PALETTE[:len(color_domain)]
                base = alt.Chart(filtered).encode(
                    x=alt.X('Year:O', title='School Year'),
                    y=alt.Y('Pct Met Above:Q', title='% Standard Met and Above',
                            scale=alt.Scale(domain=[y_min, 100])),
                    color=alt.Color('Subgroup:N',
                        scale=alt.Scale(domain=color_domain, range=color_range),
                        legend=alt.Legend(orient='bottom', columns=3, title=None)),
                    tooltip=['Year:O', 'Subgroup:N',
                             alt.Tooltip('Pct Met Above:Q', format='.1f', title='% Met Above')],
                )
                chart = alt.layer(
                    base.mark_line(strokeWidth=2.5),
                    base.mark_point(size=55, filled=True),
                ).properties(
                    width=520, height=340,
                    title=alt.TitleParams(f'{subject} — Grade {grade_sg} by {group_by.lower()}',
                                          dy=-8, fontSize=13, anchor='start'),
                    padding={'top': 35, 'bottom': 10, 'left': 5, 'right': 10},
                )
                st.altair_chart(configure(chart), width='stretch')

    if suppressed:
        st.info(
            f'**Suppressed subgroups** (fewer than 11 students — not reported by CAASPP): '
            f"{', '.join(suppressed)}. "
            'The absence of reported data for groups like Asian and White students does not mean '
            'those groups are absent from Lincoln, only that their cell sizes fall below the '
            "state's privacy threshold in most grade/year combinations."
        )


with tab_trends:
    st.subheader("Lincoln's CA Percentile Rank — All Grades Over Time")
    grade_sel = st.pills('Grades', grades, format_func=lambda g: f'Grade {g}',
                         selection_mode='multi', default=grades, key='grade_t')

    ela_col, math_col = st.columns(2)
    for col, subject in [(ela_col, 'ELA'), (math_col, 'Math')]:
        with col:
            st.markdown(f'### {subject}')
            chart = make_trend_chart(subject, grade_sel)
            if chart:
                st.altair_chart(configure(chart), width='stretch')

    rows_avg = []
    for subject in subjects:
        for g in grade_sel:
            ldf = compute_lincoln_rank(subject, g)
            if not ldf.empty:
                rows_avg.append({
                    'Subject': subject,
                    'Grade': f'Grade {g}',
                    'Avg Rank': f"{ldf['Percentile Rank'].mean():.0f}th",
                    'Min Rank': f"{ldf['Percentile Rank'].min():.0f}th",
                    'Max Rank': f"{ldf['Percentile Rank'].max():.0f}th",
                })
    if rows_avg:
        st.dataframe(pd.DataFrame(rows_avg), hide_index=True, width='stretch')


with tab_cohort:
    st.subheader('Cohort Tracking — Following the Same Class Through Grades 3 → 4 → 5')
    st.caption('Each line tracks one class year as they moved through elementary school. Gaps indicate COVID year (no 2020 testing).')

    metric = st.segmented_control('Show', ['CA Percentile Rank', '% Met and Above'],
                                  default='CA Percentile Rank', key='cohort_metric')

    all_cohort_years = [str(y) for y in range(int(min(years)), int(max(years)) - 1)]
    selected_cohorts = st.pills('Cohort 3rd-grade years', all_cohort_years,
                                selection_mode='multi', default=all_cohort_years, key='cohort_pills')
    if not selected_cohorts:
        selected_cohorts = all_cohort_years

    ela_col, math_col = st.columns(2)

    for col, subject in [(ela_col, 'ELA'), (math_col, 'Math')]:
        cohort_df = compute_cohorts(subject)
        cohort_df = cohort_df[cohort_df['Cohort'].isin(selected_cohorts)].copy()
        cohort_df = cohort_df.dropna(subset=[
            'Lincoln Pct Rank' if metric == 'CA Percentile Rank' else 'Lincoln %'
        ])

        y_field = 'Lincoln Pct Rank' if metric == 'CA Percentile Rank' else 'Lincoln %'
        y_title = "Lincoln's CA Percentile Rank" if metric == 'CA Percentile Rank' else '% Standard Met and Above'

        if metric == 'CA Percentile Rank':
            y_min = max(50, int(cohort_df[y_field].min()) - 5) if not cohort_df.empty else 50
            y_domain = [y_min, 100]
        else:
            y_min = max(0, int(cohort_df[y_field].min()) - 5) if not cohort_df.empty else 60
            y_domain = [y_min, 100]

        n_cohorts = cohort_df['Cohort'].nunique()
        color_scheme = 'tableau10' if n_cohorts <= 10 else 'tableau20'
        y_scale = alt.Scale(domain=y_domain)

        lines = alt.Chart(cohort_df).mark_line(strokeWidth=2.2, point=True).encode(
            x=alt.X('Grade:O', title='Grade', axis=alt.Axis(values=[3, 4, 5], labelAngle=0)),
            y=alt.Y(f'{y_field}:Q', title=y_title, scale=y_scale),
            color=alt.Color('Cohort:N', legend=alt.Legend(title='3rd Grade Year'),
                            scale=alt.Scale(scheme=color_scheme)),
            tooltip=[
                alt.Tooltip('Cohort:N', title='3rd Grade Year'),
                alt.Tooltip('Grade:O', title='Grade'),
                alt.Tooltip('Test Year:O', title='Test Year'),
                alt.Tooltip('Lincoln %:Q', format='.1f', title='Lincoln % Met Above'),
                alt.Tooltip('Lincoln Pct Rank:Q', format='.0f', title='CA Percentile Rank'),
            ],
        )

        if metric == 'CA Percentile Rank':
            rule_90 = alt.Chart(pd.DataFrame({'y': [90]})).mark_rule(
                color='#10B981', strokeDash=[4, 3], opacity=0.5
            ).encode(y=alt.Y('y:Q', scale=y_scale))
            rule_95 = alt.Chart(pd.DataFrame({'y': [95]})).mark_rule(
                color='#F59E0B', strokeDash=[4, 3], opacity=0.5
            ).encode(y=alt.Y('y:Q', scale=y_scale))
            chart_c = alt.layer(rule_90, rule_95, lines)
        else:
            chart_c = lines

        chart_c = chart_c.properties(width=560, height=400, title=f'Cohort Tracking — {subject}')

        with col:
            st.markdown(f'### {subject}')
            st.altair_chart(configure(chart_c), width='stretch')

    with st.expander(':material/table_chart: Cohort data table'):
        for subject in subjects:
            cohort_df = compute_cohorts(subject)
            cohort_df = cohort_df[cohort_df['Cohort'].isin(selected_cohorts)]
            display = cohort_df[['Cohort', 'Grade', 'Test Year', 'Lincoln %', 'Lincoln Pct Rank']].copy()
            display['Lincoln %'] = display['Lincoln %'].map(lambda x: f'{x:.1f}%' if pd.notna(x) else '—')
            display['Lincoln Pct Rank'] = display['Lincoln Pct Rank'].map(lambda x: f'{x:.0f}th' if pd.notna(x) else '—')
            st.markdown(f'**{subject}**')
            st.dataframe(display.rename(columns={'Lincoln Pct Rank': 'CA Rank'}),
                         hide_index=True, width='stretch')
