# Current Modeling Snapshot

These files are the current completed outputs bundled with the repository.
Running `python run_pipeline.py` will regenerate them.

## Validation — best configuration per algorithm

| Model | Window | MAE | RMSE | R2 | Peak_MAE |
| --- | --- | --- | --- | --- | --- |
| Naive 7-day persistence | nan | 28.422 | 112.191 | 0.886 | 193.358 |
| Random Forest (log-target) | 2020-2022 | 40.044 | 145.037 | 0.810 | 304.320 |
| Ridge Regression | 2022 | 47.719 | 160.939 | 0.766 | 292.394 |
| Linear Regression | 2021-2022 | 63.626 | 189.977 | 0.675 | 327.105 |

## Final Test — locked configurations

| Model | Locked_Window | MAE | RMSE | R2 | Peak_MAE |
| --- | --- | --- | --- | --- | --- |
| Naive 7-day persistence | nan | 31.046 | 127.250 | 0.850 | 213.624 |
| Random Forest (log-target) | 2020-2022 | 34.377 | 138.005 | 0.824 | 262.354 |
| Ridge Regression | 2022, alpha=40000 | 43.466 | 162.675 | 0.756 | 289.676 |
| Linear Regression | 2021-2022 | 50.069 | 168.172 | 0.739 | 268.496 |

## Top validation permutation importance

| feature | MAE_increase_mean | MAE_increase_std |
| --- | --- | --- |
| cases_roll_mean_7 | 49.157 | 0.241 |
| cases_roll_mean_14 | 43.718 | 0.629 |
| cases_roll_std_14 | 0.752 | 0.402 |
| week_of_year | 0.343 | 0.150 |
| deaths_roll_mean_14 | 0.107 | 0.047 |
| cases_lag_7 | 0.076 | 0.006 |
| current_new_cases | 0.056 | 0.008 |
| deaths_roll_mean_7 | 0.022 | 0.006 |
| is_weekend | 0.016 | 0.015 |
| dow_sin | 0.014 | 0.006 |

## Interpretation note

The persistence baseline is intentionally retained as a valid benchmark.
Random Forest is the strongest machine-learning model in the current snapshot.
Feature importance is descriptive of the fitted model and must not be interpreted
as causal effect.
