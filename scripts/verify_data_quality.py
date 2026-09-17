import pandas as pd

# 1. DOC DU LIEU
df = pd.read_csv(
    "us-counties.csv",
    dtype={
        "state": "string",
        "county": "string",
        "fips": "string"
    }
)

# Chuan hoa khoang trang, chuyen chuoi rong thanh gia tri thieu
for col in ["state", "county", "fips"]:
    df[col] = df[col].str.strip().replace("", pd.NA)

df["date"] = pd.to_datetime(df["date"], errors="raise")

for col in ["cases", "deaths"]:
    df[col] = pd.to_numeric(df[col], errors="raise")

print("Tong so dong:", len(df))

# 2. KIEM TRA MISSING VALUES
missing_summary = pd.DataFrame({
    "So dong thieu": df.isna().sum(),
    "Ty le (%)": (df.isna().mean() * 100).round(2)
})

print("\n=== MISSING VALUES ===")
print(missing_summary)

missing_fips = df["fips"].isna()
unknown_county = df["county"].str.casefold().eq("unknown").fillna(False)

print("\n=== COUNTY UNKNOWN VA FIPS THIEU ===")
print(pd.crosstab(
    unknown_county.rename("County la Unknown"),
    missing_fips.rename("FIPS bi thieu"),
    dropna=False
))

print("\nVi du cac dong thieu FIPS:")
print(
    df.loc[missing_fips, ["date", "state", "county", "fips"]]
    .head(10)
    .to_string(index=False)
)

# 3. KIEM TRA SO LUY KE AM
negative_cases = df["cases"].lt(0)
negative_deaths = df["deaths"].lt(0)

negative_rows = df.loc[
    negative_cases | negative_deaths
].copy()

print("\n=== DONG CO SO LUY KE AM ===")
print(negative_rows.head(10).to_string(index=False))

# 4. KIEM TRA KHOA VA BAN GHI TRUNG
keys = ["state", "county", "date"]

missing_key = df[keys].isna().any(axis=1)
duplicate_key = df.duplicated(subset=keys, keep=False)

# Khong so sanh cac chuoi co khoa thieu hoac trung ngay.
# Can giai quyet trung lap truoc de tranh tinh chenh lech sai.
valid = df.loc[~missing_key].copy()

bad_groups = (
    df.loc[duplicate_key & ~missing_key, ["state", "county"]]
    .drop_duplicates()
    .assign(ambiguous=True)
)

valid = valid.merge(
    bad_groups,
    on=["state", "county"],
    how="left"
)

check = (
    valid.loc[valid["ambiguous"].isna()]
    .drop(columns="ambiguous")
    .sort_values(keys)
    .copy()
)

print("\nSo dong thieu khoa:", int(missing_key.sum()))
print("So dong thuoc khoa trung:", int(duplicate_key.sum()))
print("So nhom hat tam bo qua do trung khoa:", len(bad_groups))

# 5. SO SANH VOI LAN GHI NHAN TRUOC CUA CUNG HAT
grouped = check.groupby(["state", "county"], sort=False)

check["previous_date"] = grouped["date"].shift(1)
check["previous_cases"] = grouped["cases"].shift(1)
check["previous_deaths"] = grouped["deaths"].shift(1)

check["gap_days"] = (
    check["date"] - check["previous_date"]
).dt.days

check["cases_change"] = (
    check["cases"] - check["previous_cases"]
)
check["deaths_change"] = (
    check["deaths"] - check["previous_deaths"]
)

cases_decrease = check["cases_change"].lt(0)
deaths_decrease = check["deaths_change"].lt(0)
any_decrease = cases_decrease | deaths_decrease

# Phan biet hai ngay lien tiep voi hai lan ghi nhan cach nhau nhieu ngay
consecutive = check["gap_days"].eq(1)
date_gap = check["gap_days"].gt(1)

decrease_rows = check.loc[
    any_decrease,
    [
        "state", "county", "previous_date", "date", "gap_days",
        "previous_cases", "cases", "cases_change",
        "previous_deaths", "deaths", "deaths_change"
    ]
]

print("\n=== SO LUY KE GIAM SO VOI LAN GHI NHAN TRUOC ===")
print(decrease_rows.head(20).to_string(index=False))

print(
    "\nSo dong giam giua hai ngay lien tiep:",
    int((any_decrease & consecutive).sum())
)
print(
    "So dong giam qua khoang trong ngay:",
    int((any_decrease & date_gap).sum())
)

# 6. BANG TONG HOP VA DATA CLEANING PLAN
quality_plan = pd.DataFrame([
    {
        "Van de": "FIPS thieu",
        "So dong": int(missing_fips.sum()),
        "Ke hoach xu ly": (
            "Doi chieu state + county voi danh muc dia ly; "
            "khong tu gan ma cho Unknown/khu vuc dac biet."
        ),
        "Lien he Data Viz": (
            "Tach nhom khong dinh vi duoc khoi Map; "
            "van giu trong tong hop neu phu hop."
        )
    },
    {
        "Van de": "County la Unknown",
        "So dong": int(unknown_county.sum()),
        "Ke hoach xu ly": (
            "Giu nhan Unknown; khong phan bo tuy y sang hat khac."
        ),
        "Lien he Data Viz": "Hien thi rieng bang bang hoac bieu do cot."
    },
    {
        "Van de": "Cases thieu",
        "So dong": int(df["cases"].isna().sum()),
        "Ke hoach xu ly": "Doi chieu nguon; khong tu dien 0.",
        "Lien he Data Viz": "The hien khoang trong tren Line chart."
    },
    {
        "Van de": "Deaths thieu",
        "So dong": int(df["deaths"].isna().sum()),
        "Ke hoach xu ly": "Giu NA khi khong co so lieu; khong tu dien 0.",
        "Lien he Data Viz": "Khong tinh ty le tu vong khi thieu du lieu."
    },
    {
        "Van de": "Cases luy ke am",
        "So dong": int(negative_cases.sum()),
        "Ke hoach xu ly": "Gan co, doi chieu nguon truoc khi sua.",
        "Lien he Data Viz": "Xu ly truoc khi ve quy mo ca mac."
    },
    {
        "Van de": "Deaths luy ke am",
        "So dong": int(negative_deaths.sum()),
        "Ke hoach xu ly": "Gan co, doi chieu nguon truoc khi sua.",
        "Lien he Data Viz": "Xu ly truoc khi ve quy mo tu vong."
    },
    {
        "Van de": "Cases giam so voi lan ghi nhan truoc",
        "So dong": int(cases_decrease.sum()),
        "Ke hoach xu ly": (
            "Kiem tra dieu chinh bao cao; giu du lieu goc va gan co."
        ),
        "Lien he Data Viz": "Chu thich dieu chinh tren Line chart."
    },
    {
        "Van de": "Deaths giam so voi lan ghi nhan truoc",
        "So dong": int(deaths_decrease.sum()),
        "Ke hoach xu ly": (
            "Kiem tra dieu chinh bao cao; khong tu ep chenh lech ve 0."
        ),
        "Lien he Data Viz": "Chu thich diem dieu chinh so lieu."
    },
    {
        "Van de": "Trung state + county + date",
        "So dong": int(duplicate_key.sum()),
        "Ke hoach xu ly": (
            "Bo ban sao y het; doi chieu neu gia tri khac nhau. "
            "Khong cong cac ban ghi luy ke trung."
        ),
        "Lien he Data Viz": "Tranh tong bi nhan doi."
    },
    {
        "Van de": "Thieu state, county hoac date",
        "So dong": int(missing_key.sum()),
        "Ke hoach xu ly": "Doi chieu nguon truoc khi nhom va so sanh.",
        "Lien he Data Viz": "Chua gan vao dia ly/thoi gian khi chua xac minh."
    },
    {
        "Van de": "Khoang cach giua hai lan ghi nhan > 1 ngay",
        "So dong": int(date_gap.sum()),
        "Ke hoach xu ly": (
            "Kiem tra ngay thieu; khong coi chenh lech la ca moi mot ngay."
        ),
        "Lien he Data Viz": "Giu khoang trong hoac chu thich tren Line chart."
    }
])

print("\n=== BANG TONG HOP CHAT LUONG DU LIEU ===")
print(quality_plan.to_string(index=False))

# So dong giua cac van de co the chong lap, khong cong thanh tong loi.
# Bang tren chi kiem tra, chua tu dong sua du lieu goc.

# 7. CHUAN BI DAILY NEW CASES / DEATHS
# Chi tinh khi hai ban ghi cach nhau dung 1 ngay.
# Giu gia tri am de tiep tuc kiem tra dieu chinh bao cao.
check["daily_new_cases"] = check["cases_change"].where(consecutive)
check["daily_new_deaths"] = check["deaths_change"].where(consecutive)