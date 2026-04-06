"""
Module: processor.py
Description: Centralized backend logic for data processing, KPI calculation, and report generation preparation.
Refactored: 2024-12-10 (Added Type Hints, Docstrings, and consolidated logic).
"""

import pandas as pd
import numpy as np
import utils
import reader
import streamlit as st
import os
from typing import List, Dict, Tuple, Optional, Any, Union
import datetime

# =============================================================================
# 1. CORE PROCESSING LOGIC (OLD FORM & NEW FORM)
# =============================================================================

def process_uploaded_new_form_data(
    selected_sheets_data: List[Dict[str, Any]], 
    progress_bar: Any = None
) -> Tuple[Optional[pd.DataFrame], List[str], Dict[str, str], Dict[str, Any]]:
    """
    Process a list of uploaded Excel sheets using the 'New Form' logic (Complex Structure).
    
    Args:
        selected_sheets_data: List of dicts containing file info and sheet names.
        progress_bar: Streamlit progress bar object (optional).
        
    Returns:
        Tuple containing:
        - Result DataFrame (concatenated)
        - List of log messages
        - Combined Legend dictionary
        - Metadata dictionary
    """
    master_data: List[pd.DataFrame] = []
    logs: List[str] = []
    combined_legend: Dict[str, str] = {}
    final_metadata: Dict[str, Any] = {}
    
    total_files = len(selected_sheets_data)
    
    for i, item in enumerate(selected_sheets_data):
        df, error, metadata = reader.read_complex_excel_structure(item["file"], item["sheet_name"])
        if error:
            logs.append(f"❌ {item['display_name']}: {error}")
            continue
            
        if metadata:
            logs.append(f"ℹ️ Metadata tìm thấy: {metadata}")
            final_metadata.update(metadata)
        
        try:
            legend = utils.extract_defect_legend(df)
            combined_legend.update(legend)
        except Exception: 
            pass

        logs.append(f"✅ {item['display_name']}: Đọc thành công {len(df)} dòng.")
        
        # 1. Identify Columns
        col_prod = next((c for c in df.columns if "TỔNG SẢN PHẨM" in str(c).upper() and "LỖI" not in str(c).upper()), None)
        col_fail_total = next((c for c in df.columns if "TỔNG SP LỖI" in str(c).upper() or "PHẾ" in str(c).upper()), None)
        
        defect_cols = utils.identify_complex_defect_cols(df.columns)
        if not defect_cols:
            logs.append(f"⚠️ {item['display_name']}: Không tìm thấy cột lỗi chi tiết.")
            continue
        
        base_cols = [c for c in df.columns if c not in defect_cols]
        # Preserve important base columns
        important_base_keywords = ['NGÀY', 'SỐ MÁY', 'CA SX', 'SỐ THỨ TỰ', 'GHI CHÚ', 'THÔNG TIN CUỘN', 'HỢP ĐỒNG', 'NHÀ CUNG CẤP']
        final_base = [c for c in base_cols if any(k in str(c).upper() for k in important_base_keywords)]
        
        # 2. Melt Data
        df['__Temp_ID'] = df.index
        df_melt_temp = df.melt(id_vars=final_base + ['__Temp_ID'], value_vars=defect_cols, var_name='Loại Lỗi', value_name='Số Lượng Lỗi')
        
        # --- Cleaning Helper ---
        def vectorized_clean(series: pd.Series) -> pd.Series:
            s = series.astype(str).str.replace(r'[%,_]', '', regex=True)
            s_extracted = s.str.extract(r"([-+]?(?:\d*\.\d+|\d+))", expand=False)
            return pd.to_numeric(s_extracted, errors='coerce').fillna(0)
        # -----------------------

        # 3. Map KPIs (Vectorized)
        if col_prod:
            s_prod = vectorized_clean(df[col_prod])
            s_prod = np.maximum(0, s_prod)
        else:
            s_prod = pd.Series(0, index=df.index)
            
        if col_fail_total:
            s_fail = vectorized_clean(df[col_fail_total])
            s_fail = np.maximum(0, s_fail)
        else:
            s_fail = pd.Series(0, index=df.index)

        df_melt_temp['KPI_Roll_Production'] = df_melt_temp['__Temp_ID'].map(s_prod)
        df_melt_temp['KPI_Roll_Fail'] = df_melt_temp['__Temp_ID'].map(s_fail)
             
        # Repairable Calculation
        cols_repairable = [c for c in df.columns if "QUAI" in str(c).upper() or "5-10MM" in str(c).upper() or "IN NHẸ" in str(c).upper()]
        
        if cols_repairable:
            s_repair = pd.Series(0.0, index=df.index)
            for c in cols_repairable:
                s_c = vectorized_clean(df[c])
                s_repair += np.maximum(0, s_c)
            df_melt_temp['KPI_Roll_Repair'] = df_melt_temp['__Temp_ID'].map(s_repair)
        else:
            df_melt_temp['KPI_Roll_Repair'] = 0

        # 4. Clean & Filter
        df_melt_temp['Số Lượng Lỗi'] = vectorized_clean(df_melt_temp['Số Lượng Lỗi'])
        df_melt_final = df_melt_temp[df_melt_temp['Số Lượng Lỗi'] > 0].copy()
        
        note_col = next((c for c in final_base if "GHI CHÚ" in str(c).upper()), None)
        df_melt_final['GHI CHÚ_RAW'] = df_melt_final[note_col] if note_col else ""

        if not df_melt_final.empty:
            df_melt_final['Nguồn File'] = item['display_name']
            if metadata:
                if 'item_code' in metadata: df_melt_final['Item_Code'] = metadata['item_code']
                if 'article_name' in metadata: df_melt_final['Article_Name'] = metadata['article_name']
            master_data.append(df_melt_final)
            
        if progress_bar:
            progress_bar.progress((i + 1) / total_files)
    
    if progress_bar: progress_bar.empty()
    
    # 5. Merge
    if master_data:
        df_res = pd.concat(master_data, ignore_index=True)
        if 'NGÀY' in df_res.columns:
            df_res['NGÀY'] = pd.to_datetime(df_res['NGÀY'], errors='coerce')
            df_res = df_res.sort_values(by='NGÀY')
        if 'SỐ MÁY' in df_res.columns:
            df_res['SỐ MÁY'] = df_res['SỐ MÁY'].astype(str).replace(r'\.0$', '', regex=True)
        
        roll_col = next((c for c in df_res.columns if "SỐ THỨ TỰ" in str(c).upper()), None)
        if roll_col: 
            df_res['SỐ THỨ TỰ CUỘN'] = pd.to_numeric(df_res[roll_col], errors='coerce').fillna(0).astype(int)
        else: 
            df_res['SỐ THỨ TỰ CUỘN'] = 0
        
        df_res['Unique_Row_Key'] = df_res['Nguồn File'] + "_" + df_res['__Temp_ID'].astype(str)
        return df_res, logs, combined_legend, final_metadata
    else:
        return None, logs, combined_legend, final_metadata

def process_old_form_logic(
    selected_sheets_data: List[Dict[str, Any]], 
    threshold: float, 
    manual_anchor: Optional[str],
    progress_bar: Any = None
) -> Tuple[Optional[pd.DataFrame], List[str], Dict[str, Any], int, Dict[str, Any]]:
    """
    Process uploaded files using 'Old Form' logic (Streamlit App V1).
    
    Args:
        selected_sheets_data: List of selected sheets.
        threshold: Error threshold for filtering.
        manual_anchor: Manual anchor column name if auto-detection fails.

    Returns:
        Result DF, Logs, Summary Metrics (Grand Prod, Fail, Waste), Total Missing Bags, Combined Legend.
    """
    master_data = []
    logs = []
    total_missing_bags = 0
    combined_legend = {}
    grand_production = 0
    grand_fail = 0
    grand_waste = 0
    
    total_files = len(selected_sheets_data)
    
    for i, item in enumerate(selected_sheets_data):
        try:
            df = reader.read_input_file(item["file"], item["sheet_name"])

            if not df.empty:
                # Calc Summary stats
                summary_metrics = utils.get_production_summary(df, manual_anchor_name=manual_anchor)
                grand_production += summary_metrics["total_bags"]
                grand_fail += summary_metrics["total_fail"]
                grand_waste += summary_metrics["total_waste"] 

                # Process Details
                df_processed, missing_count, legend = utils.process_single_dataframe(
                    df, item["display_name"], threshold, logs, manual_anchor_name=manual_anchor
                )
                total_missing_bags += missing_count
                combined_legend.update(legend)
                if not df_processed.empty: master_data.append(df_processed)
            else:
                logs.append(f"⚠️ Không đọc được dữ liệu từ {item['display_name']}")
        except Exception as e:
            logs.append(f"❌ Lỗi {item['display_name']}: {str(e)}")
        
        if progress_bar:
            progress_bar.progress((i + 1) / total_files)

    if progress_bar: progress_bar.empty()

    if master_data:
        df_result = pd.concat(master_data, ignore_index=True)
        
        # --- LOGIC UPDATE: Remove "Lỗi in nhẹ chờ hướng" from Waste ---
        try:
            mask_light_print = df_result['Loại Lỗi'].astype(str).str.contains("Lỗi in nhẹ chờ hướng", case=False, na=False)
            total_light_print_error = df_result.loc[mask_light_print, 'Số Lượng Lỗi'].sum()
            if total_light_print_error > 0:
                grand_waste = max(0, grand_waste - total_light_print_error)
                logs.append(f"ℹ️ Đã loại trừ {total_light_print_error:,.0f} lỗi 'In nhẹ chờ hướng' ra khỏi tổng Phế.")
        except Exception as e:
            logs.append(f"⚠️ Lỗi khi tính lại Phế cho In nhẹ: {str(e)}")
        
        # --- Normalization ---
        df_result = _normalize_dataframe(df_result)
        
        metrics = {
            "grand_production": grand_production,
            "grand_fail": grand_fail,
            "grand_waste": grand_waste
        }
        return df_result, logs, metrics, total_missing_bags, combined_legend
    
    return None, logs, {"grand_production": 0, "grand_fail": 0, "grand_waste": 0}, 0, {}

def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Internal helper to normalize common columns."""
    if 'SỐ MÁY' in df.columns:
        df['SỐ MÁY'] = df['SỐ MÁY'].astype(str).replace(r'\.0$', '', regex=True)
    
    if 'SỐ THỨ TỰ CUỘN' in df.columns:
        df['SỐ THỨ TỰ CUỘN'] = pd.to_numeric(df['SỐ THỨ TỰ CUỘN'], errors='coerce').fillna(0).astype(int)
    
    if 'CA SX' in df.columns:
        df['CA SX'] = df['CA SX'].astype(str).replace('nan', '')
    
    if 'NGÀY' in df.columns:
        df['NGÀY'] = pd.to_datetime(df['NGÀY'], dayfirst=True, errors='coerce')
        df = df.sort_values(by='NGÀY')

    # Create dummy ID if needed
    try:
        df['Unique_Roll_ID'] = (
            df['SỐ MÁY'].astype(str) + "_" + 
            df['SỐ THỨ TỰ CUỘN'].astype(str) + "_" + 
            df['NGÀY'].astype(str)
        )
    except:
        df['Unique_Roll_ID'] = df.index.astype(str)
    
    df['Unique_Row_Key'] = df['Unique_Roll_ID']
    
    # Fill missing KPI cols with 0
    for col in ['KPI_Roll_Production', 'KPI_Roll_Fail', 'KPI_Roll_Repair']:
        if col not in df.columns: df[col] = 0.0
            
    return df

# =============================================================================
# 2. FILTERING AND METRICS CALCULATOR
# =============================================================================

def filter_dataframe(
    df: pd.DataFrame, 
    date_range: Optional[Tuple[datetime.date, datetime.date]], 
    selected_machines: List[str], 
    selected_contracts: List[str], 
    selected_suppliers: List[str],
    contract_col: Optional[str],
    supplier_col: Optional[str]
) -> pd.DataFrame:
    """
    Centralized DataFrame filtering logic.
    """
    df_filtered = df.copy()
    if date_range and len(date_range) == 2 and 'NGÀY' in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered['NGÀY'].dt.date >= date_range[0]) & (df_filtered['NGÀY'].dt.date <= date_range[1])]
    
    if selected_machines and 'SỐ MÁY' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['SỐ MÁY'].isin(selected_machines)]
        
    if selected_contracts and contract_col:
        df_filtered = df_filtered[df_filtered[contract_col].astype(str).isin(selected_contracts)]
        
    if selected_suppliers and supplier_col:
        df_filtered = df_filtered[df_filtered[supplier_col].astype(str).isin(selected_suppliers)]
        
    return df_filtered

def calculate_new_form_kpis(
    df_filtered: pd.DataFrame, 
    grand_fail_raw: float, 
    grand_waste_raw: float,
    grand_production: float,
    enable_pack_sep: bool, 
    enable_xepgiut_sep: bool
) -> Dict[str, Any]:
    """
    Calculate dynamic KPIs based on User Toggles (Pack Separator, Xep Giut Separator).
    """
    # 1. Calculate specific error type sums
    pack_mask = df_filtered['Loại Lỗi'].astype(str).str.contains("ĐÓNG GÓI|DONG GOI", case=False, regex=True)
    total_pack_error = df_filtered.loc[pack_mask, 'Số Lượng Lỗi'].sum()
    
    xepgiut_mask = df_filtered['Loại Lỗi'].astype(str).str.contains("XẾP GIỰT|XEP GIUT", case=False, regex=True)
    total_xepgiut_error = df_filtered.loc[xepgiut_mask, 'Số Lượng Lỗi'].sum()
    
    kpi_pack = 0
    kpi_xepgiut = 0
    kpi_fail = grand_fail_raw
    kpi_waste = grand_waste_raw
    
    # Logic Toggles
    if enable_pack_sep:
        kpi_pack = total_pack_error
    
    if enable_xepgiut_sep:
        kpi_xepgiut = total_xepgiut_error
        
    # Final OK Calculation
    if enable_pack_sep:
        # Pack is separated, so subtraction reduces OK? 
        # Logic: OK = Prod - Fail(Defects) - Pack(Seperate)
        kpi_ok = max(0, grand_production - kpi_fail - kpi_pack)
    else:
        # Pack is OK
        kpi_ok = max(0, grand_production - kpi_fail)

    return {
        "kpi_ok": kpi_ok,
        "kpi_fail": kpi_fail,
        "kpi_waste": kpi_waste,
        "kpi_pack": kpi_pack,
        "kpi_xepgiut": kpi_xepgiut,
        "total_pack_error": total_pack_error,
        "total_xepgiut_error": total_xepgiut_error,
        "pack_mask": pack_mask,
        "xepgiut_mask": xepgiut_mask
    }

# =============================================================================
# 3. PDF DATA PREPARATION
# =============================================================================

def prepare_ncr_data(
    row_info: pd.Series, 
    df_roll_view: pd.DataFrame, 
    contract_col: Optional[str], 
    weight_col: Optional[str],
    metadata_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Prepare the dictionary required by NCRGenerator for a single roll.
    """
    r_total = row_info.get('KPI_Roll_Production', 0)
    
    # 1. Defects List
    defects_list = []
    # Keyword filter for summary items
    def is_summary_item(name: str) -> bool:
        n_up = str(name).upper()
        for k in utils.NCR_SUMMARY_ORDER:
            if k in n_up: return True
        return False

    mask_summary = df_roll_view['Loại Lỗi'].apply(is_summary_item)
    df_details_view = df_roll_view[~mask_summary].sort_values(by='Số Lượng Lỗi', ascending=False)
    
    for _, row_d in df_details_view.iterrows():
        d_qty = row_d['Số Lượng Lỗi']
        d_rate = (d_qty / r_total * 100) if r_total > 0 else 0
        defects_list.append({
            "name": row_d['Loại Lỗi'],
            "qty": d_qty,
            "rate": d_rate
        })
        
    # 2. Summary List
    calc_summary = utils.calculate_ncr_summary(df_roll_view)
    summary_list = []
    for key in utils.NCR_SUMMARY_ORDER:
        if key in metadata_summary:
            qty = metadata_summary[key].get('qty', 0)
            d_rate = metadata_summary[key].get('rate', 0)
        else:
            qty = calc_summary.get(key, 0)
            d_rate = (qty / r_total * 100) if r_total > 0 else 0
        
        summary_list.append({
            "name": key,
            "qty": qty,
            "rate": d_rate
        })
        
    # 3. Info Fields
    date_val = row_info['NGÀY']
    date_str = date_val.strftime("%d/%m/%Y") if pd.notnull(date_val) and hasattr(date_val, 'strftime') else str(date_val)
    contract_val = row_info[contract_col] if contract_col else ""
    
    qty_val = f"{row_info[weight_col]} kg" if (weight_col and pd.notnull(row_info.get(weight_col))) else f"{row_info.get('KPI_Roll_Production',0):,.0f} túi"
    
    return {
        "date_str": date_str,
        "ncr_no": f"{row_info.get('SỐ THỨ TỰ CUỘN', 'NA')}/{row_info.get('SỐ MÁY', 'NA')}",
        "item_name": row_info.get('Article_Name', ''),
        "item_code": row_info.get('Item_Code', ''), 
        "contract": str(contract_val),
        "quantity": str(qty_val),
        "defects": defects_list,
        "summary": summary_list
    }

def prepare_bulk_ncr_data(
    df_roll: pd.DataFrame,
    total_prod_group: float,
    unique_machines: int,
    contract_col: Optional[str],
    weight_col: Optional[str],
    metadata_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Prepare data for BULK (Aggregated) NCR Report.
    """
    # 1. Info Fields
    max_date = df_roll['NGÀY'].max()
    date_str = max_date.strftime("%d/%m/%Y") if pd.notnull(max_date) else ""
    
    contracts = df_roll[contract_col].astype(str).unique() if contract_col else []
    contract_str = ", ".join(contracts) if len(contracts) < 3 else f"{len(contracts)} Hợp đồng"
    
    # Quantity (Sum weights if available, else Bags)
    if weight_col and pd.api.types.is_numeric_dtype(df_roll[weight_col]):
        total_w = df_roll.drop_duplicates(subset=['Unique_Row_Key'])[weight_col].sum()
        qty_str = f"{total_w:,.1f} kg"
    else:
        qty_str = f"{total_prod_group:,.0f} túi"
    
    # Roll List String
    roll_ids = sorted(df_roll['SỐ THỨ TỰ CUỘN'].unique())
    if len(roll_ids) <= 5:
        roll_str = ",".join(map(str, roll_ids))
    else:
        roll_str = f"{len(roll_ids)} Cuộn ({min(roll_ids)}->{max(roll_ids)})"

    # 2. Defects Aggregation
    df_defects_agg = df_roll.groupby('Loại Lỗi')['Số Lượng Lỗi'].sum().reset_index()
    df_defects_agg = df_defects_agg[df_defects_agg['Số Lượng Lỗi'] > 0].sort_values(by='Số Lượng Lỗi', ascending=False)
    
    # Filter Summary Items
    def is_summary_item(name: str) -> bool:
        n_up = str(name).upper()
        for k in utils.NCR_SUMMARY_ORDER:
            if k in n_up: return True
        return False
        
    mask_summary = df_defects_agg['Loại Lỗi'].apply(is_summary_item)
    df_details_agg = df_defects_agg[~mask_summary]

    defects_list = []
    for _, row_d in df_details_agg.iterrows():
        d_qty = row_d['Số Lượng Lỗi']
        d_rate = (d_qty / total_prod_group * 100) if total_prod_group > 0 else 0
        defects_list.append({
            "name": row_d['Loại Lỗi'],
            "qty": d_qty,
            "rate": d_rate
        })
        
    # 3. Summary List
    calc_summary = utils.calculate_ncr_summary(df_defects_agg)
    summary_list = []
    for key in utils.NCR_SUMMARY_ORDER:
        if key in metadata_summary:
            qty = metadata_summary[key].get('qty', 0)
            d_rate = metadata_summary[key].get('rate', 0)
        else:
            qty = calc_summary.get(key, 0)
            d_rate = (qty / total_prod_group * 100) if total_prod_group > 0 else 0
        
        summary_list.append({
            "name": key,
            "qty": qty,
            "rate": d_rate
        })

    return {
        "date_str": date_str,
        "ncr_no": f"Batch: {roll_str} / {unique_machines} Máy",
        "item_name": "Túi (Tổng Hợp)", 
        "item_code": "N/A", 
        "contract": contract_str,
        "quantity": qty_str,
        "defects": defects_list,
        "summary": summary_list
    }