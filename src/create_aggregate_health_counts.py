#!/usr/bin/env python3

import pandas as pd
import argparse

PLOT_END_YEAR = 2025

HEALTH_CATEGORIES = [
    "general_health",
    "mortality_morbidity",
    "injury_trauma",
    "communicable_disease",
    "non_communicable_disease",
    "maternal_child_health",
    "nutrition",
    "mental_health",
    "substance_use",
    "environmental_health",
    "climate_environment",
    "vector_borne_zoonotic",
    "food_waterborne",
    "pathogens_microbiology"
]

CATEGORY_LABELS = {
    "general_health": "General Health & Services",
    "mortality_morbidity": "Mortality & Morbidity",
    "injury_trauma": "Injury & Trauma",
    "communicable_disease": "Communicable Diseases",
    "non_communicable_disease": "Non-Communicable Diseases",
    "maternal_child_health": "Maternal & Child Health",
    "nutrition": "Nutrition",
    "mental_health": "Mental Health",
    "substance_use": "Substance Use",
    "environmental_health": "Environmental Health",
    "climate_environment": "Climate & Environment",
    "vector_borne_zoonotic": "Vector-borne & Zoonotic Diseases",
    "food_waterborne": "Food & Waterborne Illnesses",
    "pathogens_microbiology": "Pathogens & Microbiology"
}

RESPONSE_TOPICS = [
    "Adaptation",
    "Disaster Risk Management",
    "Loss And Damage",
    "Mitigation"
]

EU_LABELS = ["European Union", "EU"]


# ---------------------------------------------------
# GROUPING FILE
# ---------------------------------------------------
def load_groupings(group_file):
    raw = pd.read_excel(group_file, header=1)
    raw.columns = [str(c).strip() for c in raw.columns]

    keep = [
        "Country name",
        "Eurostat code",
        "EU",
        "EEA (main results in the report 2027)",
        "WHO",
        "EEA sub-region division",
        "European sub-region (UN geoscheme)"
    ]

    raw = raw[keep].copy()

    raw = raw.rename(columns={
        "Country name": "Country",
        "Eurostat code": "ISO2",
        "EU": "EU_status",
        "EEA (main results in the report 2027)": "EEA_status",
        "WHO": "WHO_status",
        "EEA sub-region division": "EEA_subregion",
        "European sub-region (UN geoscheme)": "UN_subregion"
    })

    raw["Country"] = raw["Country"].astype(str).str.strip()
    return raw


# ---------------------------------------------------
# POLICY LIFECYCLE
# ---------------------------------------------------
def build_policy_years(legis_df):

    df = legis_df.copy()

    df["event_types"] = df["Full timeline of events (types)"].fillna("").astype(str).str.split(";")
    df["event_dates"] = df["Full timeline of events (dates)"].fillna("").astype(str).str.split(";")

    df = df.explode(["event_types", "event_dates"])

    df["event_types"] = df["event_types"].astype(str).str.strip()
    df["event_dates"] = df["event_dates"].astype(str).str.strip()

    df["Year"] = df["event_dates"].str[:4]
    df = df[df["Year"].str.match(r"^\d{4}$", na=False)]
    df["Year"] = df["Year"].astype(int)
    df = df[df["Year"] <= PLOT_END_YEAR]

    start_events = ["Passed/Approved", "Entered Into Force", "Set", "Net Zero Pledge"]
    end_events = ["Repealed/Replaced", "Closed", "Settled"]

    start_years = df[df["event_types"].isin(start_events)].groupby("Family ID")["Year"].min()
    end_years = df[df["event_types"].isin(end_events)].groupby("Family ID")["Year"].max()

    py = pd.concat([start_years, end_years], axis=1)
    py.columns = ["start_year", "end_year"]
    py = py.dropna(subset=["start_year"])

    py["end_year"] = py["end_year"].apply(
        lambda x: min(x, PLOT_END_YEAR) if pd.notnull(x) else x
    )

    return py.reset_index()


# ---------------------------------------------------
# ACTIVE STOCK ENGINE
# ---------------------------------------------------
def simulate_active(df_meta, policy_years, start_year=2000, group_name=None, group_value=None, iso2=None, iso3=None):

    years = list(range(start_year, PLOT_END_YEAR + 1))

    active_set = set()
    total_active_set = set()

    out = []

    for year in years:

        new_docs = set(policy_years[policy_years["start_year"] == year]["Family ID"])
        dropped_docs = set(policy_years[policy_years["end_year"] == year]["Family ID"])

        active_set |= new_docs
        active_set -= dropped_docs

        total_active_set |= new_docs
        total_active_set -= dropped_docs

        active_df = df_meta[df_meta["Family ID"].isin(active_set)].drop_duplicates("Family ID")
        health_df = active_df[active_df["Health relevance (1/0)"] == 1]

        rec = {"Year": year}

        if group_name:
            rec[group_name] = group_value
        if iso2 is not None:
            rec["ISO2"] = iso2
        if iso3 is not None:
            rec["ISO3"] = iso3

        rec["Total documents"] = len(total_active_set)
        rec["Health-relevant documents"] = health_df["Family ID"].nunique()
        rec["Institutional health roles"] = active_df[
            active_df["Institutional health role (1/0)"] == 1
        ]["Family ID"].nunique()

        for cat in HEALTH_CATEGORIES:
            rec[cat] = health_df[cat].sum()

        for topic in RESPONSE_TOPICS:
            rec[topic] = health_df["Response"].str.contains(topic, case=False, na=False).sum()

        out.append(rec)

    return pd.DataFrame(out)


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def run(cclw_csv, annotations_csv, group_file, output_excel):

    legis = pd.read_csv(cclw_csv)
    ann = pd.read_csv(annotations_csv)

    # ----------------------
    # CLEAN ANNOTATIONS
    # ----------------------
    ann["Health keyword categories"] = ann["Health keyword categories"].fillna("")
    ann["Response"] = ann["Response"].fillna("")
    ann["Health relevance (1/0)"] = ann["Health relevance (1/0)"].fillna(0).astype(int)
    ann["Institutional health role (1/0)"] = ann["Institutional health role (1/0)"].fillna(0).astype(int)

    for cat in HEALTH_CATEGORIES:
        ann[cat] = ann["Health keyword categories"].str.contains(cat, case=False, regex=False).astype(int)

    # ----------------------
    # MERGE LEGIS + ANNOT
    # ----------------------
    df = legis.merge(ann, on="Family ID", how="inner")

    # FORCE CANONICAL COUNTRY + ISO3 FROM LEGIS
    df["Country"] = df["Geographies"].astype(str).str.strip()
    df["ISO3"] = df["Geography ISOs"].astype(str).str.strip()

    # GROUPINGS
    groups = load_groupings(group_file)
    df = df.merge(groups, on="Country", how="left")

    # lifecycle
    policy_years = build_policy_years(legis)

    # EU separate
    df_eu = df[df["Country"].isin(EU_LABELS)]
    df_non_eu = df[~df["Country"].isin(EU_LABELS)]

    # Europe EEA+UK
    europe_uk = df_non_eu[
        df_non_eu["EEA_status"].astype(str).str.contains("Member|Cooperating", case=False, na=False)
    ]

    # Europe EEA no UK
    europe_no_uk = europe_uk[europe_uk["Country"] != "United Kingdom"]

    # policy subsets
    pol_europe_uk = policy_years[policy_years["Family ID"].isin(europe_uk["Family ID"])]
    pol_europe_no_uk = policy_years[policy_years["Family ID"].isin(europe_no_uk["Family ID"])]
    pol_eu = policy_years[policy_years["Family ID"].isin(df_eu["Family ID"])]

    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:

        # ---------------------------------------------------
        # 1 Europe (EEA+ UK)
        # ---------------------------------------------------
        out1 = simulate_active(europe_uk, pol_europe_uk)
        out1.rename(columns=CATEGORY_LABELS).to_excel(writer, sheet_name="Europe (EEA+ UK)", index=False)

        # ---------------------------------------------------
        # 2 Europe EEA(no UK)
        # ---------------------------------------------------
        out2 = simulate_active(europe_no_uk, pol_europe_no_uk)
        out2.rename(columns=CATEGORY_LABELS).to_excel(writer, sheet_name="Europe EEA(no UK)", index=False)

        # ---------------------------------------------------
        # 3 EEA38 subregion
        # ---------------------------------------------------
                # ---------------------------------------------------
        # 3 EEA38 subregion (SIDE BY SIDE)
        # ---------------------------------------------------
        sub_tables = []

        for sub in sorted(europe_uk["EEA_subregion"].dropna().unique()):
            subdf = europe_uk[europe_uk["EEA_subregion"] == sub]
            pol = policy_years[policy_years["Family ID"].isin(subdf["Family ID"])]
            tmp = simulate_active(subdf, pol, group_name="EEA_subregion", group_value=sub)
            sub_tables.append(tmp)

        block1 = pd.concat(sub_tables).rename(columns=CATEGORY_LABELS)

        sub_tables2 = []
        for sub in sorted(europe_no_uk["EEA_subregion"].dropna().unique()):
            subdf = europe_no_uk[europe_no_uk["EEA_subregion"] == sub]
            pol = policy_years[policy_years["Family ID"].isin(subdf["Family ID"])]
            tmp = simulate_active(subdf, pol, group_name="EEA_subregion", group_value=sub)
            sub_tables2.append(tmp)

        block2 = pd.concat(sub_tables2).rename(columns=CATEGORY_LABELS)

        block1.to_excel(writer, sheet_name="EEA38 subregion", index=False, startrow=1, startcol=0)
        block2.to_excel(writer, sheet_name="EEA38 subregion", index=False, startrow=1, startcol=len(block1.columns)+4)

        ws = writer.sheets["EEA38 subregion"]
        ws.cell(row=1, column=1).value = "EEA + UK (Included in northern subregion division)"
        ws.cell(row=1, column=len(block1.columns)+5).value = "EEA subregion (without UK)"

        # ---------------------------------------------------
        # 4 Country
        # ---------------------------------------------------
        country_tables = []

        for country in sorted(df_non_eu["Country"].dropna().unique()):

            cdf = df_non_eu[df_non_eu["Country"] == country]
            pol = policy_years[policy_years["Family ID"].isin(cdf["Family ID"])]

            iso2 = cdf["ISO2"].dropna().iloc[0] if cdf["ISO2"].notna().any() else None
            iso3 = cdf["ISO3"].dropna().iloc[0] if cdf["ISO3"].notna().any() else None

            tmp = simulate_active(cdf, pol, group_name="Country", group_value=country, iso2=iso2, iso3=iso3)
            country_tables.append(tmp)

        pd.concat(country_tables).rename(columns=CATEGORY_LABELS).to_excel(writer, sheet_name="Country", index=False)

        # ---------------------------------------------------
        # 5 EU
        # ---------------------------------------------------
        out5 = simulate_active(df_eu, pol_eu)
        out5.rename(columns=CATEGORY_LABELS).to_excel(writer, sheet_name="EU", index=False)

    print(f"DONE: {output_excel}")


# ---------------------------------------------------
# CLI
# ---------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cclw", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--group-file", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    run(args.cclw, args.annotations, args.group_file, args.output)


if __name__ == "__main__":
    main()