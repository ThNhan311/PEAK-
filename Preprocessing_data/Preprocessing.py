# =============================================================================
# Module tiền xử lý dữ liệu COVID-19 County-Level
# Pipeline gồm 8 bước:
#   1. Đọc dữ liệu thô
#   2. Làm sạch dữ liệu (Missing Values, Duplicates, Type Casting)
#   3. Xử lý Outliers (IQR per location)
#   4. Trích xuất đặc trưng thời gian (DayOfWeek, Month, Year, WeekOfYear)
#   5. Tạo Lag Features & Rolling Window Features (quan trọng cho Time-Series)
#   6. Chọn lọc Feature (Random Forest Importance + Mutual Information)
#   7. Chia tập Train / Test theo thời gian (temporal split, KHÔNG random)
#   8. Chuẩn hoá features + Lưu kết quả
#
# Bài toán: Dự báo số ca mắc COVID-19 (cases) theo địa điểm (geoid/county/state)
#           cho tương lai để hỗ trợ phân bổ nguồn lực y tế.
# =============================================================================

import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import warnings
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.inspection import permutation_importance

warnings.filterwarnings("ignore")

# =============================================================================
# CẤU HÌNH ĐƯỜNG DẪN
# =============================================================================
BASE_DIR        = Path(__file__).resolve().parent.parent
RAW_DATA_PATH   = BASE_DIR / "Data" / "us-counties.csv"
PROCESSED_PATH  = BASE_DIR / "Data" / "Processed_COVID.csv"
SCALER_PATH     = BASE_DIR / "Models" / "Scaler_COVID.pkl"
PLOT_DIR        = BASE_DIR / "Plots"

# =============================================================================
# CẤU HÌNH XỬ LÝ
# =============================================================================

# Cột nhận dạng địa điểm & thời gian
DATE_COL    = "date"
GEOID_COL   = "geoid"
COUNTY_COL  = "county"
STATE_COL   = "state"

# Cột mục tiêu dự báo
TARGET_COL  = "cases"

# Tất cả cột số liệu gốc
NUMERIC_COLS = ["cases", "cases_avg", "cases_avg_per_100k",
                "deaths", "deaths_avg", "deaths_avg_per_100k"]

# Cột định danh (sẽ được mã hoá hoặc loại sau khi tạo features)
ID_COLS = [DATE_COL, GEOID_COL, COUNTY_COL, STATE_COL]

# Lag (ngày trước) cần tạo cho TARGET — quan trọng cho time-series
LAG_DAYS = [1, 2, 3, 7, 14]

# Rolling windows (ngày) để tính rolling mean / std
ROLLING_WINDOWS = [7, 14]

# IQR multiplier để phát hiện outlier (mỗi nhóm địa điểm riêng)
IQR_FACTOR = 3.0        # Dùng 3.0 thay vì 1.5 vì COVID có spike hợp lệ

# Tỷ lệ temporal split: 80% train / 20% test (theo thứ tự thời gian)
TEST_RATIO = 0.20

# Số features hiển thị trong biểu đồ feature importance
TOP_N_FEATURES = 15

# Random state
RANDOM_STATE = 42


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _banner(text: str, width: int = 65) -> None:
    print()
    print("=" * width)
    print(f"   {text}")
    print("=" * width)


def _step(step_num: int, text: str) -> None:
    print(f"\n[Bước {step_num}] {text}...")


def _ok(msg: str) -> None:
    print(f"         ✔ {msg}")


def _warn(msg: str) -> None:
    print(f"         ⚠ {msg}")


def _validate_no_missing(df: pd.DataFrame, step_name: str,
                          columns: list = None) -> None:
    subset = df[columns] if columns else df
    n_missing = int(subset.isnull().sum().sum())
    if n_missing > 0:
        bad = subset.isnull().sum()
        bad = bad[bad > 0].to_dict()
        raise ValueError(
            f"[Kiểm tra sau '{step_name}'] Còn {n_missing} missing!\n"
            f"Chi tiết: {bad}"
        )
    _ok(f"Kiểm tra Missing sau '{step_name}': OK (0 missing)")


def _print_summary(df: pd.DataFrame, label: str = "DATASET SUMMARY") -> None:
    print("\n" + "─" * 40)
    print(f" {label}")
    print("─" * 40)
    print(f" Rows      : {len(df):,}")
    print(f" Columns   : {df.shape[1]}")
    print(f" Missing   : {df.isnull().sum().sum():,}")
    print(f" Duplicates: {df.duplicated().sum():,}")
    print(f" Date range: {df[DATE_COL].min()} → {df[DATE_COL].max()}"
          if DATE_COL in df.columns else "")
    print(f" Locations : {df[GEOID_COL].nunique():,} geoid"
          if GEOID_COL in df.columns else "")
    print("─" * 40)


# =============================================================================
# BƯỚC 1: ĐỌC DỮ LIỆU THÔ
# =============================================================================

def load_raw_data(filepath: Path = RAW_DATA_PATH) -> pd.DataFrame:
    _step(1, "Đọc dữ liệu thô")

    if not filepath.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file: {filepath}\n"
            "Hãy đặt file CSV vào thư mục Data/"
        )

    df = pd.read_csv(filepath, low_memory=False)
    _ok(f"Đọc thành công: {df.shape[0]:,} dòng × {df.shape[1]} cột")
    _ok(f"Cột có sẵn: {list(df.columns)}")

    # Parse cột date
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    _ok(f"Đã parse '{DATE_COL}' thành datetime")

    _print_summary(df, "DỮ LIỆU THÔ")
    return df


# =============================================================================
# BƯỚC 2: LÀM SẠCH DỮ LIỆU
# =============================================================================

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    _step(2, "Làm sạch dữ liệu")

    # [2.1] Bỏ cột Unnamed
    unnamed = [c for c in df.columns if "Unnamed" in str(c)]
    if unnamed:
        df = df.drop(columns=unnamed)
        _ok(f"[2.1] Đã bỏ {len(unnamed)} cột Unnamed: {unnamed}")

    # [2.2] Bỏ dòng không có date hoặc geoid (không xác định được địa điểm & thời gian)
    n_before = len(df)
    df = df.dropna(subset=[DATE_COL, GEOID_COL])
    _ok(f"[2.2] Bỏ {n_before - len(df):,} dòng thiếu date/geoid "
        f"(Còn {len(df):,} dòng)")

    # [2.3] Loại duplicate (cùng date + geoid)
    n_before = len(df)
    df = df.drop_duplicates(subset=[DATE_COL, GEOID_COL], keep="first")
    _ok(f"[2.3] Bỏ {n_before - len(df):,} dòng duplicate date+geoid "
        f"(Còn {len(df):,} dòng)")

    # [2.4] Ép kiểu numeric cho các cột số liệu
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    _ok(f"[2.4] Ép kiểu numeric cho: {NUMERIC_COLS}")

    # [2.5] Các giá trị âm trong cases/deaths là vô lý → thay bằng 0
    #       (có thể xảy ra do điều chỉnh báo cáo hồi tố)
    negative_cols = ["cases", "cases_avg", "deaths", "deaths_avg"]
    total_clipped = 0
    for col in negative_cols:
        if col in df.columns:
            n_neg = int((df[col] < 0).sum())
            df[col] = df[col].clip(lower=0)
            total_clipped += n_neg
    _ok(f"[2.5] Clip {total_clipped:,} giá trị âm về 0 trong các cột cases/deaths")

    # [2.6] Điền Missing Values cho các cột số
    #       → Điền 0 cho cases/deaths (không có báo cáo = 0 ca)
    #       → Điền forward-fill theo địa điểm cho các cột _avg và _per_100k
    zero_fill_cols = ["cases", "deaths"]
    ffill_cols = ["cases_avg", "cases_avg_per_100k",
                  "deaths_avg", "deaths_avg_per_100k"]

    filled_zero = 0
    for col in zero_fill_cols:
        if col in df.columns:
            n = int(df[col].isnull().sum())
            df[col] = df[col].fillna(0)
            filled_zero += n
    _ok(f"[2.6a] Điền {filled_zero:,} NaN bằng 0 cho cột cases/deaths")

    df = df.sort_values([GEOID_COL, DATE_COL]).reset_index(drop=True)
    filled_ffill = 0
    for col in ffill_cols:
        if col in df.columns:
            n = int(df[col].isnull().sum())
            df[col] = df[col].groupby(df[GEOID_COL]).transform(
                lambda x: x.ffill().bfill()
            )
            # Nếu vẫn còn NaN (location chỉ có 1 dòng) → điền median toàn cục
            remaining = int(df[col].isnull().sum())
            if remaining > 0:
                df[col] = df[col].fillna(df[col].median())
            filled_ffill += n
    _ok(f"[2.6b] Forward-fill {filled_ffill:,} NaN cho cột _avg và _per_100k")

    # [2.7] Điền county/state còn thiếu bằng mode theo geoid
    for col in [COUNTY_COL, STATE_COL]:
        if col in df.columns and df[col].isnull().any():
            mode_map = (df.groupby(GEOID_COL)[col]
                        .agg(lambda x: x.mode()[0] if not x.mode().empty else "Unknown"))
            df[col] = df[col].fillna(df[GEOID_COL].map(mode_map))
            df[col] = df[col].fillna("Unknown")
    _ok(f"[2.7] Điền county/state còn thiếu bằng mode theo geoid")

    df = df.reset_index(drop=True)
    _print_summary(df, "SAU LÀM SẠCH")
    return df


# =============================================================================
# BƯỚC 3: XỬ LÝ OUTLIER (IQR PER LOCATION)
# =============================================================================

def handle_outliers(df: pd.DataFrame) -> pd.DataFrame:
    _step(3, f"Xử lý Outlier (IQR × {IQR_FACTOR} theo từng địa điểm)")

    # Với bộ dữ liệu COVID, outlier thường là spike thật (đợt dịch bùng phát)
    # → Không xóa mà CAP (winsorize) bằng upper bound của IQR theo từng địa điểm
    # → Chỉ cap cột cases và deaths, giữ nguyên các cột _avg (đã là giá trị smooth)

    cap_cols = ["cases", "deaths"]
    total_capped = 0

    for col in cap_cols:
        if col not in df.columns:
            continue

        def cap_group(group):
            Q1 = group.quantile(0.25)
            Q3 = group.quantile(0.75)
            IQR = Q3 - Q1
            upper = Q3 + IQR_FACTOR * IQR
            # Chỉ cap upper (không cap lower vì đã clip 0 ở bước trước)
            return group.clip(upper=upper)

        before_sum = df[col].sum()
        df[col] = df.groupby(GEOID_COL)[col].transform(cap_group)
        after_sum = df[col].sum()
        n_capped = int((df[col] < before_sum).sum())  # ước lượng
        total_capped += abs(int(before_sum - after_sum))

    _ok(f"Đã winsorize (cap upper IQR×{IQR_FACTOR}) cho cột: {cap_cols}")
    _ok(f"Tổng giá trị được điều chỉnh (delta): {total_capped:,.0f}")

    return df


# =============================================================================
# BƯỚC 4: TRÍCH XUẤT ĐẶC TRƯNG THỜI GIAN
# =============================================================================

def extract_time_features(df: pd.DataFrame) -> pd.DataFrame:
    _step(4, "Trích xuất đặc trưng thời gian")

    df["year"]        = df[DATE_COL].dt.year
    df["month"]       = df[DATE_COL].dt.month
    df["day"]         = df[DATE_COL].dt.day
    df["dayofweek"]   = df[DATE_COL].dt.dayofweek      # 0=Mon, 6=Sun
    df["weekofyear"]  = df[DATE_COL].dt.isocalendar().week.astype(int)
    df["quarter"]     = df[DATE_COL].dt.quarter
    df["is_weekend"]  = (df["dayofweek"] >= 5).astype(int)

    # Mã hoá tuần hoàn (sin/cos) để capture tính chu kỳ tuần/năm
    df["month_sin"]   = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"]   = np.cos(2 * np.pi * df["month"] / 12)
    df["dow_sin"]     = np.sin(2 * np.pi * df["dayofweek"] / 7)
    df["dow_cos"]     = np.cos(2 * np.pi * df["dayofweek"] / 7)

    time_cols_created = ["year", "month", "day", "dayofweek", "weekofyear",
                         "quarter", "is_weekend",
                         "month_sin", "month_cos", "dow_sin", "dow_cos"]
    _ok(f"Đã tạo {len(time_cols_created)} đặc trưng thời gian: {time_cols_created}")

    _validate_no_missing(df, "Bước 4 - Time Features",
                         columns=time_cols_created)
    return df


# =============================================================================
# BƯỚC 5: TẠO LAG FEATURES & ROLLING WINDOW FEATURES
# =============================================================================

def create_lag_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    _step(5, "Tạo Lag Features & Rolling Window Features")

    # Sắp xếp theo địa điểm và thời gian trước khi shift
    df = df.sort_values([GEOID_COL, DATE_COL]).reset_index(drop=True)

    # --- Lag Features ---
    lag_cols_created = []
    for lag in LAG_DAYS:
        col_name = f"cases_lag_{lag}"
        df[col_name] = df.groupby(GEOID_COL)[TARGET_COL].shift(lag)
        lag_cols_created.append(col_name)
    _ok(f"Tạo lag features: {lag_cols_created}")

    # --- Rolling Mean và Std ---
    rolling_cols_created = []
    for window in ROLLING_WINDOWS:
        mean_col = f"cases_roll_mean_{window}"
        std_col  = f"cases_roll_std_{window}"
        df[mean_col] = (df.groupby(GEOID_COL)[TARGET_COL]
                        .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean()))
        df[std_col]  = (df.groupby(GEOID_COL)[TARGET_COL]
                        .transform(lambda x: x.shift(1).rolling(window, min_periods=1).std().fillna(0)))
        rolling_cols_created += [mean_col, std_col]
    _ok(f"Tạo rolling features: {rolling_cols_created}")

    # --- Trend Feature: hiệu số cases hôm nay - lag_7 ---
    if "cases_lag_7" in df.columns:
        df["cases_trend_7"] = df[TARGET_COL] - df["cases_lag_7"]
        _ok("Tạo feature cases_trend_7 (cases - lag_7)")

    # Bỏ dòng NaN do lag tạo ra (các dòng đầu mỗi địa điểm)
    lag_cols_all = lag_cols_created + rolling_cols_created + ["cases_trend_7"]
    n_before = len(df)
    df = df.dropna(subset=[c for c in lag_cols_all if c in df.columns])
    _ok(f"Bỏ {n_before - len(df):,} dòng NaN do lag (head của mỗi location) "
        f"→ Còn {len(df):,} dòng")

    _validate_no_missing(df, "Bước 5 - Lag & Rolling Features",
                         columns=[c for c in lag_cols_all if c in df.columns])
    return df


# =============================================================================
# BƯỚC 6: PHÂN TÍCH & CHỌN LỌC FEATURE
# =============================================================================

def analyze_and_select_features(df: pd.DataFrame,
                                 plot: bool = True) -> tuple:
    """
    Sử dụng 3 phương pháp để đánh giá tầm quan trọng của features:
      1. Pearson Correlation với target
      2. Mutual Information (bắt được phi tuyến)
      3. Random Forest Feature Importance

    Returns:
        (selected_feature_names, importance_df)
    """
    _step(6, "Phân tích & Chọn lọc Feature")

    # Xác định feature columns (loại bỏ ID và target)
    exclude_from_features = [DATE_COL, GEOID_COL, COUNTY_COL, STATE_COL]
    feature_cols = [c for c in df.columns
                    if c not in exclude_from_features
                    and c != TARGET_COL
                    and df[c].dtype != object]

    X = df[feature_cols].copy()
    y = df[TARGET_COL].copy()

    _ok(f"Số features để phân tích: {len(feature_cols)}")
    _ok(f"Features: {feature_cols}")

    # ── Phương pháp 1: Pearson Correlation ───────────────────────────────
    corr = X.corrwith(y).abs().sort_values(ascending=False)
    _ok(f"[M1] Pearson Correlation — Top 5: {dict(corr.head(5).round(3))}")

    # ── Phương pháp 2: Mutual Information ────────────────────────────────
    # Sample để tăng tốc với dataset lớn
    sample_size = min(100_000, len(X))
    idx = np.random.RandomState(RANDOM_STATE).choice(len(X), sample_size, replace=False)
    X_sample = X.iloc[idx]
    y_sample = y.iloc[idx]

    mi_scores = mutual_info_regression(X_sample, y_sample,
                                        random_state=RANDOM_STATE)
    mi_series = pd.Series(mi_scores, index=feature_cols).sort_values(ascending=False)
    _ok(f"[M2] Mutual Information — Top 5: {dict(mi_series.head(5).round(3))}")

    # ── Phương pháp 3: Random Forest Importance ───────────────────────────
    rf = RandomForestRegressor(n_estimators=100, max_depth=8,
                                n_jobs=-1, random_state=RANDOM_STATE)
    rf.fit(X_sample, y_sample)
    rf_imp = pd.Series(rf.feature_importances_,
                        index=feature_cols).sort_values(ascending=False)
    _ok(f"[M3] Random Forest Importance — Top 5: {dict(rf_imp.head(5).round(3))}")

    # ── Tổng hợp: chuẩn hoá mỗi phương pháp về [0,1] rồi lấy trung bình ──
    def normalize(s: pd.Series) -> pd.Series:
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else s

    importance_df = pd.DataFrame({
        "Pearson_Corr":    normalize(corr),
        "Mutual_Info":     normalize(mi_series),
        "RF_Importance":   normalize(rf_imp),
    }).fillna(0)
    importance_df["Combined_Score"] = importance_df.mean(axis=1)
    importance_df = importance_df.sort_values("Combined_Score", ascending=False)

    _ok(f"Top {TOP_N_FEATURES} features theo điểm tổng hợp:")
    print(importance_df.head(TOP_N_FEATURES).round(3).to_string())

    # ── Visualisation ─────────────────────────────────────────────────────
    if plot:
        _visualize_feature_importance(df, importance_df, corr, mi_series, rf_imp)

    # ── Chọn features: lấy tất cả features có Combined_Score > 0.1 ────────
    selected = importance_df[importance_df["Combined_Score"] > 0.1].index.tolist()
    if len(selected) < 5:                    # đảm bảo ít nhất 5 features
        selected = importance_df.head(5).index.tolist()

    _ok(f"Features được chọn ({len(selected)}): {selected}")
    return selected, importance_df


def _visualize_feature_importance(df, importance_df, corr, mi_series, rf_imp):
    """
    Tách thành 7 hàm vẽ riêng, mỗi hàm lưu 1 file ảnh độc lập:
      plot1_pearson_correlation.png
      plot2_mutual_information.png
      plot3_random_forest_importance.png
      plot4_combined_score.png
      plot5_correlation_heatmap.png
      plot6_cases_trend.png
      plot7_cases_distribution.png
    """
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    top_n = min(TOP_N_FEATURES, len(importance_df))

    _plot1_pearson_correlation(corr, top_n)
    _plot2_mutual_information(mi_series, top_n)
    _plot3_random_forest_importance(rf_imp, top_n)
    _plot4_combined_score(importance_df, top_n)
    _plot5_correlation_heatmap(df, importance_df, top_n)
    _plot6_cases_trend(df)
    _plot7_cases_distribution(df)


# ── Plot 1: Pearson Correlation ───────────────────────────────────────────────
def _plot1_pearson_correlation(corr: pd.Series, top_n: int) -> None:
    top_corr = corr.head(top_n)
    fig, ax = plt.subplots(figsize=(10, 7))

    bars = ax.barh(top_corr.index[::-1], top_corr.values[::-1],
                   color=sns.color_palette("Greens_r", top_n))
    ax.set_title("① Pearson Correlation với Cases",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("|Correlation|", fontsize=11)
    ax.set_ylabel("Feature", fontsize=11)
    ax.axvline(0.3, color="red", linestyle="--", alpha=0.7, label="Ngưỡng 0.3")
    ax.legend(fontsize=9)

    for bar, val in zip(bars, top_corr.values[::-1]):
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9)

    ax.set_xlim(0, top_corr.max() * 1.15)
    fig.tight_layout()
    path = PLOT_DIR / "plot1_pearson_correlation.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _ok(f"Đã lưu → {path}")


# ── Plot 2: Mutual Information ────────────────────────────────────────────────
def _plot2_mutual_information(mi_series: pd.Series, top_n: int) -> None:
    top_mi = mi_series.head(top_n)
    fig, ax = plt.subplots(figsize=(10, 7))

    bars = ax.barh(top_mi.index[::-1], top_mi.values[::-1],
                   color=sns.color_palette("Oranges_r", top_n))
    ax.set_title("② Mutual Information Score",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("MI Score", fontsize=11)
    ax.set_ylabel("Feature", fontsize=11)

    for bar, val in zip(bars, top_mi.values[::-1]):
        ax.text(bar.get_width() + top_mi.max() * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9)

    ax.set_xlim(0, top_mi.max() * 1.15)
    fig.tight_layout()
    path = PLOT_DIR / "plot2_mutual_information.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _ok(f"Đã lưu → {path}")


# ── Plot 3: Random Forest Importance ─────────────────────────────────────────
def _plot3_random_forest_importance(rf_imp: pd.Series, top_n: int) -> None:
    top_rf = rf_imp.head(top_n)
    fig, ax = plt.subplots(figsize=(10, 7))

    bars = ax.barh(top_rf.index[::-1], top_rf.values[::-1],
                   color=sns.color_palette("Purples_r", top_n))
    ax.set_title("③ Random Forest Feature Importance",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Importance", fontsize=11)
    ax.set_ylabel("Feature", fontsize=11)

    for bar, val in zip(bars, top_rf.values[::-1]):
        ax.text(bar.get_width() + top_rf.max() * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9)

    ax.set_xlim(0, top_rf.max() * 1.15)
    fig.tight_layout()
    path = PLOT_DIR / "plot3_random_forest_importance.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _ok(f"Đã lưu → {path}")


# ── Plot 4: Combined Score ────────────────────────────────────────────────────
def _plot4_combined_score(importance_df: pd.DataFrame, top_n: int) -> None:
    top_combined = importance_df["Combined_Score"].head(top_n)
    colors = ["#e74c3c" if v >= 0.5 else "#3498db" if v >= 0.2
              else "#95a5a6" for v in top_combined.values[::-1]]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(top_combined.index[::-1], top_combined.values[::-1],
                   color=colors)
    ax.set_title("④ Combined Score (Trung bình 3 phương pháp)",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Combined Score (0–1)", fontsize=11)
    ax.set_ylabel("Feature", fontsize=11)
    ax.axvline(0.1, color="red", linestyle="--", alpha=0.7, label="Ngưỡng chọn (0.1)")

    for bar, val in zip(bars, top_combined.values[::-1]):
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9)

    legend_els = [
        mpatches.Patch(color="#e74c3c", label="Rất quan trọng (≥ 0.5)"),
        mpatches.Patch(color="#3498db", label="Quan trọng (≥ 0.2)"),
        mpatches.Patch(color="#95a5a6", label="Ít quan trọng (< 0.2)"),
    ]
    ax.legend(handles=legend_els, fontsize=9, loc="lower right")
    ax.set_xlim(0, max(top_combined.max() * 1.15, 0.2))

    fig.tight_layout()
    path = PLOT_DIR / "plot4_combined_score.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _ok(f"Đã lưu → {path}")


# ── Plot 5: Correlation Heatmap ───────────────────────────────────────────────
def _plot5_correlation_heatmap(df: pd.DataFrame,
                                importance_df: pd.DataFrame,
                                top_n: int) -> None:
    top_feat_names = importance_df.head(min(12, top_n)).index.tolist()
    heatmap_cols   = top_feat_names + [TARGET_COL]
    corr_matrix    = df[heatmap_cols].corr()

    mask = np.zeros_like(corr_matrix, dtype=bool)
    mask[np.triu_indices_from(mask, k=1)] = True   # ẩn tam giác trên

    n = len(heatmap_cols)
    fig, ax = plt.subplots(figsize=(max(10, n * 0.9), max(8, n * 0.8)))
    sns.heatmap(corr_matrix, ax=ax, mask=mask,
                cmap="RdYlGn", center=0, annot=True, fmt=".2f",
                annot_kws={"size": 8}, linewidths=0.5,
                cbar_kws={"shrink": 0.7})
    ax.set_title("⑤ Correlation Heatmap (Top Features + Target)",
                 fontsize=14, fontweight="bold", pad=15)
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    ax.tick_params(axis="y", rotation=0,  labelsize=9)

    fig.tight_layout()
    path = PLOT_DIR / "plot5_correlation_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _ok(f"Đã lưu → {path}")


# ── Plot 6: Xu hướng ca mắc theo thời gian ───────────────────────────────────
def _plot6_cases_trend(df: pd.DataFrame) -> None:
    daily_total = (df.groupby(DATE_COL)[TARGET_COL].sum()
                     .reset_index().sort_values(DATE_COL))

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(daily_total[DATE_COL], daily_total[TARGET_COL],
            linewidth=0.9, color="#2c82c9", alpha=0.9)
    ax.fill_between(daily_total[DATE_COL], daily_total[TARGET_COL],
                    alpha=0.25, color="#2c82c9")
    ax.set_title("⑥ Tổng số ca mắc theo ngày (toàn quốc)",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Ngày", fontsize=11)
    ax.set_ylabel("Tổng cases", fontsize=11)
    ax.tick_params(axis="x", rotation=30)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{int(x):,}")
    )

    fig.tight_layout()
    path = PLOT_DIR / "plot6_cases_trend.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _ok(f"Đã lưu → {path}")


# ── Plot 7: Phân phối cases (histogram log-scale) ────────────────────────────
def _plot7_cases_distribution(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(np.log1p(df[TARGET_COL]), bins=60,
            color="#e67e22", edgecolor="white", alpha=0.85)
    ax.set_title("⑦ Phân phối log(cases + 1)",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("log(cases + 1)", fontsize=11)
    ax.set_ylabel("Tần suất", fontsize=11)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{int(x):,}")
    )

    fig.tight_layout()
    path = PLOT_DIR / "plot7_cases_distribution.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _ok(f"Đã lưu → {path}")


# =============================================================================
# BƯỚC 7: CHIA TRAIN / TEST THEO THỜI GIAN (TEMPORAL SPLIT)
# =============================================================================

def split_data_temporal(df: pd.DataFrame,
                         selected_features: list,
                         test_ratio: float = TEST_RATIO) -> tuple:
    _step(7, f"Chia Train/Test theo thời gian ({int((1-test_ratio)*100)}/{int(test_ratio*100)})")

    # !! QUAN TRỌNG: Với time-series, KHÔNG dùng random split
    # → Dùng cutoff ngày: train = trước, test = sau
    dates_sorted = df[DATE_COL].sort_values().unique()
    cutoff_idx   = int(len(dates_sorted) * (1 - test_ratio))
    cutoff_date  = dates_sorted[cutoff_idx]

    train_df = df[df[DATE_COL] <  cutoff_date]
    test_df  = df[df[DATE_COL] >= cutoff_date]

    _ok(f"Cutoff date   : {cutoff_date}")
    _ok(f"Tập Train     : {len(train_df):,} mẫu "
        f"({train_df[DATE_COL].min()} → {train_df[DATE_COL].max()})")
    _ok(f"Tập Test      : {len(test_df):,} mẫu "
        f"({test_df[DATE_COL].min()} → {test_df[DATE_COL].max()})")

    X_train = train_df[selected_features].reset_index(drop=True)
    X_test  = test_df[selected_features].reset_index(drop=True)
    y_train = train_df[TARGET_COL].reset_index(drop=True)
    y_test  = test_df[TARGET_COL].reset_index(drop=True)

    assert len(X_train) == len(y_train), "Lỗi: X_train và y_train khác size!"
    assert len(X_test)  == len(y_test),  "Lỗi: X_test  và y_test  khác size!"
    assert X_train.shape[1] == X_test.shape[1], "Lỗi: Features train/test khác nhau!"
    _ok("Kiểm tra Train/Test: OK")

    return X_train, X_test, y_train, y_test, cutoff_date


# =============================================================================
# BƯỚC 8: CHUẨN HOÁ + LƯU KẾT QUẢ
# =============================================================================

def scale_and_save(X_train: pd.DataFrame, X_test: pd.DataFrame,
                   df_processed: pd.DataFrame,
                   fit: bool = True) -> tuple:
    _step(8, "Chuẩn hoá features (StandardScaler) & Lưu kết quả")

    SCALER_PATH.parent.mkdir(parents=True, exist_ok=True)

    if fit:
        scaler = StandardScaler()
        X_train_scaled_arr = scaler.fit_transform(X_train)
        X_test_scaled_arr  = scaler.transform(X_test)
        joblib.dump(scaler, SCALER_PATH)
        _ok(f"Fit StandardScaler trên tập Train, lưu → {SCALER_PATH}")
    else:
        if not SCALER_PATH.exists():
            raise FileNotFoundError(f"Không tìm thấy Scaler tại: {SCALER_PATH}")
        scaler = joblib.load(SCALER_PATH)
        X_train_scaled_arr = scaler.transform(X_train)
        X_test_scaled_arr  = scaler.transform(X_test)
        _ok(f"Load Scaler từ: {SCALER_PATH}")

    X_train_scaled = pd.DataFrame(X_train_scaled_arr,
                                   columns=X_train.columns,
                                   index=X_train.index)
    X_test_scaled  = pd.DataFrame(X_test_scaled_arr,
                                   columns=X_test.columns,
                                   index=X_test.index)
    _ok(f"Chuẩn hoá xong: {X_train_scaled.shape[1]} features")

    # Lưu processed data
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_processed.to_csv(PROCESSED_PATH, index=False)
    _ok(f"Lưu Processed_COVID.csv → {PROCESSED_PATH} "
        f"({df_processed.shape[0]:,} dòng × {df_processed.shape[1]} cột)")

    return X_train_scaled, X_test_scaled, scaler


# =============================================================================
# PIPELINE CHÍNH
# =============================================================================

def run_preprocessing_pipeline(
    raw_path: Path = RAW_DATA_PATH,
    save: bool = True,
    fit_scaler: bool = True,
    plot: bool = True,
) -> dict:
    """
    Chạy toàn bộ pipeline tiền xử lý COVID-19 (8 bước).

    Returns:
        dict với các key:
        ┌─────────────────────┬──────────────────────────────────────────────┐
        │ Key                 │ Nội dung                                     │
        ├─────────────────────┼──────────────────────────────────────────────┤
        │ X_train_scaled      │ Features train đã chuẩn hoá                  │
        │ X_test_scaled       │ Features test đã chuẩn hoá                   │
        │ X_train_raw         │ Features train chưa chuẩn hoá                │
        │ X_test_raw          │ Features test chưa chuẩn hoá                 │
        │ y_train             │ Target train (cases)                          │
        │ y_test              │ Target test  (cases)                          │
        │ scaler              │ StandardScaler đã fit                        │
        │ feature_names       │ Danh sách features được chọn                 │
        │ importance_df       │ DataFrame tầm quan trọng từng feature         │
        │ df_processed        │ Toàn bộ dữ liệu sau xử lý                   │
        │ cutoff_date         │ Ngày phân chia train/test                    │
        └─────────────────────┴──────────────────────────────────────────────┘
    """
    _banner("PIPELINE TIỀN XỬ LÝ DỮ LIỆU — COVID-19 FORECASTING")

    df = load_raw_data(raw_path)
    df = clean_data(df)
    df = handle_outliers(df)
    df = extract_time_features(df)
    df = create_lag_rolling_features(df)

    selected_features, importance_df = analyze_and_select_features(df, plot=plot)

    X_train_raw, X_test_raw, y_train, y_test, cutoff_date = split_data_temporal(
        df, selected_features
    )

    df_processed = df.copy()

    X_train_scaled, X_test_scaled, scaler = scale_and_save(
        X_train_raw, X_test_raw, df_processed if save else df_processed,
        fit=fit_scaler
    )

    # ── Tổng kết ────────────────────────────────────────────────────────
    _banner("TỔNG KẾT PIPELINE")
    print(f" Dataset gốc          : đã xử lý → {len(df_processed):,} dòng")
    print(f" Features được chọn   : {len(selected_features)}")
    print(f" Train size           : {len(X_train_raw):,} mẫu")
    print(f" Test  size           : {len(X_test_raw):,} mẫu")
    print(f" Cutoff date          : {cutoff_date}")
    print(f" Target (y) — median  : {y_train.median():.1f} ca/ngày/địa điểm")

    return {
        "X_train_scaled":  X_train_scaled,
        "X_test_scaled":   X_test_scaled,
        "X_train_raw":     X_train_raw,
        "X_test_raw":      X_test_raw,
        "y_train":         y_train,
        "y_test":          y_test,
        "scaler":          scaler,
        "feature_names":   selected_features,
        "importance_df":   importance_df,
        "df_processed":    df_processed,
        "cutoff_date":     cutoff_date,
    }


# =============================================================================
# CHẠY TRỰC TIẾP
# =============================================================================

if __name__ == "__main__":
    result = run_preprocessing_pipeline(save=True, plot=True)

    print("\n--- KIỂM TRA KẾT QUẢ ---")
    print(f"X_train_scaled  : {result['X_train_scaled'].shape}")
    print(f"X_test_scaled   : {result['X_test_scaled'].shape}")
    print(f"y_train         : {result['y_train'].shape} | "
          f"mean={result['y_train'].mean():.2f}")
    print(f"y_test          : {result['y_test'].shape}  | "
          f"mean={result['y_test'].mean():.2f}")
    print(f"feature_names   : {result['feature_names']}")
    print(f"cutoff_date     : {result['cutoff_date']}")
    print(f"\nTop 10 features:")
    print(result["importance_df"]["Combined_Score"].head(10).round(3).to_string())