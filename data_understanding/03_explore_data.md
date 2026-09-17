# 3. Explore Data — Khám phá dữ liệu

## Mục tiêu

Hiểu quy mô, phân bố, xu hướng và các điểm bất thường để lựa chọn biểu đồ phù hợp. Khám phá dữ liệu không đồng nghĩa với đã làm sạch hoặc giải thích được nguyên nhân dịch bệnh.

## Năm câu hỏi phân tích

| STT | Câu hỏi | Cách tổng hợp | Biểu đồ |
|---|---|---|---|
| 1 | Ca mắc mới toàn Hoa Kỳ thay đổi thế nào theo thời gian? | Tính chênh lệch theo ngày từ us.csv; có thể thêm trung bình 7 ngày | Line chart |
| 2 | Mười bang nào có số ca mắc lũy kế cao nhất tại ngày cuối dữ liệu? | Lọc ngày lớn nhất, xếp giảm dần cases | Bar chart ngang |
| 3 | Xu hướng ca mắc mới giữa các bang khác nhau thế nào? | Tính chênh lệch theo từng bang, chọn một số bang hoặc tách ô | Line chart / Small multiples |
| 4 | Bang nào có tỷ lệ tử vong trên ca mắc báo cáo cao nhất tại ngày cuối? | deaths / cases × 100 tại cùng ngày | Bar chart ngang |
| 5 | Tháng nào có nhiều ca mắc mới nhất tại từng bang? | Tổng ca mới theo bang và tháng sau kiểm tra dữ liệu | Heatmap bang × tháng |

Tỷ lệ ở câu 4 là tỷ lệ thô trên số ca được báo cáo, không phải xác suất tử vong của mọi người nhiễm bệnh. Việc so sánh có thể chịu ảnh hưởng của độ tuổi, xét nghiệm và độ trễ báo cáo. Với biểu đồ ca tuyệt đối, không kết luận bang có dân số lớn hơn là nơi có nguy cơ cao hơn chỉ từ tổng ca.

## Các bước khám phá bằng pandas

1. Đọc CSV; giữ `fips` là chuỗi và chuyển `date` thành ngày.
2. Dùng `head()` để quan sát cấu trúc và ví dụ.
3. Dùng `info()` để xem số dòng, kiểu dữ liệu và giá trị không thiếu.
4. Dùng `describe()` để xem phân bố các cột số. Thống kê này gộp nhiều ngày và địa phương, không phải tổng ca duy nhất.
5. Dùng `isna().sum()` và kiểm tra khóa trùng để phát hiện vấn đề ban đầu.
6. Tính ngày nhỏ nhất/lớn nhất để xác định phạm vi thực tế của file.
7. Lọc `date == date.max()`, sau đó tìm giá trị `cases` lớn nhất, giữ cả trường hợp đồng hạng.

## Quy tắc dữ liệu cộng dồn

- Không cộng `cases` hoặc `deaths` qua nhiều ngày.
- Có thể cộng giữa các địa phương không chồng lấn tại cùng ngày khi phạm vi báo cáo tương thích.
- Muốn số lũy kế tháng: lấy giá trị cuối tháng.
- Muốn số phát sinh tháng: tổng ca mới trong tháng, cần số ngày trước đầu tháng để tính chênh lệch đầu kỳ.
- Không cộng đồng thời us.csv, cấp bang và cấp hạt vì các cấp này bao phủ trùng dân số.

## Chuẩn bị Daily New Cases

Sau khi sắp xếp ngày và xử lý khóa trùng:

**Daily New Cases(t) = cases(t) − cases(t−1)**

Tương tự với Daily New Deaths. Dùng `groupby(...).shift(1)` hoặc `diff()` trong pandas theo bang hoặc cặp bang–hạt. Trong Power BI có thể tính bằng DAX với đúng bộ lọc địa phương và ngày trước đó.

Chỉ coi chênh lệch là ca mới một ngày khi hai bản ghi cách nhau đúng một ngày. Bản ghi đầu không có mốc trước đó thì để thiếu. Giữ cờ điều chỉnh cho chênh lệch âm; không tự ép về 0. Khi tính trung bình 7 ngày cần bảo đảm đúng 7 ngày lịch, không đơn thuần là 7 dòng nếu có khoảng trống.

## Kết quả cần bổ sung sau khi chạy

| Chỉ tiêu | Trạng thái |
|---|---|
| Số dòng và số cột | Chưa chạy trên bản dữ liệu của nhóm |
| Ngày đầu và ngày cuối | Chưa chạy trên bản dữ liệu của nhóm |
| Số địa phương | Chưa chạy trên bản dữ liệu của nhóm |
| Bang có cases cao nhất tại ngày cuối | Chưa chạy trên bản dữ liệu của nhóm |
| Top 10 bang và nhận xét | Chưa chạy trên bản dữ liệu của nhóm |

## Nguồn

[NYT — định nghĩa và phương pháp](https://github.com/nytimes/covid-19-data#methodology-and-definitions).
