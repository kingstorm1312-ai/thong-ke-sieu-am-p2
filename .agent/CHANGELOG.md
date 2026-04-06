# Lịch Sự Thay Đổi (Changelog)

Toàn bộ các phiên bản hoặc thay đổi đáng chú ý của dự án sẽ được ghi nhận tại đây.

## [Unreleased]
### Added (Thêm mới)
- **Hiển thị trực quan:** Thêm cụm widget (Expander) "⏱️ Thông số đối chiếu Đồng hồ / Vật tư" tại tab "Phân Tích Cuộn" để show chỉ số mở rộng của cuộn đang chọn HOẶC TỔNG HỢP GỘP (nếu chọn tất cả các cuộn) ở cả App cũ & mới.
- Thêm script `run.bat` để thao tác chạy app nhanh với cú pháp click-to-run (hỗ trợ tự động nhận diện environment virtual).
- Thư mục quản trị `.agent/` cho mô hình lưu trữ kiến trúc ứng dụng (KI/Agentic flow).
- Hỗ trợ lưu trữ các trường dữ liệu mở rộng mới trong file Excel (Đồng hồ, Định mức, Thẻ vật tư, Chênh lệch) ở tab "Dữ Liệu Gốc".
- Thêm nút "Cập Nhật Ứng Dụng" tại Sidebar của `app.py` cho phép ấn chạy `git pull` pull code từ kho lưu trữ để dễ dàng cập nhật phiên bản ở máy tính khác trong công ty.
- Thêm `setup.bat` cài đặt 1-click tự động: kiểm tra/cài Git, Python 3.12, và tất cả thư viện cần thiết trên máy trắng hoàn toàn.
- Thêm `requirements.txt` đầy đủ các thư viện bắt buộc (streamlit, pandas, plotly, numpy, openpyxl, xlsxwriter, pywin32, kaleido).

### Changed (Thay đổi)
- Cập nhật bộ lọc hệ thống (`utils.py`, `processor.py`) để các file format mới chứa các cột "Đồng hồ" / "Định mức" không bị thuật toán nhận diện nhầm thành Lỗi hệ thống.

### Fixed (Sửa lỗi)
- Fix `git pull` trong nút Cập Nhật thiếu `cwd=project_dir`, gây lỗi "not a git repository" trên một số máy.
- Fix `requirements.txt` thiếu `pywin32` (crash NCR generator) và `kaleido` (crash export chart).
- Fix `setup.bat` thiếu `cd /d "%~dp0"`, gây lỗi không tìm thấy `requirements.txt` khi chạy từ thư mục khác.

## [1.0.0] - 2026-04-06
### Added (Thêm mới)
- Khởi tạo hệ thống giao diện với phân tích Heatmap, Pareto, Sunburst.
- Tích hợp pipeline xuất PDF/Excel NCR bằng `ncr_generator.py`.
- Tách tính năng `process_old_form_logic` và giao nhiệm vụ cụ thể cho từng module.
