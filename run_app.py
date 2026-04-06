import os
import sys
import webbrowser
from threading import Timer
from streamlit.web import cli as stcli

def find_app_path():
    """
    Tìm đường dẫn tuyệt đối tới file app.py.
    Hỗ trợ tìm kiếm trong cả thư mục gốc và thư mục _internal (PyInstaller v6+).
    """
    # 1. Xác định thư mục chứa file .exe hoặc script đang chạy
    if getattr(sys, 'frozen', False):
        # Chạy từ file EXE
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # Chạy từ dòng lệnh Python
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Danh sách các vị trí có thể chứa file app.py
    possible_paths = [
        # Trường hợp 1: Nằm ngay cạnh file exe (PyInstaller cũ hoặc cấu hình flat)
        os.path.join(base_dir, 'app.py'),
        
        # Trường hợp 2: Nằm trong thư mục _internal (PyInstaller v6+ mặc định)
        os.path.join(base_dir, '_internal', 'app.py'),
    ]

    # Trường hợp 3: Nằm trong thư mục tạm _MEIPASS (nếu dùng --onefile)
    if hasattr(sys, '_MEIPASS'):
        possible_paths.insert(0, os.path.join(sys._MEIPASS, 'app.py'))

    # 3. Kiểm tra lần lượt
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    # Nếu không tìm thấy, trả về đường dẫn mặc định để in lỗi
    return os.path.join(base_dir, 'app.py')

def open_browser(port):
    """Mở trình duyệt sau 2 giây"""
    webbrowser.open_new(f"http://localhost:{port}")

def main():
    # Tìm file app.py
    app_path = find_app_path()
    
    # Kiểm tra lần cuối
    if not os.path.exists(app_path):
        print("---------------------------------------------------------")
        print("❌ CRITICAL ERROR: Could not find 'app.py'.")
        print(f"Searched target: {app_path}")
        print("Please check inside the '_internal' folder or rebuild.")
        print("---------------------------------------------------------")
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"🚀 Starting Streamlit App...")
    print(f"📂 App Path: {app_path}")
    
    port = 8501
    
    # Giả lập tham số dòng lệnh
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        f"--server.port={port}",
        "--server.headless=true",
        "--theme.base=light"
    ]

    # Hẹn giờ mở trình duyệt
    Timer(2, open_browser, args=[port]).start()

    # Chạy ứng dụng
    try:
        sys.exit(stcli.main())
    except SystemExit:
        pass
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()