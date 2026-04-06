# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import streamlit
from PyInstaller.utils.hooks import copy_metadata

# --- CẤU HÌNH ---
APP_NAME = 'QC_Analytics_Tool'
MAIN_SCRIPT = 'run_app.py'

streamlit_path = os.path.dirname(streamlit.__file__)

# Copy metadata của streamlit
datas = copy_metadata('streamlit')

# Copy metadata cho các thư viện phụ thuộc (nếu có)
# Bọc trong try-except vì một số package có thể không cài riêng lẻ
try:
    datas += copy_metadata('jaraco.text')
except:
    pass

try:
    datas += copy_metadata('jaraco.classes')
except:
    pass

try:
    datas += copy_metadata('jaraco.collections')
except:
    pass

# --- CẬP NHẬT: THÊM CÁC MODULE MỚI VÀO ĐÂY ---
datas += [
    ('app.py', '.'),
    ('utils.py', '.'),
    ('reader.py', '.'),
    ('processor.py', '.'),      # <--- File xử lý logic
    ('visualizer.py', '.'),     # <--- File vẽ biểu đồ
    ('ncr_generator.py', '.'),  # <--- File tạo NCR PDF
    ('pages', 'pages'),         # Thư mục pages (bao gồm Template)
    (os.path.join(streamlit_path, 'static'), 'streamlit/static'),
    (os.path.join(streamlit_path, 'runtime'), 'streamlit/runtime'),
]

block_cipher = None

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[],
    binaries=[],
    datas=datas,
    # --- HIDDEN IMPORTS - CHỈ GIỮ CÁC THƯ VIỆN THỰC SỰ CẦN ---
    hiddenimports=[
        'streamlit',
        'pandas',
        'plotly',
        'openpyxl',         # Đọc/ghi Excel
        'numpy',
        'PIL',              # Xử lý ảnh
        'watchdog',         # Streamlit file watcher
        'rich',             # Streamlit console output
        'tornado',          # Streamlit web server
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # --- LOẠI TRỪ CÁC THƯ VIỆN KHÔNG DÙNG ĐỂ GIẢM DUNG LƯỢNG ---
    excludes=[
        # UI Frameworks không dùng
        'matplotlib',
        'scipy',
        'IPython', 
        'jupyter',
        'notebook',
        'qtpy',
        'PyQt5',
        'PySide2',
        'tkinter',
        # Testing frameworks
        'pytest',
        'nose',
        # Development tools
        'setuptools',
        'pip',
        'wheel',
        # Database drivers không dùng
        'psycopg2',
        'pymongo',
        'mysql',
        # Web frameworks không dùng
        'flask',
        'django',
        'fastapi',
        # Other heavy packages
        'jedi',
        'parso',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Để True để xem log lỗi nếu có, đổi thành False khi đã ổn định
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)