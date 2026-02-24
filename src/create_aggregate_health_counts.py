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

EU_COUNTRIES = [
    "Austria","Belgium","Bulgaria","Croatia","Cyprus","Czechia","Denmark",
    "Estonia","Finland","France","Germany","Greece","Hungary","Ireland",
    "Italy","Latvia","Lithuania","Luxembourg","Malta","Netherlands","Poland",
    "Portugal","Romania","Slovakia","Slovenia","Spain","Sweden"
]

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

RESPONSE_TOPICS = ["Adaptation","Disaster Risk Management","Loss And Damage","Mitigation"]
HEALTH_FEATURES = ["Health relevance (1/0)",
                   "Health adaptation mandate (1/0)",
                   "Institutional health role (1/0)"]

# -------------------------------
# Core aggregation
# -------------------------------
def aggregate_timeline(panel_csv, annotations_csv, output_excel):

    panel = pd.read_csv(panel_csv)
    annotations = pd.read_csv(annotations_csv)

    # Harmonise ID column
    if "Doc ID" in annotations.columns:
        annotations = annotations.rename(columns={"Doc ID": "Document ID"})

    # Ensure numeric fields
    for col in HEALTH_FEATURES:
        annotations[col] = annotations[col].fillna(0).astype(int)

    annotations["Health keyword categories"] = annotations["Health keyword categories"].fillna("")
    annotations["Response"] = annotations["Response"].fillna("")

    # -------------------------------
    # Extract start/end years
    # -------------------------------
    start_events = ["Passed/Approved","Entered Into Force","Set","Net Zero Pledge"]
    end_events = ["Repealed/Replaced","Closed","Settled"]

    panel["start_year"] = None
    panel["end_year"] = None

    for idx, row in panel.iterrows():
        types = str(row.get("Full timeline of events (types)", "")).split(";")
        dates = str(row.get("Full timeline of events (dates)", "")).split(";")

        start_years = [
            int(d[:4]) for t, d in zip(types, dates)
            if t.strip() in start_events and d[:4].isdigit()
        ]

        end_years = [
            int(d[:4]) for t, d in zip(types, dates)
            if t.strip() in end_events and d[:4].isdigit()
        ]

        panel.at[idx, "start_year"] = min(start_years) if start_years else None
        panel.at[idx, "end_year"] = max(end_years) if end_years else None

    panel = panel.dropna(subset=["start_year"])

    # -------------------------------
    # Merge using Document ID AND country
    # -------------------------------
    policy_years = panel.merge(
        annotations,
        left_on=["Document ID", "Geographies"],
        right_on=["Document ID", "Country"],
        how="inner"
    )

    # -------------------------------
    # Create health & response dummies
    # -------------------------------
    for cat in CATEGORY_LABELS.keys():
        policy_years[cat] = policy_years["Health keyword categories"] \
            .str.contains(cat, case=False, regex=False).astype(int)

    for resp in RESPONSE_TOPICS:
        policy_years[resp] = policy_years["Response"] \
            .str.contains(resp, case=False, regex=False).astype(int)

    # -------------------------------
    # Distribute EU-level documents
    # -------------------------------
    '''eu_rows = policy_years[policy_years["Geographies"] == "European Union"]
    non_eu_rows = policy_years[policy_years["Geographies"] != "European Union"]

    distributed = []
    for _, row in eu_rows.iterrows():
        for country in EU_COUNTRIES:
            new_row = row.copy()
            new_row["Country"] = country
            new_row["Geographies"] = country
            distributed.append(new_row)

    policy_years = pd.concat([non_eu_rows] + distributed, ignore_index=True)'''

    # -------------------------------
    # Stock logic (counts active docs)
    # -------------------------------
    min_year = int(policy_years["start_year"].min())
    max_year = int(policy_years["start_year"].max())

    YEARS = list(range(min_year, max_year + 1))

    active_docs = set()
    country_records = []
    subregion_records = []

    for year in YEARS:

        new_docs = set(policy_years[policy_years["start_year"] == year]["Document ID"])
        dropped_docs = set(policy_years[policy_years["end_year"] == year]["Document ID"])

        active_docs = active_docs.union(new_docs).difference(dropped_docs)
        active_df = policy_years[policy_years["Document ID"].isin(active_docs)]

        if year >= 2000:

            # --- Country ---
            for country, grp in active_df.groupby("Country"):

                rec = {"Country": country, "Year": year, "Total documents": len(grp)}

                health_grp = grp[grp["Health relevance (1/0)"] == 1]

                for f in HEALTH_FEATURES:
                    rec[f] = health_grp[f].sum()

                for t in RESPONSE_TOPICS:
                    rec[t] = health_grp[t].sum()

                for cat, label in CATEGORY_LABELS.items():
                    rec[label] = health_grp[cat].sum()

                country_records.append(rec)

            # --- Subregion ---
            active_df = active_df.copy()
            active_df["Subregion"] = active_df["Country"].map(SUBREGION_MAP)

            for subr, grp in active_df.groupby("Subregion"):

                rec = {"Subregion": subr, "Year": year, "Total documents": len(grp)}

                health_grp = grp[grp["Health relevance (1/0)"] == 1]

                for f in HEALTH_FEATURES:
                    rec[f] = health_grp[f].sum()

                for t in RESPONSE_TOPICS:
                    rec[t] = health_grp[t].sum()

                for cat, label in CATEGORY_LABELS.items():
                    rec[label] = health_grp[cat].sum()

                subregion_records.append(rec)

    df_country = pd.DataFrame(country_records)
    df_subregion = pd.DataFrame(subregion_records)

    # -------------------------------
    # Save
    # -------------------------------
    with pd.ExcelWriter(output_excel) as writer:
        df_country.to_excel(writer, sheet_name="Country", index=False)
        df_subregion.to_excel(writer, sheet_name="Subregion", index=False)

    print(f"✅ Aggregated counts saved to '{output_excel}'.")


# -------------------------------
# CLI
# -------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    aggregate_timeline(args.panel, args.annotations, args.output)


if __name__ == "__main__":
    main()