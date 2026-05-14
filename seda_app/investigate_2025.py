import pandas as pd

for year, fname in [(2024, "data/frpm_raw/frpm_2024.xlsx"), (2025, "data/frpm_raw/frpm_2025.xlsx"), (2026, "data/frpm_raw/frpm_2526.xlsx")]:
    df = pd.read_excel(fname, sheet_name=1, header=1, dtype=str)
    df.columns = df.columns.str.strip()
    df["county_code"] = df["County Code"].str.strip().str.zfill(2)
    df["district_code"] = df["District Code"].str.strip().str.zfill(5)
    b = df[(df["county_code"] == "41") & (df["district_code"] == "68882")].copy()

    show_cols = [c for c in b.columns if any(x in c for x in
        ["School Name", "Provision", "Enrollment", "Free Meal", "FRPM"])]

    for c in show_cols:
        b[c] = pd.to_numeric(b[c], errors="coerce") if c != "School Name" and "Provision" not in c else b[c]

    print(f"\n=== School Year Ending {year} ===")
    print(b[show_cols].to_string(index=False))
