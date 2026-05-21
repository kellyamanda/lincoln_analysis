"""
Download CDE Census Day Enrollment files and extract the Burlingame elementary
schools: total enrollment, racial/ethnic composition, English-learner count, and
enrollment by grade. Output is a tidy long table (one row per school/year/category).

Source: https://www.cde.ca.gov/ds/ad/filesenrcensus.asp (tab-delimited; Census Day,
first Wednesday in October). Long format with a ReportingCategory column; TOTAL_ENR
holds the count for that category, and GR_* columns hold by-grade counts (on the TA
total row). District CDS: county 41, district 68882. Only 2023-24+ is published here.
"""

import urllib.request
import os
import pandas as pd

DISTRICT_COUNTY = "41"
DISTRICT_CODE = "68882"

ELEMENTARIES = {
    "6043541": "Franklin",
    "6043566": "Lincoln",
    "6043574": "McKinley",
    "6043590": "Roosevelt",
    "6043608": "Washington",
    "0133157": "Hoover",
}

FILES = {
    2024: "https://www3.cde.ca.gov/demo-downloads/census/cdenroll2324-v2.txt",
    2025: "https://www3.cde.ca.gov/demo-downloads/census/cdenroll2425.txt",
    2026: "https://www3.cde.ca.gov/demo-downloads/census/cdenroll2526.txt",
}

# ReportingCategory -> (label, type). Race (RE_), gender (GN_), EL status, total (TA).
CATEGORIES = {
    "TA": ("All Students", "Total"),
    "RE_W": ("White", "Race"), "RE_A": ("Asian", "Race"), "RE_H": ("Hispanic", "Race"),
    "RE_B": ("Black", "Race"), "RE_F": ("Filipino", "Race"), "RE_I": ("American Indian", "Race"),
    "RE_P": ("Pacific Islander", "Race"), "RE_T": ("Two or More", "Race"),
    "RE_D": ("Not Reported", "Race"),
    "GN_F": ("Female", "Gender"), "GN_M": ("Male", "Gender"),
    "ELAS_EL": ("English Learners", "EL"),
}

# GR_ column -> grade label (elementary grades only).
GRADES = {"GR_TK": "TK", "GR_KN": "K", "GR_01": "1", "GR_02": "2",
          "GR_03": "3", "GR_04": "4", "GR_05": "5", "GR_06": "6"}

OUT = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(OUT, "enrollment_raw")
os.makedirs(CACHE, exist_ok=True)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def num(s):
    return pd.to_numeric(pd.Series(s).astype(str).str.strip().replace({"*": None, "": None}),
                         errors="coerce")


rows = []
for year_end, url in FILES.items():
    fname = os.path.join(CACHE, f"cdenroll_{year_end}.txt")
    if not os.path.exists(fname):
        print(f"Downloading {year_end}...")
        download(url, fname)
    else:
        print(f"Using cached {year_end}")

    df = pd.read_csv(fname, sep="\t", dtype=str, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    for c in ["AggregateLevel", "CountyCode", "DistrictCode", "SchoolCode", "ReportingCategory"]:
        df[c] = df[c].astype(str).str.strip()

    burl = df[
        (df["AggregateLevel"] == "S")
        & (df["CountyCode"] == DISTRICT_COUNTY)
        & (df["DistrictCode"] == DISTRICT_CODE)
        & (df["SchoolCode"].isin(ELEMENTARIES))
    ]

    for _, r in burl.iterrows():
        code = r["SchoolCode"]
        name = ELEMENTARIES[code]
        cat = r["ReportingCategory"]
        total = num([r["TOTAL_ENR"]]).iloc[0]
        if cat in CATEGORIES:
            label, ctype = CATEGORIES[cat]
            rows.append(dict(school_year_end=year_end, school_code=code, school_name=name,
                             category_type=ctype, label=label, count=total))
        # By-grade counts come off the total (TA) row.
        if cat == "TA":
            for gcol, glabel in GRADES.items():
                if gcol in r and pd.notna(num([r[gcol]]).iloc[0]):
                    rows.append(dict(school_year_end=year_end, school_code=code, school_name=name,
                                     category_type="Grade", label=glabel,
                                     count=num([r[gcol]]).iloc[0]))

result = pd.DataFrame(rows).sort_values(["school_year_end", "school_name", "category_type", "label"])
dest = os.path.join(OUT, "burlingame_enrollment.parquet")
result.to_parquet(dest, index=False)
print(f"\nSaved {len(result)} rows to {dest}\n")
lincoln = result[(result["school_code"] == "6043566") & (result["school_year_end"] == 2026)]
print("Lincoln 2025-26 by category:")
print(lincoln[["category_type", "label", "count"]].to_string(index=False))
