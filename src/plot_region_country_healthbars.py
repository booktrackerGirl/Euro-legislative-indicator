#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------
# COUNTRY HARMONIZATION
# ---------------------------------------------------
COUNTRY_NAME_FIX = {
    "UK": "United Kingdom",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "Turkey": "Türkiye",
    "Czech Republic": "Czechia",
    "North Macedonia (former Yugoslav Republic of Macedonia)": "North Macedonia",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Republic of Moldova": "Moldova",
    "Kosovo*": "Kosovo"
}


# ---------------------------------------------------
# LOAD COUNTRY PANEL
# ---------------------------------------------------
def load_country_panel(excel_path):

    df = pd.read_excel(excel_path, sheet_name="Country")
    df.columns = [str(c).strip() for c in df.columns]

    df = df[df["Year"].notna()]
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df[df["Year"].notna()]

    df["Country"] = df["Country"].astype(str).str.strip()
    df["Country"] = df["Country"].replace(COUNTRY_NAME_FIX)

    return df


# ---------------------------------------------------
# ROBUST GROUPINGS
# ---------------------------------------------------
def load_groupings(group_file):

    raw = pd.read_excel(group_file, header=None)

    header_row = None
    for i in range(len(raw)):
        vals = raw.iloc[i].astype(str).str.strip().tolist()
        if "Country name" in vals:
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not locate grouping workbook header row.")

    g = pd.read_excel(group_file, header=header_row)
    g.columns = [str(c).strip() for c in g.columns]

    g = g.rename(columns={
        "Country name": "Country",
        "EEA sub-region division": "EEA_subregion"
    })

    g = g[["Country", "EEA_subregion"]].copy()

    g["Country"] = g["Country"].astype(str).str.strip()
    g["Country"] = g["Country"].replace(COUNTRY_NAME_FIX)

    g["EEA_subregion"] = g["EEA_subregion"].astype(str).str.strip()

    g = g[g["EEA_subregion"] != "Not EEA"]
    g = g[g["EEA_subregion"] != ""]
    g = g[g["EEA_subregion"].notna()]

    return g.drop_duplicates()


# ---------------------------------------------------
# MAIN PLOT
# ---------------------------------------------------
def plot_country_trends_by_region(excel_path, group_file, output_png, output_pdf):

    print("Loading country active-stock panel...")
    df = load_country_panel(excel_path)
    groups = load_groupings(group_file)

    # merge region labels
    df = df.merge(groups, on="Country", how="left")
    df = df[df["EEA_subregion"].notna()].copy()

    # only health counts
    keep = df[[
        "Year",
        "Country",
        "EEA_subregion",
        "Health-relevant documents"
    ]].copy()

    region_order = [
        "Northern Europe",
        "Western Europe",
        "Southern Europe",
        "Central and Eastern Europe"
    ]

    valid_regions = [r for r in region_order if r in keep["EEA_subregion"].unique()]

    # global y max for same scale
    global_ymax = keep["Health-relevant documents"].max()

    fig, axes = plt.subplots(
        1,
        len(valid_regions),
        figsize=(4 * len(valid_regions), 5.6),
        sharey=True
    )

    if len(valid_regions) == 1:
        axes = [axes]

    for ax, region in zip(axes, valid_regions):

        temp = keep[keep["EEA_subregion"] == region].copy()

        for country in sorted(temp["Country"].unique()):

            cdf = temp[temp["Country"] == country].sort_values("Year")

            ax.plot(
                cdf["Year"],
                cdf["Health-relevant documents"],
                linewidth=1.6,
                alpha=0.9,
                label=country
            )

            # label at end
            last = cdf.iloc[-1]
            ax.text(
                last["Year"] + 0.2,
                last["Health-relevant documents"],
                country,
                fontsize=6.5,
                va="center"
            )

        # Paris marker
        ax.axvline(2015, linestyle=":", linewidth=1.1, color="black")
        ax.text(
            2015 + 0.25,
            global_ymax * 0.93,
            "Paris Agreement in force",
            fontsize=7,
            rotation=90,
            va="top"
        )

        ax.set_title(region, fontsize=11, fontweight="bold")
        ax.set_xlim(2000, 2026.5)
        ax.set_ylim(0, global_ymax * 1.08)
        ax.grid(axis="y", linestyle="--", alpha=0.3)

    axes[0].set_ylabel("Active health-relevant legislative families")

    fig.suptitle(
        "Country-Level Trends in Active Health-Relevant Legislative Families",
        fontsize=13,
        fontweight="bold",
        y=0.97
    )

    plt.tight_layout(rect=[0, 0, 1, 0.94])

    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.savefig(output_pdf, bbox_inches="tight")
    plt.close()

    print("Saved outputs.")


# ---------------------------------------------------
# CLI
# ---------------------------------------------------
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", required=True)
    parser.add_argument("--group_file", required=True)
    parser.add_argument("--output_png", required=True)
    parser.add_argument("--output_pdf", required=True)

    args = parser.parse_args()

    plot_country_trends_by_region(
        args.excel,
        args.group_file,
        args.output_png,
        args.output_pdf
    )


if __name__ == "__main__":
    main()