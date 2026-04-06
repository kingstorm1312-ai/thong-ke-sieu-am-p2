"""
Module: utils.py
Description: Helper functions for data processing, defect legend extraction, and summary calculations.
Refactored: 2024-12-10 (Added Type Hints and Docstrings).
"""

import pandas as pd
import numpy as np
import re
import reader
from typing import List, Dict, Any, Optional, Tuple, Union

# ==========================================
# CONFIG & CONSTANTS
# ==========================================
NCR_SUMMARY_ORDER: List[str] = [
    "TỔNG LỖI DO SIÊU ÂM",
    "TỔNG LỖI DO NPL VẢI",
    "TỔNG LỖI DO SAI BƯỚC LẬP",
    "TỔNG LỖI DO TRÁNG",
    "TỔNG LỖI DO IN",
    "TỔNG LỖI DO MANH CHÙNG, MỀM",
    "TỔNG LỖI QUAI",
    "TỔNG LỖI SẢN XUẤT",
    "TỔNG TÚI THÀNH PHẨM THIẾU SO VỚI QUY",
    "TỔNG CỘNG LỖI"
]

NCR_AGGREGATION_KEYWORDS: Dict[str, List[str]] = {
    "TỔNG LỖI DO SIÊU ÂM": ["SIÊU ÂM", "SIEU AM"],
    "TỔNG LỖI DO NPL VẢI": ["NPL", "VẢI", "VAI"],
    "TỔNG LỖI DO SAI BƯỚC LẬP": ["SAI BƯỚC LẬP", "SAI BUOC LAP"],
    "TỔNG LỖI DO TRÁNG": ["TRÁNG", "TRANG", "DỘP", "THIẾU NHỰA", "NHĂN", "KHÔNG MÀNG"],
    "TỔNG LỖI DO IN": ["LỖI IN", "LOI IN"],
    "TỔNG LỖI DO MANH CHÙNG, MỀM": ["MANH CHÙNG", "MỀM", "MANH CHUNG", "MEM"],
    "TỔNG LỖI QUAI": ["QUAI"],
    "TỔNG TÚI THÀNH PHẨM THIẾU SO VỚI QUY": ["THIẾU SO VỚI QUY", "THIEU SO VOI QUY"]
}

def calculate_ncr_summary(df_defects_view: pd.DataFrame) -> Dict[str, float]:
    """
    Tính toán bảng tổng hợp từ DataFrame lỗi chi tiết.
    Args:
        df_defects_view: DataFrame có cột ['Loại Lỗi', 'Số Lượng Lỗi']
    Returns:
        Dict chứa tổng số lượng lỗi theo từng nhóm.
    """
    summary_dict = {k: 0.0 for k in NCR_SUMMARY_ORDER}
    
    # helper
    def sum_by_keywords(keywords: List[str]) -> float:
        total = 0.0
        if not keywords: return 0.0
        # Iterate to check keywords
        for _, row in df_defects_view.iterrows():
            name = str(row['Loại Lỗi']).upper()
            qty = float(row['Số Lượng Lỗi'])
            if any(kw in name for kw in keywords):
                total += qty
        return total

    # 1. Calculate Basic Groups
    for key, keywords in NCR_AGGREGATION_KEYWORDS.items():
        summary_dict[key] = sum_by_keywords(keywords)
        
    # 2. Calculate TỔNG LỖI SẢN XUẤT (Sum of Production Defects)
    # Excludes "THIẾU SO VỚI QUY"
    prod_keys = [
        "TỔNG LỖI DO SIÊU ÂM", "TỔNG LỖI DO NPL VẢI", "TỔNG LỖI DO SAI BƯỚC LẬP",
        "TỔNG LỖI DO TRÁNG", "TỔNG LỖI DO IN", "TỔNG LỖI DO MANH CHÙNG, MỀM",
        "TỔNG LỖI QUAI"
    ]
    summary_dict["TỔNG LỖI SẢN XUẤT"] = sum(summary_dict[k] for k in prod_keys)
    
    # 3. Calculate TỔNG CỘNG LỖI
    summary_dict["TỔNG CỘNG LỖI"] = summary_dict["TỔNG LỖI SẢN XUẤT"] + summary_dict["TỔNG TÚI THÀNH PHẨM THIẾU SO VỚI QUY"]
    
    return summary_dict

# ==========================================
# CÁC HÀM CŨ (GIỮ NGUYÊN ĐỂ TOOL CŨ CHẠY)
# ==========================================

def extract_defect_legend(df: pd.DataFrame) -> Dict[str, str]:
    """
    Trích xuất bảng mã lỗi (Legend) từ các cột hoặc giá trị trong DataFrame.
    """
    legend_dict = {
        "1": "CUỘN CÓ NCR ĐẦU VÀO", "2": "ĐANG SX XUỐNG CUỘN", "3": "CUỘN THỪA CHẠY LẠI",
        "4": "LỖI TRONG CUỘN", "5": "HẾT CUỘN", "6": "CÒN CUỘN"
    }
    pattern = r"^(\d+)\s*[\.:]\s*(.*)" 
    for col in df.columns:
        match = re.search(pattern, str(col).strip())
        if match:
            code = match.group(1); desc = match.group(2).strip()
            if len(desc) > 2: legend_dict[code] = desc

    str_cols = df.select_dtypes(include=['object']).columns
    for col in str_cols:
        if len(df) > 0:
            unique_vals = df[col].dropna().unique()
            for val in unique_vals:
                match = re.search(pattern, str(val).strip())
                if match:
                    code = match.group(1); desc = match.group(2).strip()
                    if len(desc) > 4: legend_dict[code] = desc
    return legend_dict

def decode_roll_status(status_str: Any, legend_dict: Dict[str, str]) -> List[str]:
    """
    Giải mã chuỗi trạng thái (VD: '1, 4') thành mô tả chi tiết dựa trên legend_dict.
    """
    if pd.isna(status_str) or status_str == 0: return []
    status_str = str(status_str).strip()
    if not status_str or status_str.lower() in ['nan', '0', '0.0', '']: return []
    
    parts = re.split(r'[+,;]', status_str)
    decoded_parts = []
    for part in parts:
        code = part.strip()
        if not code: continue
        try:
            if float(code).is_integer(): code = str(int(float(code)))
        except: pass
        
        if code in legend_dict: decoded_parts.append(f"<b>{code}.</b> {legend_dict[code]}")
        else: decoded_parts.append(f"<b>{code}.</b> (Mã lạ)")
    return decoded_parts

def clean_number(val: Any) -> float:
    """Helper để làm sạch chuỗi số (xóa dấu phẩy, _, ...)."""
    try:
        if pd.isna(val): return 0.0
        s = str(val).replace(',', '').replace('_', '')
        if not s.strip(): return 0.0
        return float(s)
    except: return 0.0

# ==========================================
# CÁC HÀM MỚI (CHO TRANG PHÂN TÍCH NÂNG CAO)
# ==========================================

def clean_number_advanced(val: Any) -> float:
    """Xử lý số liệu mạnh hơn: bỏ %, handle string rỗng, units."""
    try:
        if pd.isna(val): return 0.0
        s = str(val).replace(',', '').replace('_', '')
        # Remove % if present
        s = s.replace('%', '')
        
        # Use Regex to extract the first valid float/int number found
        match = re.search(r"[-+]?(?:\d*\.\d+|\d+)", s)
        if match:
            return float(match.group())
        return 0.0
    except: return 0.0

def shorten_ext_col_name(col_name: str) -> str:
    """Rút gọn tên cột mở rộng (Đồng hồ/Vật tư) cho hiển thị trên st.metric."""
    c = str(col_name).strip()
    c_upper = c.upper()
    
    # Bảng ánh xạ theo thứ tự ưu tiên (cụ thể trước, tổng quát sau)
    # Nhãn rút gọn dùng tiếng Việt tự nhiên, dễ hiểu
    mappings = [
        ('SỐ MÉT/CUỘN THEO ĐỒNG HỒ',                          'Số mét (Đồng hồ)'),
        ('SỐ MÉT CUỘN THEO ĐỒNG HỒ',                           'Số mét (Đồng hồ)'),
        ('%SỐ MÉT THIẾU',                                       '% Mét thiếu'),
        ('% SỐ MÉT THIẾU',                                      '% Mét thiếu'),
        ('SỐ MÉT THIẾU GIỮA ĐỒNG HỒ VÀ THẺ VẬT TƯ',          'Mét thiếu (ĐH - Thẻ VT)'),
        ('SỐ MÉT THIẾU',                                        'Mét thiếu'),
        ('SỐ CÁI THEO ĐỊNH MỨC TỪ ĐỒNG HỒ',                   'Số cái theo Định mức'),
        ('SỐ CÁI THEO ĐỊNH MỨC',                                'Số cái theo Định mức'),
        ('CHÊNH LỆCH THÀNH PHẨM THỰC TẾ VÀ THÀNH PHẨM THEO ĐỒNG HỒ',  'CL: TP thực tế - TP đồng hồ'),
        ('CHÊNH LỆCH THÀNH PHẨM SỐ MÉT THẺ VẬT TƯ',           'CL: TP thẻ vật tư - TP đồng hồ'),
        ('CHÊNH LỆCH GIỮA SỐ TÚI QUI RA TỪ SỐ MÉT CUỘN VÀ SỐ TÚI QUI RA', 'CL: Túi qui từ Mét - từ KG'),
        ('CHÊNH LỆCH GIỮA SỐ TÚI SẢN XUẤT THỰC TẾ VÀ SỐ TÚI QUI',        'CL: Túi SX thực tế - Túi qui'),
        ('CHÊNH LỆCH GIỮA SỐ TÚI',                             'Chênh lệch Túi'),
        ('CHÊNH LỆCH',                                          'Chênh lệch'),
        ('ĐỒNG HỒ',                                             'Đồng hồ'),
        ('ĐỊNH MỨC',                                             'Định mức'),
        ('THẺ VẬT TƯ',                                          'Thẻ vật tư'),
    ]
    
    for keyword, short in mappings:
        if keyword in c_upper:
            return short
    
    # Fallback: cắt ngắn nếu quá 30 ký tự
    if len(c) > 30:
        return c[:27] + "..."
    return c

def identify_complex_defect_cols(df_columns: Union[pd.Index, List[str]]) -> List[str]:
    """
    Xác định cột lỗi cho file format mới (Header 2 tầng đã gộp).
    Logic: Loại trừ cột hệ thống, cột tổng, cột %. Còn lại là lỗi.
    """
    system_keywords = [
        'NGÀY', 'SỐ MÁY', 'CA SX', 'THÔNG TIN CUỘN', 'SỐ THỨ TỰ', 
        'NHÀ CUNG CẤP', 'MÁY TRÁNG', 'HỢP ĐỒNG', 'LỆNH SẢN XUẤT', 
        'SỐ MÉT', 'SỐ KG', 'SỐ TÚI QUI', 'CHÊNH LỆCH', 'GHI CHÚ', 'UNNAMED',
        'TỔNG SẢN PHẨM', 'SẢN PHẨM ĐẠT', 'SẢN PHẨM KHÔNG ĐẠT', 'TỔNG SP LỖI',
        'TỔNG PHẾ', 'TỈ LỆ', 'TỶ LỆ', '%', 'XẾP MÁY', 'PHÂN LOẠI',
        'ĐỒNG HỒ', 'ĐỊNH MỨC', 'THẺ VẬT TƯ', 'SỐ CÁI'
    ]
    
    defect_cols = []
    
    for col in df_columns:
        c_upper = str(col).upper().strip()
        
        # Whitelist summary columns (Exceptions to System Keywords)
        whitelist_prefixes = ["TỔNG LỖI DO", "TỔNG LÕI DO", "TỔNG TÚI THÀNH PHẨM THIẾU"] 
        is_whitelisted = False
        for wl in whitelist_prefixes:
            if wl in c_upper:
                is_whitelisted = True
                break
        
        if is_whitelisted:
            defect_cols.append(col)
            continue

        # 1. Bỏ qua nếu tên cột chứa từ khóa hệ thống
        is_system = False
        for kw in system_keywords:
            if kw in c_upper:
                is_system = True
                break
        
        # Logic phụ: Nếu cột bắt đầu bằng % -> Bỏ
        if c_upper.startswith("%"): is_system = True
        
        if is_system: continue
        
        defect_cols.append(col)
        
    return defect_cols

# ==========================================
# CÁC HÀM CŨ (PHỤC VỤ TOOL CŨ - GIỮ NGUYÊN)
# ==========================================

def identify_defect_columns(df_columns: List[str], manual_anchor_name: Optional[str] = None) -> List[int]:
    """Identify indices of defect columns (Old Logic)."""
    defect_cols_indices = []
    start_scan_index = -1
    include_anchor_column = False
    
    if manual_anchor_name:
        for idx, col in enumerate(df_columns):
            if str(col).strip() == str(manual_anchor_name).strip():
                start_scan_index = idx
                c_upper = str(col).upper()
                if not any(k in c_upper for k in ["TỔNG", "CHÊNH LỆCH", "KHÔNG ĐẠT", "PHẾ", "%"]):
                    include_anchor_column = True
                break
    
    if start_scan_index == -1:
        target_anchor = "CHÊNH LỆCH GIỮA SỐ TÚI SẢN XUẤT THỰC TẾ" 
        for idx, col in enumerate(df_columns):
            col_upper = str(col).upper().strip()
            if target_anchor in col_upper:
                if "%" in col_upper: start_scan_index = idx; break
                start_scan_index = idx 
    
    if start_scan_index == -1:
        backup_anchor_keywords = ["XÌ ĐÁY DO MANH CHÙNG", "XÌ ĐÁY", "XI DAY DO MANH CHUNG"]
        for idx, col in enumerate(df_columns):
            col_upper = str(col).upper().strip()
            if any(kw in col_upper for kw in backup_anchor_keywords):
                if "%" in col_upper: continue
                start_scan_index = idx
                include_anchor_column = True
                break

    blacklist_keywords = ['STT', 'MÉT', 'KG', 'TRỌNG LƯỢNG', 'SIZE', 'THỰC TẾ', 'MÁY', 'NGÀY', 'CA', 'HỢP ĐỒNG', 'MÃ HÀNG', 'GHI CHÚ', '%', 'TỶ LỆ', 'ĐẠT', 'CHÊNH LỆCH', 'TỔNG SỐ', 'TỔNG PHẾ', 'TỔNG CỘNG', 'TỔNG SP', 'ĐỒNG HỒ', 'ĐỊNH MỨC', 'THẺ VẬT TƯ', 'SỐ CÁI', 'XẾP GIỮ', 'XẾP MÁY', 'QUI RA', 'SỐ TÚI QUI']
    # Các keyword mở rộng: nếu tên cột chứa 1 trong số này, LUÔN bị blacklist bất kể bắt đầu bằng số hay không
    force_blacklist_keywords = ['ĐỒNG HỒ', 'ĐỊNH MỨC', 'THẺ VẬT TƯ', 'XẾP GIỮ', 'XẾP MÁY', 'QUI RA', 'SỐ TÚI QUI', 'SỐ CÁI']
    base_keywords = ['NGÀY', 'SỐ MÁY', 'CA', 'STT', 'HỢP ĐỒNG', 'MÃ HÀNG', 'GHI CHÚ']

    for idx, col in enumerate(df_columns):
        if start_scan_index != -1:
            if include_anchor_column:
                if idx < start_scan_index: continue
            else:
                if idx <= start_scan_index: continue
        c_upper = str(col).upper().strip()
        if any(b in c_upper for b in base_keywords): continue
        if "%" in c_upper: continue
        if "QUAI" in c_upper: continue
        if "5-10MM" in c_upper: continue 

        # Kiểm tra force-blacklist trước (các cột mở rộng luôn bị loại)
        if any(fb in c_upper for fb in force_blacklist_keywords): continue

        is_blacklisted = False
        for bl in blacklist_keywords:
            if bl in c_upper:
                if re.match(r"^\d", c_upper): 
                    if "TỔNG" in c_upper or "%" in c_upper: is_blacklisted = True
                    else: is_blacklisted = False
                else: is_blacklisted = True
                break
        if is_blacklisted: continue
        defect_cols_indices.append(idx)
    return defect_cols_indices

def identify_defect_columns_for_table(df_columns: List[str], manual_anchor_name: Optional[str] = None) -> List[int]:
    """Similar to identify_defect_columns but optimized for display tables."""
    return identify_defect_columns(df_columns, manual_anchor_name)

def get_production_summary(df: pd.DataFrame, manual_anchor_name: Optional[str] = None) -> Dict[str, int]:
    """Extract production summary metrics from DataFrame."""
    summary = {"total_bags": 0, "total_fail": 0, "total_waste": 0}
    col_prod = None; col_fail = None; cols_deduct = [] 
    for col in df.columns:
        c_upper = str(col).upper().strip()
        if "%" in c_upper: continue 
        if ("TỔNG" in c_upper or "TONG" in c_upper) and ("SẢN PHẨM" in c_upper or "TÚI" in c_upper or "SL" in c_upper):
            if "LỖI" not in c_upper and "PHẾ" not in c_upper and "KHÔNG" not in c_upper:
                col_prod = col
        if "SỐ LƯỢNG KHÔNG ĐẠT" in c_upper: col_fail = col
        elif ("KHÔNG ĐẠT" in c_upper or "PHẾ PHẨM" in c_upper) and not col_fail: col_fail = col
        elif ("TỔNG SP LỖI" in c_upper or "TỔNG PHẾ" in c_upper) and not col_fail: col_fail = col
        is_deduct = False
        if "QUAI" in c_upper: is_deduct = True
        if "5-10MM" in c_upper: is_deduct = True
        if is_deduct: cols_deduct.append(col)
        
    for idx, row in df.iterrows():
        row_prefix = " ".join([str(val).upper().strip() for val in row.iloc[:3]])
        if "TỔNG" in row_prefix or "TOTAL" in row_prefix:
            if col_prod: summary["total_bags"] = int(clean_number(row[col_prod]))
            val_fail = 0
            if col_fail: 
                val_fail = int(clean_number(row[col_fail]))
                summary["total_fail"] = val_fail
            deduct_sum = 0
            for c_deduct in cols_deduct:
                deduct_sum += clean_number(row[c_deduct])
            summary["total_waste"] = int(max(0, val_fail - deduct_sum))
            break 
    return summary

def process_single_dataframe(
    df: pd.DataFrame, 
    source_name: str, 
    error_threshold_percent: float, 
    global_logs: List[str], 
    manual_anchor_name: Optional[str] = None
) -> Tuple[pd.DataFrame, int, Dict[str, str]]:
    """
    Process a single dataframe to extract defect details.
    
    Args:
        df: Input DataFrame.
        source_name: Name of the file/source.
        error_threshold_percent: Threshold to include defect in result.
        global_logs: List to append logs to.
        manual_anchor_name: Anchor column name.
        
    Returns:
        Processed DataFrame, Missing Bags Count, Legend Map.
    """
    missing_bags_count = 0 
    legend_map = {} 
    try:
        legend_map = extract_defect_legend(df)
        keyword_missing = "THIẾU SO VỚI QUY"
        found_rows_mask = df.astype(str).apply(lambda x: x.str.contains(keyword_missing, case=False).any(), axis=1)
        if found_rows_mask.any():
            target_row = df[found_rows_mask].iloc[0]
            numeric_values = pd.to_numeric(target_row, errors='coerce').dropna()
            vals = numeric_values[numeric_values != 0]
            if not vals.empty: missing_bags_count = int(vals.abs().max())
            
        df.columns = [str(col).strip() for col in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^Unnamed') & (df.columns != 'nan')]
        if 'SỐ MÁY' in df.columns:
            df = df.dropna(subset=['SỐ MÁY'])
            df = df[~df['SỐ MÁY'].astype(str).str.upper().str.contains("TỔNG", na=False)]
            df = df[~df['SỐ MÁY'].astype(str).str.upper().str.contains("SỐ MÁY", na=False)] 
            
        note_col = 'GHI CHÚ' 
        for col in df.columns:
            if "GHI CHÚ" in col.upper() or "TÌNH TRẠNG" in col.upper():
                note_col = col; break
                
        base_cols = ['NGÀY', 'SỐ MÁY', 'CA SX', 'SỐ THỨ TỰ CUỘN', 'HỢP ĐỒNG', 'MÃ HÀNG', 'MÁY DỆT', 'MÁY TRÁNG', note_col]
        existing_base = [c for c in base_cols if c in df.columns]
        
        # Bổ sung giữ lại các cột mở rộng mới (như Đồng hồ, Thẻ vật tư)
        extended_keywords = ['ĐỒNG HỒ', 'ĐỊNH MỨC', 'THẺ VẬT TƯ', 'CHÊNH LỆCH']
        for col in df.columns:
            if col not in existing_base and any(kw in str(col).upper() for kw in extended_keywords):
                existing_base.append(col)
        
        total_col = 'TỔNG SẢN PHẨM' 
        for col in df.columns:
            c_up = col.upper()
            if ("TỔNG" in c_up) and ("SẢN PHẨM" in c_up or "TÚI" in c_up) and ("LỖI" not in c_up) and ("%" not in c_up):
                total_col = col; break
        if total_col in df.columns: existing_base.append(total_col)
        
        defect_indices = identify_defect_columns_for_table(df.columns, manual_anchor_name)
        value_vars = [df.columns[i] for i in defect_indices if df.columns[i] not in existing_base]
        
        if not value_vars:
            global_logs.append(f"⚠️ {source_name}: Không tìm thấy cột lỗi chi tiết nào.")
            return pd.DataFrame(), missing_bags_count, legend_map
            
        df_melted = df.melt(id_vars=existing_base, value_vars=value_vars, var_name='Loại Lỗi', value_name='Số Lượng Lỗi')
        cols_to_num = ['Số Lượng Lỗi']
        if total_col in df_melted.columns: cols_to_num.append(total_col)
        
        for col in cols_to_num:
            df_melted[col] = df_melted[col].apply(clean_number)
            
        df_melted = df_melted[df_melted['Số Lượng Lỗi'] > 0]
        
        if total_col in df_melted.columns:
            df_melted['% Lỗi'] = np.where(
                df_melted[total_col] > 0, 
                (df_melted['Số Lượng Lỗi'] / df_melted[total_col]) * 100, 
                0
            )
        else:
            df_melted['% Lỗi'] = 0
            
        df_final = df_melted[df_melted['% Lỗi'] >= error_threshold_percent].copy()
        
        if note_col in df_final.columns:
            df_final.rename(columns={note_col: 'GHI CHÚ_RAW'}, inplace=True)
        else:
            df_final['GHI CHÚ_RAW'] = ""
            
        if not df_final.empty:
            df_final['Nguồn File'] = source_name
            return df_final, missing_bags_count, legend_map
        else:
            return pd.DataFrame(), missing_bags_count, legend_map
            
    except Exception as e:
        global_logs.append(f"❌ Lỗi xử lý tại {source_name}: {str(e)}")
        return pd.DataFrame(), 0, {}