# Euro Legislative Indicator (part of LCDE 2027 Report)

This repository contains the code, processed data, and visual outputs for the **Lancet Countdown Project** in their annual Lancet Countdown in Europe (LCDE 2027) report. The project develops quantitative indicators to track and analyze legislative activity in the European Economic Area (EEA) countries + United Kingdom, using reproducible data workflows.

---

## 📌 Project Overview

The project aims to:

- Track legislative activity in the EEA38+UK over time.
- Construct structured indicators of legislative productivity and trends.
- Provide reproducible data pipelines from raw data to final figures.
- Generate publication-ready visualizations and structured datasets.

The repository contains scripts for data collection, cleaning, transformation, analysis, and visualization, as well as the resulting outputs.

---

## 📁 Repository Structure
```
Euro-legislative-indicator/
│
├── data/ # Raw and intermediary data files
│
├── outputs/
│ ├── dataframes/ # Processed datasets (CSV and related formats)
│ └── figures/ # Generated plots and visualizations
│
├── src/ # Python scripts for the analysis pipeline
│
├── requirements.txt # Python dependencies
├── .gitignore # Git ignored files
└── README.md # Project documentation
```

---

## 🧠 Workflow Overview

The project follows a structured pipeline:

1. **Data Acquisition**
   - Retrieve legislative data from relevant EU sources.
   - Store raw files in the `data/` directory.

2. **Data Cleaning & Transformation**
   - Standardize formats.
   - Handle missing values.
   - Construct analysis-ready variables.

3. **Indicator Construction**
   - Compute legislative indicators (e.g., counts, trends, aggregations).
   - Structure outputs into reusable dataframes.

4. **Visualization**
   - Generate figures summarizing legislative activity.
   - Export graphics to `outputs/figures/`.

---

## 📊 Outputs

### `outputs/dataframes/`

Contains processed datasets including:

- Cleaned legislative records
- Constructed indicators
- Aggregated summary tables
- Analysis-ready CSV files

These files are intended for:

- Replication
- Statistical analysis
- Integration into reports or dashboards

---

### `outputs/figures/`

Contains visual outputs such as:

- Time series plots
- Bar charts
- Comparative institutional analyses
- Trend summaries

All figures are generated programmatically to ensure reproducibility.

---

## 🚀 Getting Started

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/booktrackerGirl/Euro-legislative-indicator.git
cd Euro-legislative-indicator
```

### 2️⃣ Install Dependencies
Ensure Python 3.8+ is installed.
```bash
pip install -r requirements.txt
```

### 3️⃣ Run the Analysis Pipeline

Scripts in the src/ directory are modular and can be executed sequentially:
```bash
YET TO BE ADDED
```
Adjust execution depending on your research needs.

---
## 🔁 Reproducibility
This repository is structured to support full reproducibility:

- Raw data stored separately from processed outputs.
- Scripts clearly separated by function.
- All figures generated directly from processed datasets.
- No manual post-processing required for final outputs.

## 📚 Intended Use

This repository is designed for:

- Academic research
- Policy analysis
- Teaching and coursework
- Data science portfolio demonstration
- Extension into further legislative or institutional studies
