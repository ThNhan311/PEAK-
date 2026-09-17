# 4. Verify Data Quality — Kiểm tra chất lượng dữ liệu

## Mục tiêu và phạm vi

Kiểm tra tính đầy đủ, hợp lệ, duy nhất và nhất quán của `us-counties.csv`. Giai đoạn này ghi nhận vấn đề và đề xuất Data Cleaning Plan; việc sửa dữ liệu được thực hiện có kiểm soát ở Data Preparation. Giữ nguyên CSV gốc.

## Nguyên tắc kiểm tra

- Kiểm tra thiếu dữ liệu ở mọi cột, đặc biệt `fips`, `cases`, `deaths` và các trường khóa.
- Phân biệt `county = Unknown` với county trống và FIPS thiếu: chúng có thể giao nhau nhưng không đồng nghĩa.
- Giữ FIPS dạng chuỗi để bảo toàn số 0 đầu; kiểm tra định dạng 5 chữ số với giá trị không thiếu.
- Kiểm tra ngày, kiểu số, số âm và số không nguyên trong các cột đếm.
- Kiểm tra trùng `(state, county, date)` trước khi tính chênh lệch.
- So sánh theo cặp `state`–`county`, không nhóm riêng `county` vì có tên hạt trùng giữa các bang.
- Sắp xếp ngày, dùng shift để lấy bản ghi trước; phân biệt ngày liên tiếp và khoảng trống ngày.

## Hai dạng bất thường của số cộng dồn

1. **Giá trị lũy kế âm:** cases < 0 hoặc deaths < 0; cần xác minh nguồn trước khi sửa.
2. **Lũy kế giảm:** cases(t) < cases(t−1) hoặc deaths(t) < deaths(t−1). Đây có thể là điều chỉnh báo cáo hoặc phân bổ lại địa phương, không tự động kết luận là lỗi nhập liệu.

Đối với nhóm có nhiều dòng trong cùng ngày, giải quyết trùng trước khi so sánh. Nếu tạm bỏ nhóm khỏi phép tính, phải ghi rõ số nhóm bị bỏ qua; không diễn giải phần chưa kiểm tra là không có vấn đề.

## Data Cleaning Plan và liên hệ Data Visualization

| Vấn đề | Kiểm tra | Phương án xử lý đề xuất | Ảnh hưởng tới biểu đồ |
|---|---|---|---|
| FIPS thiếu | isna, thống kê theo county/state | Đối chiếu danh mục phù hợp; không tự gán mã cho Unknown hoặc khu vực đặc biệt | Tách phần không định vị khỏi Map, công bố phạm vi bị thiếu |
| County = Unknown | So sánh nhãn sau chuẩn hóa khoảng trắng | Giữ thành nhóm riêng, không phân bổ tùy ý | Biểu diễn riêng bằng bảng/cột; có thể giữ trong tổng hợp phù hợp |
| Cases/deaths thiếu | isna và tỷ lệ thiếu | Giữ NA khi chưa xác minh, không tự điền 0 | Line chart có khoảng trống; không tính tỷ lệ từ số liệu thiếu |
| Khóa địa phương/ngày thiếu | Kiểm tra state, county, date | Xác minh trước khi nhóm, tách các dòng chưa đủ thông tin | Tránh gán sai thời gian hoặc địa lý |
| Ngày/kiểu số không hợp lệ | Parse và ghi nhận giá trị lỗi | Đối chiếu nguồn; lưu dấu lỗi chuyển đổi riêng | Tránh sai trục thời gian và phép cộng |
| FIPS sai định dạng | Kiểm tra 5 chữ số | Kiểm tra nguồn/mã chuẩn; không bổ sung số 0 một cách mù quáng | Tránh nối sai bản đồ |
| Giá trị đếm không nguyên hoặc lũy kế âm | Kiểm tra cases, deaths | Gắn cờ, đối chiếu; không lấy trị tuyệt đối | Tránh biểu diễn quy mô sai |
| Lũy kế giảm | shift/diff theo state + county | Giữ bản gốc và cờ điều chỉnh; xem ghi chú nguồn trước khi quyết định | Chú thích trên Line chart; không âm thầm ép ca mới về 0 |
| Khóa trùng | duplicated theo state + county + date | Bỏ bản sao y hệt; đối chiếu nếu số liệu xung đột, không cộng hai số lũy kế | Tránh tổng nhân đôi và thứ tự ngày mơ hồ |
| Khoảng trống ngày | Chênh lệch ngày > 1 | Xác minh phạm vi; không coi chênh lệch nhiều ngày là ca mới một ngày | Giữ khoảng trống/chú thích; kiểm tra trước rolling 7 ngày |

Không tự động loại mọi dòng thiếu FIPS: việc này có thể làm tổng ca bị giảm không đúng. Một số khu vực không tương ứng ranh giới hạt chuẩn cần xử lý địa lý riêng.

## Bảng kết quả cần điền sau khi chạy

| Chỉ tiêu | Số lượng |
|---|---|
| Tổng số dòng kiểm tra | Chưa tính |
| Dòng thiếu FIPS | Chưa tính |
| Dòng county = Unknown | Chưa tính |
| Dòng vừa Unknown vừa thiếu FIPS | Chưa tính |
| Dòng thiếu cases / deaths | Chưa tính |
| Dòng cases âm / deaths âm | Chưa tính |
| Dòng thuộc khóa trùng | Chưa tính |
| Dòng cases giảm / deaths giảm giữa hai ngày liên tiếp | Chưa tính |
| Dòng giảm qua khoảng trống ngày | Chưa tính |
| Số nhóm chưa so sánh được do khóa trùng | Chưa tính |

Các nhóm vấn đề có thể chồng lấn; không cộng tất cả số dòng trên thành tổng lỗi. Tỷ lệ của kiểm tra giảm phải nêu rõ mẫu số là số cặp đủ điều kiện so sánh. Chưa có số liệu thực nghiệm trong tài liệu này.

## Chuyển sang Data Preparation

Sau khi kiểm tra, nhóm chuẩn hóa kiểu dữ liệu, xử lý trùng và bổ sung trường Daily New Cases/Daily New Deaths bằng shift hoặc diff. Kết quả sạch được lưu riêng trong `data/processed/`, kèm nhật ký quyết định và cờ điều chỉnh. Từ đó lựa chọn Map cho địa lý xác định được, Line chart cho chuỗi thời gian và Bar chart cho so sánh tại cùng một thời điểm.

## Nguồn

[NYT — Methodology and Definitions](https://github.com/nytimes/covid-19-data#methodology-and-definitions), đặc biệt các mục Declining Counts, Counties và Unknown Counties.
