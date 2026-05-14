import os, zipfile, pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + os.sep

for year in [2015, 2019, 2025]:
    zip_path = os.path.join(BASE_DIR, f'sb_ca{year}_1_csv.zip')
    with zipfile.ZipFile(zip_path, 'r') as z:
        names = z.namelist()
        data_files = [n for n in names if '_1_csv' in n and n.endswith('.txt')]
        if not data_files:
            data_files = [n for n in names if n.endswith('.txt') and 'entit' not in n.lower()]
        target = data_files[0]
        extracted = os.path.join(BASE_DIR, target)
        if not os.path.exists(extracted):
            z.extract(target, BASE_DIR)
    df = pd.read_csv(extracted, sep='^', dtype=str, nrows=1, encoding='latin-1')
    print(f'\n{year} columns:')
    for c in df.columns:
        print(f'  "{c}"')
