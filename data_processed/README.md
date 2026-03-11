# data_processed/

Cleaned and transformed datasets ready for model training. **Not tracked by Git** — regenerate from raw data.

## Files

| File | Source | Description |
|---|---|---|
| `brfss_diabetes_clean.csv` | `data_raw/LLCP2015.XPT` | Cleaned BRFSS 2015 data with 8 base features + diabetes label |

## Regenerate

**Option A** — Full retraining pipeline (recommended):
```bash
python retrain.py
```

**Option B** — Notebook:
```bash
jupyter notebook notebooks/brfss_cleaning.ipynb
```

## Feature Schema

The cleaned diabetes CSV contains these columns after processing:

| Column | Type | Range | Description |
|---|---|---|---|
| `diabetes` | int | 0–1 | Target label (1 = diabetic) |
| `bmi` | float | 10–80 | Body Mass Index |
| `age_group` | float | 1–13 | BRFSS age group |
| `high_bp` | int | 0–1 | High blood pressure |
| `smoker` | int | 0–1 | Has smoked 100+ cigarettes |
| `high_cholesterol` | int | 0–1 | High cholesterol |
| `physical_activity` | int | 0–1 | Physical activity in past 30 days |
| `general_health` | int | 1–5 | Self-rated health (1=Excellent, 5=Poor) |
| `mental_health` | float | 0–30 | Days of poor mental health |

Full feature definitions (including interaction features) are centralised in `feature_store/`.
