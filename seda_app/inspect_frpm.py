import pandas as pd

df = pd.read_excel("data/frpm_raw/frpm_2020.xlsx", sheet_name=1, header=1, dtype=str)
df.columns = df.columns.str.strip()
print("ALL COLUMNS:")
for c in df.columns:
    print(" ", repr(c))
