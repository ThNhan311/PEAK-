**Collect Initial Data – Thu thập dữ liệu ban đầu**

**1. Nguồn gốc và độ tin cậy**

Bộ dữ liệu NYT COVID-19 do **The New York Times** tổng hợp từ báo cáo của chính quyền và cơ quan y tế tại Hoa Kỳ. Nguồn chính thức và phương pháp công khai giúp dữ liệu có độ tin cậy tương đối cao; tuy nhiên, vẫn có hạn chế do thiếu xét nghiệm, chậm báo cáo và khác biệt cách thống kê. [Nguồn: NYT](https://github.com/nytimes/covid-19-data#methodology-and-definitions).

**2. Các file dữ liệu chính**

Dữ liệu CSV ghi nhận số ca mắc và tử vong **lũy kế theo ngày**.

| File                                                                                              | Phạm vi                                 | Dung lượng xấp xỉ trên GitHub |
| ------------------------------------------------------------------------------------------------- | --------------------------------------- | ----------------------------: |
| [us.csv](https://github.com/nytimes/covid-19-data/blob/master/us.csv)                             | Toàn Hoa Kỳ                             |                         30 KB |
| [us-states.csv](https://github.com/nytimes/covid-19-data/blob/master/us-states.csv)               | Bang và vùng lãnh thổ                   |                       2,11 MB |
| [us-counties.csv](https://github.com/nytimes/covid-19-data/blob/master/us-counties.csv)           | Cấp hạt, file tổng hợp cũ               |                       99,9 MB |
| [us-counties-2020.csv](https://github.com/nytimes/covid-19-data/blob/master/us-counties-2020.csv) | Cấp hạt năm 2020                        |                       34,2 MB |
| [us-counties-2021.csv](https://github.com/nytimes/covid-19-data/blob/master/us-counties-2021.csv) | Cấp hạt năm 2021                        |                         48 MB |
| [us-counties-2022.csv](https://github.com/nytimes/covid-19-data/blob/master/us-counties-2022.csv) | Cấp hạt năm 2022                        |                       48,8 MB |
| [us-counties-2023.csv](https://github.com/nytimes/covid-19-data/blob/master/us-counties-2023.csv) | Cấp hạt năm 2023 đến khi ngừng cập nhật |                         11 MB |

Do dung lượng lớn, dữ liệu cấp hạt được chia theo năm; nên sử dụng các file này khi thu thập toàn bộ giai đoạn. [Nguồn: mô tả dữ liệu](https://github.com/nytimes/covid-19-data#historical-data).

**3. Tần suất cập nhật và phương thức thu thập**

Trước đây, dữ liệu lịch sử được tổng hợp hằng ngày; thư mục `live/` cập nhật trong ngày. Phóng viên NYT theo dõi họp báo, phân tích báo cáo và xác minh với cơ quan chức năng, đồng thời sửa số liệu khi có thông tin mới. **Từ ngày 24/03/2023, NYT ngừng cập nhật ca mắc và tử vong trong repository**, hiện giữ lại để lưu trữ. [Nguồn: README của NYT](https://github.com/nytimes/covid-19-data#readme).
