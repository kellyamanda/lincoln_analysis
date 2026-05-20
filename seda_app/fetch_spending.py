"""
Download CDE ESSA Per-Pupil Expenditure (PPE) files and extract the Burlingame
elementary schools. Amounts are already PER-PUPIL dollars. Total per-pupil =
School (Federal + State/Local) + Central (Federal + State/Local), where Central
is the district-wide allocation shared across schools.

Source: https://www.cde.ca.gov/fg/ac/es/essappedata.asp (one .xlsx per year, with a
school-level sheet). The header row and sheet name drift year to year, so both are
detected dynamically. District CDS: county 41, district 68882.
"""

import urllib.request
import os
import pandas as pd

DISTRICT_PREFIX = "4168882"  # county 41 + district 68882

ELEMENTARIES = {
    "6043541": "Franklin",
    "6043566": "Lincoln",
    "6043574": "McKinley",
    "6043590": "Roosevelt",
    "6043608": "Washington",
    "0133157": "Hoover",
}

FILES = {
    2019: "https://www.cde.ca.gov/fg/ac/es/documents/essappe1819data.xlsx",
    2020: "https://www.cde.ca.gov/fg/ac/es/documents/essappe1920data.xlsx",
    2021: "https://www.cde.ca.gov/fg/ac/es/documents/essappe2021data.xlsx",
    2022: "https://www.cde.ca.gov/fg/ac/es/documents/essappe2122data.xlsx",
    2023: "https://www.cde.ca.gov/fg/ac/es/documents/essappe2223data.xlsx",
    2024: "https://www.cde.ca.gov/fg/ac/es/documents/essappe2324data.xlsx",
}

OUT = os.path.join(os.path.dirname(__file__), "data")
CACHE = os.path.join(OUT, "spending_raw")
os.makedirs(CACHE, exist_ok=True)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def find_col(cols, *needles, required=True):
    """Return the first column whose name contains all needles (case-insensitive)."""
    for c in cols:
        cl = str(c).lower()
        if all(n.lower() in cl for n in needles):
            return c
    if required:
        raise KeyError(f"no column matching {needles} in {list(cols)}")
    return None


def read_school_sheet(path):
    xl = pd.ExcelFile(path)
    sheet = next((s for s in xl.sheet_names if "school" in s.lower()), xl.sheet_names[-1])
    raw = pd.read_excel(xl, sheet_name=sheet, header=None, dtype=str)
    # Header row is the one containing "School CDS Code".
    header_row = next(
        i for i in range(len(raw))
        if raw.iloc[i].astype(str).str.contains("School CDS Code", case=False, na=False).any()
    )
    df = pd.read_excel(xl, sheet_name=sheet, header=header_row, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df


frames = []
for year_end, url in FILES.items():
    fname = os.path.join(CACHE, f"essappe_{year_end}.xlsx")
    if not os.path.exists(fname):
        print(f"Downloading {year_end}...")
        download(url, fname)
    else:
        print(f"Using cached {year_end}")

    df = read_school_sheet(fname)
    cds_col = find_col(df.columns, "School CDS Code")
    df[cds_col] = df[cds_col].astype(str).str.strip()
    burl = df[df[cds_col].str.startswith(DISTRICT_PREFIX)].copy()
    burl["school_code"] = burl[cds_col].str[-7:]
    burl = burl[burl["school_code"].isin(ELEMENTARIES)]

    sch_fed = pd.to_numeric(burl[find_col(df.columns, "School Expenditures", "Federal")], errors="coerce")
    sch_sl = pd.to_numeric(burl[find_col(df.columns, "School Expenditures", "State")], errors="coerce")
    cen_fed = pd.to_numeric(burl[find_col(df.columns, "Central Expenditures", "Federal")], errors="coerce")
    cen_sl = pd.to_numeric(burl[find_col(df.columns, "Central Expenditures", "State")], errors="coerce")
    mem_col = find_col(df.columns, "Student Membership", required=False)
    membership = pd.to_numeric(burl[mem_col], errors="coerce") if mem_col else pd.Series([pd.NA] * len(burl))

    out = pd.DataFrame({
        "school_year_end": year_end,
        "school_code": burl["school_code"].values,
        "school_name": burl["school_code"].map(ELEMENTARIES).values,
        "membership": membership.values,
        "school_federal": sch_fed.values,
        "school_state_local": sch_sl.values,
        "central_federal": cen_fed.values,
        "central_state_local": cen_sl.values,
    })
    out["total_ppe"] = out[["school_federal", "school_state_local",
                            "central_federal", "central_state_local"]].sum(axis=1)
    print(f"  {year_end}: {len(out)} schools")
    frames.append(out)

result = pd.concat(frames, ignore_index=True).sort_values(["school_year_end", "school_name"])
dest = os.path.join(OUT, "burlingame_spending.parquet")
result.to_parquet(dest, index=False)
print(f"\nSaved {len(result)} rows to {dest}\n")
print("Lincoln per-pupil by year:")
lincoln = result[result["school_code"] == "6043566"]
print(lincoln[["school_year_end", "membership", "school_state_local",
               "central_state_local", "total_ppe"]].to_string(index=False))
