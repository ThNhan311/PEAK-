**Collect Initial Data – Thu thập dữ liệu ban đầu**

* **Nguồn dữ liệu:** The New York Times – [GitHub Repository](https://github.com/nytimes/covid-19-data). Dữ liệu được NYT tổng hợp từ chính quyền và cơ quan y tế Hoa Kỳ, có độ tin cậy tương đối cao nhưng vẫn chịu ảnh hưởng của độ trễ báo cáo và khác biệt phương pháp thống kê.
* **Phương thức nhóm thu thập:** Clone repository hoặc tải trực tiếp các file `.csv`.
* **Phương thức NYT thu thập:** Theo dõi họp báo, tổng hợp báo cáo chính thức, xác minh với cơ quan chức năng và điều chỉnh khi có thông tin mới.
* **Tần suất cập nhật:** Trước đây cập nhật hằng ngày; NYT **ngừng cập nhật từ ngày 24/03/2023**, repository hiện phục vụ lưu trữ. [Nguồn: README của NYT](https://github.com/nytimes/covid-19-data#readme).

**Bảng danh sách tập dữ liệu sử dụng:**

| Tên file                                                                                | Định dạng | Kích thước (ước tính) | Mô tả nội dung chính                                                 |
| :-------------------------------------------------------------------------------------- | :-------: | --------------------: | :------------------------------------------------------------------- |
| [us.csv](https://github.com/nytimes/covid-19-data/blob/master/us.csv)                   |    CSV    |                 30 KB | Số ca mắc và tử vong lũy kế theo ngày trên toàn nước Mỹ              |
| [us-states.csv](https://github.com/nytimes/covid-19-data/blob/master/us-states.csv)     |    CSV    |               2,11 MB | Số ca mắc và tử vong lũy kế theo ngày tại từng bang và vùng lãnh thổ |
| [us-counties.csv](https://github.com/nytimes/covid-19-data/blob/master/us-counties.csv) |    CSV    |               99,9 MB | Dữ liệu lũy kế cấp quận/hạt trong file tổng hợp cũ                   |

**Lưu ý:** Để phân tích đầy đủ dữ liệu cấp hạt, cần sử dụng các file `us-counties-2020.csv` đến `us-counties-2023.csv`, do NYT đã chia dữ liệu theo năm khi dung lượng tăng lớn. [Nguồn: mô tả dữ liệu](https://github.com/nytimes/covid-19-data#historical-data).
