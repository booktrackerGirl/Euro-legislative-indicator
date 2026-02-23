#!/usr/bin/env bash

set -e  # Stop if any command fails

echo "--------------------------------------------"
echo "EURO LEGISLATIVE HEALTH INDICATOR PIPELINE"
echo "--------------------------------------------"

# Create required directories if they do not exist
mkdir -p ./outputs/dataframes
mkdir -p ./outputs/figures

echo "Step 1: Extracting health relevance annotations..."
python ./src/health_relevance_pipeline.py

echo "Step 2: Creating yearly panel dataset..."
python ./src/create_yearly_panel.py \
  --input ./data/euro_legis_df.csv \
  --output ./outputs/dataframes/policy_year_panel.csv

echo "Step 3: Creating aggregate health counts (EEA38+UK + subregions)..."
python ./src/create_aggregate_health_counts.py \
  --panel ./outputs/dataframes/policy_year_panel.csv \
  --health ./outputs/dataframes/health_annotations.csv \
  --output ./outputs/dataframes/health_counts.xlsx

echo "Step 4: Generating EU health relevance map..."
python ./src/plot_euromap.py \
  --input_csv ./outputs/dataframes/health_annotations.csv \
  --panel ./outputs/dataframes/policy_year_panel.csv \
  --output_csv ./outputs/dataframes/country_year_health_stats.csv \
  --output_png ./outputs/figures/europe_health_map.png \
  --output_pdf ./outputs/figures/europe_health_map.pdf

echo "Step 5: Plotting health category trends..."
python ./src/plot_euro_health_categories.py \
  --input ./outputs/dataframes/health_annotations.csv \
  --panel ./outputs/dataframes/policy_year_panel.csv \
  --output ./outputs/figures/euro_health_categories.pdf

echo "Step 6: Plotting response type stackplot..."
python ./src/plot_euro_response_topics.py \
  --annotation ./outputs/dataframes/health_annotations.csv \
  --panel ./outputs/dataframes/policy_year_panel.csv \
  --output ./outputs/figures/euro_policy_stackplot.pdf

echo "Step 7: Generating health policy flow timeline..."
python ./src/health_policy_barplot.py \
  --legislation ./data/euro_legis_df.csv \
  --health ./outputs/dataframes/health_annotations.csv \
  --output ./outputs/figures/euro_health_policy_timeline.png

echo "--------------------------------------------"
echo "Pipeline completed successfully."
echo "All datasets and figures generated."
echo "--------------------------------------------"