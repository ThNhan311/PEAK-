from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Texas COVID-19 Forecast Dashboard",
    page_icon="📈",
    layout="wide",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "dashboard_data"


@st.cache_data
def load_data():
    required = {
        "validation":
            "best_validation_config_by_algorithm.csv",
        "test":
            "final_test_model_comparison.csv",
        "predictions":
            "final_test_predictions.csv",
        "rf_impurity":
            "random_forest_feature_importance.csv",
        "rf_permutation":
            "rf_permutation_importance_validation.csv",
        "county_errors":
            "county_level_test_errors.csv",
        "statewide":
            "statewide_test_predictions_by_date.csv",
    }

    missing = [
        filename
        for filename in required.values()
        if not (DATA_DIR / filename).exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing dashboard data: "
            + ", ".join(missing)
            + ". Run: python run_pipeline.py"
        )

    validation = pd.read_csv(
        DATA_DIR / required["validation"]
    )
    test = pd.read_csv(
        DATA_DIR / required["test"]
    )
    predictions = pd.read_csv(
        DATA_DIR / required["predictions"],
        parse_dates=["date"],
    )
    rf_impurity = pd.read_csv(
        DATA_DIR / required["rf_impurity"]
    )
    rf_permutation = pd.read_csv(
        DATA_DIR / required["rf_permutation"]
    )
    county_errors = pd.read_csv(
        DATA_DIR / required["county_errors"]
    )
    statewide = pd.read_csv(
        DATA_DIR / required["statewide"],
        parse_dates=["date"],
    )

    return (
        validation,
        test,
        predictions,
        rf_impurity,
        rf_permutation,
        county_errors,
        statewide,
    )


try:
    (
        validation,
        test,
        predictions,
        rf_impurity,
        rf_permutation,
        county_errors,
        statewide,
    ) = load_data()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()


st.title("Texas COVID-19 — 7-Day Forecast Dashboard")
st.caption(
    "Historical county-level evaluation. "
    "Target: total clean new cases during the next 7 days."
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview",
    "Model comparison",
    "County explorer",
    "Interpretability",
    "Methodology",
])

with tab1:
    best_test = (
        test.sort_values("MAE")
        .iloc[0]
    )

    best_ml = (
        test[
            test["Model"]
            != "Naive 7-day persistence"
        ]
        .sort_values("MAE")
        .iloc[0]
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Best overall",
        best_test["Model"],
    )
    c2.metric(
        "Best overall MAE",
        f"{best_test['MAE']:.2f}",
    )
    c3.metric(
        "Best ML model",
        best_ml["Model"],
    )
    c4.metric(
        "Best ML R²",
        f"{best_ml['R2']:.3f}",
    )

    st.info(
        "The baseline is allowed to win. "
        "A simpler persistence forecast can be stronger "
        "when short-term temporal persistence dominates."
    )

    st.subheader(
        "Statewide aggregate — Final Test"
    )

    fig = go.Figure()

    for column, label in [
        ("actual", "Actual"),
        ("naive", "Naive"),
        ("random_forest", "Random Forest"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=statewide["date"],
                y=statewide[column],
                name=label,
            )
        )

    fig.update_layout(
        xaxis_title="Prediction date",
        yaxis_title=(
            "Sum of next-7-day cases "
            "across counties"
        ),
        hovermode="x unified",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

with tab2:
    st.subheader(
        "Validation — best configuration per algorithm"
    )
    st.dataframe(
        validation,
        use_container_width=True,
        hide_index=True,
    )

    metric = st.selectbox(
        "Metric",
        ["MAE", "RMSE", "R2", "Peak_MAE"],
    )

    val_plot = validation.sort_values(
        metric,
        ascending=(metric != "R2"),
    )

    fig = px.bar(
        val_plot,
        x=metric,
        y="Model",
        orientation="h",
        hover_data=[
            "Window",
            "Hyperparameters",
        ],
        title=f"Validation — {metric}",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.subheader(
        "Final Test — locked configurations"
    )
    st.dataframe(
        test,
        use_container_width=True,
        hide_index=True,
    )

    fig = px.bar(
        test.sort_values("MAE"),
        x="MAE",
        y="Model",
        orientation="h",
        title="Final Test MAE",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

with tab3:
    st.subheader(
        "County-level prediction explorer"
    )

    county = st.selectbox(
        "County",
        sorted(
            predictions["county"]
            .unique()
        ),
    )

    model_map = {
        "Naive": "pred_naive",
        "Random Forest": "pred_rf",
        "Ridge": "pred_ridge",
        "Linear Regression": "pred_linear",
    }

    selected_models = st.multiselect(
        "Prediction series",
        list(model_map.keys()),
        default=[
            "Naive",
            "Random Forest",
        ],
    )

    county_df = (
        predictions[
            predictions["county"]
            == county
        ]
        .sort_values("date")
        .copy()
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=county_df["date"],
            y=county_df["actual_target"],
            name="Actual",
            line=dict(width=3),
        )
    )

    for model_name in selected_models:
        column = model_map[model_name]

        fig.add_trace(
            go.Scatter(
                x=county_df["date"],
                y=county_df[column],
                name=model_name,
            )
        )

    fig.update_layout(
        xaxis_title="Prediction date",
        yaxis_title="Next-7-day cases",
        hovermode="x unified",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    err = county_errors[
        county_errors["county"]
        == county
    ]

    if not err.empty:
        st.subheader("County MAE")
        st.dataframe(
            err,
            use_container_width=True,
            hide_index=True,
        )

with tab4:
    st.subheader(
        "Random Forest interpretability"
    )

    col1, col2 = st.columns(2)

    with col1:
        impurity = (
            rf_impurity.head(12)
            .sort_values("importance")
        )

        fig = px.bar(
            impurity,
            x="importance",
            y="feature",
            orientation="h",
            title=(
                "Impurity-based "
                "feature importance"
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    with col2:
        permutation = (
            rf_permutation.head(12)
            .sort_values(
                "MAE_increase_mean"
            )
        )

        fig = px.bar(
            permutation,
            x="MAE_increase_mean",
            y="feature",
            orientation="h",
            error_x="MAE_increase_std",
            title=(
                "Permutation importance "
                "— validation"
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    st.warning(
        "Feature importance is not a causal effect. "
        "Correlated lag/rolling variables can share importance."
    )

with tab5:
    st.subheader("Pipeline methodology")

    st.markdown(
        """
        **Workflow**

        Data Understanding notebook → automated preprocessing →
        automated model comparison → locked Final Test →
        exported report figures → Streamlit dashboard.

        **Modeling rule**

        Validation selects the training window and Ridge alpha.
        The Final Test is opened only after configuration locking.

        **Scope**

        This dashboard presents historical evaluation results.
        It is not a real-time public-health forecasting service.
        """
    )
