# Data Understanding sẽ làm về những gì
# Gồm 4 phần : Thu thập dữ liệu (Collect Intial Data),  Mô tả dữ liệu (Describe Data), Khám phá dữ liệu (Explore Data), Đánh giá chất lượng data (Verify Data Quality)

# Bước 1: Thu thập
- Công việc: Nhận quyền truy cập vào các nguồn dữ liệu (Database, API, file CSV/Excel từ các phòng ban).
- Output: Load thành công dữ liệu thô vào môi trường làm việc (ví dụ: kéo data bằng SQL, đọc vào Pandas DataFrame).
- Lưu ý: Ghi chép lại chính xác nguồn gốc, phương thức lấy và thời gian lấy dữ liệu.

# Bước 2: Mô tả
- Công việc: Cung cấp cái nhìn "tổng quan về mặt vật lý" của dữ liệu.
- Output : Khối lượng dữ liệu: Có bao nhiêu dòng (rows), bao nhiêu cột (columns/features)? Định dạng dữ liệu: Kiểu dữ liệu của từng cột là gì (Numeric, Categorical, Datetime, Text)? Ý nghĩa các cột: Lập một bảng Data Dictionary (Từ điển dữ liệu) để giải thích ý nghĩa của từng biến.

# Bước 3: Khám phá
- Công việc: Dùng các kỹ thuật thống kê và trực quan hóa (Data Visualization) để tìm ra các pattern (quy luật) ban đầu.
- Output: Phân phối của dữ liệu (Distribution): Độ lệch, trung bình, trung vị. Mối tương quan (Correlation): Cột A và cột B có quan hệ với nhau không? (Ví dụ: Tuổi càng cao thì chi tiêu càng nhiều?). Sử dụng biểu đồ: Histogram, Boxplot, Scatter plot... để minh họa.

# Bước 4 : Đánh giá
- Công việc: Tìm ra các missing value của dữ liệu để team làm bước tiếp theo (Data Preparation) biết đường xử lý
- Output:Missing values: Có bao nhiêu dữ liệu bị thiếu ở mỗi cột? Outliers: Có các giá trị ngoại lai bất thường nào không? (Ví dụ: Tuổi = 200). Errors/Inconsistencies: Dữ liệu có bị lỗi format không? (Ví dụ: Cùng là giới tính nam nhưng lúc ghi "M", lúc ghi "Male"). Duplicates: Có các dòng dữ liệu bị trùng lặp không?