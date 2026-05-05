import pandas as pd

# === file paths ===
file1 = "Data/Merged_ovp_cdl_full.csv"
file2 = "Data/Tafel_Analysis_all_campaign.csv"
file3 = "Data/result_all_campaign.csv"

# === read csv ===
df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)
df3 = pd.read_csv(file3)

# === use first column as merge key ===
key1 = df1.columns[0]
key2 = df2.columns[0]
key3 = df3.columns[0]

df1 = df1.rename(columns={key1: "Experiment"})
df2 = df2.rename(columns={key2: "Experiment"})
df3 = df3.rename(columns={key3: "Experiment"})
df3 = df3.iloc[:, :14]

# === merge ===
merged = df3.merge(df2, on="Experiment", how="left")
merged = merged.merge(df1, on="Experiment", how="left")

# === save ===
merged.to_csv("Data/merged_all.csv", index=False)

print("Done. Saved as merged_all.csv")
print(merged.head())