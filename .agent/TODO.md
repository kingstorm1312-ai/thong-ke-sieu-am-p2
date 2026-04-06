# Danh Sách Công Việc (TODO)

Project lưu trữ các nhiệm vụ cần thực hiện (Backlog).

## Tối ưu / Mới
- [ ] Bảo trì định dạng phiếu NCR với thư viện tương thích PyInstaller để tránh lỗi đường dẫn font hoặc template khi xuất .exe.
- [ ] Soát lại toàn bộ các code logic cho "Đóng gói riêng" / "Xếp giựt" để chuẩn chỉ hệ KPI tổng khi xuất báo cáo.
- [ ] Clean code: Đưa style `.main` và CSS nội tuyến bên trong `app.py` ra file `.css` ngoài.

## Lỗi tồn đọng rà soát
- [ ] Đảm bảo `ncr_generator` luôn giải phóng file stream nếu truy cập mẫu Excel để không bị kẹt I/O access cho End-User.
