# START HERE

## Mục tiêu

Upload **toàn bộ nội dung folder `Texas_COVID_Analytics`** lên một GitHub repository.

## Quy trình chính

```text
1. notebooks/01_Data_Understanding_NYT_COVID.ipynb
   → xem trực tiếp EDA và kết quả Data Understanding

2. python run_pipeline.py
   → tự tải raw data
   → tự preprocess
   → tự train / compare models
   → tự xuất PNG + CSV + model
   → tự cập nhật dashboard_data

3. streamlit run app.py
   → mở interactive dashboard
```

## Những folder KHÔNG cần tự upload dữ liệu lớn

- `data/raw/`: pipeline tự tải NYT data.
- `data/processed/`: pipeline tự sinh.
- `models/`: pipeline tự sinh model `.joblib`.

`.gitignore` đã cấu hình để GitHub không nhận các file lớn này.

## Những output NÊN commit

- `notebooks/01_Data_Understanding_NYT_COVID.ipynb`
- `reports/figures/`
- `reports/tables/`
- `dashboard_data/`
- source code và README

Các output nhỏ đã được đóng gói sẵn để Streamlit chạy ngay sau khi deploy.

## Sau khi upload GitHub

### Chạy lại pipeline trên GitHub

```text
Actions
→ Refresh analytics pipeline
→ Run workflow
```

### Deploy dashboard

```text
Streamlit Community Cloud
→ New app
→ chọn repository
→ branch: main
→ file: app.py
→ Deploy
```
