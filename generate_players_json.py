# generate_players_json.py
# Run this script in JupyterLite (with the CSVs) to generate players.json
# Then deploy nbav1.py + players.json to Render/Railway

import pandas as pd
import json


# Load the datasets
df = pd.read_csv("NBA_Data.csv")  # Main player statistics data
df_averages = pd.read_csv("U_Averages.csv")  # Player averages data
df_names = pd.read_csv("Names.csv")  # NBA player IDs and names


# Define the skill columns to analyze
skills = ['FG_PCT', 'FG3_PCT', 'FT_PCT', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']


# Remove any leading/trailing whitespace from column names
df.columns = df.columns.str.strip()
df_averages.columns = df_averages.columns.str.strip()
df_names.columns = df_names.columns.str.strip()


# Remove header rows from dataframes (rows 0 and 1 contain metadata/headers)
df = df.iloc[1:]
df_averages = df_averages.iloc[1:]


# CRITICAL: Normalize Player_IDs immediately after loading
# Convert numeric-looking IDs to integers, then to strings (removes trailing .0)
df["Player_ID"] = (
    pd.to_numeric(df["Player_ID"], errors="coerce")
    .astype("Int64")
    .astype(str)
    .str.strip()
)
df_averages["Player_ID"] = (
    pd.to_numeric(df_averages["Player_ID"], errors="coerce")
    .astype("Int64")
    .astype(str)
    .str.strip()
)
df_names["Player_ID"] = (
    pd.to_numeric(df_names["Player_ID"], errors="coerce")
    .fillna(0)
    .astype("Int64")
    .astype(str)
    .str.strip()
)


# Convert skill columns to numeric
for skill in skills:
    df[skill] = pd.to_numeric(df[skill], errors="coerce")


# Reset index after slicing to avoid alignment issues
df = df.reset_index(drop=True)
df_averages = df_averages.reset_index(drop=True)


# Calculate z-scores manually (no sklearn needed)
# z-score = (value - mean) / std
for skill in skills:
    mean = df[skill].mean()
    std = df[skill].std()
    if std > 0:
        df[skill + "_z"] = (df[skill] - mean) / std
    else:
        df[skill + "_z"] = 0


# Get list of all z-score column names
z_cols = [c for c in df.columns if c.endswith("_z")]


# Remove rows where all z-scores are missing (invalid players)
df = df.dropna(subset=z_cols, how="all")


# Find each player's best skill (highest z-score) and remove the "_z" suffix
df["best_skill"] = (
    df[z_cols]
    .idxmax(axis=1, skipna=True)  # Find column with max value for each row
    .str.replace("_z", "")  # Remove suffix to get original skill name
)


# Store the actual z-score value of the best skill
df["best_score"] = df[z_cols].max(axis=1, skipna=True)


# Merge main data with averages data to get raw skill values
merged = df.merge(df_averages, on="Player_ID", suffixes=("", "_raw"))


# For each player, extract the raw value of their best skill
merged["best_skill_raw_value"] = merged.apply(
    lambda row: row[row["best_skill"]],  # Use best_skill name to lookup its raw value
    axis=1
)


# Merge the dataframes on Player_ID
final_df = merged.merge(
    df_names[['Player_ID', 'Name']],
    on='Player_ID',
    how='left'  # Keep all players even if name not found
)


# Show merge statistics
print("MERGE DIAGNOSTICS:")
print(f"Players in final dataset: {len(final_df)}")
print(f"Players with names: {final_df['Name'].notna().sum()}")
print(f"Players without names: {final_df['Name'].isna().sum()}")


# Verify LeBron is there
lebron_check = final_df[final_df['Name'].str.contains('LeBron', case=False, na=False)]
if len(lebron_check) > 0:
    print(f"\n✓ LeBron James found in final dataset!")
else:
    print(f"\n✗ LeBron James NOT in final dataset")
    lebron_in_names = df_names[df_names['Name'].str.contains('LeBron', case=False, na=False)]
    if len(lebron_in_names) > 0:
        lebron_id = lebron_in_names['Player_ID'].values[0]
        print(f"   LeBron's Player_ID in Names.csv: {lebron_id}")
        print(f"   Is this ID in NBA_Data? {lebron_id in df['Player_ID'].values}")


print("\n" + "="*60)


# Export to JSON for the FastAPI app
output = final_df[['Player_ID', 'Name', 'best_skill', 'best_score', 'best_skill_raw_value']].copy()
output.columns = ['player_id', 'name', 'best_skill', 'z_score', 'raw_value']

# Round z_score to 3 decimal places for cleaner output
output['z_score'] = output['z_score'].round(3)

# Convert to list of dictionaries and save as JSON
players_list = output.to_dict(orient='records')

with open('players.json', 'w') as f:
    json.dump(players_list, f, indent=2)

print(f"\n✓ Exported {len(players_list)} players to players.json")
print("\nNext steps:")
print("1. Copy players.json to your deployment folder")
print("2. Deploy nbav1.py + players.json to Render/Railway")
