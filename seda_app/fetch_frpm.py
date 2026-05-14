"""
Download CDE FRPM files and extract Burlingame Elementary district data.
District CDS prefix: 41-68882 (county 41, district 68882)
"""

import urllib.request
import os
import pandas as pd

def download(url, dest):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
    })
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())

OUT = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(OUT, "frpm_raw")
os.makedirs(CACHE, exist_ok=True)

DISTRICT_CODE = "41 68882"

FILES = [
    (2020, "https://www.cde.ca.gov/ds/ad/documents/frpm1920.xlsx"),
    (2021, "https://www.cde.ca.gov/ds/ad/documents/frpm2021.xlsx"),
    (2022, "https://www.cde.ca.gov/ds/ad/documents/frpm2122_v2.xlsx"),
    (2023, "https://www.cde.ca.gov/ds/ad/documents/frpm2223.xlsx"),
    (2024, "https://www.cde.ca.gov/ds/ad/documents/frpm2324.xlsx"),
    (2025, "https://www.cde.ca.gov/ds/ad/documents/frpm2425.xlsx"),
    # 2025-26 (school_year_end=2026) excluded: California Universal Meals Act eliminated
    # the reduced-price tier, making Free Meal Count = FRPM Count and rendering the
    # figure not comparable to prior years.
]

results = []

for school_year_end, url in FILES:
    fname = os.path.join(CACHE, f"frpm_{school_year_end}.xlsx")
    if not os.path.exists(fname):
        print(f"Downloading {school_year_end}...")
        download(url, fname)
    else:
        print(f"Using cached {school_year_end}")

    df = pd.read_excel(fname, sheet_name=1, header=1, dtype=str)
    df.columns = df.columns.str.strip()

    county_col = [c for c in df.columns if "County" in c and "Code" in c][0]
    district_col = [c for c in df.columns if "District" in c and "Code" in c][0]

    df["county_code"] = df[county_col].str.strip().str.zfill(2)
    df["district_code"] = df[district_col].str.strip().str.zfill(5)

    burlingame = df[(df["county_code"] == "41") & (df["district_code"] == "68882")].copy()

    print(f"  {school_year_end}: {len(burlingame)} school rows found")
    if burlingame.empty:
        print(f"  Columns sample: {list(df.columns[:15])}")
        continue

    enrollment_col = "Enrollment \n(K-12)"
    frpm_col = "FRPM Count \n(K-12)"

    burlingame[enrollment_col] = pd.to_numeric(burlingame[enrollment_col], errors="coerce")
    burlingame[frpm_col] = pd.to_numeric(burlingame[frpm_col], errors="coerce")

    total_enroll = burlingame[enrollment_col].sum()
    total_frpm = burlingame[frpm_col].sum()
    pct = (total_frpm / total_enroll * 100) if total_enroll > 0 else None

    print(f"  Enrollment: {total_enroll:.0f}, FRPM: {total_frpm:.0f}, Pct: {pct:.1f}%")
    results.append({
        "school_year_end": school_year_end,
        "enrollment": total_enroll,
        "frpm_count": total_frpm,
        "pct_frpm": round(pct, 2) if pct else None,
    })

if results:
    out_df = pd.DataFrame(results)
    print("\nSummary:")
    print(out_df.to_string(index=False))
    out_df.to_csv(os.path.join(OUT, "burlingame_frpm.csv"), index=False)
    print("\nSaved to data/burlingame_frpm.csv")
