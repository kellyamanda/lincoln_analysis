"""District-level SEDA view — restyled with Altair to match CAASPP look."""
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

from shared import data as D
from shared.theme import SUBGROUP_COLORS, GRADE_COLORS, LINCOLN_COLOR, GRAY, configure

DISTRICT_NAME = 'Burlingame Elementary'

SUBCAT_GROUPS = {
    'Race / Ethnicity': ['All Students', 'White', 'Black', 'Hispanic', 'Asian', 'Native American'],
    'Socioeconomic':    ['All Students', 'Econ. Disadvantaged', 'Not Econ. Disadvantaged'],
    'Gender':           ['All Students', 'Female', 'Male'],
}

GAP_PAIRS = {
    'White − Black':                       ('White', 'Black'),
    'White − Hispanic':                    ('White', 'Hispanic'),
    'Not Econ. Disadv. − Econ. Disadv.':   ('Not Econ. Disadvantaged', 'Econ. Disadvantaged'),
    'Female − Male':                       ('Female', 'Male'),
}

GRADE_LABELS = {3: '3rd', 4: '4th', 5: '5th', 6: '6th', 7: '7th', 8: '8th'}

SG_COL_MAP = {
    'All Students': 'all', 'White': 'wht', 'Black': 'blk',
    'Hispanic': 'hsp', 'Asian': 'asn', 'Native American': 'nam',
    'Econ. Disadvantaged': 'ecd', 'Not Econ. Disadvantaged': 'nec',
    'Female': 'fem', 'Male': 'mal',
}


# ── Data ──────────────────────────────────────────────────────────────────────

trends = D.burl_seda_trends(D.load_seda_trends())
cohorts = D.burl_seda_cohorts(D.load_seda_cohorts())
demo = D.burl_seda_demo(D.load_seda_demo()).sort_values('year').reset_index(drop=True)
frpm = D.load_frpm()


# ── Analysis helpers ──────────────────────────────────────────────────────────

def trend_stats(series_df, score_col='score', se_col='se', year_col='year'):
    d = series_df[[year_col, score_col, se_col]].dropna(subset=[score_col]).sort_values(year_col)
    if len(d) < 3:
        return None
    ses = d[se_col].fillna(d[se_col].median()).values.astype(float)
    first, last = d.iloc[0], d.iloc[-1]
    total_change = float(last[score_col] - first[score_col])
    pooled_se = float(np.sqrt(first[se_col] ** 2 + last[se_col] ** 2)) if pd.notna(first[se_col]) and pd.notna(last[se_col]) else None
    z = abs(total_change) / pooled_se if pooled_se else None
    significant = z > 2.0 if z is not None else None
    avg_se = float(ses.mean())
    min_detectable = 2 * avg_se
    return dict(
        n_years=len(d),
        first_year=int(first[year_col]),
        last_year=int(last[year_col]),
        first_score=float(first[score_col]),
        last_score=float(last[score_col]),
        total_change=total_change,
        significant=significant,
        z_score=z,
        avg_se=avg_se,
        min_detectable=min_detectable,
    )


def analysis_panel(tab_key, auto_lines):
    with st.expander(':material/insights: Analysis', expanded=True):
        st.markdown(auto_lines)


# ── Chart builders ────────────────────────────────────────────────────────────

def trend_chart(df_sub, title, show_bands, width=560):
    """Multi-subgroup line chart with optional 95% CI bands. df_sub: year, score, se, subgroup_label."""
    chart_layers = []

    if show_bands and 'se' in df_sub.columns and df_sub['se'].notna().any():
        bands = df_sub.copy()
        bands['lower'] = bands['score'] - 1.96 * bands['se']
        bands['upper'] = bands['score'] + 1.96 * bands['se']
        bands_chart = alt.Chart(bands).mark_area(opacity=0.12).encode(
            x='year:O',
            y='lower:Q',
            y2='upper:Q',
            color=alt.Color('subgroup_label:N',
                scale=alt.Scale(
                    domain=list(SUBGROUP_COLORS.keys()),
                    range=list(SUBGROUP_COLORS.values()),
                ),
                legend=None,
            ),
        )
        chart_layers.append(bands_chart)

    base = alt.Chart(df_sub).encode(
        x=alt.X('year:O', title='Year'),
        y=alt.Y('score:Q', title='Score (Grade Equivalents)'),
        color=alt.Color('subgroup_label:N',
            scale=alt.Scale(
                domain=list(SUBGROUP_COLORS.keys()),
                range=list(SUBGROUP_COLORS.values()),
            ),
            legend=alt.Legend(orient='bottom', columns=3, title=None),
        ),
        tooltip=['year:O', 'subgroup_label:N',
                 alt.Tooltip('score:Q', format='.2f', title='GE'),
                 alt.Tooltip('se:Q', format='.3f', title='SE')],
    )
    chart_layers.append(base.mark_line(strokeWidth=2.5))
    chart_layers.append(base.mark_point(size=70, filled=True))

    return alt.layer(*chart_layers).properties(
        width=width, height=320,
        title=alt.TitleParams(title, dy=-4),
        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5},
    )


# ── Page ──────────────────────────────────────────────────────────────────────

st.title(f':material/map: {DISTRICT_NAME} — SEDA District Trends')
st.caption(
    'Stanford Education Data Archive (SEDA) 2025.1 · District-level test-score estimates · '
    'Scores in grade-equivalent units, cohort-scale (0 = national on-grade-level).'
)


tab_trends, tab_gaps, tab_snap, tab_cohort, tab_demo = st.tabs([
    ':material/trending_up: Trends by Subgroup',
    ':material/compare_arrows: Achievement Gaps',
    ':material/photo_camera: Grade Snapshot',
    ':material/timeline: Cohort Tracker',
    ':material/group: Demographics',
])


with tab_trends:
    st.caption(
        'Shaded bands = 95% CI. The Trends file (`trends.parquet`) pools grades 3-8 at grade-center 5.5; '
        'scores here are raw grade equivalents (a 5th grader scoring 8 GE performs like an average 8th grader nationally).'
    )

    view = st.segmented_control('View', ['Overall', 'By Grade'], default='Overall', key='t_view')

    if view == 'Overall':
        group_by = st.segmented_control('Compare by', list(SUBCAT_GROUPS.keys()),
                                        default='Race / Ethnicity', key='t_groupby')
        sg_options = SUBCAT_GROUPS[group_by]
        available = [s for s in sg_options if s in trends['subgroup_label'].unique()]
        selected_sgs = st.pills(
            'Subgroups', available, selection_mode='multi',
            default=available,                 # all subgroups in category selected by default
            key=f't_sgs_{group_by}',           # reset when category changes
        )
        show_bands = st.toggle('Confidence bands', value=True, key='t_bands')

        if not selected_sgs:
            st.info('Select at least one subgroup above.')
        else:
            ela_col, math_col = st.columns(2)
            for subject, col in [('Math', ela_col), ('Reading/ELA', math_col)]:
                df_sub = trends[(trends['subject'] == subject) & (trends['subgroup_label'].isin(selected_sgs))]
                with col:
                    st.markdown(f'### {subject}')
                    if not df_sub.empty:
                        st.altair_chart(configure(trend_chart(df_sub, subject, show_bands)))

        # auto-stats
        stat_lines = []
        for subject in ['Math', 'Reading/ELA']:
            d = trends[(trends['subject'] == subject) & (trends['subgroup_label'] == 'All Students')]
            s = trend_stats(d)
            if not s:
                continue
            ch = s['total_change']
            direction = 'increased' if ch > 0 else 'decreased'
            arrow = '↑' if ch > 0 else '↓'
            sig_text = ' This change is **statistically meaningful**.' if s['significant'] else \
                       ' This change is **within the margin of error**.'
            stat_lines.append(
                f"- **{subject} — All Students:** {arrow} {direction} by **{abs(ch):.2f} GE** "
                f"from {s['first_year']} ({s['first_score']:.2f}) to {s['last_year']} ({s['last_score']:.2f}).{sig_text}"
            )
        stat_lines.append(
            '- **Data gaps:** 2020 and 2021 missing due to COVID testing pause. '
            'The 2013→2015 jump reflects CA\'s transition from STAR/CST to Smarter Balanced.'
        )
    else:
        sg_label = st.segmented_control('Subgroup', list(SG_COL_MAP.keys()),
                                        default='All Students', key='t_grade_sg')
        sg_col = SG_COL_MAP[sg_label]
        available_grades = sorted(cohorts['grade'].unique())
        selected_grades = st.pills(
            'Grades', [GRADE_LABELS[g] for g in available_grades],
            format_func=lambda x: x,
            selection_mode='multi', default=[GRADE_LABELS[g] for g in available_grades], key='t_grades',
        )
        grade_label_to_num = {v: k for k, v in GRADE_LABELS.items()}
        selected_grade_nums = [grade_label_to_num[g] for g in selected_grades if g in grade_label_to_num]

        if not selected_grade_nums:
            st.info('Select at least one grade above.')
        else:
            ela_col, math_col = st.columns(2)
            for subject, col in [('Math', ela_col), ('Reading/ELA', math_col)]:
                df_s = cohorts[cohorts['subject'] == subject].copy()
                df_s = df_s[df_s['grade'].isin(selected_grade_nums)]
                df_s['Grade'] = df_s['grade'].map(GRADE_LABELS)
                # Use the chosen subgroup column
                df_s = df_s[['year', 'Grade', sg_col, f'se_{sg_col}']].dropna(subset=[sg_col])
                df_s = df_s.rename(columns={sg_col: 'score', f'se_{sg_col}': 'se'})

                with col:
                    st.markdown(f'### {subject}')
                    if df_s.empty:
                        st.info('No data for this combination.')
                    else:
                        base = alt.Chart(df_s).encode(
                            x=alt.X('year:O', title='Year'),
                            y=alt.Y('score:Q', title='Score (cohort-scale GE, 0 = national average)'),
                            color=alt.Color('Grade:N',
                                scale=alt.Scale(domain=list(GRADE_COLORS.keys()),
                                                range=list(GRADE_COLORS.values())),
                                legend=alt.Legend(orient='bottom', title=None)),
                            tooltip=['year:O', 'Grade:N',
                                     alt.Tooltip('score:Q', format='.2f', title='GE'),
                                     alt.Tooltip('se:Q', format='.3f', title='SE')],
                        )
                        rule = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
                            color=GRAY, strokeDash=[2, 3]).encode(y='y:Q')
                        chart = alt.layer(
                            rule,
                            base.mark_line(strokeWidth=2.5),
                            base.mark_point(size=70, filled=True),
                        ).properties(width=560, height=340,
                                     title=alt.TitleParams(f'{subject} — {sg_label} by grade', dy=-4),
                                     padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5})
                        st.altair_chart(configure(chart))

        stat_lines = ['- Each grade is a different cohort of students each year — this is not cohort tracking. '
                      'Use the Cohort Tracker tab to follow the same group across grades.']

    analysis_panel('trends', '\n'.join(stat_lines))


with tab_gaps:
    st.caption('Gap = higher-performing group minus lower-performing group. '
               'A shrinking line means convergence; growing = divergence.')

    available_pairs = [
        name for name, (a, b) in GAP_PAIRS.items()
        if a in trends['subgroup_label'].unique() and b in trends['subgroup_label'].unique()
    ]
    selected_gaps = st.pills('Gap pairs', available_pairs, selection_mode='multi',
                             default=available_pairs[:3], key='g_pairs')

    if not selected_gaps:
        st.info('Select at least one gap pair above.')
    else:
        ela_col, math_col = st.columns(2)
        for subject, col in [('Math', ela_col), ('Reading/ELA', math_col)]:
            score_by_sg = (
                trends[trends['subject'] == subject]
                .groupby(['year', 'subgroup_label'])['score'].first()
                .unstack('subgroup_label')
            )

            rows = []
            for gap_name in selected_gaps:
                sg_a, sg_b = GAP_PAIRS[gap_name]
                if sg_a not in score_by_sg.columns or sg_b not in score_by_sg.columns:
                    continue
                gap = (score_by_sg[sg_a] - score_by_sg[sg_b]).dropna()
                for yr, val in gap.items():
                    rows.append({'Year': int(yr), 'Gap': gap_name, 'Value': float(val)})
            chart_df = pd.DataFrame(rows)

            with col:
                st.markdown(f'### {subject}')
                if chart_df.empty:
                    st.info('No data.')
                else:
                    base = alt.Chart(chart_df).encode(
                        x=alt.X('Year:O', title='Year'),
                        y=alt.Y('Value:Q', title='Gap (GE)'),
                        color=alt.Color('Gap:N', legend=alt.Legend(orient='bottom', columns=2, title=None)),
                        tooltip=['Year:O', 'Gap:N', alt.Tooltip('Value:Q', format='.2f', title='Gap (GE)')],
                    )
                    rule = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color=GRAY, strokeDash=[2, 3]).encode(y='y:Q')
                    chart = alt.layer(rule, base.mark_line(strokeWidth=2.5), base.mark_point(size=60, filled=True)).properties(
                        width=560, height=320,
                        title=alt.TitleParams(subject, dy=-4),
                        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5},
                    )
                    st.altair_chart(configure(chart))

        analysis_panel('gaps',
            '- A gap can shrink because the lower-performing group improved, '
            'because the higher-performing group declined, or both.\n'
            '- Small subgroups (e.g. Hispanic students at Burlingame) carry larger SEs on both sides.'
        )


with tab_snap:
    st.caption(
        'Scores by grade (3rd–8th) for a single year. '
        'A steep drop from 3rd to 8th means students fall behind national norms as they advance.'
    )

    available_years = sorted(cohorts['year'].unique(), reverse=True)
    selected_year = st.select_slider('School year', options=available_years, key='s_year')

    group_by = st.segmented_control('Compare by', list(SUBCAT_GROUPS.keys()),
                                    default='Race / Ethnicity', key='s_groupby')
    sg_options = SUBCAT_GROUPS[group_by]
    sg_cols_avail = [s for s in sg_options if SG_COL_MAP.get(s) in cohorts.columns]
    selected_sgs = st.pills('Subgroups', sg_cols_avail, selection_mode='multi',
                            default=sg_cols_avail, key='s_sgs')

    df_y = cohorts[(cohorts['year'] == selected_year) & (cohorts['grade'].between(3, 8))].sort_values('grade')

    if df_y.empty:
        st.warning('No grade data for this year.')
    else:
        ela_col, math_col = st.columns(2)
        for subject, col in [('Math', math_col), ('Reading/ELA', ela_col)]:
            df_s = df_y[df_y['subject'] == subject]
            rows = []
            for sg_label in selected_sgs:
                sg_col = SG_COL_MAP.get(sg_label)
                if not sg_col or sg_col not in df_s.columns:
                    continue
                pts = df_s[['grade', sg_col]].dropna(subset=[sg_col])
                for _, r in pts.iterrows():
                    rows.append({'Grade': int(r['grade']), 'Subgroup': sg_label, 'Score': float(r[sg_col])})
            chart_df = pd.DataFrame(rows)
            with col:
                st.markdown(f'### {subject}')
                if chart_df.empty:
                    st.info('No data.')
                else:
                    base = alt.Chart(chart_df).encode(
                        x=alt.X('Grade:O', title='Grade',
                                axis=alt.Axis(values=[3, 4, 5, 6, 7, 8],
                                              labelExpr="datum.value == 3 ? '3rd' : datum.value == 4 ? '4th' : datum.value == 5 ? '5th' : datum.value == 6 ? '6th' : datum.value == 7 ? '7th' : '8th'")),
                        y=alt.Y('Score:Q', title='Score (GE)'),
                        color=alt.Color('Subgroup:N',
                            scale=alt.Scale(
                                domain=list(SUBGROUP_COLORS.keys()),
                                range=list(SUBGROUP_COLORS.values()),
                            ),
                            legend=alt.Legend(orient='bottom', columns=3, title=None),
                        ),
                        tooltip=['Grade:O', 'Subgroup:N', alt.Tooltip('Score:Q', format='.2f')],
                    )
                    rule = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color=GRAY, strokeDash=[2, 3]).encode(y='y:Q')
                    chart = alt.layer(rule, base.mark_line(strokeWidth=2.5), base.mark_point(size=90, filled=True)).properties(
                        width=560, height=340,
                        title=alt.TitleParams(subject, dy=-4),
                        padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5},
                    )
                    st.altair_chart(configure(chart))

        analysis_panel('grade_snapshot',
            f'- This shows different students at each grade level in **{selected_year}**, '
            'not the same students tracked over time. Use the Cohort Tracker to follow the same group.\n'
            '- At Burlingame (~350–550 students per grade), single-grade estimates are more stable '
            'than subgroup estimates within a grade.'
        )


with tab_cohort:
    st.caption('Follows one class of students through grades 3–8. '
               'Blue = the selected cohort. Gray dashed = district average across all years at each grade.')

    sg_label = st.segmented_control('Subgroup', list(SG_COL_MAP.keys()),
                                    default='All Students', key='c_sg')
    sg_col = SG_COL_MAP[sg_label]

    df_grade = cohorts[cohorts['grade'].between(3, 8)].copy()
    df_grade['cohort_id'] = df_grade['year'] - df_grade['grade']
    available_cohorts = sorted(df_grade['cohort_id'].unique())

    def cohort_label(c):
        return f'3rd grade in {c + 3}'

    selected_cohort_label = st.select_slider(
        'Cohort (defined by 3rd-grade year)',
        options=[cohort_label(c) for c in available_cohorts],
        value=cohort_label(available_cohorts[max(0, len(available_cohorts) - 6)]),
        key='c_cohort',
    )
    selected_cohort = available_cohorts[[cohort_label(c) for c in available_cohorts].index(selected_cohort_label)]

    cohort_data = df_grade[df_grade['cohort_id'] == selected_cohort].sort_values('grade')
    avg_data = df_grade.groupby(['subject', 'grade'])[sg_col].mean().reset_index()

    ela_col, math_col = st.columns(2)
    for subject, col in [('Math', ela_col), ('Reading/ELA', math_col)]:
        c_plot = cohort_data[cohort_data['subject'] == subject][['grade', sg_col, f'se_{sg_col}']].dropna(subset=[sg_col])
        a_plot = avg_data[avg_data['subject'] == subject].dropna(subset=[sg_col])

        c_plot = c_plot.rename(columns={sg_col: 'score', f'se_{sg_col}': 'se'})
        c_plot['Series'] = selected_cohort_label
        a_plot = a_plot.rename(columns={sg_col: 'score'})
        a_plot['Series'] = 'District avg (all years)'
        a_plot['se'] = 0.0

        chart_df = pd.concat([c_plot, a_plot], ignore_index=True)

        with col:
            st.markdown(f'### {subject}')
            if chart_df.empty:
                st.info('No data.')
                continue

            base = alt.Chart(chart_df).encode(
                x=alt.X('grade:O', title='Grade',
                        axis=alt.Axis(values=[3, 4, 5, 6, 7, 8],
                                      labelExpr="datum.value == 3 ? '3rd' : datum.value == 4 ? '4th' : datum.value == 5 ? '5th' : datum.value == 6 ? '6th' : datum.value == 7 ? '7th' : '8th'")),
                y=alt.Y('score:Q', title='Score (cohort-scale GE)'),
                color=alt.Color('Series:N',
                    scale=alt.Scale(
                        domain=[selected_cohort_label, 'District avg (all years)'],
                        range=[LINCOLN_COLOR, GRAY],
                    ),
                    legend=alt.Legend(orient='bottom', title=None)),
                strokeDash=alt.condition(
                    alt.datum.Series == 'District avg (all years)',
                    alt.value([4, 3]), alt.value([1, 0])),
                strokeWidth=alt.condition(
                    alt.datum.Series == selected_cohort_label,
                    alt.value(3), alt.value(2)),
                tooltip=['grade:O', 'Series:N', alt.Tooltip('score:Q', format='.2f')],
            )
            rule = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
                color=GRAY, strokeDash=[2, 3]).encode(y='y:Q')
            chart = alt.layer(rule, base.mark_line(), base.mark_point(size=90, filled=True)).properties(
                width=560, height=380,
                title=alt.TitleParams(subject, dy=-4),
                padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5},
            )
            st.altair_chart(configure(chart))

    third_grade_year = selected_cohort + 3
    analysis_panel('cohort',
        f'- **Cohort:** Students who were in 3rd grade in {third_grade_year}. '
        f'They would have been in 8th grade in {third_grade_year + 5}.\n'
        '- Cohort tracking is sensitive to student mobility — families moving in or out '
        'change who is in the cohort year-over-year.\n'
        '- Cohorts whose 4th–6th grade years fell in 2020–2022 have missing years.'
    )


with tab_demo:
    st.caption(f'Demographic composition of {DISTRICT_NAME} over time.')

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('### Racial / Ethnic Composition')
        view = st.segmented_control('View as', ['Stacked area', 'Lines'], default='Stacked area', key='d_race_view')

        race_cols = [
            ('pct_white',           'White',           SUBGROUP_COLORS['White']),
            ('pct_hispanic',        'Hispanic',        SUBGROUP_COLORS['Hispanic']),
            ('pct_asian',           'Asian',           SUBGROUP_COLORS['Asian']),
            ('pct_black',           'Black',           SUBGROUP_COLORS['Black']),
            ('pct_native_american', 'Native American', SUBGROUP_COLORS['Native American']),
        ]
        rows = []
        for col_name, label, _ in race_cols:
            if col_name not in demo.columns:
                continue
            s = demo[['year', col_name]].dropna(subset=[col_name])
            for _, r in s.iterrows():
                rows.append({'Year': int(r['year']), 'Group': label, 'Pct': float(r[col_name])})
        race_df = pd.DataFrame(rows)

        if not race_df.empty:
            domain = [label for _, label, _ in race_cols]
            range_colors = [color for _, _, color in race_cols]
            base = alt.Chart(race_df).encode(
                x=alt.X('Year:O', title='Year'),
                y=alt.Y('Pct:Q', title='% of Students',
                        scale=alt.Scale(domain=[0, 100] if view == 'Stacked area' else None)),
                color=alt.Color('Group:N',
                    scale=alt.Scale(domain=domain, range=range_colors),
                    legend=alt.Legend(orient='bottom', columns=3, title=None)),
                tooltip=['Year:O', 'Group:N', alt.Tooltip('Pct:Q', format='.1f', title='%')],
            )
            if view == 'Stacked area':
                chart = base.mark_area(opacity=0.85)
            else:
                chart = alt.layer(base.mark_line(strokeWidth=2.5), base.mark_point(size=50, filled=True))
            chart = chart.properties(width=560, height=320,
                                     title=alt.TitleParams('Racial / Ethnic Composition', dy=-4),
                                     padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5})
            st.altair_chart(configure(chart))

    with col2:
        st.markdown('### % Economically Disadvantaged')
        rows = []
        if 'pct_econ_disadvantaged' in demo.columns:
            seda_ecd = demo[['year', 'pct_econ_disadvantaged']].dropna(subset=['pct_econ_disadvantaged'])
            seda_ecd = seda_ecd[seda_ecd['pct_econ_disadvantaged'] < 100]
            for _, r in seda_ecd.iterrows():
                rows.append({'Year': float(r['year']), 'Source': 'Econ. Disadv. (SEDA)',
                             'Pct': float(r['pct_econ_disadvantaged'])})
        if not frpm.empty:
            for _, r in frpm.iterrows():
                rows.append({'Year': float(r['school_year_end']), 'Source': 'FRPM Eligible (CDE)',
                             'Pct': float(r['pct_frpm'])})
        ecd_df = pd.DataFrame(rows)

        if not ecd_df.empty:
            base = alt.Chart(ecd_df).encode(
                x=alt.X('Year:O', title='Year'),
                y=alt.Y('Pct:Q', title='% of Students'),
                color=alt.Color('Source:N',
                    scale=alt.Scale(domain=['Econ. Disadv. (SEDA)', 'FRPM Eligible (CDE)'],
                                    range=['#B45309', '#0891B2']),
                    legend=alt.Legend(orient='bottom', title=None)),
                strokeDash=alt.condition(
                    alt.datum.Source == 'FRPM Eligible (CDE)',
                    alt.value([4, 3]), alt.value([1, 0])),
                tooltip=['Year:O', 'Source:N', alt.Tooltip('Pct:Q', format='.1f', title='%')],
            )
            chart = alt.layer(base.mark_line(strokeWidth=2.5), base.mark_point(size=50, filled=True)).properties(
                width=560, height=320,
                title=alt.TitleParams('% Economically Disadvantaged (two sources)', dy=-4),
                padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5},
            )
            st.altair_chart(configure(chart))
            st.caption(
                '**2009–2019:** SEDA state-defined economically disadvantaged. '
                '**2020–2025:** CDE FRPM eligibility (direct certification via Medi-Cal/SNAP). '
                'The 2025 spike likely reflects expanded automatic Medi-Cal direct certification, '
                'not a sudden increase in poverty.'
            )

    if 'total_enrollment' in demo.columns:
        st.markdown('### Total Enrollment')
        enrl = demo[['year', 'total_enrollment']].dropna(subset=['total_enrollment']).copy()
        enrl['Year'] = enrl['year'].astype(int)
        enrl['Students'] = enrl['total_enrollment'].astype(int)
        chart = alt.Chart(enrl).mark_bar(color=LINCOLN_COLOR).encode(
            x=alt.X('Year:O', title='Year'),
            y=alt.Y('Students:Q', title='Students Enrolled'),
            tooltip=['Year:O', alt.Tooltip('Students:Q', format=',')],
        ).properties(width=1140, height=240,
                     padding={'top': 20, 'bottom': 10, 'left': 5, 'right': 5})
        st.altair_chart(configure(chart))

    stat_lines = []
    if 'pct_white' in demo.columns and 'pct_asian' in demo.columns:
        w_first = demo['pct_white'].dropna().iloc[0]
        w_last = demo['pct_white'].dropna().iloc[-1]
        a_first = demo['pct_asian'].dropna().iloc[0]
        a_last = demo['pct_asian'].dropna().iloc[-1]
        yr_first = int(demo['year'].iloc[0])
        yr_last = int(demo['year'].iloc[-1])
        stat_lines.append(
            f'- **Racial composition shift ({yr_first}–{yr_last}):** White {w_first:.1f}% → {w_last:.1f}% '
            f'({w_last - w_first:+.1f} pp). Asian {a_first:.1f}% → {a_last:.1f}% ({a_last - a_first:+.1f} pp).'
        )
    stat_lines.append(
        '- Composition shifts can move aggregate scores even if every subgroup is unchanged.'
    )
    analysis_panel('demographics', '\n'.join(stat_lines))
