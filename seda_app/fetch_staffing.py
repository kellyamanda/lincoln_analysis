"""
Download CDE Student/Staff Ratio files and extract Burlingame Elementary
district school-level staffing (enrollment, teacher FTE, student/teacher ratio).

Source: https://www.cde.ca.gov/ds/ad/filesstrat.asp (tab-delimited, school/district/
county/state levels). Numeric fields with thousands separators are quoted, e.g. "1,234.50".
District CDS: county 41, district 68882.
"""

import urllib.request
import os
import pandas as pd

DISTRICT_COUNTY = "41"
DISTRICT_CODE = "68882"

FILES = {
    2020: "https://www3.cde.ca.gov/demo-downloads/staff/strat1920.txt",
    2021: "https://www3.cde.ca.gov/demo-downloads/staff/strat2021.txt",
    2022: "https://www3.cde.ca.gov/demo-downloads/staff/strat2122.txt",
    2023: "https://www3.cde.ca.gov/demo-downloads/staff/strat2223.txt",
    2024: "https://www3.cde.ca.gov/demo-downloads/staff/strat2324.txt",
    2025: "https://www3.cde.ca.gov/demo-downloads/staff/strat2425.txt",
}

OUT = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(OUT, "staffing_raw")
os.makedirs(CACHE, exist_ok=True)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def num(series):
    """CDE quotes numbers with thousands separators, e.g. '1,234.50'; '*' = suppressed."""
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


frames = []
for year_end, url in FILES.items():
    fname = os.path.join(CACHE, f"strat_{year_end}.txt")
    if not os.path.exists(fname):
        print(f"Downloading {year_end}...")
        download(url, fname)
    else:
        print(f"Using cached {year_end}")

    df = pd.read_csv(fname, sep="\t", dtype=str, quotechar='"', encoding="latin-1")
    df.columns = df.columns.str.strip()

    burl = df[
        (df["Aggregate Level"] == "S")
        & (df["County Code"] == DISTRICT_COUNTY)
        & (df["District Code"] == DISTRICT_CODE)
    ].copy()

    burl["enrollment"] = num(burl["TOTAL_ENR_N"])
    burl = burl[burl["enrollment"] > 0]  # drop the empty District Office row

    out = pd.DataFrame({
        "school_year_end": year_end,
        "school_code": burl["School Code"].str.strip(),
        "school_name": burl["School Name"].str.strip(),
        "grade_span": burl["School Grade Span"].str.strip(),
        "enrollment": burl["enrollment"],
        "teacher_fte": num(burl["TCH_FTE_N"]),
        "admin_fte": num(burl["ADM_FTE_N"]),
        "pupil_svc_fte": num(burl["PSV_FTE_N"]),
        "stu_tch_ratio": num(burl["STU_TCH_RATIO"]),
    })
    print(f"  {year_end}: {len(out)} schools")
    frames.append(out)

result = pd.concat(frames, ignore_index=True).sort_values(["school_year_end", "school_name"])
dest = os.path.join(OUT, "burlingame_staffing.parquet")
result.to_parquet(dest, index=False)
print(f"\nSaved {len(result)} rows to {dest}")
print(result.to_string(index=False))
