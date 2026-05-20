"""
Download CDE Chronic Absenteeism files and extract the Burlingame elementary
schools, all reporting categories (total, race, gender, programs, grade span).

Source: https://www.cde.ca.gov/ds/ad/filesabd.asp (tab-delimited; state/county/
district/school levels). Rate = chronically-absent count / eligible cumulative
enrollment. '*' marks small-N suppressed cells. 2019-20 is not published.
District CDS: county 41, district 68882.
"""

import urllib.request
import os
import pandas as pd

DISTRICT_COUNTY = "41"
DISTRICT_CODE = "68882"

# Burlingame K-6 elementaries (same codes as shared/data.py BURL_ELEMENTARIES).
ELEMENTARIES = {
    "6043541": "Franklin",
    "6043566": "Lincoln",
    "6043574": "McKinley",
    "6043590": "Roosevelt",
    "6043608": "Washington",
    "0133157": "Hoover",
}

FILES = {
    2017: "https://www3.cde.ca.gov/demo-downloads/attendance/chronicabsenteeism17.txt",
    2018: "https://www3.cde.ca.gov/demo-downloads/attendance/chronicabsenteeism18.txt",
    2019: "https://www3.cde.ca.gov/demo-downloads/attendance/chronicabsenteeism19.txt",
    2021: "https://www3.cde.ca.gov/demo-downloads/attendance/chronicabsenteeism21.txt",
    2022: "https://www3.cde.ca.gov/demo-downloads/attendance/chronicabsenteeism22-v3.txt",
    2023: "https://www3.cde.ca.gov/demo-downloads/attendance/chronicabsenteeism23.txt",
    2024: "https://www3.cde.ca.gov/demo-downloads/attendance/chronicabsenteeism24.txt",
    2025: "https://www3.cde.ca.gov/demo-downloads/attendance/chronicabsenteeism25-v2.txt",
}

# Reporting Category code -> (readable label, category type).
CATEGORIES = {
    "TA": ("All Students", "Total"),
    "GF": ("Female", "Gender"),
    "GM": ("Male", "Gender"),
    "RW": ("White", "Race"),
    "RA": ("Asian", "Race"),
    "RH": ("Hispanic", "Race"),
    "RB": ("Black", "Race"),
    "RF": ("Filipino", "Race"),
    "RI": ("American Indian", "Race"),
    "RP": ("Pacific Islander", "Race"),
    "RT": ("Two or More", "Race"),
    "RD": ("Not Reported", "Race"),
    "SS": ("Socioecon. Disadvantaged", "Program"),
    "SE": ("English Learner", "Program"),
    "SD": ("Students w/ Disabilities", "Program"),
    "SF": ("Foster", "Program"),
    "SH": ("Homeless", "Program"),
    "SM": ("Migrant", "Program"),
    "GRTKKN": ("TK / Kindergarten", "Grade"),
    "GR13": ("Grades 1-3", "Grade"),
    "GR46": ("Grades 4-6", "Grade"),
    "GRTK8": ("Grades TK-8", "Grade"),
}

OUT = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(OUT, "absenteeism_raw")
os.makedirs(CACHE, exist_ok=True)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())


frames = []
for year_end, url in FILES.items():
    fname = os.path.join(CACHE, f"chronic_{year_end}.txt")
    if not os.path.exists(fname):
        print(f"Downloading {year_end}...")
        download(url, fname)
    else:
        print(f"Using cached {year_end}")

    df = pd.read_csv(fname, sep="\t", dtype=str, encoding="latin-1")
    # Column names vary by year: some have spaces ("County Code"), older files
    # drop them ("CountyCode") and truncate the long enrollment header. Normalize
    # to spaceless lowercase and resolve fields by prefix.
    norm = {c: c.replace(" ", "").lower() for c in df.columns}
    df = df.rename(columns=norm)

    def col(prefix):
        for c in df.columns:
            if c.startswith(prefix):
                return c
        raise KeyError(f"no column starting with {prefix!r} in {list(df.columns)}")

    level = df[col("aggregatelevel")].str.strip()
    county = df[col("countycode")].str.strip()
    district = df[col("districtcode")].str.strip()
    school = df[col("schoolcode")].str.strip()
    category = df[col("reportingcategory")].str.strip()

    mask = (
        (level == "S")
        & (county == DISTRICT_COUNTY)
        & (district == DISTRICT_CODE)
        & (school.isin(ELEMENTARIES))
        & (category.isin(CATEGORIES))
    )
    burl = df[mask]
    sc = school[mask]
    cat = category[mask]

    out = pd.DataFrame({
        "school_year_end": year_end,
        "level": "school",
        "school_code": sc.values,
        "school_name": sc.map(ELEMENTARIES).values,
        "category_code": cat.values,
        "subgroup": cat.map(lambda c: CATEGORIES[c][0]).values,
        "category_type": cat.map(lambda c: CATEGORIES[c][1]).values,
        "eligible_enrollment": pd.to_numeric(burl[col("chronicabsenteeismeligible")], errors="coerce").values,
        "chronic_count": pd.to_numeric(burl[col("chronicabsenteeismcount")], errors="coerce").values,
        "chronic_rate": pd.to_numeric(burl[col("chronicabsenteeismrate")], errors="coerce").values,
    })
    frames.append(out)

    # Statewide total (aggregate level T, category TA) — for the CA reference line.
    st_mask = (level == "T") & (category == "TA")
    st = df[st_mask]
    if len(st):
        state_row = pd.DataFrame({
            "school_year_end": [year_end],
            "level": ["state"],
            "school_code": ["CA"],
            "school_name": ["California"],
            "category_code": ["TA"],
            "subgroup": ["All Students"],
            "category_type": ["Total"],
            "eligible_enrollment": [pd.to_numeric(st[col("chronicabsenteeismeligible")], errors="coerce").iloc[0]],
            "chronic_count": [pd.to_numeric(st[col("chronicabsenteeismcount")], errors="coerce").iloc[0]],
            "chronic_rate": [pd.to_numeric(st[col("chronicabsenteeismrate")], errors="coerce").iloc[0]],
        })
        frames.append(state_row)
    print(f"  {year_end}: {len(out)} school rows ({out['school_code'].nunique()} schools) + state")

result = pd.concat(frames, ignore_index=True).sort_values(
    ["school_year_end", "school_name", "category_type", "subgroup"])
dest = os.path.join(OUT, "burlingame_absenteeism.parquet")
result.to_parquet(dest, index=False)
print(f"\nSaved {len(result)} rows to {dest}")
print("\nLincoln 'All Students' by year:")
lincoln = result[(result["school_code"] == "6043566") & (result["category_code"] == "TA")]
print(lincoln[["school_year_end", "eligible_enrollment", "chronic_count", "chronic_rate"]].to_string(index=False))
