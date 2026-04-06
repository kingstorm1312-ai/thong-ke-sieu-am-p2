@echo off
title Khoi dong TK Sieu Am P2 (Antigravity)
color 0B

echo ===================================================
echo     PHAN MEM PHAN TICH LOI SIEU AM P2
echo ===================================================
echo.

:: Di chuyển đến thư mục chứa file .bat
cd /d "%~dp0"

:: Kiểm tra và kích hoạt môi trường ảo (nếu có)
if exist "venv\Scripts\activate.bat" (
    echo [*] Tim thay moi truong venv. Dang kich hoat...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [*] Tim thay moi truong .venv. Dang kich hoat...
    call .venv\Scripts\activate.bat
) else if exist "env\Scripts\activate.bat" (
    echo [*] Tim thay moi truong env. Dang kich hoat...
    call env\Scripts\activate.bat
) else (
    echo [*] Khong tim thay moi truong ao. Su dung Python mac dinh cua he thong.
)

echo.
echo [*] Dang khoi dong ung dung Streamlit, vui long doi giay lat...
echo [*] Trinh duyet se tu dong mo len sau vai giay.
echo.

:: Chạy file run_app.py
python run_app.py

:: Tạm dừng màn hình nếu có lỗi xảy ra để người dùng đọc thông báo
pause
