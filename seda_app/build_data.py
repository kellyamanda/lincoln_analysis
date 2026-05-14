"""
Build processed Parquet files from raw SEDA CSVs.
Run once: python3 build_data.py
Outputs: data/trends.parquet, data/cohorts.parquet, data/demographics.parquet
"""

import pandas as pd
import numpy as np
import os

RAW = os.path.join(os.path.dirname(__file__), "../seda_data/seda2025.1")
OUT = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUT, exist_ok=True)

SUBGROUP_LABELS = {
    "all": "All Students",
    "wht": "White",
    "blk": "Black",
    "hsp": "Hispanic",
    "asn": "Asian",
    "nam": "Native American",
    "ecd": "Econ. Disadvantaged",
    "nec": "Not Econ. Disadvantaged",
    "fem": "Female",
    "mal": "Male",
}

SUBJECT_LABELS = {"mth": "Math", "rla": "Reading/ELA"}


def build_trends():
    """
    District × year × grade × subgroup × subject from annualsub_gys.
    gradecenter is the mean tested grade (e.g. 5.5 = pooled gr 3-8).
    Score is in grade-equivalent units.
    """
    print("Loading annualsub_gys...")
    path = os.path.join(RAW, "seda_admindist_annualsub_gys_2025.1.csv")
    df = pd.read_csv(path, dtype={"sedaadmin": str, "fips": str, "year": int})

    df = df.rename(columns={
        "sedaadmin": "district_id",
        "sedaadminname": "district_name",
        "stateabb": "state",
        "gradecenter": "grade_center",
        "gys_mn_avg_mth_eb": "score_mth",
        "gys_mn_avg_rla_eb": "score_rla",
        "gys_mn_avg_mth_eb_se": "se_mth",
        "gys_mn_avg_rla_eb_se": "se_rla",
        "tot_asmts_mth": "n_mth",
        "tot_asmts_rla": "n_rla",
    })

    keep = ["district_id", "district_name", "state", "year", "grade_center",
            "subgroup", "subcat",
            "score_mth", "score_rla", "se_mth", "se_rla", "n_mth", "n_rla"]
    df = df[keep].copy()

    for col in ["score_mth", "score_rla", "se_mth", "se_rla"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["n_mth", "n_rla"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["grade_center"] = pd.to_numeric(df["grade_center"], errors="coerce")

    df["subgroup_label"] = df["subgroup"].map(SUBGROUP_LABELS).fillna(df["subgroup"])

    df = df.melt(
        id_vars=["district_id", "district_name", "state", "year", "grade_center",
                 "subgroup", "subcat", "subgroup_label"],
        value_vars=["score_mth", "score_rla"],
        var_name="subject_raw",
        value_name="score",
    )
    df["subject"] = df["subject_raw"].map({"score_mth": "Math", "score_rla": "Reading/ELA"})

    se_df = df.copy()
    se_df["subject_raw"] = se_df["subject_raw"].str.replace("score_", "se_")
    se_df = se_df.rename(columns={"score": "se"})

    se_lookup = pd.read_csv(path, dtype={"sedaadmin": str, "fips": str, "year": int})
    se_lookup = se_lookup.rename(columns={
        "sedaadmin": "district_id",
        "sedaadminname": "district_name",
        "stateabb": "state",
        "gradecenter": "grade_center",
        "gys_mn_avg_mth_eb_se": "se_mth",
        "gys_mn_avg_rla_eb_se": "se_rla",
    })
    se_lookup = se_lookup[["district_id", "year", "grade_center", "subgroup", "se_mth", "se_rla"]]
    se_lookup["grade_center"] = pd.to_numeric(se_lookup["grade_center"], errors="coerce")
    for col in ["se_mth", "se_rla"]:
        se_lookup[col] = pd.to_numeric(se_lookup[col], errors="coerce")

    se_long = se_lookup.melt(
        id_vars=["district_id", "year", "grade_center", "subgroup"],
        value_vars=["se_mth", "se_rla"],
        var_name="se_key",
        value_name="se",
    )
    se_long["subject"] = se_long["se_key"].map({"se_mth": "Math", "se_rla": "Reading/ELA"})
    se_long = se_long.drop(columns="se_key")

    df = df.merge(se_long, on=["district_id", "year", "grade_center", "subgroup", "subject"], how="left")
    df = df.drop(columns="subject_raw")
    df = df.dropna(subset=["score"])

    out_path = os.path.join(OUT, "trends.parquet")
    df.to_parquet(out_path, index=False)
    print(f"  Saved {len(df):,} rows -> {out_path}")
    return df


def build_cohorts():
    """
    District × subject × grade × year with all subgroups as columns.
    cohort_id = year - grade (students who started 3rd grade in that year).
    """
    print("Loading long format...")
    path = os.path.join(RAW, "seda_admindist_long_cs_2025.1.csv")
    df = pd.read_csv(path, dtype={"sedaadmin": str, "fips": str, "grade": int, "year": int})

    df = df.rename(columns={
        "sedaadmin": "district_id",
        "sedaadminname": "district_name",
        "stateabb": "state",
    })

    subgroups = ["all", "wht", "blk", "hsp", "asn", "nam", "ecd", "nec", "fem", "mal"]
    score_cols = {f"cs_mn_{s}": s for s in subgroups}
    se_cols = {f"cs_mn_se_{s}": f"se_{s}" for s in subgroups}

    rename_map = {**score_cols, **se_cols}
    df = df.rename(columns=rename_map)

    keep = ["district_id", "district_name", "state", "subject", "grade", "year"]
    score_names = list(score_cols.values())
    se_names = list(se_cols.values())
    df = df[keep + score_names + se_names].copy()

    for col in score_names + se_names:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["subject"] = df["subject"].map(SUBJECT_LABELS).fillna(df["subject"])
    df["cohort_id"] = df["year"] - df["grade"]

    out_path = os.path.join(OUT, "cohorts.parquet")
    df.to_parquet(out_path, index=False)
    print(f"  Saved {len(df):,} rows -> {out_path}")
    return df


def build_demographics():
    """
    District × year demographic composition from the covariate file.
    Includes racial/ethnic percentages, % econ. disadvantaged, total enrollment, SES.
    """
    print("Loading covariate (demographics)...")
    path = os.path.join(RAW, "seda_cov_admindist_annual_2025.1.csv")
    df = pd.read_csv(path, dtype={"sedaadmin": str, "fips": str, "year": int})

    df = df.rename(columns={
        "sedaadmin": "district_id",
        "sedaadminname": "district_name",
        "stateabb": "state",
        "totenrl": "total_enrollment",
        "perwht": "pct_white",
        "perblk": "pct_black",
        "perhsp": "pct_hispanic",
        "perasn": "pct_asian",
        "pernam": "pct_native_american",
        "perecd": "pct_econ_disadvantaged",
        "perfl":  "pct_free_lunch",
        "perfrl": "pct_free_reduced_lunch",
        "perell": "pct_ell",
        "perspeced": "pct_special_ed",
        "sesall": "ses_all",
        "urbanicity": "urbanicity",
    })

    keep = [
        "district_id", "district_name", "state", "year",
        "total_enrollment",
        "pct_white", "pct_black", "pct_hispanic", "pct_asian", "pct_native_american",
        "pct_econ_disadvantaged", "pct_free_lunch", "pct_free_reduced_lunch",
        "pct_ell", "pct_special_ed",
        "ses_all", "urbanicity",
    ]
    df = df[[c for c in keep if c in df.columns]].copy()

    pct_cols = [c for c in keep if c.startswith("pct_")]
    for col in pct_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce") * 100

    df["total_enrollment"] = pd.to_numeric(df["total_enrollment"], errors="coerce").round().astype("Int64")
    df["ses_all"] = pd.to_numeric(df["ses_all"], errors="coerce")

    out_path = os.path.join(OUT, "demographics.parquet")
    df.to_parquet(out_path, index=False)
    print(f"  Saved {len(df):,} rows -> {out_path}")
    return df


if __name__ == "__main__":
    build_trends()
    build_cohorts()
    build_demographics()
    print("Done.")
