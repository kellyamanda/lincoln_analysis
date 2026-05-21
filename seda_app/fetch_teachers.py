"""
Download CDE Staff Experience files and extract teacher experience for the
Burlingame elementary schools: average years of experience and the share of
"inexperienced" teachers (<=2 years total experience). Also captures the
statewide teacher average as a reference.

Source: https://www.cde.ca.gov/ds/ad/filesstex.asp (tab-delimited; Census Day).
Rows are disaggregated by staff type, grade span, and gender — we take
Staff Type = TCH (teachers), School Grade Span = GS_K6, Staff Gender = ALL.
District CDS: county 41, district 68882.
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
    2020: "https://www3.cde.ca.gov/demo-downloads/staff/stex1920.txt",
    2021: "https://www3.cde.ca.gov/demo-downloads/staff/stex2021.txt",
    2022: "https://www3.cde.ca.gov/demo-downloads/staff/stex2122.txt",
    2023: "https://www3.cde.ca.gov/demo-downloads/staff/stex2223.txt",
    2024: "https://www3.cde.ca.gov/demo-downloads/staff/stex2324.txt",
    2025: "https://www3.cde.ca.gov/demo-downloads/staff/stex2425.txt",
}

OUT = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(OUT, "teachers_raw")
os.makedirs(CACHE, exist_ok=True)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def num(s):
    return pd.to_numeric(s.astype(str).str.strip().replace({"*": None, "": None}), errors="coerce")


frames = []
for year_end, url in FILES.items():
    fname = os.path.join(CACHE, f"stex_{year_end}.txt")
    if not os.path.exists(fname):
        print(f"Downloading {year_end}...")
        download(url, fname)
    else:
        print(f"Using cached {year_end}")

    df = pd.read_csv(fname, sep="\t", dtype=str, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    for c in ["Aggregate Level", "County Code", "District Code", "School Code",
              "Staff Type", "School Grade Span", "Staff Gender"]:
        df[c] = df[c].astype(str).str.strip()

    teach = df[(df["Staff Type"] == "TCH") & (df["Staff Gender"] == "ALL")]

    burl = teach[
        (teach["Aggregate Level"] == "S")
        & (teach["County Code"] == DISTRICT_COUNTY)
        & (teach["District Code"] == DISTRICT_CODE)
        & (teach["School Code"].isin(ELEMENTARIES))
        & (teach["School Grade Span"] == "GS_K6")
    ].copy()

    total = num(burl["Total Staff Count"])
    inexp = num(burl["Inexperienced"])
    out = pd.DataFrame({
        "school_year_end": year_end,
        "school_code": burl["School Code"].values,
        "school_name": burl["School Code"].map(ELEMENTARIES).values,
        "teachers": total.values,
        "avg_years_exp": num(burl["Average Total Years Experience"]).values,
        "avg_years_district": num(burl["Average District Years Experience"]).values,
        "inexperienced": inexp.values,
        "first_year": num(burl["First Year"]).values,
    })
    out["pct_inexperienced"] = (inexp.values / total.values) * 100
    frames.append(out)

    # Statewide teacher average (all grade spans) as a reference.
    state = teach[(teach["Aggregate Level"] == "T") & (teach["School Grade Span"] == "ALL")]
    if len(state):
        ca = num(state["Average Total Years Experience"]).iloc[0]
        print(f"  {year_end}: {len(out)} schools | CA avg teacher experience = {ca:.1f} yrs")
    else:
        print(f"  {year_end}: {len(out)} schools")

result = pd.concat(frames, ignore_index=True).sort_values(["school_year_end", "school_name"])
dest = os.path.join(OUT, "burlingame_teachers.parquet")
result.to_parquet(dest, index=False)
print(f"\nSaved {len(result)} rows to {dest}\n")
lincoln = result[result["school_code"] == "6043566"]
print("Lincoln teacher experience by year:")
print(lincoln[["school_year_end", "teachers", "avg_years_exp", "pct_inexperienced"]].to_string(index=False))
