from pathlib import Path
import pandas as pd

# Doc du lieu, giu so 0 o dau ma FIPS

ROOT = Path(__file__).resolve().parent.parent
file_path = ROOT / "data" / "raw" / "us-states.csv"

df = pd.read_csv(
    file_path,
    dtype={
        "state": "string",
        "fips": "string"
    },
    parse_dates=["date"]
)

# Xem 5 dong dau
print("=== 5 DONG DAU ===")
print(df.head())

# Xem so dong, cot, kieu du lieu va gia tri khong thieu
print("\n=== THONG TIN DU LIEU ===")
df.info()

# Thong ke mo ta cac cot so
print("\n=== THONG KE MO TA ===")
print(df.describe())

# Kiem tra du lieu thieu
print("\n=== SO GIA TRI THIEU ===")
print(df.isna().sum())

# Kiem tra trung bang trong cung ngay
print("\n=== SO DONG TRUNG THEO NGAY VA BANG ===")
print(df.duplicated(subset=["date", "state"]).sum())

# Lay ngay cuoi cung cua toan bo du lieu
last_date = df["date"].max()
latest = df.loc[df["date"].eq(last_date)].copy()

# Tim bang co so ca mac luy ke cao nhat, giu ca truong hop dong hang
max_cases = latest["cases"].max()
top_states = latest.loc[
    latest["cases"].eq(max_cases),
    ["state", "cases", "deaths"]
]

print(f"\n=== NGAY CUOI CUNG: {last_date:%Y-%m-%d} ===")
print("Bang co so ca mac luy ke cao nhat:")
print(top_states.to_string(index=False))

# Xem 10 bang dung dau de chuan bi ve bieu do
print("\n=== TOP 10 BANG ===")
print(
    latest.nlargest(10, "cases")[["state", "cases", "deaths"]]
    .to_string(index=False)
)