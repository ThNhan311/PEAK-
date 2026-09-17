# 2. Describe Data — Mô tả dữ liệu

## Đơn vị quan sát và kiểu dữ liệu

Mỗi dòng của `us-counties.csv` là số liệu một hạt/khu vực báo cáo tại một ngày. Mỗi dòng của `us-states.csv` là số liệu một bang/vùng lãnh thổ tại một ngày. CSV không khai báo kiểu dữ liệu; các kiểu dưới đây là đề xuất khi nhập và xử lý.

## Data Dictionary: us-counties.csv

| Tên cột | Kiểu dữ liệu | Ý nghĩa | Ví dụ thực tế |
|---|---|---|---|
| `date` | Date | Ngày báo cáo, dạng YYYY-MM-DD | `2020-01-21`, `2020-01-24` |
| `county` | String | Hạt hoặc khu vực được NYT thống kê riêng | `Snohomish`, `Cook` |
| `state` | String | Bang/vùng lãnh thổ chứa khu vực báo cáo | `Washington`, `Illinois` |
| `fips` | String, 5 ký tự; có thể thiếu | Mã địa lý cấp hạt; 2 số đầu là bang, 3 số sau là hạt | `53061`, `17031` |
| `cases` | Integer | Số ca mắc lũy kế đến ngày báo cáo | `1` |
| `deaths` | Integer cho phép thiếu | Số ca tử vong lũy kế; ô trống không đồng nghĩa 0 | `0` |

## Data Dictionary: us-states.csv

| Tên cột | Kiểu dữ liệu | Ý nghĩa | Ví dụ thực tế |
|---|---|---|---|
| `date` | Date | Ngày báo cáo, dạng YYYY-MM-DD | `2020-01-21`, `2020-01-25` |
| `state` | String | Bang hoặc vùng lãnh thổ | `Washington`, `California` |
| `fips` | String, 2 ký tự | Mã địa lý cấp bang, giữ số 0 đầu | `53`, `06` |
| `cases` | Integer | Số ca mắc lũy kế đến ngày báo cáo | `1`, `2` |
| `deaths` | Integer | Số ca tử vong lũy kế đến ngày báo cáo | `0` |

Ví dụ lấy từ các dòng đầu của hai file nguồn.

## Dimensions và Measures

| Nhóm | Trường | Cách sử dụng |
|---|---|---|
| Dimension | `date` | Phân cấp năm, quý, tháng, ngày |
| Dimension | `state` | Lọc và so sánh theo bang |
| Dimension | `county` | Phân tích cấp hạt; kết hợp với bang |
| Dimension | `fips` | Mã định danh địa lý, không cộng hoặc lấy trung bình |
| Measure | `cases`, `deaths` | Lũy kế tại ngày xác định |
| Measure tính toán | Daily New Cases | Chênh lệch ca mắc giữa hai ngày liên tiếp của cùng địa phương |
| Measure tính toán | Daily New Deaths | Chênh lệch tử vong giữa hai ngày liên tiếp |
| Measure tính toán | Tỷ lệ tử vong/ca mắc báo cáo | deaths / cases × 100; thiếu nếu mẫu số bằng 0 hoặc dữ liệu thiếu |
| Measure tính toán | Trung bình ca mới 7 ngày | Trung bình ca mới trong cửa sổ 7 ngày lịch |

Trong Tableau, dùng FIPS dưới dạng Dimension dạng chuỗi. Trong Power BI, đặt FIPS là Text và Do not summarize. Map cấp hạt cần trường địa lý hoặc bản đồ ranh giới tương thích; việc có FIPS không đảm bảo công cụ tự định vị được.

## Các đặc điểm cần lưu ý

- `cases` và `deaths` là **cộng dồn**, gồm số xác nhận và số có khả năng theo báo cáo địa phương.
- Ngày báo cáo không nhất thiết là ngày nhiễm bệnh hoặc tử vong.
- `Unknown` là nhãn chưa xác định hạt, không phải tên một hạt thực tế.
- Một số địa lý đặc biệt không có FIPS; ví dụ NYT có thể gộp nhiều hạt thành một khu vực.
- Cần kiểm tra tính duy nhất của `(state, county, date)` hoặc `(state, date)`; không dùng riêng tên hạt làm khóa.

## Nguồn

[Phương pháp NYT](https://github.com/nytimes/covid-19-data#methodology-and-definitions), [us-counties.csv](https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv), [us-states.csv](https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv).
