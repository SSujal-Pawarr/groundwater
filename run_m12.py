import pandas as pd
import numpy as np
import os
from features.groundwater_stress import compute_scarcity_intelligence

from features.seasonal import assign_india_season

print("Loading data...")
india_path = "data/processed/india/india_normalized.parquet"
mh_path = "data/processed/maharashtra/maharashtra_normalized.parquet"

df_in = pd.read_parquet(india_path)
df_in = assign_india_season(df_in)

df_mh = pd.read_parquet(mh_path)
df_mh["month"] = pd.to_datetime(df_mh["observation_timestamp"]).dt.month.astype(str).str.zfill(2)

print(f"India rows: {len(df_in)}")
print(f"MH rows: {len(df_mh)}")

print("Computing India Stress Intelligence...")
res_in = compute_scarcity_intelligence(df_in, is_india=True, region_col="district")

print("Computing Maharashtra Stress Intelligence...")
res_mh = compute_scarcity_intelligence(df_mh, is_india=False, region_col="district")

os.makedirs("data/stress_intelligence", exist_ok=True)

out_in = "data/stress_intelligence/india_stress_intelligence.parquet"
out_mh = "data/stress_intelligence/maharashtra_stress_intelligence.parquet"

res_in.to_parquet(out_in, index=False)
res_mh.to_parquet(out_mh, index=False)

print("\n--- M12 REPORT ---")
print(f"Total rows: {len(res_in) + len(res_mh)}")
print(f"India rows: {len(res_in)}")
print(f"Maharashtra rows: {len(res_mh)}")
print(f"Number of sites (India): {res_in['candidate_site_id'].nunique()}")
print(f"Number of districts (India): {df_in['district'].nunique()}")

in_state_counts = res_in["stress_state"].value_counts(dropna=False)
mh_state_counts = res_mh["stress_state"].value_counts(dropna=False)

total_states = in_state_counts.add(mh_state_counts, fill_value=0)

print("\nStress Distribution (Combined):")
print(total_states)

print("\nStress Distribution (India):")
print(in_state_counts)

print("\nStress Distribution (Maharashtra):")
print(mh_state_counts)

print("\nMissing values (India):")
print(res_in.isna().sum())

print("\nArtifact paths:")
print(f"- {out_in}")
print(f"- {out_mh}")

