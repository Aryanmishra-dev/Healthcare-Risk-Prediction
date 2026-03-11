# data_raw/

Raw source datasets for model training. **Not tracked by Git** (large files).

## Files

| File | Size | Source | Used By |
|---|---|---|---|
| `LLCP2015.XPT` | ~1.1 GB | CDC BRFSS 2015 | Diabetes + Heart Disease models |

## Download

**Automatic** — run `python retrain.py` and the script downloads + extracts automatically.

**Manual:**
1. Download: https://www.cdc.gov/brfss/annual_data/2015/files/LLCP2015XPT.zip
2. Extract `LLCP2015.XPT` into this directory.

## Data Versioning

This directory is tracked by [DVC](https://dvc.org/) when a remote is configured.  
See `dvc.yaml` in the project root for pipeline stage definitions.
