import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'sb_ca2025_1_csv_v1.txt')
OUT_DIR = BASE_DIR + os.sep

LINCOLN_SCHOOL_CODE = '6043566'
LINCOLN_DISTRICT_CODE = '68882'

df = pd.read_csv(DATA_FILE, sep='^', dtype=str, low_memory=False, encoding='latin-1')

numeric_cols = ['Mean Scale Score', 'Percentage Standard Met and Above',
                'Total Students Tested with Scores']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

school_types = {'7', '9', '10'}
df_schools = df[df['Type ID'].isin(school_types)].copy()

df_schools = df_schools[df_schools['Total Students Tested with Scores'] >= 20]

ELEM_GRADES = ['3', '4', '5']

ELA = '1'
MATH = '2'

PERCENTILES = [25, 50, 75, 90, 95]
COLORS = {
    'lincoln': '#2563EB',
    25: '#F87171',
    50: '#9CA3AF',
    75: '#6B7280',
    90: '#F59E0B',
    95: '#10B981',
    'dist': '#E5E7EB',
}

lincoln_rows = df[
    (df['School Code'] == LINCOLN_SCHOOL_CODE) &
    (df['District Code'] == LINCOLN_DISTRICT_CODE)
].copy()
for col in numeric_cols:
    lincoln_rows[col] = pd.to_numeric(lincoln_rows[col], errors='coerce')


def get_lincoln(grade, test_id):
    row = lincoln_rows[
        (lincoln_rows['Grade'] == grade) &
        (lincoln_rows['Test ID'] == test_id)
    ]
    if len(row) == 0:
        return None
    return float(row['Percentage Standard Met and Above'].iloc[0])


def grade_pool(grade, test_id):
    pool = df_schools[
        (df_schools['Grade'] == grade) &
        (df_schools['Test ID'] == test_id)
    ]['Percentage Standard Met and Above'].dropna()
    return pool


def percentile_val(pool, pct):
    return float(np.percentile(pool, pct))


def lincoln_percentile(pool, lincoln_val):
    return float((pool < lincoln_val).mean() * 100)


fig, axes = plt.subplots(2, 3, figsize=(16, 10))
fig.suptitle(
    'Lincoln Elementary (Burlingame) vs. California Elementary Schools\n2024–25 CAASPP Smarter Balanced',
    fontsize=14, fontweight='bold', y=0.98
)

for row_idx, (test_id, subject) in enumerate([(ELA, 'ELA'), (MATH, 'Math')]):
    for col_idx, grade in enumerate(ELEM_GRADES):
        ax = axes[row_idx][col_idx]
        pool = grade_pool(grade, test_id)
        lincoln_val = get_lincoln(grade, test_id)

        pct_vals = {p: percentile_val(pool, p) for p in PERCENTILES}

        ax.hist(pool, bins=40, color=COLORS['dist'], edgecolor='white', linewidth=0.5)

        for pct in PERCENTILES:
            ax.axvline(pct_vals[pct], color=COLORS[pct], linestyle='--', linewidth=1.4,
                       label=f'{pct}th pct ({pct_vals[pct]:.1f}%)')

        if lincoln_val is not None:
            lincoln_pct = lincoln_percentile(pool, lincoln_val)
            ax.axvline(lincoln_val, color=COLORS['lincoln'], linewidth=2.5,
                       label=f'Lincoln ({lincoln_val:.1f}%) — {lincoln_pct:.0f}th pct')

        ax.set_title(f'{subject} — Grade {grade}', fontweight='bold')
        ax.set_xlabel('% Standard Met and Above')
        ax.set_ylabel('Number of Schools')
        ax.legend(fontsize=7.5, loc='upper left')

plt.tight_layout(rect=[0, 0, 1, 0.96])
dist_path = OUT_DIR + 'distribution_charts.png'
plt.savefig(dist_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved: {dist_path}')


fig2, axes2 = plt.subplots(1, 2, figsize=(14, 7))
fig2.suptitle(
    'Lincoln Elementary (Burlingame) — % Standard Met & Above vs. CA Benchmarks\n2024–25 CAASPP',
    fontsize=13, fontweight='bold'
)

for col_idx, (test_id, subject) in enumerate([(ELA, 'ELA'), (MATH, 'Math')]):
    ax = axes2[col_idx]
    grades = ELEM_GRADES
    x = np.arange(len(grades))
    width = 0.18

    lincoln_vals = [get_lincoln(g, test_id) for g in grades]
    pct_series = {p: [percentile_val(grade_pool(g, test_id), p) for g in grades] for p in PERCENTILES}

    offsets = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]
    pct_labels = {25: '25th Percentile', 50: '50th (Median)', 75: '75th Percentile',
                  90: '90th Percentile', 95: '95th Percentile'}

    for i, pct in enumerate(PERCENTILES):
        ax.bar(x + offsets[i]*width, pct_series[pct], width, label=pct_labels[pct], color=COLORS[pct])
    ax.bar(x + offsets[5]*width, lincoln_vals, width, label='Lincoln', color=COLORS['lincoln'], zorder=5)

    for i, (g, lv) in enumerate(zip(grades, lincoln_vals)):
        if lv is not None:
            pool = grade_pool(g, test_id)
            lp = lincoln_percentile(pool, lv)
            ax.text(x[i] + offsets[5]*width, lv + 0.8, f'{lp:.0f}th', ha='center', fontsize=8,
                    color=COLORS['lincoln'], fontweight='bold')

    ax.set_title(f'{subject}', fontweight='bold', fontsize=12)
    ax.set_xlabel('Grade')
    ax.set_ylabel('% Standard Met and Above')
    ax.set_xticks(x)
    ax.set_xticklabels([f'Grade {g}' for g in grades])
    ax.set_ylim(0, 105)
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.93])
bar_path = OUT_DIR + 'benchmark_comparison.png'
plt.savefig(bar_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved: {bar_path}')


print('\n=== LINCOLN ELEMENTARY — SUMMARY ===')
for test_id, subject in [(ELA, 'ELA'), (MATH, 'Math')]:
    print(f'\n{subject}')
    print(f"{'Grade':<8} {'Lincoln %':>10} {'Lincoln Pct':>12} {'25th':>8} {'50th':>8} {'75th':>8} {'90th':>8} {'95th':>8}")
    print('-' * 78)
    for grade in ELEM_GRADES:
        pool = grade_pool(grade, test_id)
        lv = get_lincoln(grade, test_id)
        if lv is None:
            continue
        lp = lincoln_percentile(pool, lv)
        p25 = percentile_val(pool, 25)
        p50 = percentile_val(pool, 50)
        p75 = percentile_val(pool, 75)
        p90 = percentile_val(pool, 90)
        p95 = percentile_val(pool, 95)
        print(f"{'Grade '+grade:<8} {lv:>10.1f} {lp:>11.0f}th {p25:>8.1f} {p50:>8.1f} {p75:>8.1f} {p90:>8.1f} {p95:>8.1f}")
