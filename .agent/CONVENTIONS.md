# Quy Ước Code (Conventions)

Dự án này tuân thủ các quy chuẩn cấu trúc mã nguồn chung để đảm bảo hệ thống dễ bảo trì khi Agent xử lý.

## 1. Naming Conventions (Quy chuẩn đặt tên)
- **Tên file & Module**: Đặt tên dạng `snake_case` (VD: `processor.py`, `run_app.py`, `ncr_generator.py`).
- **Tên Class**: Dùng `PascalCase` (VD: `NCRGenerator`).
- **Tên Function & Biến**: `snake_case` (VD: `read_input_file`, `df_result`).
- **Tên Hằng số**: `UPPER_SNAKE_CASE` (VD: `CURRENT_MODEL_NAME`, `NCR_SUMMARY_ORDER`).

## 2. Code Style
- **Type Hinting**: Khuyến khích dùng Type Hint cho function signature mới (VD: `def process(data: pd.DataFrame) -> dict:`).
- **Import Statements**: Tổ chức Import tiêu chuẩn lên đầu > Thư viện ngoài > File local bên trong hệ thống Python.
- **Xử lý file tĩnh/Relative paths**: Tuyệt đối dùng `os.path.join(os.path.dirname(__file__), ...)` thay cho relative path `"./pages"`, phục vụ việc biên dịch được via PyInstaller sang `.exe`.

## 3. Quản trị lỗi & Comment
- Các xử lý `try catch` quan trọng phải in lỗi và block UI ra màn hình thay vì im lặng (Silently fail). Streamlit thường cần thông báo: `st.error(f"Lỗi: {e}")`.
- Ghi chú 100% bằng TIẾNG VIỆT, ngắn gọn, dễ hiểu ở những module tính toán KPI phức tạp. Mọi chỉnh sửa cho file UI cần chú ý đến Sidebar và Tab phân luồng tránh nhầm lẫn.

## 4. Workflows / Agent Rules
- **Luôn tự động sửa lỗi và chạy lại**: Dành cho AI Agent.
- **Auto-Update Admin Files**: Ghi chú cập nhật `CHANGELOG.md` & `TODO.md` sau khi hoàn tất tính năng.
- **Full file edits**: Không sử dụng `...` hoặc `//rest of code` thay vì code nguyên trạng trừ phi dùng tool regex multi lines thay thế. Báo cáo bằng Tiếng Việt.
