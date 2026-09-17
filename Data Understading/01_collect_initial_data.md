# 1. Collect Initial Data — Thu thập dữ liệu ban đầu

## Mục tiêu

Xác định nguồn dữ liệu, phương thức tiếp cận, các file cần sử dụng và giới hạn phạm vi trước khi phân tích.

## Nguồn và độ tin cậy

Bộ dữ liệu do The New York Times (NYT) tổng hợp từ báo cáo của chính quyền và cơ quan y tế Hoa Kỳ. Nguồn chính thức và phương pháp công khai là cơ sở đánh giá độ tin cậy, nhưng dữ liệu vẫn chịu ảnh hưởng của thiếu xét nghiệm, độ trễ và khác biệt trong cách thống kê giữa các địa phương.

## Phương thức thu thập

- **Phía NYT:** theo dõi họp báo, phân tích báo cáo và xác minh với cơ quan chức năng; sửa số liệu khi có thông tin mới.
- **Phía nhóm:** tải CSV trực tiếp từ repository hoặc clone repository để lấy dữ liệu. Giữ nguyên bản gốc trong `data/raw/`.
- **Thông tin cần ghi khi tải:** ngày tải thực tế, tên file, đường dẫn nguồn, khoảng thời gian trong file và commit nếu có.

## Tần suất cập nhật

Trước đây, dữ liệu lịch sử ghi nhận số liệu cuối mỗi ngày; thư mục `live/` cập nhật trong ngày. NYT thông báo ngừng cập nhật ca mắc và tử vong từ **24/03/2023**. Repository hiện là nguồn dữ liệu lịch sử; không dùng để mô tả tình hình hiện tại.

## Danh sách dữ liệu

Dung lượng xấp xỉ theo hiển thị GitHub, không phải bộ nhớ RAM khi đọc bằng pandas.

| File | Định dạng | Dung lượng | Nội dung |
|---|---|---:|---|
| `us.csv` | CSV | 30 KB | Ca mắc và tử vong lũy kế toàn Hoa Kỳ theo ngày |
| `us-states.csv` | CSV | 2,11 MB | Ca mắc và tử vong lũy kế theo bang/vùng lãnh thổ |
| `us-counties.csv` | CSV | 99,9 MB | File tổng hợp cấp hạt cũ |
| `us-counties-2020.csv` | CSV | 34,2 MB | Dữ liệu cấp hạt năm 2020 |
| `us-counties-2021.csv` | CSV | 48 MB | Dữ liệu cấp hạt năm 2021 |
| `us-counties-2022.csv` | CSV | 48,8 MB | Dữ liệu cấp hạt năm 2022 |
| `us-counties-2023.csv` | CSV | 11 MB | Dữ liệu cấp hạt năm 2023 đến khi ngừng cập nhật |

Không mặc định `us-counties.csv` chứa toàn bộ giai đoạn. Nếu cần đầy đủ, sử dụng các file theo năm và kiểm tra ngày nhỏ nhất/lớn nhất sau khi đọc. Không nối file tổng hợp cũ với toàn bộ file theo năm vì có thể trùng bản ghi.

## Liên hệ trực quan hóa

Dữ liệu có cả thời gian và địa lý nên phù hợp với Line chart để theo dõi xu hướng, Bar chart để so sánh bang và Map để xem phân bố không gian. So sánh số ca tuyệt đối thể hiện quy mô báo cáo; muốn so sánh theo dân số cần bổ sung dữ liệu dân số.

## Nguồn tham khảo

- [README và phương pháp NYT](https://github.com/nytimes/covid-19-data#readme).
- [us.csv](https://github.com/nytimes/covid-19-data/blob/master/us.csv), [us-states.csv](https://github.com/nytimes/covid-19-data/blob/master/us-states.csv), [us-counties.csv](https://github.com/nytimes/covid-19-data/blob/master/us-counties.csv).
- [2020](https://github.com/nytimes/covid-19-data/blob/master/us-counties-2020.csv), [2021](https://github.com/nytimes/covid-19-data/blob/master/us-counties-2021.csv), [2022](https://github.com/nytimes/covid-19-data/blob/master/us-counties-2022.csv), [2023](https://github.com/nytimes/covid-19-data/blob/master/us-counties-2023.csv).
