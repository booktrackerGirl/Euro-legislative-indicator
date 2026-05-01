#!/usr/bin/env python3
"""
Build health_counts Excel from CCLW legislative CSV + health annotations CSV
+ country groupings file.

Population definitions
----------------------
Europe (EEA+ UK) : EEA Members (32) + Former Member (UK) + Cooperating (6)
                   = 39 countries. EU tracked separately.
Europe EEA(no UK): same minus United Kingdom.
EEA38 subregion  : Left block  = EEA+UK split by EEA_subregion
                                 (UK lands in "Not EEA" subregion)
                   Right block = EEA without UK split by EEA_subregion
                                 (Cooperating countries already folded into
                                  their correct geographic subregion per the
                                  2027 groupings file, e.g. Albania → Southern)
EU               : "European Union" / "EU" entries from CCLW only.

Active stock simulation
-----------------------
Uses CCLW event timelines to identify:
  start_events : Passed/Approved | Entered Into Force | Set | Net Zero Pledge
  end_events   : Repealed/Replaced | Closed | Settled
A family is "active" in year Y if it has a start event <= Y and no end event <= Y.

Usage
-----
python build_health_counts_cclw.py \\
    --cclw       cclw_europe_legislative.csv \\
    --annotations health_annotations_by_family.csv \\
    --group-file  2027_Country_names_and_groupings_HK_08042026.xlsx \\
    --output      health_counts.xlsx
"""

import argparse
import pandas as pd

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
    "pathogens_microbiology",
]

CATEGORY_LABELS = {
    "general_health":           "General Health & Services",
    "mortality_morbidity":      "Mortality & Morbidity",
    "injury_trauma":            "Injury & Trauma",
    "communicable_disease":     "Communicable Diseases",
    "non_communicable_disease": "Non-Communicable Diseases",
    "maternal_child_health":    "Maternal & Child Health",
    "nutrition":                "Nutrition",
    "mental_health":            "Mental Health",
    "substance_use":            "Substance Use",
    "environmental_health":     "Environmental Health",
    "climate_environment":      "Climate & Environment",
    "vector_borne_zoonotic":    "Vector-borne & Zoonotic Diseases",
    "food_waterborne":          "Food & Waterborne Illnesses",
    "pathogens_microbiology":   "Pathogens & Microbiology",
}

RESPONSE_TOPICS = [
    "Adaptation",
    "Disaster Risk Management",
    "Loss And Damage",
    "Mitigation",
]

EU_LABELS = ["European Union", "EU"]


# ── loaders ───────────────────────────────────────────────────────────────────

def load_groupings(group_file: str) -> pd.DataFrame:
    raw = pd.read_excel(group_file, header=1)
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw.rename(columns={
        "Country name":                          "Country",
        "Eurostat code":                         "ISO2",
        "EU":                                    "EU_status",
        "EEA (main results in the report 2027)": "EEA_status",
        "WHO":                                   "WHO_status",
        "EEA sub-region division":               "EEA_subregion",
        "European sub-region (UN geoscheme)":    "UN_subregion",
    })
    raw["Country"] = raw["Country"].astype(str).str.strip()
    return raw


# ── policy lifecycle ──────────────────────────────────────────────────────────

def build_policy_years(legis_df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the CCLW event timeline columns to derive (Family ID, start_year,
    end_year) for every legislative family.
    """
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
    end_events   = ["Repealed/Replaced", "Closed", "Settled"]

    start_years = df[df["event_types"].isin(start_events)].groupby("Family ID")["Year"].min()
    end_years   = df[df["event_types"].isin(end_events)].groupby("Family ID")["Year"].max()

    py = pd.concat([start_years, end_years], axis=1)
    py.columns = ["start_year", "end_year"]
    py = py.dropna(subset=["start_year"])
    py["end_year"] = py["end_year"].apply(
        lambda x: min(x, PLOT_END_YEAR) if pd.notnull(x) else x
    )
    return py.reset_index()


# ── active stock engine ───────────────────────────────────────────────────────

def simulate_active(
    df_meta: pd.DataFrame,
    policy_years: pd.DataFrame,
    start_year: int = 2000,
    group_name: str = None,
    group_value: str = None,
    iso2: str = None,
    iso3: str = None,
) -> pd.DataFrame:
    """
    For each year in [start_year, PLOT_END_YEAR], maintain the set of active
    Family IDs (started but not yet repealed/closed) and count health-relevant
    documents and category mentions within that active set.
    """
    years = list(range(start_year, PLOT_END_YEAR + 1))

    # Seed the active set with families that started BEFORE the plot window
    # and have not yet been repealed by start_year. Without this, pre-2000
    # legislation that is still active in 2000+ is silently excluded.
    pre_start  = policy_years[policy_years["start_year"] < start_year]
    pre_active = pre_start[
        pre_start["end_year"].isna() | (pre_start["end_year"] >= start_year)
    ]["Family ID"]
    active_set       = set(pre_active)
    total_active_set = set(pre_active)
    out = []

    for year in years:
        new_docs     = set(policy_years[policy_years["start_year"] == year]["Family ID"])
        dropped_docs = set(policy_years[policy_years["end_year"]   == year]["Family ID"])

        active_set       |= new_docs
        active_set       -= dropped_docs
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

        rec["Total documents"]            = len(total_active_set)
        rec["Health-relevant documents"]  = health_df["Family ID"].nunique()
        rec["Institutional health roles"] = active_df[
            active_df["Institutional health role (1/0)"] == 1
        ]["Family ID"].nunique()

        for cat in HEALTH_CATEGORIES:
            rec[cat] = int(health_df[cat].sum())

        for topic in RESPONSE_TOPICS:
            rec[topic] = int(
                health_df["Response"].str.contains(topic, case=False, na=False).sum()
            )

        out.append(rec)

    return pd.DataFrame(out)


# ── main ──────────────────────────────────────────────────────────────────────

def run(cclw_csv: str, annotations_csv: str, group_file: str, output_excel: str):

    # ── load inputs ───────────────────────────────────────────────────────────
    print("Loading CCLW legislative data...")
    legis = pd.read_csv(cclw_csv)

    print("Loading health annotations...")
    ann = pd.read_csv(annotations_csv)
    ann["Health keyword categories"]       = ann["Health keyword categories"].fillna("")
    ann["Response"]                        = ann["Response"].fillna("")
    ann["Health relevance (1/0)"]          = ann["Health relevance (1/0)"].fillna(0).astype(int)
    ann["Institutional health role (1/0)"] = ann["Institutional health role (1/0)"].fillna(0).astype(int)

    for cat in HEALTH_CATEGORIES:
        ann[cat] = ann["Health keyword categories"].str.contains(
            cat, case=False, regex=False
        ).astype(int)

    # ── merge CCLW + annotations on Family ID ─────────────────────────────────
    # Use canonical Country and ISO3 from CCLW (Geographies / Geography ISOs)
    df = legis.merge(ann, on="Family ID", how="inner")
    df["Country"] = df["Geographies"].astype(str).str.strip()
    df["ISO3"]    = df["Geography ISOs"].astype(str).str.strip()

    # ── attach grouping metadata ───────────────────────────────────────────────
    print("Loading country groupings...")
    groups = load_groupings(group_file)
    df = df.merge(groups, on="Country", how="left")

    # ── build policy lifecycle from CCLW timelines (all families) ─────────────
    print("Building policy lifecycle from CCLW event timelines...")
    policy_years = build_policy_years(legis)

    # ── define population subsets ─────────────────────────────────────────────
    #
    # EU: families explicitly labelled as European Union / EU in CCLW
    df_eu     = df[df["Country"].isin(EU_LABELS)].copy()
    df_non_eu = df[~df["Country"].isin(EU_LABELS)].copy()

    # EEA + UK:
    #   - EEA Members (32 countries, EEA_status == "Member")
    #   - Former Member = United Kingdom (EEA_status == "Former Member";
    #     "Former Member" contains "Member" so the regex catches it)
    #   - Cooperating countries = Albania, Bosnia and Herzegovina, Kosovo,
    #     Montenegro, North Macedonia, Serbia (EEA_status == "Cooperating")
    #     These 6 countries have EEA_subregion = "Southern" in the groupings
    #     file, so they are correctly folded into the Southern subregion group.
    europe_uk = df_non_eu[
        df_non_eu["EEA_status"].astype(str).str.contains(
            "Member|Cooperating", case=False, na=False
        )
    ].copy()

    # EEA without UK (UK: EEA_status == "Former Member")
    europe_no_uk = europe_uk[europe_uk["Country"] != "United Kingdom"].copy()

    # Policy-year subsets scoped to each population
    pol_europe_uk    = policy_years[policy_years["Family ID"].isin(europe_uk["Family ID"])]
    pol_europe_no_uk = policy_years[policy_years["Family ID"].isin(europe_no_uk["Family ID"])]
    pol_eu           = policy_years[policy_years["Family ID"].isin(df_eu["Family ID"])]

    print(f"  EEA+UK families:    {europe_uk['Family ID'].nunique()}")
    print(f"  EEA (no UK):        {europe_no_uk['Family ID'].nunique()}")
    print(f"  EU families:        {df_eu['Family ID'].nunique()}")
    print(f"  Countries in EEA+UK: {sorted(europe_uk['Country'].unique())}")

    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:

        # ── Sheet 1: Europe (EEA+ UK) ─────────────────────────────────────────
        print("\nBuilding sheet: Europe (EEA+ UK)...")
        out1 = simulate_active(europe_uk, pol_europe_uk)
        out1.rename(columns=CATEGORY_LABELS).to_excel(
            writer, sheet_name="Europe (EEA+ UK)", index=False
        )

        # ── Sheet 2: Europe EEA(no UK) ────────────────────────────────────────
        print("Building sheet: Europe EEA(no UK)...")
        out2 = simulate_active(europe_no_uk, pol_europe_no_uk)
        out2.rename(columns=CATEGORY_LABELS).to_excel(
            writer, sheet_name="Europe EEA(no UK)", index=False
        )

        # ── Sheet 3: EEA38 subregion (two side-by-side blocks) ───────────────
        #
        # LEFT block  = EEA+UK split by EEA_subregion
        #               Subregions: Eastern, Northern, Southern, Western, Not EEA
        #               "Not EEA" subregion = UK (Former Member) only.
        #               Cooperating countries appear under their geographic
        #               subregion (Southern) NOT as a separate group.
        #
        # RIGHT block = EEA without UK split by EEA_subregion
        #               Subregions: Eastern, Northern, Southern, Western
        #               No "Not EEA" row since UK is excluded.
        #               Cooperating countries remain in Southern.
        print("Building sheet: EEA38 subregion...")

        sub_tables_uk = []
        for sub in sorted(europe_uk["EEA_subregion"].dropna().unique()):
            subdf = europe_uk[europe_uk["EEA_subregion"] == sub]
            pol   = policy_years[policy_years["Family ID"].isin(subdf["Family ID"])]
            tmp   = simulate_active(subdf, pol, group_name="EEA_subregion", group_value=sub)
            sub_tables_uk.append(tmp)
        block1 = pd.concat(sub_tables_uk, ignore_index=True).rename(columns=CATEGORY_LABELS)

        sub_tables_no_uk = []
        for sub in sorted(europe_no_uk["EEA_subregion"].dropna().unique()):
            subdf = europe_no_uk[europe_no_uk["EEA_subregion"] == sub]
            pol   = policy_years[policy_years["Family ID"].isin(subdf["Family ID"])]
            tmp   = simulate_active(subdf, pol, group_name="EEA_subregion", group_value=sub)
            sub_tables_no_uk.append(tmp)
        block2 = pd.concat(sub_tables_no_uk, ignore_index=True).rename(columns=CATEGORY_LABELS)

        block1.to_excel(writer, sheet_name="EEA38 subregion",
                        index=False, startrow=1, startcol=0)
        block2.to_excel(writer, sheet_name="EEA38 subregion",
                        index=False, startrow=1, startcol=len(block1.columns) + 4)

        ws = writer.sheets["EEA38 subregion"]
        ws.cell(row=1, column=1).value = "EEA + UK (Included in northern subregion division)"
        ws.cell(row=1, column=len(block1.columns) + 5).value = "EEA subregion (without UK)"

        # ── Sheet 4: Country ──────────────────────────────────────────────────
        print("Building sheet: Country...")
        country_tables = []
        for country in sorted(df_non_eu["Country"].dropna().unique()):
            cdf  = df_non_eu[df_non_eu["Country"] == country]
            pol  = policy_years[policy_years["Family ID"].isin(cdf["Family ID"])]
            iso2 = cdf["ISO2"].dropna().iloc[0] if cdf["ISO2"].notna().any() else None
            iso3 = cdf["ISO3"].dropna().iloc[0] if cdf["ISO3"].notna().any() else None
            tmp  = simulate_active(cdf, pol,
                                   group_name="Country", group_value=country,
                                   iso2=iso2, iso3=iso3)
            country_tables.append(tmp)
        pd.concat(country_tables, ignore_index=True).rename(columns=CATEGORY_LABELS).to_excel(
            writer, sheet_name="Country", index=False
        )

        # ── Sheet 5: EU ───────────────────────────────────────────────────────
        print("Building sheet: EU...")
        out5 = simulate_active(df_eu, pol_eu)
        out5.rename(columns=CATEGORY_LABELS).to_excel(
            writer, sheet_name="EU", index=False
        )

    print(f"\nDONE → {output_excel}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cclw",        required=True, help="CCLW legislative CSV")
    parser.add_argument("--annotations", required=True, help="health_annotations_by_family.csv")
    parser.add_argument("--group-file",  required=True, help="Country groupings Excel file")
    parser.add_argument("--output",      required=True, help="Output Excel path (.xlsx)")
    args = parser.parse_args()

    run(args.cclw, args.annotations, args.group_file, args.output)


if __name__ == "__main__":
    main()