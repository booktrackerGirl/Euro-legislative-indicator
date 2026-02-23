# Pverview
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

## 🧠 Step 2 – Create Yearly Policy Panel

### Script:
python ./src/create_yearly_panel.py
--input ./data/euro_legis_df.csv
--output ./outputs/dataframes/policy_year_panel.csv



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

## 🧠 Step 3 – Aggregate Health Counts

### Script:
python ./src/create_aggregate_health_counts.py
--panel ./outputs/dataframes/policy_year_panel.csv
--health ./outputs/dataframes/health_annotations.csv
--output ./outputs/dataframes/health_counts.xlsx

