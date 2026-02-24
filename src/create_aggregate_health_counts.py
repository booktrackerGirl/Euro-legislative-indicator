#!/usr/bin/env python3

import pandas as pd
import argparse

# -------------------------------
# Country → Subregion mapping
# -------------------------------
SUBREGION_MAP = {
    "Albania": "Southern","Austria": "Western","Belgium": "Western","Bosnia and Herzegovina": "Southern",
    "Bulgaria": "Eastern","Croatia": "Southern","Cyprus": "Southern","Czechia": "Eastern",
    "Denmark": "Northern","Estonia": "Northern","Finland": "Northern","France": "Western",
    "Germany": "Western","Greece": "Southern","Hungary": "Eastern","Iceland": "Northern",
    "Ireland": "Northern","Italy": "Southern","Kosovo": "Southern","Latvia": "Northern",
    "Liechtenstein": "Western","Lithuania": "Northern","Luxembourg": "Western","Malta": "Southern",
    "Montenegro": "Southern","Netherlands": "Western","North Macedonia": "Southern","Norway": "Northern",
    "Poland": "Eastern","Portugal": "Southern","Romania": "Eastern","Serbia": "Southern",
    "Slovakia": "Eastern","Slovenia": "Southern","Spain": "Southern","Sweden": "Northern",
    "Switzerland": "Western","Türkiye": "Southern","United Kingdom": "UK"
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
HEALTH_FEATURES = ["Health relevance (1/0)","Health adaptation mandate (1/0)","Institutional health role (1/0)"]

# -------------------------------
# Core aggregation function
# -------------------------------
def aggregate_timeline(panel_csv, annotations_csv, output_excel):
    panel = pd.read_csv(panel_csv)
    annotations = pd.read_csv(annotations_csv)

    # Harmonize IDs
    if "Doc ID" in annotations.columns:
        annotations = annotations.rename(columns={"Doc ID": "Document ID"})

    # Merge annotations
    df = panel.merge(
        annotations[["Document ID","Country"] + HEALTH_FEATURES + ["Response","Health keyword categories"]],
        on="Document ID",
        how="left"
    )

    # Fill missing numeric columns
    for col in HEALTH_FEATURES:
        df[col] = df[col].fillna(0).astype(int)
    df["Country"] = df["Country"].fillna("Unknown")
    df["Health keyword categories"] = df["Health keyword categories"].fillna("")
    df["Response"] = df["Response"].fillna("")

    # -------------------------------
    # Timeline-based start/end logic
    # -------------------------------
    start_events = ["Passed/Approved","Entered Into Force","Set","Net Zero Pledge"]
    end_events = ["Repealed/Replaced","Closed","Settled"]

    df_long = panel.copy()
    df_long["start_year"] = None
    df_long["end_year"] = None

    for idx, row in df_long.iterrows():
        types = str(row.get("Full timeline of events (types)","")).split(";")
        dates = str(row.get("Full timeline of events (dates)","")).split(";")
        start_years = [int(d[:4]) for t,d in zip(types,dates) if t.strip() in start_events and d[:4].isdigit()]
        end_years = [int(d[:4]) for t,d in zip(types,dates) if t.strip() in end_events and d[:4].isdigit()]
        df_long.at[idx,"start_year"] = min(start_years) if start_years else None
        df_long.at[idx,"end_year"] = max(end_years) if end_years else None

    # Keep only documents with a start year
    df_long = df_long.dropna(subset=["start_year"])

    # Merge with annotations
    policy_years = df_long[["Document ID","start_year","end_year"]].merge(
        annotations[["Document ID","Country"] + HEALTH_FEATURES + ["Response","Health keyword categories"]],
        on="Document ID", how="left"
    )

    # -------------------------------
    # Create dummy columns
    # -------------------------------
    for cat in CATEGORY_LABELS.keys():
        policy_years[cat] = policy_years["Health keyword categories"].str.contains(cat, case=False, regex=False).astype(int)
    for resp in RESPONSE_TOPICS:
        policy_years[resp] = policy_years["Response"].str.contains(resp, case=False, regex=False).astype(int)

    # -------------------------------
    # Stock aggregation
    # -------------------------------
    all_years = sorted(list(set(policy_years["start_year"].dropna().astype(int).tolist() +
                                policy_years["end_year"].dropna().astype(int).tolist())))
    min_year = min(all_years)
    max_year = max(all_years)
    YEARS = list(range(min_year, max_year + 1))

    active_docs = set()
    country_records = []
    subregion_records = []

    for year in YEARS:
        # Identify new / dropped
        new_docs = set(policy_years[policy_years["start_year"] == year]["Document ID"])
        dropped_docs = set(policy_years[policy_years["end_year"] == year]["Document ID"])
        active_docs = active_docs.union(new_docs).difference(dropped_docs)

        active_df = policy_years[policy_years["Document ID"].isin(active_docs)]
        health_df = active_df[active_df["Health relevance (1/0)"] == 1]

        if year >= 2000:  # Only report from 2000
            # --- Country-level ---
            for country, grp in active_df.groupby("Country"):
                rec = {"Country": country, "Year": year, "Total documents": len(grp)}
                health_grp = grp[grp["Health relevance (1/0)"] == 1]
                for f in HEALTH_FEATURES:
                    rec[f] = health_grp[f].sum()
                for t in RESPONSE_TOPICS:
                    rec[t] = health_grp[t].sum()
                for cat,label in CATEGORY_LABELS.items():
                    rec[label] = health_grp[cat].sum()
                country_records.append(rec)

            # --- Subregion-level ---
            active_df["Subregion"] = active_df["Country"].map(SUBREGION_MAP).fillna("Other")
            for subr, grp in active_df.groupby("Subregion"):
                rec = {"Subregion": subr, "Year": year, "Total documents": len(grp)}
                health_grp = grp[grp["Health relevance (1/0)"] == 1]
                for f in HEALTH_FEATURES:
                    rec[f] = health_grp[f].sum()
                for t in RESPONSE_TOPICS:
                    rec[t] = health_grp[t].sum()
                for cat,label in CATEGORY_LABELS.items():
                    rec[label] = health_grp[cat].sum()
                subregion_records.append(rec)

    df_country = pd.DataFrame(country_records)
    df_subregion = pd.DataFrame(subregion_records)

    # -------------------------------
    # Save to Excel
    # -------------------------------
    with pd.ExcelWriter(output_excel) as writer:
        df_country.to_excel(writer, sheet_name="Country", index=False)
        df_subregion.to_excel(writer, sheet_name="Subregion", index=False)

    print(f"✅ Aggregated counts saved to '{output_excel}'.")


# -------------------------------
# CLI
# -------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Timeline-based aggregation of health panel counts by country & subregion"
    )
    parser.add_argument("--legis", required=True, help="Legislative CSV with timeline columns")
    parser.add_argument("--annotations", required=True, help="Health annotations CSV")
    parser.add_argument("--output", required=True, help="Output Excel file")
    args = parser.parse_args()

    aggregate_timeline(args.panel, args.annotations, args.output)


if __name__ == "__main__":
    main()