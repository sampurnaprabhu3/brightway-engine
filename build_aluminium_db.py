import pandas as pd
from builders import build_single_metal_db

# ---- 1. Load CSV ----
csv_path = "data/iai_aluminium_simple.csv"
df = pd.read_csv(csv_path)

# ---- 2. Filter aluminium + primary_global ----
metal = "aluminium"
route = "primary_global"

df_subset = df[(df["metal"] == metal) & (df["route"] == route)]

# ---- 3. Build DB ----
build_single_metal_db(df_subset, metal, route)

print("✔ Aluminium DB built successfully using universal builder.")
