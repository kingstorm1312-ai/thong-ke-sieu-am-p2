# Lịch Sự Thay Đổi (Changelog)

Toàn bộ các phiên bản hoặc thay đổi đáng chú ý của dự án sẽ được ghi nhận tại đây.

## [Unreleased]
### Added (Thêm mới)
- Thư mục quản trị `.agent/` cho mô hình lưu trữ kiến trúc ứng dụng (KI/Agentic flow).
- Hỗ trợ lưu trữ các trường dữ liệu mở rộng mới trong file Excel (Đồng hồ, Định mức, Thẻ vật tư, Chênh lệch) ở tab "Dữ Liệu Gốc".

### Changed (Thay đổi)
- Cập nhật bộ lọc hệ thống (`utils.py`, `processor.py`) để các file format mới chứa các cột "Đồng hồ" / "Định mức" không bị thuật toán nhận diện nhầm thành Lỗi hệ thống.

### Fixed (Sửa lỗi)
- (Chưa có sửa chữa bảo trì).

## [1.0.0] - 2026-04-06
### Added (Thêm mới)
- Khởi tạo hệ thống giao diện với phân tích Heatmap, Pareto, Sunburst.
- Tích hợp pipeline xuất PDF/Excel NCR bằng `ncr_generator.py`.
- Tách tính năng `process_old_form_logic` và giao nhiệm vụ cụ thể cho từng module.
