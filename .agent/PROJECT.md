# Tổng Quan Dự Án: Thống Kê Siêu Âm P2 (TK sieu am p2)

## 1. Giới thiệu
Dự án "Phần mềm phân tích lỗi siêu âm P2" (TK sieu am p2) là một ứng dụng nội bộ được xây dựng nhằm hỗ trợ Phòng KCS phân tích lỗi sản xuất, thống kê trực quan sản lượng, tỷ lệ lỗi/đạt từ các dữ liệu Excel/CSV (nhật ký máy siêu âm bảo vệ). Hệ thống tích hợp khả năng sinh báo cáo Non-Conformance Report (NCR) cho các cuộn hàng cụ thể.

## 2. Tech Stack
- **Ngôn ngữ chính**: Python 3.x
- **Framework Frontend**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Visualizations**: Plotly (plotly.express, plotly.graph_objects)
- **Đóng gói ứng dụng**: PyInstaller (được định nghĩa cấu hình tại `build.spec`, chạy thông qua `run_app.py`)

## 3. Cấu trúc thư mục (Tóm tắt)
```
<project_root>/
├── app.py                 # File giao diện chính Streamlit (Entry point)
├── run_app.py             # Script nén/chạy dự án dưới dạng ứng dụng (.exe/standalone) qua PyInstaller
├── reader.py              # Xử lý đọc file (Excel, CSV, scan sheet)
├── processor.py           # Logic phân tích và làm sạch dữ liệu
├── visualizer.py          # Vẽ biểu đồ trực quan (Sunburst, Pareto, Heatmap...)
├── ncr_generator.py       # Khởi tạo báo cáo/phiếu NCR (Non-Conformance Report)
├── utils.py               # Các hàm tiện ích (giải mã ghi chú, tính toán tóm tắt)
├── build.spec             # Tệp cấu hình build production
├── pages/                 # Thư mục phụ trợ (Template NCR, Multiple pages Streamlit nếu có)
├── NCR_Output/            # Thư mục lưu trữ phiếu NCR xuất ra
├── build/                 # Thư mục chứa thư viện/cache khi chạy quá trình đóng gói ứng dụng
└── dist/                  # Ứng dụng sau khi biên dịch bằng PyInstaller
```

## 4. Chức năng chính
- Tải lên một hoặc nhiều tệp Excel/CSV, quét và phân tích sheets dữ liệu.
- Làm sạch và tiêu chuẩn hóa dữ liệu với ngưỡng lỗi động (Threshold).
- Thống kê tỷ lệ Tổng Sản lượng, Đạt, Lỗi Phế, Lỗi Xếp Giựt, Đóng Gói (hỗ trợ phân tách các loại lỗi bằng toggle).
- Vẽ biểu đồ trực quan (Pareto, Sunburst, Heatmap lỗi trên dãy).
- Chọn một hoặc nhiều cuộn hàng lỗi để phân tích mức thiết yếu ("Mũi nhọn").
- Lập và tải file mẫu NCR PDF/Excel riêng biệt từng cuộn hoặc báo cáo rủi ro gộp (Bulk NCR) dựa trên Template `Phieu_NCR.xlsx`.

## 5. Trạng thái hiện tại
- Đang ổn định tại phiên bản nội bộ, tích hợp thêm khả năng xuất bảng mẫu NCR.
