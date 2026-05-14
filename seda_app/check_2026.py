import pandas as pd

df = pd.read_excel("data/frpm_raw/frpm_2026.xlsx", sheet_name=1, header=1, dtype=str)
df.columns = df.columns.str.strip()
df["county_code"] = df["County Code"].str.strip().str.zfill(2)
df["district_code"] = df["District Code"].str.strip().str.zfill(5)
b = df[(df["county_code"] == "41") & (df["district_code"] == "68882")].copy()

show_cols = [c for c in b.columns if any(x in c for x in ["School Name", "Provision", "Enrollment", "Free Meal", "FRPM", "Certification"])]
print(b[show_cols].to_string(index=False))

print("\nAcademic year label in file:", df["Academic Year"].iloc[0])
