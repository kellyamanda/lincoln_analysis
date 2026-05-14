import os
import urllib.request
import zipfile
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + os.sep

YEAR_URLS = {
    2015: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2015_1_csv_v3.zip',
    2016: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2016_1_csv_v3.zip',
    2017: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2017_1_csv_v2.zip',
    2018: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2018_1_csv_v3.zip',
    2019: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2019_1_csv_v4.zip',
    2021: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2021_1_csv_v2.zip',
    2022: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2022_1_csv_v1.zip',
    2023: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2023_1_csv_v1.zip',
    2024: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2024_1_csv_v1.zip',
    2025: 'https://caaspp-elpac.ets.org/caaspp/researchfiles/sb_ca2025_1_csv_v1.zip',
}

LINCOLN_SCHOOL_CODE = '6043566'
LINCOLN_DISTRICT_CODE = '68882'
ELEM_GRADES = ['3', '4', '5']
ELA = '1'
MATH = '2'
SCHOOL_TYPES = {'7', '9', '10'}
MIN_STUDENTS = 20
PERCENTILES = [25, 50, 75, 90, 95]


def zip_path_for(year):
    return os.path.join(BASE_DIR, f'sb_ca{year}_1_csv.zip')


def download_year(year, url):
    zp = zip_path_for(year)
    orig = os.path.join(BASE_DIR, os.path.basename(url))
    if os.path.exists(zp):
        print(f'  {year}: already downloaded')
        return zp
    if os.path.exists(orig):
        os.rename(orig, zp)
        print(f'  {year}: renamed existing file')
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
            print(f'  {year}: no data .txt found in {names}')
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
    rename = {}
    for c in df.columns:
        clean = c.strip().strip('"')
        rename[c] = clean
    df = df.rename(columns=rename)

    aliases = {
        'Type ID': ['Type ID', 'TypeID'],
        'School Code': ['School Code', 'SchoolCode'],
        'District Code': ['District Code', 'DistrictCode'],
        'Grade': ['Grade'],
        'Test ID': ['Test ID', 'Test Id', 'TestID', 'TestId'],
        'Percentage Standard Met and Above': ['Percentage Standard Met and Above'],
        'Students with Scores': [
            'Total Students Tested with Scores',
            'Students with Scores',
            'Students Tested',
        ],
        'Subgroup ID': ['Subgroup ID', 'Student Group ID'],
    }

    col_map = {}
    for canonical, options in aliases.items():
        for opt in options:
            if opt in df.columns:
                col_map[opt] = canonical
                break

    df = df.rename(columns=col_map)
    return df


def load_year(year, path):
    sep = detect_sep(path)
    df = pd.read_csv(path, sep=sep, dtype=str, low_memory=False, encoding='latin-1')
    df = normalise_cols(df)

    numeric_cols = ['Percentage Standard Met and Above', 'Students with Scores']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'Type ID' in df.columns:
        df_schools = df[df['Type ID'].isin(SCHOOL_TYPES)].copy()
    else:
        non_zero_school = df['School Code'].str.strip().str.lstrip('0') != ''
        df_schools = df[non_zero_school].copy()
        df_schools = df_schools[df_schools['School Code'].str.strip() != '0000000']

    if 'Subgroup ID' in df_schools.columns:
        df_schools = df_schools[df_schools['Subgroup ID'].str.strip() == '1']

    if 'Students with Scores' in df_schools.columns:
        df_schools = df_schools[df_schools['Students with Scores'] >= MIN_STUDENTS]

    lincoln = df[df['School Code'].str.strip() == LINCOLN_SCHOOL_CODE].copy()
    if 'Subgroup ID' in lincoln.columns:
        lincoln = lincoln[lincoln['Subgroup ID'].str.strip() == '1']
    for col in numeric_cols:
        if col in lincoln.columns:
            lincoln[col] = pd.to_numeric(lincoln[col], errors='coerce')

    return df_schools, lincoln


def compute_year_stats(year, df_schools, lincoln):
    results = {}
    for test_id, subject in [(ELA, 'ELA'), (MATH, 'Math')]:
        for grade in ELEM_GRADES:
            pool = df_schools[
                (df_schools['Grade'].str.strip() == grade) &
                (df_schools['Test ID'].str.strip() == test_id)
            ]['Percentage Standard Met and Above'].dropna()

            lincoln_row = lincoln[
                (lincoln['Grade'].str.strip() == grade) &
                (lincoln['Test ID'].str.strip() == test_id)
            ]

            lincoln_val = None
            lincoln_pct = None
            if len(lincoln_row) > 0:
                v = lincoln_row['Percentage Standard Met and Above'].iloc[0]
                if pd.notna(v):
                    lincoln_val = float(v)
                    if len(pool) > 0:
                        lincoln_pct = float((pool < lincoln_val).mean() * 100)

            pct_vals = {}
            if len(pool) > 0:
                pct_vals = {p: float(np.percentile(pool, p)) for p in PERCENTILES}

            results[(subject, grade)] = {
                'lincoln_val': lincoln_val,
                'lincoln_pct': lincoln_pct,
                'pool_size': len(pool),
                **{f'p{p}': pct_vals.get(p) for p in PERCENTILES},
            }
    return results


print('=== DOWNLOADING AND PROCESSING DATA ===\n')
all_stats = {}
for year, url in sorted(YEAR_URLS.items()):
    zp = download_year(year, url)
    data_path = extract_data_file(year, zp)
    if data_path is None:
        continue
    df_schools, lincoln = load_year(year, data_path)
    print(f'  {year}: {len(df_schools)} school rows, {len(lincoln)} Lincoln rows')
    all_stats[year] = compute_year_stats(year, df_schools, lincoln)

print('\n=== PROCESSING COMPLETE ===\n')

years = sorted(all_stats.keys())
COLORS_GRADE = {'3': '#2563EB', '4': '#F59E0B', '5': '#10B981'}
COLORS_PCT = {25: '#F87171', 50: '#9CA3AF', 75: '#6B7280', 90: '#F59E0B', 95: '#10B981'}
LINCOLN_COLOR = '#2563EB'


fig, axes = plt.subplots(2, 3, figsize=(18, 11))
fig.suptitle(
    "Lincoln Elementary (Burlingame) — % Standard Met & Above Over Time\nvs. California Percentile Benchmarks",
    fontsize=14, fontweight='bold', y=0.99
)

for row_idx, subject in enumerate(['ELA', 'Math']):
    for col_idx, grade in enumerate(ELEM_GRADES):
        ax = axes[row_idx][col_idx]
        valid_years, lincoln_vals, lincoln_pcts = [], [], []
        p_series = {p: [] for p in PERCENTILES}

        for yr in years:
            stats = all_stats[yr].get((subject, grade), {})
            if stats.get('lincoln_val') is None:
                continue
            valid_years.append(yr)
            lincoln_vals.append(stats['lincoln_val'])
            lincoln_pcts.append(stats['lincoln_pct'])
            for p in PERCENTILES:
                p_series[p].append(stats.get(f'p{p}'))

        for p in PERCENTILES:
            vals = p_series[p]
            if any(v is not None for v in vals):
                ax.plot(valid_years, vals, color=COLORS_PCT[p], linewidth=1.2,
                        linestyle='--', alpha=0.8, label=f'{p}th pct CA')

        ax.plot(valid_years, lincoln_vals, color=LINCOLN_COLOR, linewidth=2.5,
                marker='o', markersize=5, label='Lincoln', zorder=5)

        for yr, lv, lp in zip(valid_years, lincoln_vals, lincoln_pcts):
            if lp is not None:
                ax.annotate(f'{lp:.0f}th', (yr, lv), textcoords='offset points',
                            xytext=(0, 7), ha='center', fontsize=7,
                            color=LINCOLN_COLOR, fontweight='bold')

        ax.axvspan(2019.6, 2020.4, alpha=0.12, color='red')
        ax.text(2020, 5, 'COVID\n(no test)', ha='center', fontsize=6.5, color='red', alpha=0.7)

        ax.set_title(f'{subject} — Grade {grade}', fontweight='bold')
        ax.set_xlabel('School Year')
        ax.set_ylabel('% Standard Met and Above')
        ax.set_xticks(valid_years)
        ax.set_xticklabels([str(y) for y in valid_years], rotation=45, fontsize=8)
        ax.set_ylim(0, 108)
        ax.legend(fontsize=7, loc='lower left')
        ax.grid(axis='y', alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.97])
trend_path = os.path.join(BASE_DIR, 'multiyear_trend.png')
plt.savefig(trend_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved: {trend_path}')


fig2, axes2 = plt.subplots(1, 2, figsize=(16, 7))
fig2.suptitle(
    "Lincoln Elementary — CA Percentile Rank Over Time",
    fontsize=13, fontweight='bold'
)

for col_idx, subject in enumerate(['ELA', 'Math']):
    ax = axes2[col_idx]
    for grade in ELEM_GRADES:
        pcts, valid_years = [], []
        for yr in years:
            stats = all_stats[yr].get((subject, grade), {})
            if stats.get('lincoln_pct') is not None:
                valid_years.append(yr)
                pcts.append(stats['lincoln_pct'])
        ax.plot(valid_years, pcts, color=COLORS_GRADE[grade], linewidth=2,
                marker='o', markersize=5, label=f'Grade {grade}')

    avg_pcts, avg_years = [], []
    for yr in years:
        vals = [all_stats[yr][(subject, g)]['lincoln_pct']
                for g in ELEM_GRADES
                if all_stats[yr].get((subject, g), {}).get('lincoln_pct') is not None]
        if vals:
            avg_years.append(yr)
            avg_pcts.append(np.mean(vals))
    ax.plot(avg_years, avg_pcts, color='black', linewidth=2.5, linestyle='--',
            marker='s', markersize=5, label='Avg grade', zorder=5)

    ax.axhline(90, color='#10B981', linestyle=':', linewidth=1.2, alpha=0.7, label='90th pct line')
    ax.axhline(95, color='#F59E0B', linestyle=':', linewidth=1.2, alpha=0.7, label='95th pct line')
    ax.axvspan(2019.6, 2020.4, alpha=0.12, color='red')

    ax.set_title(f'{subject}', fontweight='bold', fontsize=12)
    ax.set_xlabel('School Year')
    ax.set_ylabel("Lincoln's Percentile Rank Among CA Schools")
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45)
    ax.set_ylim(50, 100)
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.95])
rank_path = os.path.join(BASE_DIR, 'multiyear_rank.png')
plt.savefig(rank_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved: {rank_path}')


print('\n=== LINCOLN MULTI-YEAR SUMMARY ===')
for subject in ['ELA', 'Math']:
    print(f'\n{subject}')
    print(f"{'Year':<6}" + ''.join(f"  Gr{g} val  pct" for g in ELEM_GRADES))
    print('-' * 54)
    for yr in years:
        row = f'{yr:<6}'
        for grade in ELEM_GRADES:
            stats = all_stats[yr].get((subject, grade), {})
            lv = stats.get('lincoln_val')
            lp = stats.get('lincoln_pct')
            if lv is not None and lp is not None:
                row += f'  {lv:>7.1f}  {lp:>3.0f}th'
            else:
                row += f'  {"N/A":>7}  {"":>4}'
        print(row)
