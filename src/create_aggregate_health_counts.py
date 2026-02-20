#!/usr/bin/env python3

import pandas as pd
import argparse
from collections import Counter

# -------------------------------
# Country → Subregion mapping
# -------------------------------
SUBREGION_MAP = {
    "Albania": "Southern",
    "Austria": "Western",
    "Belgium": "Western",
    "Bosnia and Herzegovina": "Southern",
    "Bulgaria": "Eastern",
    "Croatia": "Southern",
    "Cyprus": "Southern",
    "Czechia": "Eastern",
    "Denmark": "Northern",
    "Estonia": "Northern",
    "Finland": "Northern",
    "France": "Western",
    "Germany": "Western",
    "Greece": "Southern",
    "Hungary": "Eastern",
    "Iceland": "Northern",
    "Ireland": "Northern",
    "Italy": "Southern",
    "Kosovo": "Southern",
    "Latvia": "Northern",
    "Liechtenstein": "Western",
    "Lithuania": "Northern",
    "Luxembourg": "Western",
    "Malta": "Southern",
    "Montenegro": "Southern",
    "Netherlands": "Western",
    "North Macedonia": "Southern",
    "Norway": "Northern",
    "Poland": "Eastern",
    "Portugal": "Southern",
    "Romania": "Eastern",
    "Serbia": "Southern",
    "Slovakia": "Eastern",
    "Slovenia": "Southern",
    "Spain": "Southern",
    "Sweden": "Northern",
    "Switzerland": "Western",
    "Türkiye": "Southern",
    "United Kingdom": "UK"
}

# -------------------------------
# Health categories and labels
# -------------------------------
CATEGORY_LABELS = {
    "general_health": "General health",
    "communicable_disease": "Communicable disease",
    "non_communicable_disease": "Non-communicable disease",
    "vector_borne_zoonotic": "Vector-borne & zoonotic",
    "food_waterborne": "Food & waterborne",
    "environmental_health": "Environmental health",
    "nutrition": "Nutrition",
    "maternal_child_health": "Maternal & child health",
    "mental_health": "Mental health",
    "injury_trauma": "Injury & trauma",
    "mortality_morbidity": "Mortality & morbidity",
    "pathogens_microbiology": "Pathogens & microbiology",
    "substance_use": "Substance use"
}

RESPONSE_TOPICS = ["Adaptation", "Disaster Risk Management", "Loss And Damage", "Mitigation"]

HEALTH_FEATURES = [
    "Health relevance (1/0)",
    "Health adaptation mandate (1/0)",
    "Institutional health role (1/0)"
]

# -------------------------------
# Core aggregation function
# -------------------------------
def aggregate_panel_annotations(panel_csv, annotations_csv, output_excel):
    panel = pd.read_csv(panel_csv)
    annotations = pd.read_csv(annotations_csv)

    # Merge panel and annotations
    df = panel.merge(
        annotations[["Doc ID", "Country"] + HEALTH_FEATURES + ["Response", "Health keyword categories"]],
        left_on="Document ID",
        right_on="Doc ID",
        how="left"
    )

    # Fill missing numeric columns
    for col in HEALTH_FEATURES:
        df[col] = df[col].fillna(0).astype(int)

    df["Country"] = df["Country"].fillna("Unknown")
    df["Year"] = df["Year"].astype(int)
    df["Health keyword categories"] = df["Health keyword categories"].fillna("")

    min_year = 2000
    max_year = df["Year"].max()
    all_years = list(range(min_year, max_year + 1))

    # --- Helper function to count multi-keyword columns ---
    def count_keywords(series, allowed_keywords):
        counts = Counter()
        for val in series.dropna():
            for kw in val.split(";"):
                kw = kw.strip()
                if kw in allowed_keywords:
                    counts[kw] += 1
        return counts

    # --- Country-level aggregation ---
    country_records = []
    for country, group in df.groupby("Country"):
        for year in all_years:
            df_year = group[group["Year"] == year]
            rec = {"Country": country, "Year": year, "Total documents": len(df_year)}
            for f in HEALTH_FEATURES:
                rec[f] = df_year[f].sum()
            # Count Response topics
            resp_counts = count_keywords(df_year["Response"], RESPONSE_TOPICS)
            for t in RESPONSE_TOPICS:
                rec[t] = resp_counts.get(t, 0)
            # Count health keyword categories
            health_counts = count_keywords(df_year["Health keyword categories"], CATEGORY_LABELS.keys())
            for cat, label in CATEGORY_LABELS.items():
                rec[label] = health_counts.get(cat, 0)
            country_records.append(rec)
    df_country = pd.DataFrame(country_records)

    # --- Subregion-level aggregation ---
    df["Subregion"] = df["Country"].map(SUBREGION_MAP).fillna("Other")
    subregion_records = []
    for subregion, group in df.groupby("Subregion"):
        for year in all_years:
            df_year = group[group["Year"] == year]
            rec = {"Subregion": subregion, "Year": year, "Total documents": len(df_year)}
            for f in HEALTH_FEATURES:
                rec[f] = df_year[f].sum()
            resp_counts = count_keywords(df_year["Response"], RESPONSE_TOPICS)
            for t in RESPONSE_TOPICS:
                rec[t] = resp_counts.get(t, 0)
            health_counts = count_keywords(df_year["Health keyword categories"], CATEGORY_LABELS.keys())
            for cat, label in CATEGORY_LABELS.items():
                rec[label] = health_counts.get(cat, 0)
            subregion_records.append(rec)
    df_subregion = pd.DataFrame(subregion_records)

    # --- Save to Excel ---
    with pd.ExcelWriter(output_excel) as writer:
        df_country.to_excel(writer, sheet_name="Country", index=False)
        df_subregion.to_excel(writer, sheet_name="Subregion", index=False)

    print(f"✅ Aggregated counts saved to '{output_excel}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate yearly health-panel counts by country and subregion with readable health category names."
    )
    parser.add_argument("--panel", required=True, help="Expanded panel CSV (Document ID + Year)")
    parser.add_argument("--annotations", required=True, help="Health annotation CSV (Doc ID + Country + Health + Response + Health keyword categories)")
    parser.add_argument("--output", required=True, help="Output Excel file with two sheets: Country & Subregion")

    args = parser.parse_args()
    aggregate_panel_annotations(args.panel, args.annotations, args.output)


if __name__ == "__main__":
    main()