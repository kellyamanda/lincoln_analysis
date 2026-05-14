import os
import pandas as pd

df = pd.read_csv(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sb_ca2025_1_csv_v1.txt'),
    sep='^',
    dtype=str,
    low_memory=False,
    encoding='latin-1'
)

print('Type ID values:', df['Type ID'].value_counts().to_dict())
print()
print('Grade values:', sorted(df['Grade'].unique().tolist()))
print()

lincoln = df[(df['School Code'] == '6043566') & (df['District Code'] == '68882')]
print('Lincoln rows:', len(lincoln))
cols = ['School Name', 'Type ID', 'Grade', 'Test Type', 'Test ID', 'Mean Scale Score', 'Percentage Standard Met and Above']
print(lincoln[cols].to_string())
