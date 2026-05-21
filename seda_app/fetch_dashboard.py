"""
Download California School Dashboard research files and extract the Burlingame
elementary schools. The Dashboard's signature output is a color performance level
per indicator (1=Red, 2=Orange, 3=Yellow, 4=Green, 5=Blue) combining current
status with change. Files share named columns but differ in column ORDER and count,
so columns are selected by name.

Source: https://www.cde.ca.gov/ta/ac/cm/ (one tab-delimited .txt per indicator/year).
currstatus meaning varies by indicator: CHRONIC/SUSP = rate % (lower better);
ELA/MATH = Distance From Standard in points (higher better, 0 = at standard);
ELPI = % of English learners making progress (higher better).
District CDS prefix: 4168882 (county 41, district 68882).
"""

import urllib.request
import os
import pandas as pd

DISTRICT_PREFIX = "4168882"

ELEMENTARIES = {
    "6043541": "Franklin",
    "6043566": "Lincoln",
    "6043574": "McKinley",
    "6043590": "Roosevelt",
    "6043608": "Washington",
    "0133157": "Hoover",
}

# Indicator file-prefix -> display label.
INDICATORS = {
    "ela": "ELA",
    "math": "Math",
    "chronic": "Chronic Absenteeism",
    "susp": "Suspension",
    "elpi": "EL Progress",
}

# ELPI has no "ALL" group — it is reported for English Learners only.
STUDENTGROUP = {"elpi": "EL"}

YEARS = [2025]  # latest Dashboard; each file also carries prior status + change

COLOR_NAMES = {1: "Red", 2: "Orange", 3: "Yellow", 4: "Green", 5: "Blue"}

OUT = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(OUT, "dashboard_raw")
os.makedirs(CACHE, exist_ok=True)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def to_num(s):
    return pd.to_numeric(s, errors="coerce")


frames = []
for year in YEARS:
    for prefix, label in INDICATORS.items():
        url = f"https://www3.cde.ca.gov/researchfiles/cadashboard/{prefix}download{year}.txt"
        fname = os.path.join(CACHE, f"{prefix}{year}.txt")
        if not os.path.exists(fname):
            print(f"Downloading {prefix} {year}...")
            download(url, fname)
        else:
            print(f"Using cached {prefix} {year}")

        df = pd.read_csv(fname, sep="\t", dtype=str, encoding="latin-1")
        df.columns = [c.strip().lower() for c in df.columns]
        df["cds"] = df["cds"].astype(str).str.strip()
        df["school_code"] = df["cds"].str[-7:]

        group = STUDENTGROUP.get(prefix, "ALL")
        sub = df[
            (df["rtype"].str.strip() == "S")
            & (df["cds"].str.startswith(DISTRICT_PREFIX))
            & (df["school_code"].isin(ELEMENTARIES))
            & (df["studentgroup"].str.strip() == group)
        ].copy()

        out = pd.DataFrame({
            "school_year_end": year,
            "school_code": sub["school_code"].values,
            "school_name": sub["school_code"].map(ELEMENTARIES).values,
            "indicator": label,
            "currstatus": to_num(sub["currstatus"]).values,
            "priorstatus": to_num(sub["priorstatus"]).values,
            "change": to_num(sub["change"]).values,
            "color": to_num(sub["color"]).astype("Int64").values,
        })
        out["color_name"] = out["color"].map(COLOR_NAMES)
        print(f"  {prefix} {year}: {len(out)} schools")
        frames.append(out)

result = pd.concat(frames, ignore_index=True).sort_values(
    ["school_year_end", "school_name", "indicator"])
dest = os.path.join(OUT, "burlingame_dashboard.parquet")
result.to_parquet(dest, index=False)
print(f"\nSaved {len(result)} rows to {dest}\n")
print("Lincoln Dashboard colors (2025):")
lincoln = result[result["school_code"] == "6043566"]
print(lincoln[["indicator", "currstatus", "change", "color", "color_name"]].to_string(index=False))
