#!/usr/bin/env python3

import pandas as pd
import argparse
import sys


def create_yearly_panel(input_path, output_path):

    print("Reading data...")
    data = pd.read_csv(input_path)
    data = data[~data['Document Content URL'].isna()]

    # Select needed columns
    data_copy = data[[
        'Document ID',
        'Full timeline of events (types)',
        'Full timeline of events (dates)'
    ]].copy()

    print("Splitting event types and dates...")
    data_copy["event_types"] = data_copy["Full timeline of events (types)"].str.split(";")
    data_copy["event_dates"] = data_copy["Full timeline of events (dates)"].str.split(";")

    df_long = data_copy.explode(["event_types", "event_dates"])

    # Clean dates
    df_long["event_dates"] = df_long["event_dates"].astype(str).str.strip()

    # Extract 4-digit year safely
    df_long["year"] = df_long["event_dates"].str[:4]
    df_long = df_long[df_long["year"].str.match(r"^\d{4}$", na=False)]
    df_long["year"] = df_long["year"].astype(int)

    # Define start/end events
    start_events = [
        "Passed/Approved",
        "Entered Into Force",
        "Set",
        "Net Zero Pledge"
    ]

    end_events = [
        "Repealed/Replaced",
        "Closed",
        "Settled"
    ]

    print("Calculating start and end years (prefer Passed/Approved)...")

    # Filter start events only
    df_starts = df_long[df_long["event_types"].isin(start_events)].copy()

    # Earliest Passed/Approved per Document
    passed_years = (
        df_starts[df_starts["event_types"] == "Passed/Approved"]
        .groupby("Document ID")["year"]
        .min()
    )

    # Earliest among OTHER start events
    other_years = (
        df_starts[df_starts["event_types"] != "Passed/Approved"]
        .groupby("Document ID")["year"]
        .min()
    )

    # Combine with priority rule
    start_years = other_years.copy()

    # Overwrite with Passed/Approved wherever it exists
    start_years.update(passed_years)

    # Also include documents that ONLY have Passed/Approved
    start_years = start_years.combine_first(passed_years)


    end_years = (
        df_long[df_long["event_types"].isin(end_events)]
        .groupby("Document ID")["year"]
        .max()
    )

    policy_years = pd.concat([start_years, end_years], axis=1)
    policy_years.columns = ["start_year", "end_year"]

    # Manual fixes
    manual_starts = {
        "national-energy-and-climate-plan-2019-draft_6002": 2019,
        "order-22-february-2024-amending-order-no-4264-establishing-the-organising-committee-for-cop29_fbe6": 2024,
    }

    for doc_id, start_year in manual_starts.items():
        if doc_id in policy_years.index:
            policy_years.loc[doc_id, "start_year"] = start_year

    # Fix truncated years
    def fix_year(y):
        if pd.isna(y):
            return y
        y = int(y)
        if y < 100:
            return 2000 + y
        return y

    policy_years["start_year"] = policy_years["start_year"].apply(fix_year)
    policy_years["end_year"] = policy_years["end_year"].apply(fix_year)

    # Drop rows without start_year
    policy_years = policy_years[policy_years["start_year"].notna()]

    policy_years["start_year"] = policy_years["start_year"].astype(int)

    min_year = df_long["year"].min()
    max_year = df_long["year"].max()

    print(f"Expanding policies into yearly panel ({min_year}–{max_year})...")

    rows = []

    for doc_id, row in policy_years.iterrows():
        start = row["start_year"]
        end = row["end_year"] if pd.notna(row["end_year"]) else max_year

        for year in range(int(start), int(end) + 1):
            rows.append({
                "Document ID": doc_id,
                "Year": year
            })

    df_panel = pd.DataFrame(rows)

    print(f"Saving output to {output_path}...")
    df_panel.to_csv(output_path, index=False)

    print("Done.")
    print(f"Total rows created: {len(df_panel):,}")


def main():
    parser = argparse.ArgumentParser(
        description="Create expanded yearly policy panel from legislative dataset."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to input CSV (legis_df.csv)"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path to output CSV (expanded panel)"
    )

    args = parser.parse_args()

    create_yearly_panel(args.input, args.output)


if __name__ == "__main__":
    main()
