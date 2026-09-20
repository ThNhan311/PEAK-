from __future__ import annotations

import json
import re
import shutil

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)

from .config import (
    DASHBOARD_DATA_DIR,
    FIGURES_DIR,
    MODELS_DIR,
    PRIMARY_METRIC,
    PROCESSED_DIR,
    RANDOM_STATE,
    TABLES_DIR,
)


TARGET = "target_next_7d_cases"

TRAIN_FILES = {
    "2022": "train_candidate_2022_final.csv",
    "2021-2022":
        "train_candidate_2021_2022_final.csv",
    "2020-2022":
        "train_candidate_2020_2022_final.csv",
}

RIDGE_ALPHA_GRID = [
    1, 10, 100, 1000, 10000,
    20000, 30000, 40000,
    50000, 100000,
]


def load_inputs():
    manifest = pd.read_csv(
        PROCESSED_DIR
        / "feature_manifest_final.csv"
    )

    numeric_features = manifest[
        (manifest["role"] == "numeric_feature")
        & (
            manifest["use_in_model"]
            .astype(str)
            .eq("True")
        )
    ]["column"].tolist()

    linear_features = [
        "county",
        *numeric_features,
    ]

    validation = pd.read_csv(
        PROCESSED_DIR
        / "validation_2022_nov_dec_final.csv",
        parse_dates=["date"],
    )

    test = pd.read_csv(
        PROCESSED_DIR
        / "test_2023_jan01_mar07_final.csv",
        parse_dates=["date"],
    )

    master = pd.read_csv(
        PROCESSED_DIR
        / "texas_model_master_final.csv",
        parse_dates=["date"],
    )

    return (
        manifest,
        numeric_features,
        linear_features,
        validation,
        test,
        master,
    )


def evaluate_predictions(
    y_true,
    y_pred,
    peak_quantile=0.90,
):
    y_true = np.asarray(
        y_true,
        dtype=float,
    )
    raw_pred = np.asarray(
        y_pred,
        dtype=float,
    )

    negative_pct = float(
        (raw_pred < 0).mean() * 100
    )

    y_pred = np.clip(
        raw_pred,
        0,
        None,
    )

    peak_threshold = float(
        np.quantile(
            y_true,
            peak_quantile,
        )
    )

    peak_mask = (
        y_true >= peak_threshold
    )

    return {
        "MAE": float(
            mean_absolute_error(
                y_true,
                y_pred,
            )
        ),
        "RMSE": float(
            mean_squared_error(
                y_true,
                y_pred,
            ) ** 0.5
        ),
        "R2": float(
            r2_score(
                y_true,
                y_pred,
            )
        ),
        "Peak_MAE": float(
            mean_absolute_error(
                y_true[peak_mask],
                y_pred[peak_mask],
            )
        ),
        "Peak_Threshold":
            peak_threshold,
        "NegPredPct_before_clip":
            negative_pct,
    }


def make_linear_preprocessor(
    numeric_features,
):
    return ColumnTransformer([
        (
            "num",
            StandardScaler(),
            numeric_features,
        ),
        (
            "county",
            OneHotEncoder(
                handle_unknown="ignore"
            ),
            ["county"],
        ),
    ])


def naive_predict(df):
    return (
        pd.to_numeric(
            df["cases_roll_mean_7"]
        )
        .to_numpy(dtype=float)
        * 7.0
    )


def best_row_for(
    best_by_algorithm,
    model_name,
):
    return (
        best_by_algorithm[
            best_by_algorithm["Model"]
            == model_name
        ]
        .sort_values(
            ["MAE", "RMSE"]
        )
        .iloc[0]
    )


def parse_ridge_alpha(text):
    match = re.search(
        r"alpha=([0-9.]+)",
        str(text),
    )
    if not match:
        raise ValueError(
            f"Cannot parse Ridge alpha: {text}"
        )
    return float(
        match.group(1)
    )


def save_barh(
    df,
    x,
    y,
    title,
    xlabel,
    filename,
):
    fig, ax = plt.subplots(
        figsize=(9, 5)
    )
    ax.barh(
        df[y],
        df[x],
    )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(y)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(
        FIGURES_DIR / filename,
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)


def run_training() -> dict:
    print("=" * 68)
    print("MODELING & MODEL COMPARISON")
    print("=" * 68)

    (
        manifest,
        numeric_features,
        linear_features,
        validation,
        test,
        master,
    ) = load_inputs()

    y_val = validation[
        TARGET
    ].to_numpy(dtype=float)

    validation_results = []

    # Naive baseline.
    naive_val_pred = naive_predict(
        validation
    )
    validation_results.append({
        "Model":
            "Naive 7-day persistence",
        "Window": "N/A",
        "Hyperparameters":
            "past_7d_sum",
        **evaluate_predictions(
            y_val,
            naive_val_pred,
        ),
    })

    rf_validation_models = {}

    # Compare three training windows.
    for window, filename in (
        TRAIN_FILES.items()
    ):
        print(
            f"[train] window={window}"
        )

        train = pd.read_csv(
            PROCESSED_DIR / filename,
            parse_dates=["date"],
        )

        x_train_linear = train[
            linear_features
        ]
        x_val_linear = validation[
            linear_features
        ]

        x_train_rf = (
            train[numeric_features]
            .astype(np.float32)
        )
        x_val_rf = (
            validation[numeric_features]
            .astype(np.float32)
        )

        y_train = train[
            TARGET
        ].to_numpy(dtype=float)

        # Fit the linear preprocessor ONCE per train window.
        # Reuse the same transformed matrices for Linear + all Ridge alphas.
        # This is mathematically equivalent to refitting an identical
        # StandardScaler/OneHotEncoder for every alpha, but much faster.
        validation_preprocessor = (
            make_linear_preprocessor(
                numeric_features
            )
        )
        x_train_linear_t = (
            validation_preprocessor
            .fit_transform(
                x_train_linear
            )
        )
        x_val_linear_t = (
            validation_preprocessor
            .transform(
                x_val_linear
            )
        )

        # Linear Regression.
        linear_model = LinearRegression()
        linear_model.fit(
            x_train_linear_t,
            y_train,
        )

        pred = linear_model.predict(
            x_val_linear_t
        )

        validation_results.append({
            "Model": "Linear Regression",
            "Window": window,
            "Hyperparameters":
                "county OHE + standardize",
            **evaluate_predictions(
                y_val,
                pred,
            ),
        })

        # Ridge alpha selection on the same train-fitted matrix.
        best_ridge = None

        for alpha in RIDGE_ALPHA_GRID:
            ridge_model = Ridge(
                alpha=float(alpha),
                solver="lsqr",
            )

            ridge_model.fit(
                x_train_linear_t,
                y_train,
            )

            pred = ridge_model.predict(
                x_val_linear_t
            )

            candidate = {
                "Model": "Ridge Regression",
                "Window": window,
                "Hyperparameters":
                    f"alpha={alpha}",
                **evaluate_predictions(
                    y_val,
                    pred,
                ),
            }

            if (
                best_ridge is None
                or candidate[
                    PRIMARY_METRIC
                ] < best_ridge[
                    PRIMARY_METRIC
                ]
            ):
                best_ridge = candidate

        validation_results.append(
            best_ridge
        )

        # Random Forest on log1p target.
        rf_model = RandomForestRegressor(
            n_estimators=60,
            max_depth=8,
            min_samples_leaf=5,
            max_features=0.7,
            max_samples=0.8,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )

        rf_model.fit(
            x_train_rf,
            np.log1p(y_train),
        )

        pred = np.expm1(
            rf_model.predict(
                x_val_rf
            )
        )

        validation_results.append({
            "Model":
                "Random Forest (log-target)",
            "Window": window,
            "Hyperparameters": (
                "60 trees, depth=8, "
                "leaf=5, max_features=.7, "
                "max_samples=.8"
            ),
            **evaluate_predictions(
                y_val,
                pred,
            ),
        })

        rf_validation_models[
            window
        ] = rf_model

    validation_results = (
        pd.DataFrame(
            validation_results
        )
        .sort_values(
            ["MAE", "RMSE"]
        )
        .reset_index(drop=True)
    )

    best_by_algorithm = (
        validation_results
        .sort_values(
            ["MAE", "RMSE"]
        )
        .groupby(
            "Model",
            as_index=False,
        )
        .first()
        .sort_values("MAE")
        .reset_index(drop=True)
    )

    naive_mae = float(
        best_by_algorithm.loc[
            best_by_algorithm["Model"]
            == "Naive 7-day persistence",
            "MAE",
        ].iloc[0]
    )

    best_by_algorithm[
        "MAE_vs_Naive_pct"
    ] = (
        (
            best_by_algorithm["MAE"]
            / naive_mae
        )
        - 1
    ) * 100

    # Save validation tables.
    validation_results.to_csv(
        TABLES_DIR
        / "validation_model_comparison.csv",
        index=False,
    )

    best_by_algorithm.to_csv(
        TABLES_DIR
        / "best_validation_config_by_algorithm.csv",
        index=False,
    )

    save_barh(
        best_by_algorithm.sort_values(
            "MAE",
            ascending=True,
        ),
        "MAE",
        "Model",
        "Best validation MAE by model",
        "Validation MAE",
        "03_validation_mae_comparison.png",
    )

    # Auto-lock from validation only.
    window_start = {
        "2022":
            pd.Timestamp("2022-01-01"),
        "2021-2022":
            pd.Timestamp("2021-01-01"),
        "2020-2022":
            master["date"].min(),
    }

    final_train_end = pd.Timestamp(
        "2022-12-31"
    )

    linear_best = best_row_for(
        best_by_algorithm,
        "Linear Regression",
    )
    ridge_best = best_row_for(
        best_by_algorithm,
        "Ridge Regression",
    )
    rf_best = best_row_for(
        best_by_algorithm,
        "Random Forest (log-target)",
    )

    locked = {
        "Linear Regression": {
            "validation_window":
                str(linear_best["Window"]),
            "start":
                window_start[
                    str(
                        linear_best[
                            "Window"
                        ]
                    )
                ],
            "end": final_train_end,
            "validation_MAE":
                float(
                    linear_best["MAE"]
                ),
        },
        "Ridge Regression": {
            "validation_window":
                str(ridge_best["Window"]),
            "start":
                window_start[
                    str(
                        ridge_best[
                            "Window"
                        ]
                    )
                ],
            "end": final_train_end,
            "alpha":
                parse_ridge_alpha(
                    ridge_best[
                        "Hyperparameters"
                    ]
                ),
            "validation_MAE":
                float(
                    ridge_best["MAE"]
                ),
        },
        "Random Forest (log-target)": {
            "validation_window":
                str(rf_best["Window"]),
            "start":
                window_start[
                    str(
                        rf_best[
                            "Window"
                        ]
                    )
                ],
            "end": final_train_end,
            "validation_MAE":
                float(
                    rf_best["MAE"]
                ),
        },
    }

    # Final test — locked configurations.
    test_results = []
    predictions = (
        test[["date", "county", TARGET]]
        .copy()
        .rename(
            columns={
                TARGET: "actual_target"
            }
        )
    )

    y_test = test[
        TARGET
    ].to_numpy(dtype=float)

    p_naive = naive_predict(test)
    predictions["pred_naive"] = np.clip(
        p_naive,
        0,
        None,
    )

    test_results.append({
        "Model":
            "Naive 7-day persistence",
        "Locked_Window": "N/A",
        **evaluate_predictions(
            y_test,
            p_naive,
        ),
    })

    # Linear.
    cfg = locked[
        "Linear Regression"
    ]
    tr = master[
        master["date"].between(
            cfg["start"],
            cfg["end"],
        )
    ].copy()

    linear_final = Pipeline([
        (
            "preprocessor",
            make_linear_preprocessor(
                numeric_features
            ),
        ),
        (
            "model",
            LinearRegression(),
        ),
    ])

    linear_final.fit(
        tr[linear_features],
        tr[TARGET].to_numpy(
            dtype=float
        ),
    )

    p_linear = linear_final.predict(
        test[linear_features]
    )
    predictions["pred_linear"] = (
        np.clip(
            p_linear,
            0,
            None,
        )
    )

    test_results.append({
        "Model": "Linear Regression",
        "Locked_Window":
            cfg["validation_window"],
        **evaluate_predictions(
            y_test,
            p_linear,
        ),
    })

    # Ridge.
    cfg = locked[
        "Ridge Regression"
    ]
    tr = master[
        master["date"].between(
            cfg["start"],
            cfg["end"],
        )
    ].copy()

    ridge_final = Pipeline([
        (
            "preprocessor",
            make_linear_preprocessor(
                numeric_features
            ),
        ),
        (
            "model",
            Ridge(
                alpha=cfg["alpha"],
                solver="lsqr",
            ),
        ),
    ])

    ridge_final.fit(
        tr[linear_features],
        tr[TARGET].to_numpy(
            dtype=float
        ),
    )

    p_ridge = ridge_final.predict(
        test[linear_features]
    )
    predictions["pred_ridge"] = (
        np.clip(
            p_ridge,
            0,
            None,
        )
    )

    test_results.append({
        "Model": "Ridge Regression",
        "Locked_Window": (
            f"{cfg['validation_window']}, "
            f"alpha={cfg['alpha']:g}"
        ),
        **evaluate_predictions(
            y_test,
            p_ridge,
        ),
    })

    # Random Forest.
    cfg = locked[
        "Random Forest (log-target)"
    ]
    tr = master[
        master["date"].between(
            cfg["start"],
            cfg["end"],
        )
    ].copy()

    rf_final = RandomForestRegressor(
        n_estimators=60,
        max_depth=8,
        min_samples_leaf=5,
        max_features=0.7,
        max_samples=0.8,
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )

    rf_final.fit(
        tr[numeric_features]
        .astype(np.float32),
        np.log1p(
            tr[TARGET].to_numpy(
                dtype=float
            )
        ),
    )

    p_rf = np.expm1(
        rf_final.predict(
            test[numeric_features]
            .astype(np.float32)
        )
    )
    predictions["pred_rf"] = (
        np.clip(
            p_rf,
            0,
            None,
        )
    )

    test_results.append({
        "Model":
            "Random Forest (log-target)",
        "Locked_Window":
            cfg["validation_window"],
        **evaluate_predictions(
            y_test,
            p_rf,
        ),
    })

    test_results = (
        pd.DataFrame(test_results)
        .sort_values(
            ["MAE", "RMSE"]
        )
        .reset_index(drop=True)
    )

    test_naive_mae = float(
        test_results.loc[
            test_results["Model"]
            == "Naive 7-day persistence",
            "MAE",
        ].iloc[0]
    )

    test_results[
        "MAE_vs_Naive_pct"
    ] = (
        (
            test_results["MAE"]
            / test_naive_mae
        )
        - 1
    ) * 100

    test_results.to_csv(
        TABLES_DIR
        / "final_test_model_comparison.csv",
        index=False,
    )
    predictions.to_csv(
        TABLES_DIR
        / "final_test_predictions.csv",
        index=False,
    )

    save_barh(
        test_results.sort_values(
            "MAE",
            ascending=True,
        ),
        "MAE",
        "Model",
        "Final test MAE — locked configurations",
        "Final Test MAE",
        "04_final_test_mae_comparison.png",
    )

    # Statewide aggregate.
    state_daily = (
        predictions.groupby(
            "date",
            as_index=False,
        )
        .agg(
            actual=(
                "actual_target", "sum"
            ),
            naive=("pred_naive", "sum"),
            random_forest=(
                "pred_rf", "sum"
            ),
            ridge=("pred_ridge", "sum"),
            linear=("pred_linear", "sum"),
        )
    )

    state_daily.to_csv(
        TABLES_DIR
        / "statewide_test_predictions_by_date.csv",
        index=False,
    )

    fig, ax = plt.subplots(
        figsize=(12, 6)
    )
    ax.plot(
        state_daily["date"],
        state_daily["actual"],
        label="Actual",
    )
    ax.plot(
        state_daily["date"],
        state_daily["naive"],
        label="Naive",
    )
    ax.plot(
        state_daily["date"],
        state_daily["random_forest"],
        label="Random Forest",
    )
    ax.set_title(
        "Texas aggregate next-7-day cases: "
        "Actual vs predictions"
    )
    ax.set_xlabel(
        "Prediction date"
    )
    ax.set_ylabel(
        "Sum of next-7-day cases "
        "across counties"
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        FIGURES_DIR
        / "05_statewide_actual_vs_prediction.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)

    # RF impurity feature importance.
    rf_importance = (
        pd.DataFrame({
            "feature":
                numeric_features,
            "importance":
                rf_final.feature_importances_,
        })
        .sort_values(
            "importance",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    rf_importance.to_csv(
        TABLES_DIR
        / "random_forest_feature_importance.csv",
        index=False,
    )

    top = (
        rf_importance.head(12)
        .sort_values(
            "importance",
            ascending=True,
        )
    )

    fig, ax = plt.subplots(
        figsize=(9, 6)
    )
    ax.barh(
        top["feature"],
        top["importance"],
    )
    ax.set_xlabel(
        "Feature importance"
    )
    ax.set_ylabel("Feature")
    ax.set_title(
        "Random Forest feature importance — top 12"
    )
    fig.tight_layout()
    fig.savefig(
        FIGURES_DIR
        / "06_rf_impurity_feature_importance.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)

    # Validation permutation importance.
    rf_best_window = locked[
        "Random Forest (log-target)"
    ]["validation_window"]

    rf_validation_best = (
        rf_validation_models[
            rf_best_window
        ]
    )

    permutation_sample_size = min(
        5000,
        len(validation),
    )

    validation_perm = (
        validation.sample(
            n=permutation_sample_size,
            random_state=RANDOM_STATE,
        )
        .reset_index(drop=True)
    )

    x_val_perm = (
        validation_perm[
            numeric_features
        ]
        .astype(np.float32)
        .copy()
    )

    y_val_perm = (
        validation_perm[TARGET]
        .to_numpy(dtype=float)
    )

    baseline_perm_pred = np.expm1(
        rf_validation_best.predict(
            x_val_perm
        )
    )

    baseline_perm_mae = (
        mean_absolute_error(
            y_val_perm,
            baseline_perm_pred,
        )
    )

    rng = np.random.default_rng(
        RANDOM_STATE
    )
    perm_rows = []

    for feature in numeric_features:
        original = (
            x_val_perm[feature]
            .to_numpy(copy=True)
        )
        increases = []

        for _ in range(3):
            shuffled = (
                x_val_perm.copy()
            )
            shuffled[feature] = (
                rng.permutation(
                    original
                )
            )

            pred = np.expm1(
                rf_validation_best.predict(
                    shuffled
                )
            )

            increases.append(
                mean_absolute_error(
                    y_val_perm,
                    pred,
                )
                - baseline_perm_mae
            )

        perm_rows.append({
            "feature": feature,
            "MAE_increase_mean":
                float(
                    np.mean(
                        increases
                    )
                ),
            "MAE_increase_std":
                float(
                    np.std(
                        increases
                    )
                ),
        })

    permutation_importance = (
        pd.DataFrame(
            perm_rows
        )
        .sort_values(
            "MAE_increase_mean",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    permutation_importance.to_csv(
        TABLES_DIR
        / "rf_permutation_importance_validation.csv",
        index=False,
    )

    top_perm = (
        permutation_importance.head(12)
        .sort_values(
            "MAE_increase_mean",
            ascending=True,
        )
    )

    fig, ax = plt.subplots(
        figsize=(9, 6)
    )
    ax.barh(
        top_perm["feature"],
        top_perm["MAE_increase_mean"],
        xerr=top_perm[
            "MAE_increase_std"
        ],
    )
    ax.set_xlabel(
        "Increase in validation MAE "
        "after permutation"
    )
    ax.set_ylabel("Feature")
    ax.set_title(
        "Random Forest permutation importance — Validation"
    )
    fig.tight_layout()
    fig.savefig(
        FIGURES_DIR
        / "07_rf_permutation_importance.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)

    # Ridge coefficients.
    pre = ridge_final.named_steps[
        "preprocessor"
    ]
    feature_names = (
        pre.get_feature_names_out()
    )
    coefficients = (
        ridge_final.named_steps[
            "model"
        ].coef_
    )

    ridge_coefficients = (
        pd.DataFrame({
            "feature": feature_names,
            "coefficient":
                coefficients,
            "abs_coefficient":
                np.abs(
                    coefficients
                ),
        })
        .sort_values(
            "abs_coefficient",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    ridge_coefficients.to_csv(
        TABLES_DIR
        / "ridge_standardized_coefficients.csv",
        index=False,
    )

    # County-level errors.
    county_rows = []

    for county, group in (
        predictions.groupby("county")
    ):
        y = group[
            "actual_target"
        ].to_numpy(dtype=float)

        county_rows.append({
            "county": county,
            "n": len(group),
            "MAE_Naive":
                mean_absolute_error(
                    y,
                    group[
                        "pred_naive"
                    ],
                ),
            "MAE_Linear":
                mean_absolute_error(
                    y,
                    group[
                        "pred_linear"
                    ],
                ),
            "MAE_Ridge":
                mean_absolute_error(
                    y,
                    group[
                        "pred_ridge"
                    ],
                ),
            "MAE_RF":
                mean_absolute_error(
                    y,
                    group["pred_rf"],
                ),
        })

    county_errors = pd.DataFrame(
        county_rows
    )
    county_errors.to_csv(
        TABLES_DIR
        / "county_level_test_errors.csv",
        index=False,
    )

    # Save models.
    joblib.dump(
        linear_final,
        MODELS_DIR
        / "linear_final.joblib",
    )
    joblib.dump(
        ridge_final,
        MODELS_DIR
        / "ridge_final.joblib",
    )
    joblib.dump(
        rf_final,
        MODELS_DIR
        / "random_forest_final.joblib",
    )

    feature_config = {
        "target": TARGET,
        "numeric_features":
            numeric_features,
        "linear_features":
            linear_features,
        "random_state":
            RANDOM_STATE,
    }

    (
        MODELS_DIR
        / "model_feature_config.json"
    ).write_text(
        json.dumps(
            feature_config,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Summary.
    validation_winner = (
        best_by_algorithm
        .sort_values(
            ["MAE", "RMSE"]
        )
        .iloc[0]
    )

    best_ml_test = (
        test_results[
            test_results["Model"]
            != "Naive 7-day persistence"
        ]
        .sort_values(
            ["MAE", "RMSE"]
        )
        .iloc[0]
    )

    serializable_locked = {
        model: {
            key: (
                str(value)
                if isinstance(
                    value,
                    pd.Timestamp,
                )
                else value
            )
            for key, value
            in config.items()
        }
        for model, config
        in locked.items()
    }

    summary = {
        "primary_metric":
            PRIMARY_METRIC,
        "validation_winner":
            validation_winner.to_dict(),
        "best_validation_by_algorithm":
            best_by_algorithm.to_dict(
                "records"
            ),
        "locked_configurations":
            serializable_locked,
        "final_test_results":
            test_results.to_dict(
                "records"
            ),
        "best_ml_final_test":
            best_ml_test.to_dict(),
        "top_rf_impurity_features":
            rf_importance.head(
                10
            ).to_dict("records"),
        "top_rf_permutation_features_validation":
            permutation_importance.head(
                10
            ).to_dict("records"),
    }

    (
        TABLES_DIR
        / "modeling_summary.json"
    ).write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Dashboard data gets the small report tables only.
    dashboard_files = [
        "best_validation_config_by_algorithm.csv",
        "final_test_model_comparison.csv",
        "final_test_predictions.csv",
        "random_forest_feature_importance.csv",
        "rf_permutation_importance_validation.csv",
        "county_level_test_errors.csv",
        "statewide_test_predictions_by_date.csv",
    ]

    for filename in dashboard_files:
        shutil.copy2(
            TABLES_DIR / filename,
            DASHBOARD_DATA_DIR / filename,
        )

    print(
        "[done] model tables ->",
        TABLES_DIR,
    )
    print(
        "[done] report figures ->",
        FIGURES_DIR,
    )
    print(
        "[done] model artifacts ->",
        MODELS_DIR,
    )
    print(
        "[done] dashboard data ->",
        DASHBOARD_DATA_DIR,
    )

    print("\nFINAL TEST")
    print(
        test_results[
            [
                "Model",
                "MAE",
                "RMSE",
                "R2",
                "Peak_MAE",
            ]
        ].to_string(
            index=False
        )
    )

    return {
        "validation_winner":
            str(
                validation_winner[
                    "Model"
                ]
            ),
        "best_ml_test":
            str(
                best_ml_test[
                    "Model"
                ]
            ),
        "tables_dir":
            str(TABLES_DIR),
        "figures_dir":
            str(FIGURES_DIR),
    }


def main() -> None:
    run_training()


if __name__ == "__main__":
    main()
