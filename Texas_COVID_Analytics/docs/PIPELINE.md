# Pipeline Architecture

```text
01_Data_Understanding_NYT_COVID.ipynb
        │
        │  human-readable / GitHub-rendered EDA
        ▼
src/preprocess.py
        │
        ├── download NYT county files
        ├── Texas filtering
        ├── data-quality gate
        ├── cumulative → daily incidence
        ├── causal correction cleaning
        ├── lag / rolling features
        ├── next-7-day target
        ├── temporal split
        └── preprocessing report figures
        ▼
data/processed/
        ▼
src/train.py
        │
        ├── Naive persistence
        ├── Linear Regression
        ├── Ridge Regression
        ├── Random Forest
        ├── compare 3 train windows
        ├── validation auto-lock
        ├── final test
        ├── feature importance
        ├── permutation importance
        ├── save trained models
        └── export comparison figures
        ▼
reports/
models/
dashboard_data/
        ▼
app.py (Streamlit)
```

## Reproducibility rule

The Data Understanding notebook is intentionally kept as a notebook with
its executed outputs so reviewers can inspect the exploration directly.

Preprocessing and modeling are implemented as Python modules and can be
regenerated with:

```bash
python run_pipeline.py
```

The Final Test is not used to tune model choices.
