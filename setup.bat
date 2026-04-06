@echo off
:: Di chuyen den dung thu muc chua file .bat nay (QUAN TRONG!)
cd /d "%~dp0"

:: Set UTF-8 encoding
chcp 65001 > nul
title Cai dat Moi truong App Sieu Am P2

echo ==============================================
echo    CAI DAT MOI TRUONG APP SIEU AM P2
echo ==============================================
echo.

:: ==============================================
:: BUOC 1: KIEM TRA GIT
:: ==============================================
echo [1/3] Kiem tra Git...

git --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo [OK] Da tim thay Git.
    goto check_python
)

echo [!] Chua cai Git. Bat dau tu dong tai va cai dat Git...
echo Dang tai bo cai Git (dung luong ~55MB, vui long cho)...
curl -L -o git_installer.exe "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe"
IF NOT EXIST git_installer.exe (
    echo [Loi] Tai Git that bai. Kiem tra ket noi mang.
    pause
    exit /b
)

echo Dang cai dat Git ngam... Vui long cho 1-2 phut.
start /wait git_installer.exe /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"
del git_installer.exe

:: Refresh PATH cho phien hien tai
set "PATH=%PATH%;C:\Program Files\Git\cmd"

git --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [Loi] Khong tim thay Git sau khi cai. Vui long khoi dong lai may.
    pause
    exit /b
)
echo [OK] Da cai dat xong Git.

:: ==============================================
:: BUOC 2: KIEM TRA PYTHON
:: ==============================================
:check_python
echo.
echo [2/3] Kiem tra Python...

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
    echo [Loi] Tai Python that bai. Kiem tra ket noi mang.
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
    echo Vui long tat cua so nay, khoi dong lai may va chay lai setup.bat.
    pause
    exit /b
)

echo [OK] Da cai dat xong Python.

:: ==============================================
:: BUOC 3: CAI DAT THU VIEN
:: ==============================================
:install_libs
echo.
echo [3/3] Kiem tra va cai dat thu vien (libraries)...

:: Nang cap pip truoc
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet

:: Cai file requirements
IF EXIST "requirements.txt" (
    "%PYTHON_EXE%" -m pip install -r requirements.txt
) ELSE (
    echo [Loi] Khong tim thay file requirements.txt trong thu muc hien tai!
    echo Thu muc hien tai: %CD%
    pause
    exit /b
)

echo.
echo ==============================================
echo [OK] HOAN TAT CAI DAT MOI THU!
echo ==============================================
echo.
echo Ban co the chay app ngay bang cach mo file run.bat
echo.
pause
