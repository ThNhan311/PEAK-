from __future__ import annotations

import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import (
    COUNTY_YEARS,
    FIGURES_DIR,
    FORECAST_HORIZON,
    LAGS,
    NYT_BASE,
    PROCESSED_DIR,
    RAW_DIR,
    ROLL_WINDOWS,
    TARGET_STATE,
    TECHNICAL_COUNTY_LABELS,
    TEST_END,
    TEST_START,
    TRAIN_COMMON_END,
    TRAIN_START_2021,
    TRAIN_START_2022,
    VALIDATION_END,
    VALIDATION_START,
)


MODEL_FEATURES_NUMERIC = [
    "current_new_cases",
    "current_new_deaths",
    "cases_lag_1",
    "cases_lag_2",
    "cases_lag_3",
    "cases_lag_7",
    "cases_lag_14",
    "deaths_lag_1",
    "deaths_lag_7",
    "deaths_lag_14",
    "cases_roll_mean_7",
    "cases_roll_std_7",
    "cases_roll_mean_14",
    "cases_roll_std_14",
    "deaths_roll_mean_7",
    "deaths_roll_mean_14",
    "cases_trend_7",
    "month",
    "day_of_week",
    "week_of_year",
    "quarter",
    "is_weekend",
    "month_sin",
    "month_cos",
    "dow_sin",
    "dow_cos",
    "days_since_start",
]

TARGET_COL = "target_next_7d_cases"


def download_raw_files() -> None:
    """Download NYT annual county files only when missing."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for year in COUNTY_YEARS:
        filename = f"us-counties-{year}.csv"
        destination = RAW_DIR / filename

        if destination.exists() and destination.stat().st_size > 0:
            print(f"[raw] cached: {filename}")
            continue

        url = f"{NYT_BASE}/{filename}"
        print(f"[raw] downloading: {url}")
        urllib.request.urlretrieve(url, destination)
        print(f"[raw] saved: {destination}")


def load_raw() -> pd.DataFrame:
    frames = []

    for year in COUNTY_YEARS:
        path = RAW_DIR / f"us-counties-{year}.csv"

        if not path.exists():
            raise FileNotFoundError(
                f"Missing raw file: {path}. "
                "Run download_raw_files() first."
            )

        frame = pd.read_csv(
            path,
            dtype={"fips": "string"},
            low_memory=False,
        )
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)

    expected = [
        "date", "county", "state",
        "fips", "cases", "deaths",
    ]
    missing = [c for c in expected if c not in df.columns]

    if missing:
        raise ValueError(
            f"Raw data is missing required columns: {missing}"
        )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )
    return df


def assert_daily_continuity(df: pd.DataFrame) -> None:
    """Lags/rolling must represent exact consecutive calendar days."""
    ordered = df.sort_values(["county", "date"]).copy()
    gaps = (
        ordered.groupby("county")["date"]
        .diff()
        .dropna()
    )

    bad = gaps[gaps != pd.Timedelta(days=1)]

    if not bad.empty:
        raise ValueError(
            "Detected non-daily county sequences. "
            "Do not create row-based lags until gaps are investigated."
        )


def run_preprocessing(download: bool = True) -> dict:
    print("=" * 68)
    print("DATA PREPARATION — TEXAS COVID-19")
    print("=" * 68)

    if download:
        download_raw_files()

    df_raw = load_raw()

    # Scope to Texas and exclude technical county labels.
    df_state = df_raw[
        df_raw["state"].eq(TARGET_STATE)
    ].copy()

    df_state["county_norm"] = (
        df_state["county"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    technical_mask = df_state[
        "county_norm"
    ].isin(TECHNICAL_COUNTY_LABELS)

    df_scope = (
        df_state.loc[~technical_mask]
        .drop(columns=["county_norm"])
        .copy()
    )

    # Quality gate.
    essential = ["date", "county", "state", "cases"]
    if df_scope[essential].isna().any().any():
        raise ValueError(
            "Missing values found in essential raw fields. "
            "Pipeline stops instead of imputing them."
        )

    duplicate_mask = df_scope.duplicated(
        subset=["date", "state", "county"],
        keep=False,
    )
    if duplicate_mask.any():
        raise ValueError(
            "Duplicate county-day records detected."
        )

    assert_daily_continuity(df_scope)

    # Cumulative -> daily incidence.
    df_daily = (
        df_scope
        .sort_values(["county", "date"])
        .reset_index(drop=True)
        .copy()
    )

    df_daily["new_cases_raw"] = (
        df_daily.groupby("county")["cases"]
        .diff()
    )
    df_daily["new_deaths_raw"] = (
        df_daily.groupby("county")["deaths"]
        .diff()
    )

    df_daily["negative_case_correction"] = (
        df_daily["new_cases_raw"] < 0
    )
    df_daily["negative_death_correction"] = (
        df_daily["new_deaths_raw"] < 0
    )

    # Causal correction cleaning.
    df_daily["case_correction_amount"] = (
        (-df_daily["new_cases_raw"])
        .clip(lower=0)
    )
    df_daily["death_correction_amount"] = (
        (-df_daily["new_deaths_raw"])
        .clip(lower=0)
    )

    df_daily["new_cases_clean"] = (
        df_daily["new_cases_raw"]
        .clip(lower=0)
    )
    df_daily["new_deaths_clean"] = (
        df_daily["new_deaths_raw"]
        .clip(lower=0)
    )

    correction_audit = (
        df_daily.groupby("county", as_index=False)
        .agg(
            negative_case_days=(
                "negative_case_correction", "sum"
            ),
            negative_death_days=(
                "negative_death_correction", "sum"
            ),
            total_case_correction_amount=(
                "case_correction_amount", "sum"
            ),
            total_death_correction_amount=(
                "death_correction_amount", "sum"
            ),
        )
    )

    correction_impact = (
        df_daily.groupby("county", as_index=False)
        .agg(
            raw_case_sum=("new_cases_raw", "sum"),
            clean_case_sum=("new_cases_clean", "sum"),
            raw_death_sum=("new_deaths_raw", "sum"),
            clean_death_sum=("new_deaths_clean", "sum"),
            case_correction_amount=(
                "case_correction_amount", "sum"
            ),
            death_correction_amount=(
                "death_correction_amount", "sum"
            ),
        )
    )

    correction_impact["case_cleaning_delta"] = (
        correction_impact["clean_case_sum"]
        - correction_impact["raw_case_sum"]
    )
    correction_impact["death_cleaning_delta"] = (
        correction_impact["clean_death_sum"]
        - correction_impact["raw_death_sum"]
    )

    case_gap = (
        correction_impact["case_cleaning_delta"]
        - correction_impact["case_correction_amount"]
    ).abs().max()

    death_gap = (
        correction_impact["death_cleaning_delta"]
        - correction_impact["death_correction_amount"]
    ).abs().max()

    if case_gap >= 1e-6 or death_gap >= 1e-6:
        raise AssertionError(
            "Correction impact audit failed."
        )

    # Outlier diagnostic only; positive epidemic spikes are retained.
    reference = df_daily[
        df_daily["date"] <= TRAIN_COMMON_END
    ].copy()

    county_thresholds = (
        reference.groupby("county")["new_cases_clean"]
        .agg(
            q1=lambda s: s.quantile(0.25),
            q3=lambda s: s.quantile(0.75),
        )
        .reset_index()
    )

    county_thresholds["iqr"] = (
        county_thresholds["q3"]
        - county_thresholds["q1"]
    )
    county_thresholds["upper_iqr3"] = (
        county_thresholds["q3"]
        + 3 * county_thresholds["iqr"]
    )

    df_daily = df_daily.merge(
        county_thresholds[
            ["county", "q1", "q3", "iqr", "upper_iqr3"]
        ],
        on="county",
        how="left",
    )

    df_daily["high_extreme_iqr3_flag"] = (
        df_daily["new_cases_clean"]
        > df_daily["upper_iqr3"]
    )

    outlier_by_county = (
        df_daily.groupby("county", as_index=False)
        .agg(
            extreme_days=("high_extreme_iqr3_flag", "sum"),
            total_days=("date", "size"),
            max_new_cases=("new_cases_clean", "max"),
            upper_iqr3=("upper_iqr3", "first"),
        )
    )
    outlier_by_county["extreme_pct"] = (
        outlier_by_county["extreme_days"]
        / outlier_by_county["total_days"]
        * 100
    )

    # Save preprocessing diagnostic figure.
    monthly_extreme = (
        df_daily.assign(
            month=df_daily["date"]
            .dt.to_period("M")
            .astype(str)
        )
        .groupby("month", as_index=False)
        .agg(
            extreme_days=(
                "high_extreme_iqr3_flag", "sum"
            ),
            total_new_cases=("new_cases_clean", "sum"),
        )
    )

    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax1.plot(
        monthly_extreme["month"],
        monthly_extreme["total_new_cases"],
        label="Total clean new cases",
    )
    ax1.set_ylabel("Total clean new cases")
    ax1.set_xlabel("Month")

    ax2 = ax1.twinx()
    ax2.plot(
        monthly_extreme["month"],
        monthly_extreme["extreme_days"],
        linestyle="--",
        label="IQR3 extreme flags",
    )
    ax2.set_ylabel("Number of extreme flags")

    step = max(1, len(monthly_extreme) // 12)
    ax1.set_xticks(
        range(0, len(monthly_extreme), step)
    )
    ax1.set_xticklabels(
        monthly_extreme["month"].iloc[::step],
        rotation=45,
    )

    plt.title(
        "Preprocessing diagnostic: extreme flags "
        "vs epidemic activity — Texas"
    )
    fig.tight_layout()
    fig.savefig(
        FIGURES_DIR
        / "01_preprocess_extreme_flags_vs_activity.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)

    # Target: next 7-day total.
    df_feat = (
        df_daily
        .sort_values(["county", "date"])
        .reset_index(drop=True)
        .copy()
    )

    future_case_cols = []
    future_death_cols = []

    for h in range(1, FORECAST_HORIZON + 1):
        ccol = f"_future_cases_{h}"
        dcol = f"_future_deaths_{h}"

        df_feat[ccol] = (
            df_feat.groupby("county")["new_cases_clean"]
            .shift(-h)
        )
        df_feat[dcol] = (
            df_feat.groupby("county")["new_deaths_clean"]
            .shift(-h)
        )

        future_case_cols.append(ccol)
        future_death_cols.append(dcol)

    df_feat[TARGET_COL] = (
        df_feat[future_case_cols]
        .sum(
            axis=1,
            min_count=FORECAST_HORIZON,
        )
    )

    df_feat["target_next_7d_deaths"] = (
        df_feat[future_death_cols]
        .sum(
            axis=1,
            min_count=FORECAST_HORIZON,
        )
    )

    # Last calendar day used by this forecast target. Splits use
    # this key to prevent targets from crossing period boundaries.
    df_feat["target_end_date"] = (
        df_feat["date"]
        + pd.Timedelta(days=FORECAST_HORIZON)
    )

    df_feat.drop(
        columns=(
            future_case_cols
            + future_death_cols
        ),
        inplace=True,
    )

    # Feature engineering — present/past only.
    df_feat["current_new_cases"] = (
        df_feat["new_cases_clean"]
    )
    df_feat["current_new_deaths"] = (
        df_feat["new_deaths_clean"]
    )

    for lag in LAGS:
        df_feat[f"cases_lag_{lag}"] = (
            df_feat.groupby("county")["new_cases_clean"]
            .shift(lag)
        )

    for lag in [1, 7, 14]:
        df_feat[f"deaths_lag_{lag}"] = (
            df_feat.groupby("county")["new_deaths_clean"]
            .shift(lag)
        )

    for window in ROLL_WINDOWS:
        df_feat[f"cases_roll_mean_{window}"] = (
            df_feat.groupby("county")["new_cases_clean"]
            .transform(
                lambda s: s.rolling(
                    window,
                    min_periods=window,
                ).mean()
            )
        )
        df_feat[f"cases_roll_std_{window}"] = (
            df_feat.groupby("county")["new_cases_clean"]
            .transform(
                lambda s: s.rolling(
                    window,
                    min_periods=window,
                ).std()
            )
        )
        df_feat[f"deaths_roll_mean_{window}"] = (
            df_feat.groupby("county")["new_deaths_clean"]
            .transform(
                lambda s: s.rolling(
                    window,
                    min_periods=window,
                ).mean()
            )
        )

    df_feat["cases_trend_7"] = (
        df_feat["current_new_cases"]
        - df_feat["cases_lag_7"]
    )

    df_feat["year"] = df_feat["date"].dt.year
    df_feat["month"] = df_feat["date"].dt.month
    df_feat["day_of_week"] = (
        df_feat["date"].dt.dayofweek
    )
    df_feat["week_of_year"] = (
        df_feat["date"]
        .dt.isocalendar()
        .week
        .astype(int)
    )
    df_feat["quarter"] = (
        df_feat["date"].dt.quarter
    )
    df_feat["is_weekend"] = (
        df_feat["day_of_week"] >= 5
    ).astype(int)

    df_feat["month_sin"] = np.sin(
        2 * np.pi * df_feat["month"] / 12
    )
    df_feat["month_cos"] = np.cos(
        2 * np.pi * df_feat["month"] / 12
    )
    df_feat["dow_sin"] = np.sin(
        2 * np.pi * df_feat["day_of_week"] / 7
    )
    df_feat["dow_cos"] = np.cos(
        2 * np.pi * df_feat["day_of_week"] / 7
    )

    global_start = df_feat["date"].min()
    df_feat["days_since_start"] = (
        df_feat["date"] - global_start
    ).dt.days

    required = (
        MODEL_FEATURES_NUMERIC
        + [TARGET_COL]
    )

    df_model = (
        df_feat.dropna(
            subset=required
        )
        .copy()
    )

    if df_model[required].isna().any().any():
        raise AssertionError(
            "Model-ready dataset still contains NaN."
        )

    # Temporal split.
    validation_mask = (
        (df_model["date"] >= VALIDATION_START)
        & (df_model["target_end_date"] < TEST_START)
    )
    test_mask = df_model["date"].between(
        TEST_START,
        TEST_END,
    )
    train_2022_mask = (
        (df_model["date"] >= TRAIN_START_2022)
        & (df_model["target_end_date"] < VALIDATION_START)
    )
    train_2021_2022_mask = (
        (df_model["date"] >= TRAIN_START_2021)
        & (df_model["target_end_date"] < VALIDATION_START)
    )
    train_2020_2022_mask = (
        df_model["target_end_date"] < VALIDATION_START
    )

    split_summary = pd.DataFrame({
        "dataset": [
            "train_candidate_2022",
            "train_candidate_2021_2022",
            "train_candidate_2020_2022",
            "validation",
            "test",
        ],
        "rows": [
            int(train_2022_mask.sum()),
            int(train_2021_2022_mask.sum()),
            int(train_2020_2022_mask.sum()),
            int(validation_mask.sum()),
            int(test_mask.sum()),
        ],
        "start_date": [
            df_model.loc[
                train_2022_mask, "date"
            ].min(),
            df_model.loc[
                train_2021_2022_mask, "date"
            ].min(),
            df_model.loc[
                train_2020_2022_mask, "date"
            ].min(),
            df_model.loc[
                validation_mask, "date"
            ].min(),
            df_model.loc[
                test_mask, "date"
            ].min(),
        ],
        "end_date": [
            df_model.loc[
                train_2022_mask, "date"
            ].max(),
            df_model.loc[
                train_2021_2022_mask, "date"
            ].max(),
            df_model.loc[
                train_2020_2022_mask, "date"
            ].max(),
            df_model.loc[
                validation_mask, "date"
            ].max(),
            df_model.loc[
                test_mask, "date"
            ].max(),
        ],
    })

    # Leakage / integrity audit.
    forbidden = {
        TARGET_COL,
        "target_next_7d_deaths",
        "split_default",
        "candidate_train_2022",
        "candidate_train_2021_2022",
        "candidate_train_2020_2022",
    }

    if not forbidden.isdisjoint(
        set(MODEL_FEATURES_NUMERIC)
    ):
        raise AssertionError(
            "Forbidden feature found."
        )

    if (
        train_2021_2022_mask
        & validation_mask
    ).any():
        raise AssertionError(
            "Train/validation overlap."
        )

    if (
        train_2021_2022_mask
        & test_mask
    ).any():
        raise AssertionError(
            "Train/test overlap."
        )

    if (
        validation_mask
        & test_mask
    ).any():
        raise AssertionError(
            "Validation/test overlap."
        )

    if (
        df_model.loc[
            train_2020_2022_mask,
            "target_end_date",
        ].max()
        >= VALIDATION_START
    ):
        raise AssertionError(
            "Train target crosses into validation."
        )

    if (
        df_model.loc[
            validation_mask,
            "target_end_date",
        ].max()
        >= TEST_START
    ):
        raise AssertionError(
            "Validation target crosses into test."
        )

    if (df_model[TARGET_COL] < 0).any():
        raise AssertionError(
            "Negative target detected."
        )

    if df_model.loc[
        test_mask, "date"
    ].max() != TEST_END:
        raise AssertionError(
            "Final test boundary is not correct."
        )

    # Feature manifest.
    feature_manifest = pd.DataFrame([
        {
            "column": "date",
            "role": "time_key",
            "use_in_model": False,
            "note": "Temporal split key",
        },
        {
            "column": "county",
            "role": "categorical_identifier",
            "use_in_model": "optional",
            "note": "OneHotEncoder is fit on train when used",
        },
        {
            "column": "fips",
            "role": "identifier",
            "use_in_model": False,
            "note": "Identifier, not continuous numeric feature",
        },
        *[
            {
                "column": c,
                "role": "numeric_feature",
                "use_in_model": True,
                "note": "Past/current-known feature",
            }
            for c in MODEL_FEATURES_NUMERIC
        ],
        {
            "column": TARGET_COL,
            "role": "target",
            "use_in_model": False,
            "note": "Total clean cases in next 7 days",
        },
    ])

    safe_id_cols = [
        "date", "county", "state", "fips",
    ]
    safe_model_cols = (
        safe_id_cols
        + MODEL_FEATURES_NUMERIC
        + [TARGET_COL]
    )

    # Export.
    daily_export_cols = [
        "date", "county", "state", "fips",
        "cases", "deaths",
        "new_cases_raw", "new_deaths_raw",
        "new_cases_clean", "new_deaths_clean",
        "negative_case_correction",
        "negative_death_correction",
        "case_correction_amount",
        "death_correction_amount",
        "high_extreme_iqr3_flag",
    ]

    outputs = {
        "texas_daily_prepared_final.csv":
            df_daily[daily_export_cols],
        "correction_audit_final.csv":
            correction_audit,
        "correction_impact_audit_final.csv":
            correction_impact,
        "outlier_diagnostic_by_county_final.csv":
            outlier_by_county,
        "feature_manifest_final.csv":
            feature_manifest,
        "split_summary_final.csv":
            split_summary,
        "texas_model_master_final.csv":
            df_model[safe_model_cols],
        "train_candidate_2022_final.csv":
            df_model.loc[
                train_2022_mask,
                safe_model_cols,
            ],
        "train_candidate_2021_2022_final.csv":
            df_model.loc[
                train_2021_2022_mask,
                safe_model_cols,
            ],
        "train_candidate_2020_2022_final.csv":
            df_model.loc[
                train_2020_2022_mask,
                safe_model_cols,
            ],
        "validation_2022_nov_dec_final.csv":
            df_model.loc[
                validation_mask,
                safe_model_cols,
            ],
        "test_2023_jan01_mar07_final.csv":
            df_model.loc[
                test_mask,
                safe_model_cols,
            ],
    }

    for filename, frame in outputs.items():
        frame.to_csv(
            PROCESSED_DIR / filename,
            index=False,
        )

    summary_lines = [
        f"# DATA PREPARATION SUMMARY — {TARGET_STATE}",
        f"- Raw Texas rows: {len(df_state):,}",
        (
            "- Technical-label rows removed: "
            f"{int(technical_mask.sum()):,}"
        ),
        (
            "- Real counties: "
            f"{df_scope['county'].nunique():,}"
        ),
        (
            "- Negative case corrections detected: "
            f"{int(df_daily['negative_case_correction'].sum()):,}"
        ),
        (
            "- Negative death corrections detected: "
            f"{int(df_daily['negative_death_correction'].sum()):,}"
        ),
        (
            "- Extreme-positive IQR3 flags retained: "
            f"{int(df_daily['high_extreme_iqr3_flag'].sum()):,}"
        ),
        (
            "- Model-ready rows: "
            f"{len(df_model):,}"
        ),
        (
            "- Final test window: "
            f"{TEST_START.date()} → {TEST_END.date()}"
        ),
        (
            "- Negative revisions use causal clip(lower=0); "
            "no backward redistribution."
        ),
        (
            "- Positive epidemic extremes are retained."
        ),
        (
            "- Scaling/model selection are deferred to training."
        ),
    ]

    summary_text = "\n".join(summary_lines)
    (
        PROCESSED_DIR
        / "data_preparation_summary_final.txt"
    ).write_text(
        summary_text,
        encoding="utf-8",
    )

    # Split-size report figure.
    plot_split = split_summary.copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(
        plot_split["dataset"],
        plot_split["rows"],
    )
    ax.set_xlabel("Rows")
    ax.set_ylabel("Dataset")
    ax.set_title(
        "Temporal split sizes — preprocessing output"
    )
    fig.tight_layout()
    fig.savefig(
        FIGURES_DIR
        / "02_preprocess_split_sizes.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(summary_text)
    print(
        f"[done] processed data -> {PROCESSED_DIR}"
    )
    print(
        f"[done] preprocess figures -> {FIGURES_DIR}"
    )

    return {
        "model_rows": len(df_model),
        "counties": df_scope["county"].nunique(),
        "processed_dir": str(PROCESSED_DIR),
    }


def main() -> None:
    run_preprocessing(download=True)


if __name__ == "__main__":
    main()
