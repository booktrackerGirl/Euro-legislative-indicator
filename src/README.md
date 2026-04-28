# Overview
This documentation is to understand the purpose of each python script used in this repository. This corresponds to the 

## 🧠 Step 1 – Health Relevance Extraction

### Script:
```
python ./src/health_relevance_pipeline.py
```

### Purpose:
- Extract health-related terms from the full text of each legislative document.
- Identify presence of health keywords.
- Map keywords into 13 structured health categories.

### Output:
outputs/dataframes/health_annotations.csv


### Health Term Mapping

Health keywords are grouped into the following categories:

- general_health
- mortality_morbidity
- injury_trauma
- communicable_disease
- non_communicable_disease
- vector_borne_zoonotic
- pathogens_microbiology
- food_waterborne
- nutrition
- maternal_child_health
- environmental_health
- mental_health
- substance_use

⚠️ A single document may contain multiple categories.

---

## Step 2 - Aggregate documents by their Family ID


## 🧠 Step 3 – Create Yearly Policy Panel

### Script:
```
python ./src/create_yearly_panel.py
--input ./data/euro_legis_df.csv
--output ./outputs/dataframes/policy_year_panel.csv
```


### Purpose:
Creates a **document-year panel dataset**.

Each policy:
- Is uniquely identified by document ID.
- Has active years derived from:
  - `Full timeline of events (types)`
  - `Full timeline of events (dates)`

### Output:
outputs/dataframes/policy_year_panel.csv



This panel is later merged with health annotations.

---

## 🧠 Step 4 – Aggregate Health Counts

### Script:
```
python ./src/create_aggregate_health_counts.py 
  --cclw ./data/euro_legis_df.csv 
  --annotations ./outputs/dataframes/health_annotations_by_family.csv 
  --group-file "./data/2027 Country names and groupings.xlsx" 
  --output ./outputs/dataframes/health_counts.xlsx
```


### Purpose:
Creates aggregated counts for:

- Europe (EEA+ UK): collective yearly counts for all EEA members + UK
- Europe EEA(no UK): collective yearly counts for all EEA members excluding UK
- EEA38+UK, EEA38(no UK) subregions: same sheet containing TWO vertically stacked tables: 
  - Table A: EEA + UK (Included in northern subregion division) grouped by EEA sub-region division 
  - Table B: EEA subregion (without UK) grouped by EEA sub-region division. Aggregation follows official EEA38+UK subregion divisions.
- Country: grouped by each individual Europe country
- EU: collective yearly counts for European Union entries only

### Output:
outputs/dataframes/health_counts.xlsx


---

## 📊 Figures

---

## 1️⃣ Europe Health Relevance Map

### Script:
```
python ./src/plot_euromap.py
--input_csv ./outputs/dataframes/health_annotations_by_family.csv
--panel ./outputs/dataframes/policy_year_panel.csv
--output_csv ./outputs/dataframes/country_year_health_stats.csv
--output_png ./outputs/figures/europe_health_map.png
--output_pdf ./outputs/figures/europe_health_map.pdf
```


### Description:
Generates a map of EEA38+UK countries showing:

- Number of active unique legislative documents
- Containing health relevance
- Active between 2000–2025

### Outputs:
outputs/figures/europe_health_map.png,
outputs/figures/europe_health_map.pdf

---

## 2️⃣ Health Category Trends (Stackplot)

### Script:
```
python ./src/plot_euro_health_categories.py \
  --annotation ./outputs/dataframes/health_annotations_by_family.csv \
  --legis ./data/euro_legis_df.csv \
  --output ./outputs/figures/euro_health_categories.pdf
```


### Description:
- Yearly total active health-related documents (2000–2025)
- Stacked by 13 health categories
- Flow-based stock (not cumulative)

⚠️ Documents may belong to multiple categories.

### Output:
outputs/figures/euro_health_categories.pdf

---

## 3️⃣ Policy Response Topics Stackplot

### Script:
```
python ./src/plot_euro_response_topics.py \
    --annotation ./outputs/dataframes/health_annotations_by_family.csv \
    --legis ./data/euro_legis_df.csv \
    --output ./outputs/figures/euro_policy_stackplot.pdf

```

### Description:
Same yearly active framework, but categorized by:

- Adaptation
- Mitigation
- Disaster Risk Management
- Loss and Damage

Documents may:
- Belong to multiple response types
- Rarely belong to none

### Output:
outputs/figures/euro_policy_stackplot.pdf


---

## 4️⃣ Health Policy Flow Timeline

### Script:
```
python ./src/health_policy_barplot.py
--legislation ./data/euro_legis_df.csv
--health ./outputs/dataframes/health_annotations_by_family.csv
--output ./outputs/figures/euro_health_policy_timeline.png
```


### Description:
Visualizes policy dynamics:

- Policies active from previous year
- Newly added policies
- Removed/expired policies

Shows legislative health policy flow over time.

### Output:
outputs/figures/euro_health_policy_timeline.png

---

## ▶️ Run Full Pipeline

Instead of running scripts individually:
```
chmod +x src/run_full_pipeline.sh
./src/run_full_pipeline.sh
```
