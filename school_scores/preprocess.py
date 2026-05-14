import os, zipfile
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + os.sep

YEAR_ZIPS = {
    2015: 'sb_ca2015_1_csv.zip',
    2016: 'sb_ca2016_1_csv.zip',
    2017: 'sb_ca2017_1_csv.zip',
    2018: 'sb_ca2018_1_csv.zip',
    2019: 'sb_ca2019_1_csv.zip',
    2021: 'sb_ca2021_1_csv.zip',
    2022: 'sb_ca2022_1_csv.zip',
    2023: 'sb_ca2023_1_csv.zip',
    2024: 'sb_ca2024_1_csv.zip',
    2025: 'sb_ca2025_1_csv.zip',
}

LINCOLN_SCHOOL_CODE = '6043566'
LINCOLN_DISTRICT_CODE = '68882'
ELEM_GRADES = ['3', '4', '5']
SCHOOL_TYPES = {'7', '9', '10'}
MIN_STUDENTS = 20
ENTITY_FILE = 'sb_ca2025entities_csv.txt'


def load_entities():
    """Load the CAASPP entity table for school/district/county name lookup."""
    path = os.path.join(BASE_DIR, ENTITY_FILE)
    if not os.path.exists(path):
        print(f'  WARNING: entity file {ENTITY_FILE} not found — names will be blank')
        return None
    ent = pd.read_csv(path, sep='^', dtype=str, encoding='latin-1', low_memory=False)
    ent = ent[ent['Type ID'].isin(SCHOOL_TYPES)]
    for c in ['District Code', 'School Code']:
        ent[c] = ent[c].str.strip()
    ent = ent[['District Code', 'School Code', 'School Name', 'District Name', 'County Name']]
    ent = ent.drop_duplicates(subset=['District Code', 'School Code'], keep='first')
    return ent.reset_index(drop=True)


def extract_data_file(year, zip_path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        names = z.namelist()
        data_files = [n for n in names if n.endswith('.txt') and 'entit' not in n.lower()]
        if not data_files:
            return None
        target = data_files[0]
        extracted = os.path.join(BASE_DIR, os.path.basename(target))
        if not os.path.exists(extracted):
            z.extract(target, BASE_DIR)
            src = os.path.join(BASE_DIR, target)
            if src != extracted and os.path.exists(src):
                os.rename(src, extracted)
        return extracted


def detect_sep(path):
    with open(path, 'r', encoding='latin-1') as f:
        line = f.readline()
    return '^' if '^' in line else ','


def normalise_cols(df):
    df = df.rename(columns={c: c.strip().strip('"') for c in df.columns})
    aliases = {
        'Type ID':                         ['Type ID', 'TypeID'],
        'School Code':                     ['School Code'],
        'District Code':                   ['District Code'],
        'School Name':                     ['School Name'],
        'District Name':                   ['District Name'],
        'County Name':                     ['County Name'],
        'Grade':                           ['Grade'],
        'Test ID':                         ['Test ID', 'Test Id'],
        'Percentage Standard Met and Above': ['Percentage Standard Met and Above'],
        'Mean Scale Score':                ['Mean Scale Score'],
        'Students with Scores':            [
            'Total Students Tested with Scores',
            'Students with Scores',
            'Students Tested',
        ],
        'Subgroup ID':                     ['Subgroup ID', 'Student Group ID'],
    }
    col_map = {}
    for canonical, options in aliases.items():
        for opt in options:
            if opt in df.columns and opt not in col_map.values():
                col_map[opt] = canonical
                break
    return df.rename(columns=col_map)


def load_year(year, path):
    sep = detect_sep(path)
    df = pd.read_csv(path, sep=sep, dtype=str, low_memory=False, encoding='latin-1')
    df = normalise_cols(df)

    for col in ['Percentage Standard Met and Above', 'Mean Scale Score', 'Students with Scores']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'Type ID' in df.columns:
        df = df[df['Type ID'].isin(SCHOOL_TYPES)]
    else:
        df = df[df['School Code'].str.strip().str.lstrip('0') != '']
        df = df[df['School Code'].str.strip() != '0000000']

    if 'Subgroup ID' in df.columns:
        df = df[df['Subgroup ID'].str.strip() == '1']

    if 'Students with Scores' in df.columns:
        df = df[df['Students with Scores'] >= MIN_STUDENTS]

    df = df[df['Grade'].str.strip().isin(ELEM_GRADES)]
    df = df[df['Test ID'].str.strip().isin(['1', '2'])]

    # Drop per-year name columns; we'll join them in from the entity table for
    # consistent coverage across all years (pre-2024 files don't have names).
    keep = ['School Code', 'District Code', 'Grade', 'Test ID',
            'Percentage Standard Met and Above', 'Mean Scale Score', 'Students with Scores']
    df = df[[c for c in keep if c in df.columns]].copy()
    df['Year'] = year
    df['Subject'] = df['Test ID'].str.strip().map({'1': 'ELA', '2': 'Math'})
    df['Grade'] = df['Grade'].str.strip()
    df['School Code'] = df['School Code'].str.strip()
    df['District Code'] = df['District Code'].str.strip()
    return df


frames = []
for year, zname in sorted(YEAR_ZIPS.items()):
    zp = os.path.join(BASE_DIR, zname)
    if not os.path.exists(zp):
        print(f'  {year}: zip not found, skipping')
        continue
    path = extract_data_file(year, zp)
    if path is None:
        continue
    df = load_year(year, path)
    frames.append(df)
    print(f'  {year}: {len(df)} rows')

all_data = pd.concat(frames, ignore_index=True)

# Join entity table for school / district / county names
entities = load_entities()
if entities is not None:
    before = len(all_data)
    all_data = all_data.merge(
        entities, on=['District Code', 'School Code'], how='left',
    )
    if len(all_data) != before:
        print(f'  WARNING: row count changed during entity join ({before} -> {len(all_data)})')
    missing = all_data['School Name'].isna().sum()
    print(f'\nEntity join: {len(all_data) - missing:,}/{len(all_data):,} rows matched '
          f'({missing:,} missing — likely closed or out-of-scope schools)')

for col in ['School Name', 'District Name', 'County Name']:
    if col not in all_data.columns:
        all_data[col] = ''
    all_data[col] = all_data[col].fillna('')

all_data['is_lincoln'] = (
    (all_data['School Code'] == LINCOLN_SCHOOL_CODE) &
    (all_data['District Code'] == LINCOLN_DISTRICT_CODE)
)

print(f'\nTotal rows: {len(all_data)}')
print(f'Lincoln rows: {all_data["is_lincoln"].sum()}')

out = os.path.join(BASE_DIR, 'school_data.parquet')
all_data.to_parquet(out, index=False)
print(f'Saved: {out}')
