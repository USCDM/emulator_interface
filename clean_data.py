import os
import pandas as pd

RAW_DATASETS = {
    "pdiabe": "data/uscdm_emu_pdiabe_regression_ests.csv",
    "phearte": "data/uscdm_emu_phearte_regression_ests.csv",
    "phibpe": "data/uscdm_emu_phibpe_regression_ests.csv",
    "pcogstate": "data/uscdm_emu_pcogstate_regression_ests.csv"
}

CLEANED_DIR = "clean_data"
os.makedirs(CLEANED_DIR, exist_ok=True)


def clean_column(col):
    col = str(col).strip()
    if col.startswith("=\"") and col.endswith("\""):
        col = col[2:-1]
    col = col.strip('"')
    return col


def clean_cell(val):
    if isinstance(val, str):
        val = val.strip()
        if val.startswith("=\"") and val.endswith("\""):
            return val[2:-1]
        return val.strip('"')
    return val


def debug_dataset(df, name):
    print("\n" + "="*80)
    print(f"DEBUG: Checking cleaned dataset --> {name}")
    print("="*80)

    print(f"Shape: {df.shape}")

    print("\nFirst 10 column names:")
    print(df.columns[:10].tolist())

    print("\nSample rows:")
    print(df.head(3))

    # Check numeric conversion
    numeric_check = df.apply(pd.to_numeric, errors='coerce')
    non_numeric_cols = numeric_check.columns[numeric_check.isna().any()].tolist()

    print("\n➡ Columns with non-numeric values (after coercion):")
    print(non_numeric_cols[:10])   # print only first 10 if long

    # Check Year column
    if "Year" in df.columns:
        print("\n'Year' column unique values:")
        print(df["Year"].unique()[:10])

    print("="*80 + "\n")

for name, path in RAW_DATASETS.items():
    if not os.path.exists(path):
        print(f"File not found: {path}")
        continue

    print(f"\n🔄 Cleaning dataset: {name}")

    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    # Clean columns
    df.columns = [clean_column(c) for c in df.columns]

    # Clean cells
    df = df.applymap(clean_cell)

    # Convert numeric columns safely
    for col in df.columns:
        if col != "Year":  # keep Year as string
            df[col] = pd.to_numeric(df[col], errors="ignore")

    output_path = os.path.join(CLEANED_DIR, f"{name}_cleaned.csv")
    df.to_csv(output_path, index=False)

    print(f"Saved cleaned dataset: {output_path}")

    debug_dataset(df, name)
