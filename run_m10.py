import pandas as pd
from src.features.drought_intelligence import compute_drought_intelligence
from src.features.seasonal import assign_india_season

print("Loading dataset...")
df = pd.read_parquet("data/processed/india/india_normalized.parquet")
df = assign_india_season(df)

print("Running M10 Drought Intelligence Engine...")
res = compute_drought_intelligence(df)

print("\n--- M10 DROUGHT INTELLIGENCE REPORT ---")
print(f"Total historical observations processed: {len(res)}")

status_counts = res["drought_status"].value_counts(dropna=False)
print("\nStatus Distribution:")
print(status_counts.to_string())

# Calculate spatial aggregation info (only for SEVERE and MODERATE)
drought_df = res[res["drought_status"].isin(["SEVERE_DEFICIT", "MODERATE_DEFICIT"])]
print(f"\nTotal observations classified as actively in drought: {len(drought_df)}")

# See how many unique districts have ever experienced a drought status
districts_with_drought = drought_df["district"].nunique() if "district" in drought_df.columns else 0
print(f"Unique districts that ever recorded a severe/moderate drought status: {districts_with_drought}")

# Persistence stats
max_persistence = res["consecutive_deficit_seasons"].max()
print(f"\nMaximum recorded consecutive deficit seasons across all sites: {max_persistence}")

# Insufficient history
insufficient = status_counts.get("INSUFFICIENT_HISTORY", 0)
pct_insufficient = (insufficient / len(res)) * 100
print(f"Observations lacking 10-year history: {insufficient} ({pct_insufficient:.2f}%)")

