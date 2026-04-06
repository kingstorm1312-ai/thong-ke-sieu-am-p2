@echo off
:: Set UTF-8 encoding
chcp 65001 > nul
title Cai dat Moi truong App Sieu Am P2

echo ==============================================
echo 1. KIEM TRA PYTHON
echo ==============================================

:: Check if python is accessible
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo [OK] Da tim thay Python.
    set "PYTHON_EXE=python"
    goto install_libs
)

:: If not found, try py launcher
py --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo [OK] Da tim thay Python Launcher.
    set "PYTHON_EXE=py"
    goto install_libs
)

echo [!] Chua cai Python. Bat dau tu dong tai va cai dat Python 3.12...
echo Dang tai bo cai (dung luong ~25MB)...
curl -L -o python_installer.exe "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
IF NOT EXIST python_installer.exe (
    echo [Loi] Tai tệp cài đặt thất bại. Vui lòng kiểm tra kết nối mạng.
    pause
    exit /b
)

echo Dang cai dat Python ngam... Vui long cho 1-2 phut.
:: /quiet: silent install, PrependPath: add to PATH
start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0 Include_launcher=1
del python_installer.exe

:: Try to find the python executable directly since PATH won't update in this session
set "PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"

IF NOT EXIST "%PYTHON_EXE%" (
    echo [Loi] Khong tim thay Python sau khi cai.
    echo Vui long tat cua so nay, hoac khoi dong lai may va mo lai.
    pause
    exit /b
)

echo [OK] Da cai dat xong Python.

:install_libs
echo.
echo ==============================================
echo 2. KIEM TRA VA CAI DAT THU VIEN (LIBRARIES)
echo ==============================================
echo Dang kiem tra va cai dat (neu thieu)...

:: Nang cap pip truoc
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet

:: Cai file requirements
IF EXIST "requirements.txt" (
    "%PYTHON_EXE%" -m pip install -r requirements.txt
) ELSE (
    echo Loi: Khong tim thay file requirements.txt
    pause
    exit /b
)

echo.
echo ==============================================
echo [X] HOAN TAT CAI DAT MOi THU!
echo ==============================================
echo Ban co the chay app ngay bang cach mo file run.bat!
pause
