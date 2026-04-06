import streamlit as st
import pandas as pd
import json
import io
import numpy as np

st.set_page_config(page_title="🔍 AI Data X-Ray (Profiler)", layout="wide")

st.title("🔍 AI Data X-Ray: Soi Cấu Trúc & Chất Lượng Dữ Liệu")
st.markdown("""
Công cụ này giúp lấy cấu trúc dữ liệu chi tiết để AI viết code chính xác.
**Tối ưu:** Chọn sheet trước khi quét để tiết kiệm thời gian với file lớn.
""")

def get_column_profile(series):
    """Phân tích sâu từng cột: Kiểu dữ liệu, Missing, Unique, Min/Max"""
    # Chuyển đổi sang string để tránh lỗi JSON serializable
    dtype_str = str(series.dtype)
    
    profile = {
        "dtype": dtype_str,
        "count": int(series.count()),
        "missing_ratio": f"{series.isna().mean() * 100:.1f}%",
        "unique_count": int(series.nunique())
    }
    
    # Nếu là số: Lấy Min/Max
    if pd.api.types.is_numeric_dtype(series):
        try:
            profile["min"] = float(series.min()) if not pd.isna(series.min()) else None
            profile["max"] = float(series.max()) if not pd.isna(series.max()) else None
            # Kiểm tra xem có phải số nguyên giả dạng float không (VD: 1.0, 2.0)
            if not series.empty:
                profile["is_integer_like"] = bool(series.dropna().apply(lambda x: float(x).is_integer()).all())
        except: pass

    # Nếu là object (chữ) hoặc số ít giá trị unique: Liệt kê các giá trị (Categories)
    # Giới hạn liệt kê để file JSON không quá nặng
    if series.dtype == 'object' or series.nunique() < 20:
        try:
            unique_vals = series.dropna().unique().tolist()
            # Chỉ lấy tối đa 10 giá trị mẫu để AI hiểu context
            if len(unique_vals) <= 10:
                profile["categories"] = [str(x) for x in unique_vals]
            else:
                profile["categories"] = [str(x) for x in unique_vals[:10]] + ["..."]
        except: pass
            
    # Lấy 3 mẫu đầu và 3 mẫu cuối để AI hình dung dữ liệu
    try:
        head_vals = series.head(3).tolist()
        tail_vals = series.tail(3).tolist()
        profile["samples"] = [str(x) for x in head_vals + tail_vals]
    except: pass
    
    return profile

def scan_excel_advanced(file, target_sheets):
    """
    Hàm quét chính, chỉ quét các sheet được chỉ định trong target_sheets
    """
    file.seek(0) # Đưa con trỏ file về đầu
    xl = pd.ExcelFile(file)
    
    schema_report = {
        "filename": file.name,
        "sheets": {}
    }
    
    # Progress bar
    progress_bar = st.progress(0)
    total_sheets = len(target_sheets)
    
    for i, sheet in enumerate(target_sheets):
        try:
            # 1. Tìm Header động
            # Đọc thử 20 dòng đầu không header để tìm vị trí tên cột
            df_preview = pd.read_excel(file, sheet_name=sheet, header=None, nrows=20)
            header_idx = -1
            
            # Thuật toán tìm header: Dòng nào có nhiều cột dạng text nhất hoặc chứa từ khóa quan trọng
            for idx, row in df_preview.iterrows():
                row_str = " ".join([str(x).upper() for x in row])
                # Điều kiện này có thể tùy chỉnh theo đặc thù file của bạn
                # Ví dụ: Tìm dòng chứa 'NGÀY' và 'MÁY' hoặc chỉ cần dòng có >3 cột không null
                if "NGÀY" in row_str or "STT" in row_str or "MÃ" in row_str: 
                    header_idx = idx
                    break
            
            if header_idx == -1: header_idx = 0 # Fallback về dòng đầu tiên
            
            # 2. Đọc Full Data của Sheet đó
            # Dùng dtype=object ban đầu để bảo toàn dữ liệu gốc, tránh pandas tự ép kiểu sai
            df = pd.read_excel(file, sheet_name=sheet, header=header_idx, dtype=object) 
            
            # 3. Profile từng cột
            cols_profile = {}
            for col in df.columns:
                # Bỏ qua các cột Unnamed vô nghĩa nếu muốn file nhẹ hơn
                if "Unnamed" in str(col) and df[col].isna().all():
                    continue
                    
                # Cố gắng convert sang numeric nếu được để profile chính xác hơn về min/max
                s_converted = pd.to_numeric(df[col], errors='ignore')
                cols_profile[str(col)] = get_column_profile(s_converted)
            
            schema_report["sheets"][sheet] = {
                "header_row_index": header_idx,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns_profile": cols_profile
            }
            
        except Exception as e:
            schema_report["sheets"][sheet] = {"error": str(e)}
        
        # Cập nhật tiến trình
        progress_bar.progress((i + 1) / total_sheets)
        
    return schema_report

# --- GIAO DIỆN CHÍNH ---
uploaded_file = st.file_uploader("1. Upload file Excel (.xlsx, .xls)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Bước 1: Đọc nhanh danh sách sheet (Lazy load)
        uploaded_file.seek(0)
        xl = pd.ExcelFile(uploaded_file)
        all_sheets = xl.sheet_names
        
        st.success(f"✅ Đã đọc file! Tìm thấy {len(all_sheets)} sheet.")
        
        # Bước 2: Chọn sheet
        selected_sheets = st.multiselect(
            "2. Chọn các sheet quan trọng cần phân tích:",
            options=all_sheets,
            default=[all_sheets[0]] if all_sheets else []
        )
        
        # Bước 3: Nút bấm xử lý
        if st.button("3. 🚀 Bắt đầu quét (X-Ray)"):
            if not selected_sheets:
                st.warning("Vui lòng chọn ít nhất một sheet.")
            else:
                with st.spinner(f"Đang phân tích {len(selected_sheets)} sheet được chọn... (Việc này có thể mất vài giây với file lớn)"):
                    report = scan_excel_advanced(uploaded_file, selected_sheets)
                    
                    # Chuyển thành JSON text
                    json_str = json.dumps(report, indent=2, ensure_ascii=False)
                    
                    st.success("🎉 Đã phân tích xong!")
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.download_button(
                            label="📥 Tải xuống JSON (Gửi cho AI)",
                            data=json_str,
                            file_name="data_profile.json",
                            mime="application/json"
                        )
                    with c2:
                        st.info("💡 Mẹo: File JSON này chứa thông tin về kiểu dữ liệu, giá trị rỗng, giúp AI viết code xử lý lỗi chính xác.")
                        
                    with st.expander("Xem trước kết quả phân tích"):
                        st.json(report)
                        
    except Exception as e:
        st.error(f"Không thể đọc file Excel này: {e}")