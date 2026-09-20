from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"
DASHBOARD_DATA_DIR = ROOT / "dashboard_data"

for directory in [
    RAW_DIR,
    PROCESSED_DIR,
    MODELS_DIR,
    FIGURES_DIR,
    TABLES_DIR,
    DASHBOARD_DATA_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

NYT_BASE = (
    "https://raw.githubusercontent.com/"
    "nytimes/covid-19-data/master"
)
COUNTY_YEARS = [2020, 2021, 2022, 2023]

TARGET_STATE = "Texas"
TECHNICAL_COUNTY_LABELS = {
    "unknown",
    "pending county assignment",
}

FORECAST_HORIZON = 7
LAGS = [1, 2, 3, 7, 14]
ROLL_WINDOWS = [7, 14]

TRAIN_COMMON_END = pd.Timestamp("2022-10-31")
VALIDATION_START = pd.Timestamp("2022-11-01")
VALIDATION_END = pd.Timestamp("2022-12-31")
TEST_START = pd.Timestamp("2023-01-01")
TEST_END = pd.Timestamp("2023-03-07")

TRAIN_START_2022 = pd.Timestamp("2022-01-01")
TRAIN_START_2021 = pd.Timestamp("2021-01-01")

RANDOM_STATE = 42
PRIMARY_METRIC = "MAE"
