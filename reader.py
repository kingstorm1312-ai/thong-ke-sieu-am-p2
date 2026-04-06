"""
Module: reader.py
Description: Functions for reading and parsing Excel/CSV files, including complex header structures.
Refactored: 2024-12-10 (Added Type Hints and Docstrings).
"""

CURRENT_MODEL_NAME = "gemini-2.5-flash"

import pandas as pd
import io
import re
import utils
from typing import Dict, Any, Tuple, Optional, List, Union

def extract_summary_from_df(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Extract Summary Table from the DataFrame (usually at the bottom).
    Returns a dictionary: {'KEY': {'qty': ..., 'rate': ...}}
    """
    summary_raw: Dict[str, Dict[str, float]] = {}
    if df.empty: return summary_raw
    
    # 1. Find Anchor
    start_idx = -1
    target_col = None
    # Scan first 5 cols for Anchor
    for col in df.columns[:5]: 
        matches = df[col].astype(str).str.upper().str.contains("TỔNG LỖI DO SIÊU ÂM", na=False)
        if matches.any():
            start_idx = matches.idxmax()
            target_col = col
            break
            
    if start_idx == -1: return summary_raw
    
    # 2. Extract
    try:
        # Find absolute integer integer location of start_idx
        int_loc = df.index.get_loc(start_idx)
    except:
        return summary_raw

    # Limit scan
    scan_limit = min(len(df), int_loc + 25)
    
    # Identify Data Columns dynamically on the Anchor Row
    qty_col_idx = -1
    rate_col_idx = -1
    
    anchor_row = df.iloc[int_loc]
    
    numeric_indices = []
    for i in range(len(df.columns)):
        val = anchor_row.iloc[i]
        # Skip Text Column
        if i == df.columns.get_loc(target_col): continue
        
        # Check if numeric
        try:
            s_val = str(val).replace(',', '').replace('%', '')
            if not s_val.strip() or s_val.lower() == 'nan': continue
            f_val = float(s_val)
            if pd.isna(f_val): continue
            numeric_indices.append(i)
        except: pass
        
    if len(numeric_indices) >= 1:
        qty_col_idx = numeric_indices[0]
        # User Requirement: Rate is IMMEDIATELY to the right of Qty
        rate_col_idx = qty_col_idx + 1
    else:
        return summary_raw
        
    # Extraction Loop
    for i in range(int_loc, scan_limit):
        row = df.iloc[i]
        val_str = str(row[target_col]).upper().strip()
        val_norm = val_str.replace('LÕI', 'LỖI').replace('  ', ' ')
        
        found_key = None
        for key in utils.NCR_SUMMARY_ORDER:
             # Match Key
             key_norm = key.replace('LÕI', 'LỖI')
             if key_norm in val_norm:
                 found_key = key
                 break
        
        if found_key:
            qty = 0.0; rate = 0.0
            if qty_col_idx != -1:
                try:
                    q_val = str(row.iloc[qty_col_idx]).replace(',', '')
                    extracted = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", q_val)
                    if extracted: qty = float(extracted[0])
                except: qty = 0.0
            
            if rate_col_idx != -1:
                try:
                    r_val = str(row.iloc[rate_col_idx]).replace(',', '').replace('%', '')
                    extracted = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", r_val)
                    if extracted:
                        rate = float(extracted[0])
                        # Fix percentage heuristic
                        if rate < 1.0 and rate > 0: rate = rate * 100
                except: rate = 0.0
                
            summary_raw[found_key] = {'qty': qty, 'rate': rate}
            
    return summary_raw

def extract_header_metadata(df: pd.DataFrame) -> Dict[str, str]:
    """
    Extract General Metadata from Fixed Header Locations (F2, G2).
    User Requirement: 
      - Item Code (Mã vật tư) = F2
      - Article Name (Tên hàng) = G2
    """
    metadata: Dict[str, str] = {}
    if df.empty or len(df) < 2: return metadata
    
    try:
        # F2 -> Row 1, Col 5
        if df.shape[1] > 5:
            val_f2 = df.iloc[1, 5]
            if pd.notnull(val_f2):
                metadata['item_code'] = str(val_f2).strip()
        
        # G2 -> Row 1, Col 6
        if df.shape[1] > 6:
            val_g2 = df.iloc[1, 6]
            if pd.notnull(val_g2):
                 metadata['article_name'] = str(val_g2).strip()
    except: pass
                   
    return metadata

def scan_uploaded_files(uploaded_files: List[Any]) -> Dict[str, Tuple[int, Optional[str]]]:
    """
    Quét danh sách file upload và trả về dictionary để chọn sheet (Dùng trong Sidebar).
    """
    sheet_options = {}
    is_single_file = len(uploaded_files) == 1
    for idx, uploaded_file in enumerate(uploaded_files):
        filename = uploaded_file.name
        if filename.endswith(('.xlsx', '.xls')):
            try:
                xls = pd.ExcelFile(uploaded_file)
                for sheet in xls.sheet_names:
                    display_name = sheet if is_single_file else f"[{filename}] - {sheet}"
                    sheet_options[display_name] = (idx, sheet)
            except: pass
        elif filename.endswith('.csv'):
            display_name = "(File CSV)" if is_single_file else f"[{filename}] - (CSV)"
            sheet_options[display_name] = (idx, None)
    return sheet_options

def read_input_file(file_obj: Any, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    Hàm đọc file Bền bỉ (Robust Reader) cho file CSV/Excel thông thường.
    """
    try:
        file_obj.seek(0)
        df = pd.DataFrame()
        PREVIEW_ROWS = 50 
        
        is_excel = file_obj.name.lower().endswith(('.xlsx', '.xls'))
        header_idx = -1
        
        # --- 1. PREVIEW ---
        if is_excel: 
            xls = pd.ExcelFile(file_obj)
            target_sheet = sheet_name if sheet_name else xls.sheet_names[0]
            df_preview = pd.read_excel(xls, sheet_name=target_sheet, header=None, nrows=PREVIEW_ROWS)
        else:
            encodings = ['utf-8-sig', 'cp1252', 'latin-1']
            df_preview = None
            valid_encoding = 'utf-8-sig' # Default

            for enc in encodings:
                try:
                    file_obj.seek(0)
                    df_preview = pd.read_csv(file_obj, header=None, nrows=PREVIEW_ROWS, encoding=enc, engine='python', on_bad_lines='skip')
                    valid_encoding = enc
                    break
                except Exception:
                    continue
            
            if df_preview is None:
                # print("❌ Không dò được bảng mã của file CSV này.")
                return pd.DataFrame()

        # 2. FIND HEADER (Anchor: 'SỐ MÁY')
        for idx, row in df_preview.iterrows():
            row_str = " ".join([str(x).upper().strip() for x in row.values])
            if "SỐ MÁY" in row_str:
                header_idx = idx
                break
        
        # 3. READ FULL FILE
        file_obj.seek(0)
        if is_excel:
            target_sheet = sheet_name if sheet_name else pd.ExcelFile(file_obj).sheet_names[0]
            if header_idx != -1: 
                df = pd.read_excel(file_obj, sheet_name=target_sheet, header=header_idx)
            else: 
                df = pd.read_excel(file_obj, sheet_name=target_sheet)
        else:
            if header_idx != -1: 
                df = pd.read_csv(file_obj, encoding=valid_encoding, header=header_idx, engine='python', on_bad_lines='skip')
            else: 
                df = pd.read_csv(file_obj, encoding=valid_encoding, engine='python', on_bad_lines='skip')
            
        # Extract Metadata
        summary = extract_summary_from_df(df)
        
        file_obj.seek(0)
        df_raw_header = pd.read_excel(file_obj, sheet_name=target_sheet, header=None, nrows=5)
        header_meta = extract_header_metadata(df_raw_header)
        
        if summary: df.attrs['summary_raw'] = summary
        if header_meta: df.attrs['header_meta'] = header_meta
            
        return df
    except Exception as e:
        # print(f"Final Error reading file: {e}")
        return pd.DataFrame()

def read_complex_excel_structure(file_obj: Any, sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, Optional[str], Dict[str, Any]]:
    """
    Hàm chuyên dụng đọc file Excel cấu trúc phức tạp (Header 2 tầng đã gộp).
    Returns: DataFrame, Error String (Optional), Metadata Dict.
    """
    try:
        file_obj.seek(0)
        # 1. LOAD TOÀN BỘ SHEET VÀO MEMORY (Header=None)
        xls = pd.ExcelFile(file_obj)
        target_sheet = sheet_name if sheet_name else xls.sheet_names[0]
        
        df_raw_full = pd.read_excel(xls, sheet_name=target_sheet, header=None)
        
        if df_raw_full.empty:
            return pd.DataFrame(), "File rỗng.", {}

        metadata: Dict[str, Any] = {} 

        # --- METADATA EXTRACTION (F2, G2) ---
        try:
             # F2 -> Row 1 (0-idx), Col 5. (Index 5 is Correct for F)
             if len(df_raw_full) > 1 and len(df_raw_full.columns) > 5:
                 val_f2 = str(df_raw_full.iloc[1, 5]).strip()
                 if val_f2 and val_f2.lower() != 'nan': metadata['item_code'] = val_f2
                 
             # G2 -> Row 1 (0-idx), Col 6
             if len(df_raw_full) > 1 and len(df_raw_full.columns) > 6:
                 val_g2 = str(df_raw_full.iloc[1, 6]).strip()
                 if val_g2 and val_g2.lower() != 'nan': metadata['article_name'] = val_g2
        except: pass

        # [NEW] Summary Extraction with Explicit Anchor
        summary_raw: Dict[str, Dict[str, float]] = {}
        try:
            # Anchor Strategy: Find "TỔNG LỖI DO SIÊU ÂM" row first
            start_row_idx = -1
            for index, row in df_raw_full.iterrows():
                if pd.isna(row.iloc[0]): continue
                val_str = str(row.iloc[0]).upper().strip()
                val_norm = val_str.replace('LÕI', 'LỖI').replace('  ', ' ')
                
                if "TỔNG LỖI DO SIÊU ÂM" in val_norm:
                    start_row_idx = index
                    break
            
            if start_row_idx != -1:
                scan_end = min(len(df_raw_full), start_row_idx + 25)
                
                for i in range(start_row_idx, scan_end):
                    row = df_raw_full.iloc[i]
                    if pd.isna(row.iloc[0]): continue
                    val_str = str(row.iloc[0]).upper().strip()
                    val_norm = val_str.replace('LÕI', 'LỖI').replace('  ', ' ')
                    
                    found_key = None
                    for key in utils.NCR_SUMMARY_ORDER:
                         key_norm = key.replace('LÕI', 'LỖI').replace('  ', ' ')
                         if key_norm in val_norm:
                             found_key = key
                             break
                    
                    if found_key:
                        # Extract Data (Col J=9, K=10)
                         try:
                             qty = row.iloc[9] if (len(row) > 9 and pd.notnull(row.iloc[9])) else 0
                             rate_raw = row.iloc[10] if (len(row) > 10 and pd.notnull(row.iloc[10])) else 0
                             
                             if isinstance(qty, str): 
                                 qty_clean = re.sub(r'[^\d.]', '', qty.replace(',', ''))
                                 qty = float(qty_clean) if qty_clean else 0
                             if isinstance(rate_raw, str): 
                                 rate_clean = re.sub(r'[^\d.]', '', rate_raw.replace(',', ''))
                                 rate_raw = float(rate_clean) if rate_clean else 0
                                 
                             # Convert decimal to percent
                             rate = float(rate_raw) * 100
                         except:
                             qty = 0; rate = 0
                             
                         summary_raw[found_key] = {'qty': qty, 'rate': rate}
            
            metadata['summary_raw'] = summary_raw
            
        except Exception:
            pass

        # 2. Tìm dòng header trong bộ nhớ (Scan 30 dòng đầu)
        header_row_idx = -1
        scan_limit = min(30, len(df_raw_full))
        
        for idx in range(scan_limit):
            row = df_raw_full.iloc[idx]
            row_str = " ".join([str(val).upper() for val in row])
            if "NGÀY" in row_str and "SỐ MÁY" in row_str:
                header_row_idx = idx
                break
        
        if header_row_idx == -1:
            return pd.DataFrame(), "Không tìm thấy dòng tiêu đề chứa 'NGÀY' và 'SỐ MÁY'.", metadata 

        # 3. Xử lý Header
        if header_row_idx + 1 >= len(df_raw_full):
             return pd.DataFrame(), "File không có dữ liệu sau dòng tiêu đề.", metadata 

        row_main = df_raw_full.iloc[header_row_idx]
        row_sub = df_raw_full.iloc[header_row_idx + 1]
        
        new_columns = []
        system_keywords = ['NGÀY', 'SỐ MÁY', 'CA SX', 'THÔNG TIN CUỘN', 'GHI CHÚ', 'SỐ THỨ TỰ', 'NHÀ CUNG CẤP', 'MÁY TRÁNG', 'HỢP ĐỒNG', 'LỆNH SẢN XUẤT', 'SỐ MÉT', 'SỐ KG', 'MÃ HÀNG', 'NCC']
        
        for i in range(len(row_main)):
            val_main = str(row_main.iloc[i]).strip() if i < len(row_main) else "nan"
            val_sub = str(row_sub.iloc[i]).strip() if i < len(row_sub) else "nan"
            val_main_upper = val_main.upper()
            
            # Nếu là cột hệ thống -> Lấy dòng trên
            is_system = False
            for kw in system_keywords:
                if kw in val_main_upper:
                    new_columns.append(val_main)
                    is_system = True
                    break
            if is_system: continue

            if val_main == 'nan' or val_main == '':
                 if val_sub != 'nan' and val_sub != '': new_columns.append(val_sub)
                 else: new_columns.append(f"Unnamed_{i}")
                 continue

            final_name = val_main
            if "%" in val_sub or "TỶ LỆ" in val_sub.upper():
                final_name = f"% {val_main}" 
            elif len(val_sub) > 4 and not val_sub.replace('.','').isdigit(): 
                final_name = val_sub
            
            new_columns.append(final_name)

        # 4. Cắt lấy dữ liệu thật
        df_data = df_raw_full.iloc[header_row_idx + 1:].copy()
        df_data.reset_index(drop=True, inplace=True)
        
        current_cols = len(df_data.columns)
        expected_cols = len(new_columns)
        
        if current_cols <= expected_cols:
             df_data.columns = new_columns[:current_cols]
        else:
             df_data.columns = new_columns + [f"Extra_{j}" for j in range(current_cols - expected_cols)]
        
        return df_data, None, metadata
        
    except Exception as e:
        return pd.DataFrame(), str(e), {}