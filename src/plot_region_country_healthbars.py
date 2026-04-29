#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import math


# ---------------------------------------------------
# LOAD LEFT BLOCK OF "EEA38 subregion" SHEET
# ---------------------------------------------------
def load_left_subregion_block(excel_path):

    raw = pd.read_excel(
        excel_path,
        sheet_name="EEA38 subregion",
        header=1
    )

    # keep only columns until first unnamed gap
    keep_cols = []
    for c in raw.columns:
        if str(c).startswith("Unnamed"):
            break
        keep_cols.append(c)

    df = raw[keep_cols].copy()
    df.columns = [str(c).strip() for c in df.columns]

    # drop blank rows
    df = df[df["Year"].notna()]
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df[df["Year"].notna()]

    # remove Not EEA
    df = df[df["EEA_subregion"].astype(str).str.strip() != "Not EEA"]

    return df


# ---------------------------------------------------
# LOAD COUNTRY SHEET
# ---------------------------------------------------
def load_country_sheet(excel_path):

    cdf = pd.read_excel(excel_path, sheet_name="Country")
    cdf.columns = [str(c).strip() for c in cdf.columns]

    cdf = cdf[cdf["Year"].notna()]
    cdf["Year"] = pd.to_numeric(cdf["Year"], errors="coerce")
    cdf = cdf[cdf["Year"].notna()]

    cdf = cdf[cdf["EEA_subregion"].astype(str).str.strip() != "Not EEA"]

    return cdf


# ---------------------------------------------------
# MAIN PLOT
# ---------------------------------------------------
def plot_region_country_healthbars(excel_path, output_png, output_pdf):

    print("Loading regional tables...")
    subregion_df = load_left_subregion_block(excel_path)
    country_df = load_country_sheet(excel_path)

    # latest year from workbook
    latest_year = int(country_df["Year"].max())
    country_df = country_df[country_df["Year"] == latest_year].copy()

    valid_regions = sorted(subregion_df["EEA_subregion"].dropna().unique())

    n_regions = len(valid_regions)
    fig, axes = plt.subplots(
        1,
        n_regions,
        figsize=(5 * n_regions, 9),
        sharex=False
    )

    if n_regions == 1:
        axes = [axes]

    global_max = country_df["Health-relevant documents"].max()

    for ax, region in zip(axes, valid_regions):

        temp = country_df[country_df["EEA_subregion"] == region].copy()
        temp = temp.sort_values("Health-relevant documents", ascending=True)

        ax.barh(
            temp["Country"],
            temp["Health-relevant documents"],
            color="#C44E52",
            edgecolor="black",
            linewidth=0.6
        )

        for i, val in enumerate(temp["Health-relevant documents"]):
            ax.text(
                val + global_max * 0.015,
                i,
                str(int(val)),
                va="center",
                fontsize=9
            )

        ax.set_title(region, fontsize=13, fontweight="bold")
        ax.set_xlim(0, global_max * 1.20)
        ax.grid(axis="x", linestyle="--", alpha=0.35)

        if ax != axes[0]:
            ax.set_ylabel("")

    fig.suptitle(
        f"Active Health-Relevant Legislative Families by Country and EEA Subregion ({latest_year})",
        fontsize=15,
        fontweight="bold"
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.savefig(output_pdf, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_png}")
    print(f"Saved: {output_pdf}")


# ---------------------------------------------------
# CLI
# ---------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", required=True)
    parser.add_argument("--output_png", required=True)
    parser.add_argument("--output_pdf", required=True)

    args = parser.parse_args()

    plot_region_country_healthbars(
        args.excel,
        args.output_png,
        args.output_pdf
    )


if __name__ == "__main__":
    main()