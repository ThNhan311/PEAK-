# Texas COVID-19 Analytics Pipeline

Project phân tích dữ liệu COVID-19 cấp county tại Texas, gồm:

- Data Understanding có thể xem trực tiếp bằng notebook.
- Data Preparation chạy tự động.
- Modeling + model comparison chạy tự động.
- Tự động xuất bảng kết quả và ảnh biểu đồ báo cáo.
- Streamlit dashboard dùng các output đã khóa từ Modeling.

## 1. Cấu trúc repository

```text
Texas_COVID_Analytics/
├── README.md
├── requirements.txt
├── run_pipeline.py
├── app.py
│
├── notebooks/
│   └── 01_Data_Understanding_NYT_COVID.ipynb
│
├── src/
│   ├── config.py
│   ├── preprocess.py
│   └── train.py
│
├── data/
│   ├── raw/                # tự tải, không commit CSV
│   └── processed/          # tự sinh, không commit CSV
│
├── models/                 # tự sinh .joblib, không commit
│
├── reports/
│   ├── figures/            # PNG tự sinh
│   └── tables/             # CSV/JSON kết quả
│
├── dashboard_data/         # output nhỏ để Streamlit đọc
│
├── docs/
│   └── PIPELINE.md
│
└── .github/
    └── workflows/
        └── refresh_pipeline.yml
```

## 2. Quy trình sử dụng

### A. Xem Data Understanding

Mở:

```text
notebooks/01_Data_Understanding_NYT_COVID.ipynb
```

Notebook giữ output đã chạy để người xem có thể quan sát EDA, lựa chọn Texas,
phân tích theo năm, correction, coverage và các kết luận trước Modeling.

### B. Chạy toàn bộ pipeline tự động

Cài thư viện:

```bash
pip install -r requirements.txt
```

Sau đó chạy:

```bash
python run_pipeline.py
```

Pipeline sẽ tự:

```text
Download NYT data
→ Preprocess
→ Feature Engineering
→ Temporal Split
→ Train / Compare models
→ Auto-lock bằng Validation
→ Final Test
→ Export CSV/JSON
→ Export PNG charts
→ Update dashboard_data
→ Save trained models
```

Nếu raw data đã có:

```bash
python run_pipeline.py --no-download
```

Nếu chỉ muốn train lại từ `data/processed`:

```bash
python run_pipeline.py --skip-preprocess
```

## 3. Các model được so sánh

- Naive 7-day Persistence baseline
- Linear Regression
- Ridge Regression
- Random Forest Regressor với log-target

Ba training windows được so sánh trên cùng Validation:

- 2022
- 2021–2022
- 2020–2022

Model configuration được khóa từ Validation trước khi đánh giá Final Test.

## 4. Output tự động

### `reports/figures/`

Pipeline xuất ảnh PNG:

- preprocessing extreme flags vs epidemic activity
- temporal split size
- validation MAE comparison
- final-test MAE comparison
- statewide actual vs prediction
- Random Forest impurity importance
- Random Forest permutation importance

Các ảnh này có thể chèn trực tiếp vào báo cáo/slides.

### `reports/tables/`

Chứa:

- validation comparison
- best configuration by algorithm
- final-test comparison
- final-test predictions
- county-level errors
- feature importance
- permutation importance
- modeling summary

### `dashboard_data/`

Chỉ chứa các file nhỏ cần cho Streamlit.
Folder này nên được commit để Streamlit Community Cloud chạy ngay mà không
phải train lại model khi mở app.

## 5. Chạy Streamlit local

Sau khi clone repo:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Dashboard gồm:

- Overview
- Model comparison
- County explorer
- Interpretability
- Methodology

## 6. Upload lên GitHub

Khuyến nghị:

```bash
git init
git add .
git commit -m "Initial Texas COVID analytics pipeline"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

Không upload raw CSV hoặc processed CSV lớn vì `.gitignore` đã loại chúng.

## 7. Chạy pipeline trực tiếp trên GitHub

Repository có GitHub Actions workflow:

```text
Actions → Refresh analytics pipeline → Run workflow
```

Workflow sẽ:

1. cài Python và dependencies;
2. cache raw NYT data;
3. chạy `python run_pipeline.py`;
4. cập nhật `dashboard_data/` và `reports/`;
5. commit các output nhỏ trở lại repository nếu có thay đổi;
6. upload report/model artifacts của lần chạy.

Do workflow chỉ dùng `workflow_dispatch`, pipeline không tự chạy ở mọi commit.

## 8. Deploy Streamlit

Sau khi push lên GitHub:

1. mở Streamlit Community Cloud;
2. kết nối GitHub;
3. chọn repository này;
4. branch `main`;
5. entry point: `app.py`;
6. Deploy.

Mỗi khi `dashboard_data/` được cập nhật và push lên GitHub, Streamlit sẽ dùng
kết quả mới.

## 9. Lưu ý phương pháp

- Không random split cho forecasting.
- Không dùng Final Test để tuning.
- Negative reporting corrections được xử lý causal bằng `clip(lower=0)`.
- Epidemic spikes dương không bị xóa tự động.
- Feature importance không được diễn giải như quan hệ nhân quả.
- Dashboard hiện là historical evaluation dashboard, không phải real-time
  public-health forecasting service.
