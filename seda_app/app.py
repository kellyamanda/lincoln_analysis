import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import json

st.set_page_config(
    page_title="Burlingame Elementary — Achievement Trends",
    page_icon="📊",
    layout="wide",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
NOTES_FILE = os.path.join(DATA_DIR, "analysis_notes.json")
DISTRICT_ID = "606480"
DISTRICT_NAME = "Burlingame Elementary"

SUBGROUP_COLORS = {
    "All Students":            "#2563eb",
    "White":                   "#16a34a",
    "Black":                   "#dc2626",
    "Hispanic":                "#d97706",
    "Asian":                   "#7c3aed",
    "Native American":         "#0891b2",
    "Econ. Disadvantaged":     "#b45309",
    "Not Econ. Disadvantaged": "#059669",
    "Female":                  "#db2777",
    "Male":                    "#1d4ed8",
}

SUBCAT_GROUPS = {
    "Race / Ethnicity": ["All Students", "White", "Black", "Hispanic", "Asian", "Native American"],
    "Socioeconomic":    ["All Students", "Econ. Disadvantaged", "Not Econ. Disadvantaged"],
    "Gender":           ["All Students", "Female", "Male"],
}

GAP_PAIRS = {
    "White − Black":                      ("White", "Black"),
    "White − Hispanic":                   ("White", "Hispanic"),
    "Not Econ. Disadv. − Econ. Disadv.": ("Not Econ. Disadvantaged", "Econ. Disadvantaged"),
    "Female − Male":                      ("Female", "Male"),
}

GRADE_LABELS = {3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th", 8: "8th"}

GRADE_COLORS = {
    3: "#2563eb", 4: "#16a34a", 5: "#d97706",
    6: "#dc2626", 7: "#7c3aed", 8: "#0891b2",
}

SG_COL_MAP = {
    "All Students": "all", "White": "wht", "Black": "blk",
    "Hispanic": "hsp", "Asian": "asn", "Native American": "nam",
    "Econ. Disadvantaged": "ecd", "Not Econ. Disadvantaged": "nec",
    "Female": "fem", "Male": "mal",
}


# ── Data loaders ──────────────────────────────────────────────────────────────

@st.cache_data
def load_trends():
    df = pd.read_parquet(os.path.join(DATA_DIR, "trends.parquet"))
    return df[df["district_id"] == DISTRICT_ID].copy()

@st.cache_data
def load_cohorts():
    df = pd.read_parquet(os.path.join(DATA_DIR, "cohorts.parquet"))
    return df[df["district_id"] == DISTRICT_ID].copy()

@st.cache_data
def load_demographics():
    df = pd.read_parquet(os.path.join(DATA_DIR, "demographics.parquet"))
    return df[df["district_id"] == DISTRICT_ID].copy()

@st.cache_data
def load_frpm():
    path = os.path.join(DATA_DIR, "burlingame_frpm.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)

def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE) as f:
            return json.load(f)
    return {}

def save_notes(notes):
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f, indent=2)


# ── Chart helpers ─────────────────────────────────────────────────────────────

def chart_layout(title):
    return dict(
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(title="Year", tickformat="d", showgrid=False, showline=True, linecolor="#e5e7eb"),
        yaxis=dict(title="Score (Grade Equivalents)", zeroline=False, showgrid=True, gridcolor="#f3f4f6"),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=400,
        margin=dict(l=50, r=10, t=45, b=40),
        legend=dict(orientation="h", y=-0.22, x=0),
    )

def trend_fig(df_sub, title, show_bands):
    fig = go.Figure()
    for sg, gdf in df_sub.groupby("subgroup_label", sort=False):
        gdf = gdf.sort_values("year")
        color = SUBGROUP_COLORS.get(sg, "#6b7280")
        if show_bands and gdf["se"].notna().any():
            fig.add_trace(go.Scatter(
                x=pd.concat([gdf["year"], gdf["year"][::-1]]),
                y=pd.concat([gdf["score"] + 1.96 * gdf["se"],
                             (gdf["score"] - 1.96 * gdf["se"])[::-1]]),
                fill="toself", fillcolor=color, opacity=0.12,
                line=dict(width=0), showlegend=False, hoverinfo="skip",
            ))
        fig.add_trace(go.Scatter(
            x=gdf["year"], y=gdf["score"],
            mode="lines+markers", name=sg,
            line=dict(color=color, width=2.5), marker=dict(size=6),
            hovertemplate=f"<b>{sg}</b>: %{{y:.2f}} GE<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="#9ca3af", line_width=1)
    fig.update_layout(**chart_layout(title))
    return fig


# ── Analysis engine ───────────────────────────────────────────────────────────

def trend_stats(series_df, score_col="score", se_col="se", year_col="year", n_col=None):
    """
    Given a dataframe with year, score, se columns for a single series,
    return a dict of computed statistics.
    """
    d = series_df[[year_col, score_col, se_col]].dropna(subset=[score_col]).sort_values(year_col)
    if len(d) < 3:
        return None

    years = d[year_col].values.astype(float)
    scores = d[score_col].values.astype(float)
    ses = d[se_col].fillna(d[se_col].median()).values.astype(float)
    weights = 1.0 / np.maximum(ses ** 2, 1e-6)

    # Weighted linear trend
    slope, intercept = np.polyfit(years - years.mean(), scores, 1, w=weights)

    first, last = d.iloc[0], d.iloc[-1]
    total_change = float(last[score_col] - first[score_col])
    pooled_se = float(np.sqrt(first[se_col] ** 2 + last[se_col] ** 2)) if pd.notna(first[se_col]) and pd.notna(last[se_col]) else None
    z = abs(total_change) / pooled_se if pooled_se else None
    significant = z > 2.0 if z is not None else None

    avg_se = float(ses.mean())
    min_detectable = 2 * avg_se  # change you'd need to be confident it's real

    # Estimate typical N from SE (rough: SE ≈ σ/√N, assume σ≈1 GE for raw scores)
    # SEDA SEs are in GE units; typical student SD ~1.5 GE
    typical_n = int(round((1.5 / avg_se) ** 2)) if avg_se > 0 else None

    return dict(
        n_years=len(d),
        first_year=int(first[year_col]),
        last_year=int(last[year_col]),
        first_score=float(first[score_col]),
        last_score=float(last[score_col]),
        total_change=total_change,
        slope_per_year=float(slope),
        significant=significant,
        z_score=z,
        pooled_se=pooled_se,
        avg_se=avg_se,
        min_detectable=min_detectable,
        typical_n=typical_n,
    )


def format_stats(stats, label):
    """Turn a stats dict into readable bullet points."""
    if not stats:
        return f"- *Not enough data to compute trend for {label}.*"

    ch = stats["total_change"]
    direction = "increased" if ch > 0 else "decreased"
    arrow = "↑" if ch > 0 else "↓"

    lines = []

    # Overall change
    sig_text = ""
    if stats["significant"] is True:
        sig_text = " This change is **statistically meaningful** — it exceeds twice the margin of error."
    elif stats["significant"] is False:
        sig_text = " This change is **within the margin of error** and may reflect normal year-to-year noise rather than a real shift."

    lines.append(
        f"- **{label}:** {arrow} {direction} by **{abs(ch):.2f} grade equivalents** "
        f"from {stats['first_year']} ({stats['first_score']:.2f} GE) "
        f"to {stats['last_year']} ({stats['last_score']:.2f} GE).{sig_text}"
    )

    # Margin of error / noise floor
    lines.append(
        f"- **Noise floor:** Year-to-year changes smaller than **±{stats['min_detectable']:.2f} GE** "
        f"are within the 95% confidence band and should not be over-interpreted. "
        f"Only sustained moves across multiple years are likely real."
    )

    # Small numbers framing
    if stats["typical_n"]:
        n = stats["typical_n"]
        one_student_effect = 1.5 / n  # roughly: 1 student 1 SD off shifts mean by σ/N
        students_for_change = abs(ch) / one_student_effect if one_student_effect > 0 else None
        if n < 50:
            lines.append(
                f"- **Small sample warning:** Estimated ~{n} students tested per year in this subgroup. "
                f"With a group this small, a handful of unusually strong or weak test-takers "
                f"could move the average by {one_student_effect:.2f}–{one_student_effect*3:.2f} GE on their own. "
                f"Treat single-year jumps with caution."
            )
        else:
            if students_for_change:
                lines.append(
                    f"- **Sample context:** Estimated ~{n} students tested per year. "
                    f"To produce the observed {abs(ch):.2f} GE shift by chance, roughly "
                    f"{int(students_for_change)} students would need to perform ~1 grade level differently "
                    f"in the same direction — {'plausible in a small district' if n < 200 else 'unlikely to be noise alone'}."
                )

    return "\n".join(lines)


def analysis_panel(tab_key, auto_lines, notes_dict):
    """Render auto-stats + editable notes in an expander."""
    with st.expander("📝 Analysis & Notes", expanded=True):
        st.markdown("**What the data shows**")
        st.markdown(auto_lines)
        st.markdown("---")
        st.markdown("**Your notes** — interpretation, context, questions, things to follow up")
        current = notes_dict.get(tab_key, "")
        new_text = st.text_area(
            label="notes",
            value=current,
            height=160,
            key=f"notes_{tab_key}",
            label_visibility="collapsed",
            placeholder="Add your observations here — what might explain these trends? What do you want to investigate further?",
        )
        if new_text != current:
            notes_dict[tab_key] = new_text
            save_notes(notes_dict)


# ── Tab 1: District Trends ────────────────────────────────────────────────────

@st.fragment
def tab_district_trends(trends, cohorts, notes):
    st.caption(
        "Scores in **grade-equivalent (GE) units**: 0 = national on-grade-level, "
        "+1 = one grade level above, −1 = one grade below. Shaded bands = 95% CI."
    )

    view = st.segmented_control("View", ["Overall", "By Grade"], default="Overall", key="t_view")

    if view == "Overall":
        group_by = st.segmented_control(
            "Compare by", list(SUBCAT_GROUPS.keys()), default="Race / Ethnicity", key="t_groupby"
        )
        sg_options = SUBCAT_GROUPS[group_by]
        available = [s for s in sg_options if s in trends["subgroup_label"].unique()]
        selected_sgs = st.pills("Subgroups", available, selection_mode="multi", default=["All Students"], key="t_sgs")
        show_bands = st.toggle("Confidence bands", value=True, key="t_bands")

        if not selected_sgs:
            st.info("Select at least one subgroup above.")
            return

        col_math, col_ela = st.columns(2)
        for subject, col in [("Math", col_math), ("Reading/ELA", col_ela)]:
            df_sub = trends[(trends["subject"] == subject) & (trends["subgroup_label"].isin(selected_sgs))]
            with col:
                st.plotly_chart(trend_fig(df_sub, subject, show_bands), use_container_width=True, key=f"t_fig_{subject}")

        # Auto-stats for All Students
        stat_lines = []
        for subject in ["Math", "Reading/ELA"]:
            d = trends[(trends["subject"] == subject) & (trends["subgroup_label"] == "All Students")]
            s = trend_stats(d)
            stat_lines.append(format_stats(s, f"{subject} — All Students"))
        stat_lines.append(
            "- **Data gap:** 2020 and 2021 are missing due to COVID-era testing suspensions. "
            "The jump between 2019 and 2022 should not be interpreted as a single-year change."
        )

    else:
        sg_label = st.segmented_control("Subgroup", list(SG_COL_MAP.keys()), default="All Students", key="t_grade_sg")
        sg_col = SG_COL_MAP[sg_label]
        available_grades = sorted(cohorts["grade"].unique())
        selected_grades = st.pills(
            "Grades", [GRADE_LABELS[g] for g in available_grades],
            selection_mode="multi", default=[GRADE_LABELS[g] for g in available_grades], key="t_grades",
        )
        grade_label_to_num = {v: k for k, v in GRADE_LABELS.items()}
        selected_grade_nums = [grade_label_to_num[g] for g in selected_grades if g in grade_label_to_num]

        if not selected_grade_nums:
            st.info("Select at least one grade above.")
            return

        col_math, col_ela = st.columns(2)
        for subject, col in [("Math", col_math), ("Reading/ELA", col_ela)]:
            fig = go.Figure()
            df_s = cohorts[cohorts["subject"] == subject]
            for grade in selected_grade_nums:
                gdf = df_s[df_s["grade"] == grade].sort_values("year")
                if sg_col not in gdf.columns or gdf[sg_col].isna().all():
                    continue
                gdf = gdf.dropna(subset=[sg_col])
                color = GRADE_COLORS.get(grade, "#6b7280")
                se_col = f"se_{sg_col}"
                if se_col in gdf.columns and gdf[se_col].notna().any():
                    se = gdf[se_col].fillna(0)
                    fig.add_trace(go.Scatter(
                        x=pd.concat([gdf["year"], gdf["year"][::-1]]),
                        y=pd.concat([gdf[sg_col] + 1.96 * se, (gdf[sg_col] - 1.96 * se)[::-1]]),
                        fill="toself", fillcolor=color, opacity=0.12,
                        line=dict(width=0), showlegend=False, hoverinfo="skip",
                    ))
                fig.add_trace(go.Scatter(
                    x=gdf["year"], y=gdf[sg_col],
                    mode="lines+markers", name=GRADE_LABELS[grade],
                    line=dict(color=color, width=2.5), marker=dict(size=6),
                    hovertemplate=f"<b>{GRADE_LABELS[grade]}</b>: %{{y:.2f}} GE<extra></extra>",
                ))
            fig.add_hline(y=0, line_dash="dot", line_color="#9ca3af", line_width=1)
            fig.update_layout(**chart_layout(f"{subject} — {sg_label} by Grade"))
            with col:
                st.plotly_chart(fig, use_container_width=True, key=f"t_grade_fig_{subject}")

        # Grade-level stats
        stat_lines = []
        for subject in ["Math", "Reading/ELA"]:
            df_s = cohorts[cohorts["subject"] == subject]
            grade_trends = []
            for grade in sorted(cohorts["grade"].unique()):
                gdf = df_s[df_s["grade"] == grade].sort_values("year")
                if sg_col not in gdf.columns:
                    continue
                s = trend_stats(gdf.rename(columns={sg_col: "score", f"se_{sg_col}": "se"}))
                if s and abs(s["total_change"]) > 0.05:
                    arrow = "↑" if s["total_change"] > 0 else "↓"
                    sig = " ✓" if s["significant"] else " (within margin of error)"
                    grade_trends.append(f"{GRADE_LABELS[grade]}: {arrow} {abs(s['total_change']):.2f} GE{sig}")
            if grade_trends:
                stat_lines.append(f"- **{subject} trends by grade:** " + " · ".join(grade_trends))

        stat_lines.append(
            "- Each grade's score reflects different students each year — this is not cohort tracking. "
            "Use the Cohort Tracker tab to follow the same group of students across grades."
        )

    analysis_panel("trends", "\n".join(stat_lines), notes)


# ── Tab 2: Achievement Gaps ───────────────────────────────────────────────────

@st.fragment
def tab_gaps(trends, notes):
    st.caption(
        "Gap = higher-performing group minus lower-performing group. "
        "A shrinking line means convergence; growing = divergence."
    )

    available_pairs = [
        name for name, (a, b) in GAP_PAIRS.items()
        if a in trends["subgroup_label"].unique() and b in trends["subgroup_label"].unique()
    ]
    selected_gaps = st.pills(
        "Gap pairs", available_pairs, selection_mode="multi", default=available_pairs[:3], key="g_pairs"
    )

    if not selected_gaps:
        st.info("Select at least one gap pair above.")
        return

    gap_colors = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed"]

    col_math, col_ela = st.columns(2)
    for subject, col in [("Math", col_math), ("Reading/ELA", col_ela)]:
        score_by_sg = (
            trends[trends["subject"] == subject]
            .groupby(["year", "subgroup_label"])["score"].first()
            .unstack("subgroup_label")
        )
        fig = go.Figure()
        for i, gap_name in enumerate(selected_gaps):
            sg_a, sg_b = GAP_PAIRS[gap_name]
            if sg_a not in score_by_sg.columns or sg_b not in score_by_sg.columns:
                continue
            gap = (score_by_sg[sg_a] - score_by_sg[sg_b]).dropna()
            color = gap_colors[i % len(gap_colors)]
            fig.add_trace(go.Scatter(
                x=gap.index, y=gap.values,
                mode="lines+markers", name=gap_name,
                line=dict(color=color, width=2.5), marker=dict(size=6),
                hovertemplate=f"<b>{gap_name}</b>: %{{y:.2f}} GE<extra></extra>",
            ))
        fig.add_hline(y=0, line_dash="dot", line_color="#9ca3af", line_width=1)
        layout = chart_layout(subject)
        layout["yaxis"]["title"] = "Gap (Grade Equivalents)"
        fig.update_layout(**layout)
        with col:
            st.plotly_chart(fig, use_container_width=True, key=f"g_fig_{subject}")

    # Auto-stats for gaps
    stat_lines = []
    score_by_sg_math = (
        trends[trends["subject"] == "Math"]
        .groupby(["year", "subgroup_label"])["score"].first()
        .unstack("subgroup_label")
    )
    se_by_sg_math = (
        trends[trends["subject"] == "Math"]
        .groupby(["year", "subgroup_label"])["se"].first()
        .unstack("subgroup_label")
    )

    for gap_name in available_pairs:
        sg_a, sg_b = GAP_PAIRS[gap_name]
        if sg_a not in score_by_sg_math.columns or sg_b not in score_by_sg_math.columns:
            continue
        gap_series = (score_by_sg_math[sg_a] - score_by_sg_math[sg_b]).dropna()
        # Combined SE for the gap
        se_a = se_by_sg_math.get(sg_a, pd.Series(dtype=float))
        se_b = se_by_sg_math.get(sg_b, pd.Series(dtype=float))
        gap_se = np.sqrt(se_a ** 2 + se_b ** 2).reindex(gap_series.index)

        gap_df = pd.DataFrame({"year": gap_series.index, "score": gap_series.values, "se": gap_se.values})
        s = trend_stats(gap_df)
        if s:
            ch = s["total_change"]
            direction = "narrowed" if ch < 0 else "widened"
            sig = "statistically meaningful" if s["significant"] else "within the margin of error"
            stat_lines.append(
                f"- **{gap_name} (Math):** Gap {direction} by {abs(ch):.2f} GE "
                f"({s['first_year']}: {s['first_score']:.2f} GE → {s['last_year']}: {s['last_score']:.2f} GE). "
                f"Change is {sig}."
            )

    stat_lines.append(
        "- **Interpreting gap changes:** A gap can shrink because the lower-performing group improved, "
        "or because the higher-performing group declined — or both. Check the Trends tab to see which."
    )
    stat_lines.append(
        "- **Small subgroups:** Gaps involving small groups (e.g. Hispanic students at Burlingame) "
        "carry larger standard errors on both sides, making the combined gap estimate noisier. "
        "Year-to-year swings may not be real."
    )

    analysis_panel("gaps", "\n".join(stat_lines), notes)


# ── Tab 3: Grade Snapshot ─────────────────────────────────────────────────────

@st.fragment
def tab_grade_snapshot(cohorts, notes):
    st.caption(
        "Scores by grade (3rd–8th) for a single year. "
        "A steep drop from 3rd to 8th suggests students fall behind national norms as they advance."
    )

    available_years = sorted(cohorts["year"].unique(), reverse=True)
    selected_year = st.select_slider("School year", options=available_years, key="s_year")

    group_by = st.segmented_control(
        "Compare by", list(SUBCAT_GROUPS.keys()), default="Race / Ethnicity", key="s_groupby"
    )
    sg_options = SUBCAT_GROUPS[group_by]
    sg_cols_avail = [s for s in sg_options if SG_COL_MAP.get(s) in cohorts.columns]
    selected_sgs = st.pills("Subgroups", sg_cols_avail, selection_mode="multi", default=sg_cols_avail, key="s_sgs")

    df_y = cohorts[(cohorts["year"] == selected_year) & (cohorts["grade"].between(3, 8))].sort_values("grade")

    if df_y.empty:
        st.warning("No grade data for this year.")
        return

    col_math, col_ela = st.columns(2)
    for subject, col in [("Math", col_ela), ("Reading/ELA", col_math)]:
        df_s = df_y[df_y["subject"] == subject]
        fig = go.Figure()
        for sg_label in selected_sgs:
            sg_col = SG_COL_MAP.get(sg_label)
            if not sg_col or sg_col not in df_s.columns:
                continue
            pts = df_s[["grade", sg_col]].dropna(subset=[sg_col])
            if pts.empty:
                continue
            color = SUBGROUP_COLORS.get(sg_label, "#6b7280")
            fig.add_trace(go.Scatter(
                x=pts["grade"], y=pts[sg_col],
                mode="lines+markers", name=sg_label,
                line=dict(color=color, width=2.5), marker=dict(size=8),
                hovertemplate=f"<b>{sg_label}</b>: %{{y:.2f}} GE<extra></extra>",
            ))
        fig.add_hline(y=0, line_dash="dot", line_color="#9ca3af", line_width=1)
        layout = chart_layout(subject)
        layout["xaxis"].update(title="Grade", tickvals=[3, 4, 5, 6, 7, 8],
                               ticktext=["3rd", "4th", "5th", "6th", "7th", "8th"])
        fig.update_layout(**layout)
        with col:
            st.plotly_chart(fig, use_container_width=True, key=f"s_fig_{subject}")

    # Auto-stats
    stat_lines = []
    for subject in ["Math", "Reading/ELA"]:
        df_s = df_y[(df_y["subject"] == subject)].sort_values("grade")
        all_pts = df_s[["grade", "all"]].dropna()
        if len(all_pts) >= 2:
            lo = all_pts.iloc[0]
            hi = all_pts.iloc[-1]
            gradient = hi["all"] - lo["all"]
            direction = "rises" if gradient > 0 else "falls"
            stat_lines.append(
                f"- **{subject} grade gradient ({selected_year}):** All Students score {direction} "
                f"by {abs(gradient):.2f} GE from {GRADE_LABELS[int(lo['grade'])]} ({lo['all']:.2f}) "
                f"to {GRADE_LABELS[int(hi['grade'])]} ({hi['all']:.2f}). "
                + ("Students are outperforming national norms more in upper grades." if gradient > 0
                   else "Students fall further behind national norms in upper grades.")
            )

    stat_lines.append(
        f"- **Caution:** This shows different students at each grade level in **{selected_year}**, "
        "not the same students tracked over time. A dip at one grade could reflect that year's 3rd graders, "
        "not that students declined as they aged. Use the Cohort Tracker to follow the same cohort."
    )
    stat_lines.append(
        "- **Grade-level N:** Each grade-year cell covers approximately one grade's cohort. "
        "At Burlingame (~350–550 students per grade), single-grade estimates are more stable "
        "than subgroup estimates within a grade."
    )

    analysis_panel("grade_snapshot", "\n".join(stat_lines), notes)


# ── Tab 4: Cohort Tracker ─────────────────────────────────────────────────────

@st.fragment
def tab_cohort_tracker(cohorts, notes):
    st.caption(
        "Follows one class of students through grades 3–8. "
        "Blue = the selected cohort. Gray dashed = district average across all years at each grade."
    )

    sg_label = st.segmented_control("Subgroup", list(SG_COL_MAP.keys()), default="All Students", key="c_sg")
    sg_col = SG_COL_MAP[sg_label]

    df_grade = cohorts[cohorts["grade"].between(3, 8)].copy()
    df_grade["cohort_id"] = df_grade["year"] - df_grade["grade"]
    available_cohorts = sorted(df_grade["cohort_id"].unique())

    def cohort_label(c):
        return f"3rd grade in {c + 3}"

    selected_cohort_label = st.select_slider(
        "Cohort (defined by 3rd-grade year)",
        options=[cohort_label(c) for c in available_cohorts],
        value=cohort_label(available_cohorts[max(0, len(available_cohorts) - 6)]),
        key="c_cohort",
    )
    selected_cohort = available_cohorts[[cohort_label(c) for c in available_cohorts].index(selected_cohort_label)]

    cohort_data = df_grade[df_grade["cohort_id"] == selected_cohort].sort_values("grade")
    avg_data = df_grade.groupby(["subject", "grade"])[sg_col].mean().reset_index()

    col_math, col_ela = st.columns(2)
    for subject, col in [("Math", col_math), ("Reading/ELA", col_ela)]:
        c_plot = cohort_data[cohort_data["subject"] == subject][["grade", sg_col, f"se_{sg_col}"]].dropna(subset=[sg_col])
        a_plot = avg_data[avg_data["subject"] == subject].dropna(subset=[sg_col])

        fig = go.Figure()
        if not c_plot.empty:
            se_vals = c_plot[f"se_{sg_col}"].fillna(0)
            fig.add_trace(go.Scatter(
                x=pd.concat([c_plot["grade"], c_plot["grade"][::-1]]),
                y=pd.concat([c_plot[sg_col] + 1.96 * se_vals,
                             (c_plot[sg_col] - 1.96 * se_vals)[::-1]]),
                fill="toself", fillcolor="#2563eb", opacity=0.12,
                line=dict(width=0), showlegend=False, hoverinfo="skip",
            ))
            fig.add_trace(go.Scatter(
                x=c_plot["grade"], y=c_plot[sg_col],
                mode="lines+markers", name=selected_cohort_label,
                line=dict(color="#2563eb", width=3), marker=dict(size=9),
                hovertemplate="<b>Cohort</b>: %{y:.2f} GE<extra></extra>",
            ))
        if not a_plot.empty:
            fig.add_trace(go.Scatter(
                x=a_plot["grade"], y=a_plot[sg_col],
                mode="lines+markers", name="District avg (all years)",
                line=dict(color="#9ca3af", width=2, dash="dash"), marker=dict(size=7),
                hovertemplate="<b>District avg</b>: %{y:.2f} GE<extra></extra>",
            ))
        fig.add_hline(y=0, line_dash="dot", line_color="#9ca3af", line_width=1)
        layout = chart_layout(subject)
        layout["xaxis"].update(title="Grade", tickvals=[3, 4, 5, 6, 7, 8],
                               ticktext=["3rd", "4th", "5th", "6th", "7th", "8th"])
        fig.update_layout(**layout)
        with col:
            st.plotly_chart(fig, use_container_width=True, key=f"c_fig_{subject}")

    # Auto-stats
    stat_lines = []
    third_grade_year = selected_cohort + 3
    stat_lines.append(
        f"- **Cohort:** Students who were in 3rd grade in {third_grade_year}. "
        f"They would have been in 8th grade in {third_grade_year + 5}."
    )

    for subject in ["Math", "Reading/ELA"]:
        c_plot = cohort_data[cohort_data["subject"] == subject][["grade", sg_col, f"se_{sg_col}"]].dropna(subset=[sg_col])
        a_plot = avg_data[avg_data["subject"] == subject].dropna(subset=[sg_col])
        if c_plot.empty or a_plot.empty:
            continue

        merged = c_plot.merge(a_plot.rename(columns={sg_col: "avg"}), on="grade")
        merged["diff"] = merged[sg_col] - merged["avg"]
        above = (merged["diff"] > 0).sum()
        below = (merged["diff"] < 0).sum()
        avg_diff = merged["diff"].mean()

        direction = "above" if avg_diff > 0 else "below"
        stat_lines.append(
            f"- **{subject}:** This cohort scored an average of **{abs(avg_diff):.2f} GE {direction}** "
            f"the district's all-years average across the grades where data exists "
            f"({above} grades above, {below} below)."
        )

    stat_lines.append(
        "- **What cohort tracking can and can't tell you:** A cohort that starts strong and stays strong "
        "suggests durable learning. A cohort that starts average but diverges (up or down) by 8th grade "
        "may reflect curriculum transitions, teacher effects, or changes in who stays enrolled. "
        "Student mobility — families moving in or out of the district — also changes who is in the cohort over time."
    )
    stat_lines.append(
        "- **COVID cohorts:** Cohorts whose 4th–6th grade years fell in 2020–2022 have missing years "
        "and the grades immediately after COVID may reflect disruption rather than the cohort's true trajectory."
    )

    analysis_panel("cohort", "\n".join(stat_lines), notes)


# ── Tab 5: Demographics ───────────────────────────────────────────────────────

@st.fragment
def tab_demographics(demo, notes):
    st.caption("Demographic composition of Burlingame Elementary over time, from SEDA covariate data.")

    demo = demo.sort_values("year").reset_index(drop=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Racial / Ethnic Composition")
        view = st.segmented_control("View as", ["Stacked area", "Lines"], default="Stacked area", key="d_race_view")

        RACE_COLS = [
            ("pct_white",           "White",           "#16a34a"),
            ("pct_hispanic",        "Hispanic",        "#d97706"),
            ("pct_asian",           "Asian",           "#7c3aed"),
            ("pct_black",           "Black",           "#dc2626"),
            ("pct_native_american", "Native American", "#0891b2"),
        ]
        fig_race = go.Figure()
        for col_name, label, color in RACE_COLS:
            if col_name not in demo.columns:
                continue
            s = demo[["year", col_name]].dropna(subset=[col_name])
            if view == "Stacked area":
                fig_race.add_trace(go.Scatter(
                    x=s["year"], y=s[col_name], mode="lines", name=label,
                    stackgroup="one", line=dict(color=color, width=0.5),
                    fillcolor=color, opacity=0.8,
                    hovertemplate=f"<b>{label}</b>: %{{y:.1f}}%<extra></extra>",
                ))
            else:
                fig_race.add_trace(go.Scatter(
                    x=s["year"], y=s[col_name], mode="lines+markers", name=label,
                    line=dict(color=color, width=2.5), marker=dict(size=5),
                    hovertemplate=f"<b>{label}</b>: %{{y:.1f}}%<extra></extra>",
                ))
        race_layout = chart_layout("Racial / Ethnic Composition")
        race_layout["yaxis"]["title"] = "% of Students"
        if view == "Stacked area":
            race_layout["yaxis"]["range"] = [0, 100]
        race_layout["xaxis"]["title"] = "Year"
        fig_race.update_layout(**race_layout)
        st.plotly_chart(fig_race, use_container_width=True, key="d_race_fig")

    with col2:
        st.markdown("#### % Economically Disadvantaged")
        frpm = load_frpm()
        fig_ecd = go.Figure()

        if "pct_econ_disadvantaged" in demo.columns:
            seda = demo[["year", "pct_econ_disadvantaged"]].dropna(subset=["pct_econ_disadvantaged"])
            seda = seda[seda["pct_econ_disadvantaged"] < 100]
            fig_ecd.add_trace(go.Scatter(
                x=seda["year"], y=seda["pct_econ_disadvantaged"],
                mode="lines+markers", name="Econ. Disadvantaged (SEDA)",
                line=dict(color="#b45309", width=2.5), marker=dict(size=6),
                hovertemplate="%{y:.1f}%<extra></extra>",
            ))

        if not frpm.empty:
            fig_ecd.add_trace(go.Scatter(
                x=frpm["school_year_end"], y=frpm["pct_frpm"],
                mode="lines+markers", name="FRPM Eligible (CDE)",
                line=dict(color="#b45309", width=2.5, dash="dash"), marker=dict(size=6, symbol="diamond"),
                hovertemplate="%{y:.1f}%<extra></extra>",
            ))
            fig_ecd.add_vline(
                x=2019.5, line_dash="dot", line_color="#9ca3af", line_width=1.5,
                annotation_text="Source change",
                annotation_position="top right",
                annotation=dict(font=dict(size=10, color="#6b7280")),
            )

        ecd_layout = chart_layout("% Economically Disadvantaged")
        ecd_layout["yaxis"]["title"] = "% of Students"
        ecd_layout["xaxis"].update(title="Year", range=[2008.5, 2025.5])
        fig_ecd.update_layout(**ecd_layout)
        st.plotly_chart(fig_ecd, use_container_width=True, key="d_ecd_fig")
        st.caption(
            "**2009–2019:** SEDA state-defined economically disadvantaged. "
            "**2020–2025:** CDE FRPM eligibility (direct certification via Medi-Cal/SNAP). "
            "The 2025 spike is driven by Burlingame Intermediate and likely reflects expanded "
            "automatic Medi-Cal direct certification, not a sudden increase in poverty."
        )

    if "total_enrollment" in demo.columns:
        st.markdown("#### Total Enrollment")
        enrl = demo[["year", "total_enrollment"]].dropna(subset=["total_enrollment"])
        fig_enrl = go.Figure(go.Bar(
            x=enrl["year"], y=enrl["total_enrollment"], marker_color="#2563eb",
            hovertemplate="Year: %{x}<br>Enrollment: %{y:,}<extra></extra>",
        ))
        fig_enrl.update_layout(
            xaxis=dict(title="Year", tickformat="d", showgrid=False, showline=True, linecolor="#e5e7eb"),
            yaxis=dict(title="Students Enrolled", showgrid=True, gridcolor="#f3f4f6"),
            plot_bgcolor="white", paper_bgcolor="white",
            height=260, margin=dict(l=50, r=10, t=10, b=40),
        )
        st.plotly_chart(fig_enrl, use_container_width=True, key="d_enrl_fig")

    # Auto-stats
    stat_lines = []
    if "pct_white" in demo.columns and "pct_asian" in demo.columns:
        w_first = demo["pct_white"].dropna().iloc[0]
        w_last  = demo["pct_white"].dropna().iloc[-1]
        a_first = demo["pct_asian"].dropna().iloc[0]
        a_last  = demo["pct_asian"].dropna().iloc[-1]
        yr_first = int(demo["year"].iloc[0])
        yr_last  = int(demo["year"].iloc[-1])
        stat_lines.append(
            f"- **Racial composition shift ({yr_first}–{yr_last}):** White enrollment "
            f"{'increased' if w_last > w_first else 'decreased'} from {w_first:.1f}% to {w_last:.1f}% "
            f"({w_last - w_first:+.1f} pp). Asian enrollment "
            f"{'increased' if a_last > a_first else 'decreased'} from {a_first:.1f}% to {a_last:.1f}% "
            f"({a_last - a_first:+.1f} pp)."
        )
    if "total_enrollment" in demo.columns:
        enrl_vals = demo["total_enrollment"].dropna()
        stat_lines.append(
            f"- **Enrollment:** Grew from {int(enrl_vals.iloc[0]):,} to {int(enrl_vals.iloc[-1]):,} "
            f"({int(enrl_vals.iloc[-1]) - int(enrl_vals.iloc[0]):+,} students over the period). "
            f"A growing district means demographic shifts reflect both composition changes and raw growth."
        )
    stat_lines.append(
        "- **Why demographics matter for achievement:** Changes in the racial/economic composition "
        "of the district can shift aggregate scores even if every subgroup is improving. "
        "If the share of higher-scoring groups grows, overall averages may rise without any "
        "individual subgroup getting better — and vice versa."
    )

    analysis_panel("demographics", "\n".join(stat_lines), notes)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.title(f"📊 {DISTRICT_NAME} — Achievement Trends")
    st.caption(
        "Data from the [Stanford Education Data Archive (SEDA) 2025.1](https://edopportunity.org). "
        "Scores are in grade-equivalent units (0 = national on-grade-level)."
    )

    if not os.path.exists(os.path.join(DATA_DIR, "trends.parquet")):
        st.error("Run `python3 build_data.py` first to generate data files.")
        st.stop()

    trends  = load_trends()
    cohorts = load_cohorts()
    demo    = load_demographics()
    notes   = load_notes()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Trends by Subgroup",
        "📉 Achievement Gaps",
        "🎓 Grade Snapshot",
        "👥 Cohort Tracker",
        "🏫 Demographics",
    ])

    with tab1:
        tab_district_trends(trends, cohorts, notes)
    with tab2:
        tab_gaps(trends, notes)
    with tab3:
        tab_grade_snapshot(cohorts, notes)
    with tab4:
        tab_cohort_tracker(cohorts, notes)
    with tab5:
        tab_demographics(demo, notes)


if __name__ == "__main__":
    main()
