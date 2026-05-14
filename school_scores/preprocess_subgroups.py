import os, zipfile, urllib.request
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + os.sep

YEAR_URLS = {
    2015: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2015_all_41_csv_v3.zip',
    2016: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2016_all_41_csv_v3.zip',
    2017: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2017_all_41_csv_v2.zip',
    2018: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2018_all_41_csv_v3.zip',
    2019: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2019_all_41_csv_v4.zip',
    2021: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2021_all_41_csv_v2.zip',
    2022: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2022_all_41_csv_v1.zip',
    2023: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2023_all_41_csv_v1.zip',
    2024: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2024_all_41_csv_v1.zip',
    2025: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2025_all_41_csv_v1.zip',
}

LINCOLN_SCHOOL_CODE = '6043566'
ELEM_GRADES = ['3', '4', '5']

SUBGROUP_NAMES = {
    '1':   'All Students',
    '3':   'Male',
    '4':   'Female',
    '28':  'Hispanic or Latino',
    '74':  'Asian',
    '75':  'Black or African American',
    '76':  'Filipino',
    '78':  'White',
    '79':  'Two or More Races',
    '160': 'Economically Disadvantaged',
    '180': 'English Learners',
    '200': 'Students with Disabilities',
}


def download_year(year, url):
    zp = os.path.join(BASE_DIR, f'sb_ca{year}_all_41_csv.zip')
    if os.path.exists(zp):
        print(f'  {year}: already downloaded')
        return zp
    print(f'  {year}: downloading...', end=' ', flush=True)
    urllib.request.urlretrieve(url, zp)
    print('done')
    return zp


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
        'School Code':                      ['School Code'],
        'District Code':                    ['District Code'],
        'Grade':                            ['Grade'],
        'Test ID':                          ['Test ID', 'Test Id'],
        'Subgroup ID':                      ['Subgroup ID', 'Student Group ID'],
        'Percentage Standard Met and Above': ['Percentage Standard Met and Above'],
        'Mean Scale Score':                 ['Mean Scale Score'],
        'Students with Scores':             [
            'Total Students Tested with Scores',
            'Students with Scores',
            'Students Tested',
        ],
    }
    col_map = {}
    for canonical, options in aliases.items():
        for opt in options:
            if opt in df.columns and opt not in col_map:
                col_map[opt] = canonical
                break
    return df.rename(columns=col_map)


def load_lincoln_subgroups(year, path):
    sep = detect_sep(path)
    df = pd.read_csv(path, sep=sep, dtype=str, low_memory=False, encoding='latin-1')
    df = normalise_cols(df)

    lincoln = df[df['School Code'].str.strip() == LINCOLN_SCHOOL_CODE].copy()
    lincoln = lincoln[lincoln['Grade'].str.strip().isin(ELEM_GRADES)]
    lincoln = lincoln[lincoln['Test ID'].str.strip().isin(['1', '2'])]
    lincoln = lincoln[lincoln['Subgroup ID'].str.strip().isin(SUBGROUP_NAMES.keys())]

    for col in ['Percentage Standard Met and Above', 'Mean Scale Score', 'Students with Scores']:
        if col in lincoln.columns:
            lincoln[col] = pd.to_numeric(lincoln[col], errors='coerce')

    lincoln['Year'] = year
    lincoln['Subject'] = lincoln['Test ID'].str.strip().map({'1': 'ELA', '2': 'Math'})
    lincoln['Grade'] = lincoln['Grade'].str.strip()
    lincoln['Subgroup ID'] = lincoln['Subgroup ID'].str.strip()
    lincoln['Subgroup'] = lincoln['Subgroup ID'].map(SUBGROUP_NAMES)

    keep = ['Year', 'Subject', 'Grade', 'Subgroup ID', 'Subgroup',
            'Percentage Standard Met and Above', 'Mean Scale Score', 'Students with Scores']
    return lincoln[[c for c in keep if c in lincoln.columns]]


print('=== DOWNLOADING SUBGROUP DATA (San Mateo County) ===\n')
frames = []
for year, url in sorted(YEAR_URLS.items()):
    zp = download_year(year, url)
    path = extract_data_file(year, zp)
    if path is None:
        print(f'  {year}: no data file found')
        continue
    sub_df = load_lincoln_subgroups(year, path)
    print(f'  {year}: {len(sub_df)} Lincoln subgroup rows, {sub_df["Subgroup"].nunique()} subgroups')
    frames.append(sub_df)

all_subgroups = pd.concat(frames, ignore_index=True)
all_subgroups = all_subgroups.rename(columns={'Percentage Standard Met and Above': 'Pct Met Above'})

out = os.path.join(BASE_DIR, 'subgroup_data.parquet')
all_subgroups.to_parquet(out, index=False)
print(f'\nSaved: {out}')
print(f'Total rows: {len(all_subgroups)}')
print(all_subgroups.groupby('Subgroup')['Pct Met Above'].count().sort_values(ascending=False))
