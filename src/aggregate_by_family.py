#!/usr/bin/env python3
import pandas as pd
import argparse

# ===============================
# ARGUMENT PARSER
# ===============================
parser = argparse.ArgumentParser(description="Aggregate health annotations by Family ID")
parser.add_argument("-i", "--input", required=True, help="Input health annotation CSV file")
parser.add_argument("-o", "--output", required=True, help="Output aggregated CSV file")
args = parser.parse_args()

# ===============================
# LOAD INPUT
# ===============================
print("Loading input file...")
df = pd.read_csv(args.input)

print(f"Health annotation rows loaded: {len(df)}")
print("Columns detected:", df.columns.tolist())

# ===============================
# CHECK FAMILY ID EXISTS
# ===============================
if "Family ID" not in df.columns:
    raise ValueError("Input file must contain 'Family ID' column")

# ===============================
# SAFE SEMICOLON JOIN
# ===============================
def safe_join(series):
    vals = set()
    for item in series.dropna():
        item = str(item)
        vals.update([x.strip().lower() for x in item.split(";") if x.strip()])
    return ";".join(sorted(vals))

# ===============================
# BUILD AGGREGATION DICTIONARY
# ===============================
agg_dict = {}

# metadata columns
for col in ["Country", "Year", "Response"]:
    if col in df.columns:
        agg_dict[col] = "first"

# binary health columns
for col in [
    "Health relevance (1/0)",
    "Health adaptation mandate (1/0)",
    "Institutional health role (1/0)"
]:
    if col in df.columns:
        agg_dict[col] = "max"

# keyword columns
if "Matched health keywords" in df.columns:
    agg_dict["Matched health keywords"] = safe_join

if "Health keyword categories" in df.columns:
    agg_dict["Health keyword categories"] = safe_join

# ===============================
# AGGREGATE BY FAMILY ID
# ===============================
print("Aggregating by Family ID...")

df_family = df.groupby("Family ID", dropna=False).agg(agg_dict).reset_index()


# ===============================
# SAVE OUTPUT
# ===============================
df_family.to_csv(args.output, index=False)

print(f"✔ Aggregated output saved to: {args.output}")
print(f"Total Family IDs in output: {len(df_family)}")