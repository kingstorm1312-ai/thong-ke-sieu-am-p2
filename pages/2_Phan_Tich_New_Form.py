CURRENT_MODEL_NAME = "gemini-2.5-flash"

import streamlit as st
import pandas as pd
import plotly.express as px
import io
import sys
import os

# --- LIÊN KẾT MODULE ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils
import reader
import processor   # Module Mới
import visualizer  # Module Mới
import ncr_generator # Module PDF NCR

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Phân tích New Form", page_icon="📊", layout="wide")

# --- CSS STYLING ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] { font-family: "Arial", sans-serif; }
    .material-icons, span[class^="material-"], span[class*=" material-"] { font-family: 'Material Icons' !important; }
    .metric-card {
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 6px solid #4B0082; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px;
    }
    .metric-value { font-size: 28px; font-weight: 800; color: #0e1117; margin: 5px 0; }
    .metric-label { font-size: 15px; color: #555; font-weight: 500; }
    .status-box {
        background-color: #e8f4f8; padding: 15px; border-radius: 8px; 
        border-left: 5px solid #00a8cc; color: #00607a; margin: 10px 0;
    }
    .status-title { font-weight: bold; text-transform: uppercase; border-bottom: 1px solid #bce6f2; display: block; margin-bottom: 5px;}
    .streamlit-expanderHeader { font-weight: bold; font-family: "Arial", sans-serif; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'nf_data_processed' not in st.session_state:
    st.session_state.nf_data_processed = False
    st.session_state.nf_df_result = None
    st.session_state.nf_logs = []
    st.session_state.nf_combined_legend = {}

st.title("📊 Phân tích New Form")
st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Nhập Dữ Liệu")
    uploaded_files = st.file_uploader("Upload Excel (.xlsx)", type=['xlsx', 'xls'], accept_multiple_files=True, key="nf_uploader")
    selected_sheets_data = []
    
    if uploaded_files:
        st.divider()
        st.header("⚙️ Cấu Hình")
        with st.spinner("Đang đọc file..."):
            sheet_map = reader.scan_uploaded_files(uploaded_files)
        if sheet_map:
            default_sheet = [k for k in sheet_map.keys() if "🧾" in k]
            if not default_sheet and sheet_map: default_sheet = [list(sheet_map.keys())[0]]
            selected_keys = st.multiselect("Chọn Sheet dữ liệu:", options=list(sheet_map.keys()), default=default_sheet)
            for key in selected_keys:
                file_idx, sheet_name = sheet_map[key]
                selected_sheets_data.append({"file": uploaded_files[file_idx], "sheet_name": sheet_name, "display_name": key})
    
    st.divider()
    st.divider()
    btn_process = st.button("🔄 Cập nhật dữ liệu gốc", type="primary", disabled=not selected_sheets_data)

# --- BACKEND PROCESSING (GỌI PROCESSOR) ---
if btn_process:
    progress = st.progress(0)
    df_res, logs, combined_legend, metadata = processor.process_uploaded_new_form_data(selected_sheets_data, progress)
    
    if df_res is not None:
        st.session_state.nf_df_result = df_res
        st.session_state.nf_logs = logs
        st.session_state.nf_combined_legend = combined_legend
        st.session_state.metadata = metadata
        st.session_state.nf_data_processed = True
        st.rerun()
    else:
        st.session_state.nf_data_processed = False
        st.error("Không trích xuất được dữ liệu.")
        if logs: st.write(logs)

# --- FRONTEND (GỌI VISUALIZER) ---
if st.session_state.nf_data_processed and st.session_state.nf_df_result is not None:
    df_raw = st.session_state.nf_df_result
    logs = st.session_state.nf_logs
    combined_legend = st.session_state.nf_combined_legend

    # 1. FILTER UI
    with st.container():
        st.markdown("### 🗓️ Bộ Lọc Dữ Liệu")
        contract_col = next((c for c in df_raw.columns if "HỢP ĐỒNG" in str(c).upper()), None)
        supplier_col = next((c for c in df_raw.columns if "NHÀ CUNG CẤP" in str(c).upper()), None)
        
        # Tìm cột Ngày Tráng/In & Số Kg Cuộn (Quan trọng để hiển thị và gom nhóm)
        print_date_col = next((c for c in df_raw.columns if "NGÀY TRÁNG" in str(c).upper() or "NGÀY IN" in str(c).upper()), None)
        weight_col = next((c for c in df_raw.columns if "SỐ KG" in str(c).upper() and "CUỘN" in str(c).upper()), None)

        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            if 'NGÀY' in df_raw.columns:
                extra_date_cols = [c for c in df_raw.columns if ("NGÀY TRÁNG" in str(c).upper() or "NGÀY IN" in str(c).upper()) and c != 'NGÀY']
                for c in extra_date_cols:
                    if not pd.api.types.is_datetime64_any_dtype(df_raw[c]):
                        df_raw[c] = pd.to_datetime(df_raw[c], errors='coerce')

                # Filter Range Input
                valid_dates = df_raw['NGÀY'].dropna()
                if not valid_dates.empty:
                    min_date = valid_dates.min().date()
                    max_date = valid_dates.max().date()
                    date_range = st.date_input("Chọn thời gian:", value=(min_date, max_date), min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
                else: date_range = None
            else: date_range = None
        with col_f2:
            unique_machines = sorted(df_raw['SỐ MÁY'].unique()) if 'SỐ MÁY' in df_raw.columns else []
            selected_machines = st.multiselect("Chọn Máy:", unique_machines)
        with col_f3:
            unique_contracts = sorted(df_raw[contract_col].dropna().astype(str).unique()) if contract_col else []
            selected_contracts = st.multiselect("Chọn Hợp Đồng:", unique_contracts)
        with col_f4:
            unique_suppliers = sorted(df_raw[supplier_col].dropna().astype(str).unique()) if supplier_col else []
            selected_suppliers = st.multiselect("Chọn Nhà Cung Cấp:", unique_suppliers)

    # FILTER LOGIC
    df_filtered = processor.filter_dataframe(
        df_raw, date_range, selected_machines, selected_contracts, selected_suppliers, contract_col, supplier_col
    )
    
    # --- TÍNH NĂNG MỚI: TÁCH LỖI ĐÓNG GÓI & XẾP GIỰT ---
    st.markdown("---")
    col_toggle_1, col_toggle_2, _ = st.columns([1, 1, 3])
    with col_toggle_1:
        enable_pack_sep = st.toggle("Tách 'Đóng Gói Riêng'", value=True, help="Bật: Hiển thị đóng gói riêng biệt.\nTắt: Tính đóng gói vào hàng ĐẠT.")
    with col_toggle_2:
        enable_xepgiut_sep = st.toggle("Ẩn 'Xếp Giựt Mũi Tàu'", value=True, help="Bật: Coi là 'Đạt Thủ Công', tách khỏi Fail và ẩn khỏi biểu đồ.\nTắt: Tính là Lỗi bình thường.")

    # KPI CALCULATION
    df_unique_rolls = df_filtered.drop_duplicates(subset=['Unique_Row_Key'])
    grand_production = df_unique_rolls['KPI_Roll_Production'].sum()
    grand_fail_raw = df_unique_rolls['KPI_Roll_Fail'].sum()
    grand_repair_raw = df_unique_rolls['KPI_Roll_Repair'].sum()
    grand_waste_raw = max(0, grand_fail_raw - grand_repair_raw)
    
    # Call Processor for KPIs
    kpi_results = processor.calculate_new_form_kpis(
        df_filtered, grand_fail_raw, grand_waste_raw, grand_production, enable_pack_sep, enable_xepgiut_sep
    )
    
    kpi_ok = kpi_results["kpi_ok"]
    kpi_fail = kpi_results["kpi_fail"]
    kpi_waste = kpi_results["kpi_waste"]
    kpi_pack = kpi_results["kpi_pack"]
    kpi_xepgiut = kpi_results["kpi_xepgiut"]
    total_pack_error = kpi_results["total_pack_error"]
    total_xepgiut_error = kpi_results["total_xepgiut_error"]
    pack_mask = kpi_results["pack_mask"]
    xepgiut_mask = kpi_results["xepgiut_mask"]

    # 5. Create df_visuals
    mask_hide = pd.Series(False, index=df_filtered.index)
    if enable_pack_sep: mask_hide |= pack_mask
    if enable_xepgiut_sep: mask_hide |= xepgiut_mask
    df_visuals = df_filtered[~mask_hide].copy()

    pct_fail = (kpi_waste / grand_production * 100) if grand_production > 0 else 0

    # ========================== GIAO DIỆN TABS ==========================
    tab_overview, tab_rolls, tab_machines, tab_raw_data = st.tabs([
        "📊 Tổng Quan", 
        "🔍 Phân Tích Cuộn", 
        "🏭 Chi Tiết Theo Máy", 
        "📋 Dữ Liệu Gốc"
    ])

    # --- TAB 1: TỔNG QUAN ---
    with tab_overview:
        st.markdown("### Tổng Quan Sản Xuất")
        
        # A. KPI Cards

        

        c_kpi1, c_kpi2, c_kpi3, c_kpi4, c_kpi5, c_kpi6 = st.columns(6)
        c_kpi1.metric("Tổng Sản Lượng", f"{grand_production:,.0f}")
        c_kpi2.metric("Đạt (OK)", f"{kpi_ok:,.0f}", help="Sản lượng đạt chất lượng.")
        c_kpi3.metric("Tổng Fail", f"{kpi_fail:,.0f}", f"{pct_fail:.2f}% (Phế)", delta_color="inverse")
        
        if enable_pack_sep:
             c_kpi4.metric("Đóng Gói Riêng", f"{kpi_pack:,.0f}", "Tách Riêng", delta_color="off")
        else:
             c_kpi4.metric("Đóng Gói Riêng", f"{total_pack_error:,.0f}", "Gộp OK", delta_color="normal")
             
        if enable_xepgiut_sep:
             c_kpi5.metric("Xếp giựt mũi tàu", f"{kpi_xepgiut:,.0f}", "Xếp thủ công", delta_color="off")
        else:
             c_kpi5.metric("Xếp giựt mũi tàu", f"{total_xepgiut_error:,.0f}", "Tính là Lỗi", delta_color="inverse")
             
        c_kpi6.metric("Tổng Phế", f"{kpi_waste:,.0f}")

        st.divider()

        # B. Sunburst Chart
        if grand_production > 0:
            col_chart, col_note = st.columns([3, 1])
            with col_chart:
                # SUNBURST SPECIAL LOGIC: "Dat" already includes "Xep Giut" now based on new KPI calc
                labels = ["Tổng SX", "Đạt", "Không Đạt", "Sửa Được", "Phế"]
                parents = ["", "Tổng SX", "Tổng SX", "Không Đạt", "Không Đạt"]
                values = [grand_production, kpi_ok, kpi_fail, grand_repair_raw, kpi_waste]
                
                if enable_pack_sep and kpi_pack > 0:
                    labels.append("Đóng Gói Riêng")
                    parents.append("Tổng SX")
                    values.append(kpi_pack)
                
                # Removed 'Xep Giut' branch appending because it's merged into 'Dat'
                
                percents = [1.0 if grand_production > 0 else 0]
                for v in values[1:]: percents.append(v/grand_production if grand_production > 0 else 0)
                text_labels = [f"{p:.2%}" if p>0 else "0%" for p in percents]

                fig_sun = visualizer.draw_sunburst(labels, parents, values, text_labels, percents)
                st.plotly_chart(fig_sun, use_container_width=True)
            with col_note:
                note_content = "**Ghi chú:**\n* **% hiển thị:** Tỷ lệ so với Tổng Sản Xuất.\n* **Sửa Được:** Lỗi nhẹ.\n* **Phế:** Lỗi nặng."
                if enable_pack_sep:
                     note_content += "\n* **Đóng Gói Riêng:** Hàng đóng gói riêng, tách khỏi Đạt, không tính là Lỗi."
                st.info(note_content)

        # C. Global Pareto
        st.divider()
        st.markdown("### Phân Tích Pareto & Tỷ Lệ Lỗi (Toàn Bộ)")
        
        df_pareto = df_visuals.groupby('Loại Lỗi')['Số Lượng Lỗi'].sum().reset_index().sort_values(by='Số Lượng Lỗi', ascending=False)
        total_defects = df_pareto['Số Lượng Lỗi'].sum()
        df_pareto['Cumulative %'] = 100 * df_pareto['Số Lượng Lỗi'].cumsum() / total_defects
        df_pareto['Rate_On_Prod'] = (df_pareto['Số Lượng Lỗi'] / grand_production * 100) if grand_production > 0 else 0

        subtab_p1, subtab_p2 = st.tabs(["Biểu đồ", "Dữ Liệu Bảng"])
        with subtab_p1:
            st.markdown("**Biểu đồ Pareto Lỗi**")
            st.plotly_chart(visualizer.draw_pareto_main(df_pareto), use_container_width=True, key="pareto_global")
            
            st.divider()
            st.markdown("**Tỷ trọng lỗi chính**")
            vital_few = df_pareto[df_pareto['Cumulative %'] <= 85].copy()
            if vital_few.empty: vital_few = df_pareto.head(1)
            st.plotly_chart(visualizer.draw_pie_chart(vital_few), use_container_width=True)
            
            st.markdown("**Tỷ lệ % Lỗi trên TỔNG SẢN LƯỢNG**")
            df_rate_chart = df_pareto.head(20).sort_values(by='Rate_On_Prod', ascending=True) 
            st.plotly_chart(visualizer.draw_horizontal_rate_chart(df_rate_chart), use_container_width=True)

        with subtab_p2:
             df_pareto_display = df_pareto.rename(columns={
                 'Cumulative %': 'Tỷ Lệ Tích Lũy (%)',
                 'Rate_On_Prod': '% Lỗi / Tổng SX'
             })
             format_rules_pareto = {
                 'Số Lượng Lỗi': '{:,.0f}',
                 'Tỷ Lệ Tích Lũy (%)': '{:,.2f}%',
                 '% Lỗi / Tổng SX': '{:,.2f}%'
             }
             st.dataframe(df_pareto_display.style.format(format_rules_pareto), use_container_width=True, height=600, hide_index=True)

    # --- TAB 2: PHÂN TÍCH CUỘN ---
    with tab_rolls:
        st.markdown("### Tra Cứu & Tình Trạng Cuộn")
        if not df_filtered.empty and 'SỐ THỨ TỰ CUỘN' in df_filtered.columns:
            id_cols = ['SỐ THỨ TỰ CUỘN', 'SỐ MÁY']
            if 'NGÀY' in df_filtered.columns: id_cols.append('NGÀY')
            if contract_col: id_cols.append(contract_col)
            if print_date_col: id_cols.append(print_date_col)
            if weight_col: id_cols.append(weight_col)
            
            all_rolls = df_filtered[id_cols].drop_duplicates().sort_values(by=['NGÀY', 'SỐ THỨ TỰ CUỘN'], ascending=[False, True])
            
            def create_label(row):
                d = row['NGÀY'].strftime('%d/%m') if (pd.notnull(row.get('NGÀY')) and hasattr(row['NGÀY'], 'strftime')) else "N/A"
                c = str(row[contract_col]) if (contract_col and pd.notnull(row[contract_col])) else "N/A"
                extra_info = []
                if print_date_col and pd.notnull(row[print_date_col]):
                    p_val = row[print_date_col]
                    p_str = p_val.strftime('%d/%m') if hasattr(p_val, 'strftime') else str(p_val)
                    extra_info.append(f"In: {p_str}")
                if weight_col and pd.notnull(row[weight_col]): extra_info.append(f"{row[weight_col]}kg")
                extra_str = f" | {' '.join(extra_info)}" if extra_info else ""
                return f"Cuộn {row['SỐ THỨ TỰ CUỘN']} | Ngày: {d} | HĐ: {c}{extra_str} (Máy {row['SỐ MÁY']})"
            
            all_rolls['label'] = all_rolls.apply(create_label, axis=1)
            all_rolls['label'] = all_rolls.apply(create_label, axis=1)
            
            # --- BUTTON LỌC TOP CUỘN CAO HƠN TB ---
            # --- BUTTON LỌC TOP CUỘN CAO HƠN TB ---
            col_search_1, col_search_2 = st.columns([3, 1])
            with col_search_2:
                 st.write("") # Spacer
                 st.write("") # Spacer
                 if st.button("⚡ Lọc Cuộn Lỗi Cao (>TB)", help="Lọc các cuộn có tỷ lệ lỗi cao hơn mức trung bình toàn nhà máy.", type="primary"):
                     # 1. Calc Global Average
                     current_avg_rate_ref = (grand_fail_raw / grand_production * 100) if grand_production > 0 else 0
                     
                     # 2. Calc Rate for Each Roll
                     group_keys_calc = [c for c in id_cols if c in df_filtered.columns]
                     df_roll_gr = df_filtered.drop_duplicates(subset=['Unique_Row_Key']).groupby(group_keys_calc).agg({'KPI_Roll_Production':'sum','KPI_Roll_Fail':'sum'}).reset_index()
                     df_roll_gr['Rate'] = (df_roll_gr['KPI_Roll_Fail'] / df_roll_gr['KPI_Roll_Production'] * 100).fillna(0)
                     
                     # 3. Filter > Avg
                     high_error_rolls = df_roll_gr[df_roll_gr['Rate'] > current_avg_rate_ref]
                     
                     # 4. Get Labels
                     def make_id(r): return f"{r['SỐ THỨ TỰ CUỘN']}_{r['SỐ MÁY']}"
                     high_ids = set(high_error_rolls.apply(make_id, axis=1))
                     
                     filtered_labels = all_rolls[all_rolls.apply(lambda x: f"{x['SỐ THỨ TỰ CUỘN']}_{x['SỐ MÁY']}", axis=1).isin(high_ids)]['label'].tolist()
                     
                     if filtered_labels:
                         st.session_state["ms_rolls"] = filtered_labels
                         # NO RERUN NEEDED since we are before the widget
                     else:
                         st.toast("Không có cuộn nào cao hơn mức trung bình!", icon="✅")

            with col_search_1:
                 selected_roll_labels = st.multiselect("Chọn Cuộn (Mặc định: Tất Cả):", all_rolls['label'].unique(), key="ms_rolls")

            # --- LOGIC MẶC ĐỊNH LÀ CHỌN TẤT CẢ ---
            if not selected_roll_labels:
                target_labels = all_rolls['label'].unique()
                is_all_selected = True
                st.info(f"Đang hiển thị phân tích cho TẤT CẢ {len(target_labels)} cuộn.")
            else:
                target_labels = selected_roll_labels
                is_all_selected = False

            if len(target_labels) > 0:
                selected_infos = all_rolls[all_rolls['label'].isin(target_labels)]
                mask = pd.Series(False, index=df_filtered.index)
                for _, row in selected_infos.iterrows():
                    sub_mask = (df_filtered['SỐ THỨ TỰ CUỘN'] == row['SỐ THỨ TỰ CUỘN']) & (df_filtered['SỐ MÁY'] == row['SỐ MÁY'])
                    if 'NGÀY' in df_filtered.columns: sub_mask &= (df_filtered['NGÀY'] == row['NGÀY'])
                    if contract_col: sub_mask &= (df_filtered[contract_col].astype(str) == str(row[contract_col]))
                    mask |= sub_mask
                df_roll = df_filtered[mask]
                
                if not df_roll.empty:
                    df_roll_unique_rows = df_roll.drop_duplicates(subset=['Unique_Row_Key'])
                    total_prod_group = df_roll_unique_rows['KPI_Roll_Production'].sum()
                    total_fail_group = df_roll_unique_rows['KPI_Roll_Fail'].sum()
                    
                    # --- BRANCHING: CHỌN 1 CUỘN ---
                    if len(target_labels) == 1:
                         r0 = df_roll_unique_rows.iloc[0]
                         r_total = r0['KPI_Roll_Production']
                         r_fail = r0['KPI_Roll_Fail']
                         st.info(f"Đang xem chi tiết Cuộn {r0['SỐ THỨ TỰ CUỘN']} (Lỗi: {r_fail/r_total*100:.2f}%)")
                         
                         # --- HIỂN THỊ CÁC CỘT MỞ RỘNG (ĐỒNG HỒ/ĐỊNH MỨC) ---
                         ext_keywords = ['ĐỒNG HỒ', 'ĐỊNH MỨC', 'THẺ VẬT TƯ', 'CHÊNH LỆCH']
                         ext_cols = [c for c in r0.index if any(kw in str(c).upper() for kw in ext_keywords) and pd.notnull(r0[c]) and str(r0[c]).strip() != ""]
                         if ext_cols:
                             with st.expander("⏱️ Thông số đối chiếu Đồng hồ / Vật tư", expanded=True):
                                 for i in range(0, len(ext_cols), 3):
                                     cols = st.columns(3)
                                     for j in range(3):
                                         if i + j < len(ext_cols):
                                             c_name = ext_cols[i + j]
                                             val = r0[c_name]
                                             if isinstance(val, (float, np.float64, np.float32)): val = round(float(val), 3)
                                             # Fix JSON Serialization Streamlit Error
                                             c_clean = str(c_name).replace("\\", "/").replace('"', "'").replace("\n", " ").replace("\r", " ")
                                             v_clean = str(val).replace("\\", "/")
                                             cols[j].metric(c_clean, v_clean)

                         
                         df_roll_view = df_roll.groupby('Loại Lỗi')['Số Lượng Lỗi'].sum().reset_index()
                         df_roll_view = df_roll_view[df_roll_view['Số Lượng Lỗi'] > 0]
                         
                         df_roll_pareto = df_roll_view.sort_values(by='Số Lượng Lỗi', ascending=False)
                         df_roll_pareto['Cumulative %'] = 100 * df_roll_pareto['Số Lượng Lỗi'].cumsum() / df_roll_pareto['Số Lượng Lỗi'].sum()
                         df_roll_pareto['% Trên Tổng Túi'] = (df_roll_pareto['Số Lượng Lỗi'] / r_total * 100).fillna(0)
                         
                         st.plotly_chart(visualizer.draw_roll_pareto(df_roll_pareto, r0['SỐ THỨ TỰ CUỘN']), use_container_width=True)
                         
                         combined_notes = " | ".join(df_roll_unique_rows['GHI CHÚ_RAW'].dropna().astype(str).unique())
                         decoded = utils.decode_roll_status(combined_notes, combined_legend)
                         if decoded: st.markdown(f"<div class='status-box'>{'<br>'.join(decoded)}</div>", unsafe_allow_html=True)

                         # --- NCR PDF EXPORT ---
                         st.divider()
                         col_pdf, _ = st.columns([1, 1])
                         with col_pdf:
                             if st.button("🖨️ Xuất Phiếu NCR (PDF)", type="secondary", help="Tạo file PDF phiếu NCR cho cuộn này từ Template."):
                                 with st.spinner("Đang tạo PDF..."):
                                     try:
                                         # 1. Prepare Data
                                         template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Template', 'Phieu_NCR.xlsx'))
                                         
                                         meta_summary = st.session_state.get('metadata', {}).get('summary_raw', {})
                                         
                                         ncr_data = processor.prepare_ncr_data(
                                             row_info=r0, 
                                             df_roll_view=df_roll_view, 
                                             contract_col=contract_col, 
                                             weight_col=weight_col,
                                             metadata_summary=meta_summary
                                         )
                                         
                                         # 2. Generate
                                         generator = ncr_generator.NCRGenerator(template_path)
                                         # Output dir in pages/NCR_Output to be accessible? Or temp.
                                         # Streamlit can serve files from anywhere if we read binary.
                                         output_dir = os.path.join(os.path.dirname(__file__), '..', 'NCR_Output')
                                         
                                         result_path = generator.generate(ncr_data, output_dir=output_dir)
                                         
                                         if result_path and os.path.exists(result_path):
                                             st.success(f"Đã tạo xong: {os.path.basename(result_path)}")
                                             # Read content to download
                                             with open(result_path, "rb") as f:
                                                 pdf_data = f.read()
                                             
                                             file_ext = os.path.splitext(result_path)[1]
                                             mime_type = "application/pdf" if file_ext.lower() == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                             
                                             st.download_button(
                                                 label=f"📥 Tải {os.path.basename(result_path)}",
                                                 data=pdf_data,
                                                 file_name=os.path.basename(result_path),
                                                 mime=mime_type
                                             )
                                         else:
                                             st.error("Không thể tạo file (Trả về None).")
                                     
                                     except Exception as e:
                                         st.error(f"Lỗi khi tạo NCR: {str(e)}")

                    # --- BRANCHING: CHỌN NHIỀU CUỘN ---
                    else:
                        weighted_fail_rate = (total_fail_group / total_prod_group * 100) if total_prod_group > 0 else 0
                        
                        st.markdown(f"#### 📊 Phân Tích Mũi Nhọn ({len(target_labels)} Cuộn)")
                        k1, k2, k3 = st.columns(3)
                        k1.metric("Tổng Sản Lượng", f"{total_prod_group:,.0f}")
                        k2.metric("Tổng Lỗi", f"{total_fail_group:,.0f}")
                        k3.metric("Tỷ Lệ Lỗi (Gia Quyền)", f"{weighted_fail_rate:.2f}%")
                        
                        # --- HIỂN THỊ TỔNG HỢP CỰC BỘ (ĐỒNG HỒ/ĐỊNH MỨC) KHI CHỌN NHIỀU CUỘN ---
                        ext_keywords = ['ĐỒNG HỒ', 'ĐỊNH MỨC', 'THẺ VẬT TƯ', 'CHÊNH LỆCH']
                        ext_cols = [c for c in df_roll.columns if any(kw in str(c).upper() for kw in ext_keywords)]
                        if ext_cols:
                            unique_rows = df_roll.drop_duplicates(subset=['Unique_Row_Key'])
                            valid_ext_cols = []
                            for c in ext_cols:
                                if '%' not in str(c):
                                    num_series = pd.to_numeric(unique_rows[c].astype(str).str.replace(',', '').str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce')
                                    if num_series.notnull().any():
                                        valid_ext_cols.append((c, num_series))
                            
                            if valid_ext_cols:
                                with st.expander(f"⏱️ Tổng Hợp Đối Chiếu Đồng Hồ / Vật Tư ({len(target_labels)} Cuộn)", expanded=True):
                                    for i in range(0, len(valid_ext_cols), 3):
                                        cols = st.columns(3)
                                        for j in range(3):
                                            if i + j < len(valid_ext_cols):
                                                c_name, num_series = valid_ext_cols[i + j]
                                                val = num_series.sum()
                                                if pd.isna(val) or val == float('inf') or val == float('-inf'): val = 0.0
                                                c_str = str(c_name).replace("\\", "/").replace('"', "'").replace('\n', ' ').replace('\r', ' ')
                                                c_clean = f"Tổng {c_str}"
                                                cols[j].metric(c_clean, f"{float(val):,.1f}")
                        
                        st.markdown("#### 1. So Sánh & Tham Chiếu")
                        group_keys = [c for c in id_cols if c in df_roll.columns]
                        roll_stats_df = df_roll.drop_duplicates(subset=['Unique_Row_Key']).groupby(group_keys, dropna=False).agg({'KPI_Roll_Production':'sum','KPI_Roll_Fail':'sum'}).reset_index()
                        roll_stats_df['Rate'] = (roll_stats_df['KPI_Roll_Fail'] / roll_stats_df['KPI_Roll_Production'] * 100).fillna(0).replace([float('inf'), float('-inf')], 0)
                        roll_stats_df['Display_Name'] = roll_stats_df.apply(lambda r: f"C.{r['SỐ THỨ TỰ CUỘN']} (M{r['SỐ MÁY']})".replace("\\", "/"), axis=1)
                        
                        current_period_avg = (grand_fail_raw / grand_production * 100) if grand_production > 0 else 0
                        st.plotly_chart(visualizer.draw_comparative_bar_with_reference(roll_stats_df, current_period_avg), use_container_width=True)

                        # --- BULK/AGGREGATED NCR EXPORT ---
                        st.divider()
                        col_pdf_bulk, _ = st.columns([1, 1])
                        with col_pdf_bulk:
                             if st.button("🖨️ Xuất NCR Tổng Hợp (Gộp)", type="secondary", help="Tạo 1 file PDF NCR tổng hợp cho tất cả các cuộn đang chọn (Cộng gộp lỗi)."):
                                 with st.spinner("Đang tạo PDF tổng hợp..."):
                                     try:
                                         # 1. Prepare Data (Aggregation)
                                         template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Template', 'Phieu_NCR.xlsx'))
                                         
                                         meta_summary = st.session_state.get('metadata', {}).get('summary_raw', {})
                                         
                                         ncr_data = processor.prepare_bulk_ncr_data(
                                             df_roll=df_roll,
                                             total_prod_group=total_prod_group,
                                             unique_machines=len(unique_machines), 
                                             contract_col=contract_col,
                                             weight_col=weight_col,
                                             metadata_summary=meta_summary
                                         )
                                         
                                         # 2. Generate
                                         generator = ncr_generator.NCRGenerator(template_path)
                                         output_dir = os.path.join(os.path.dirname(__file__), '..', 'NCR_Output')
                                         
                                         result_path = generator.generate(ncr_data, output_dir=output_dir)
                                         
                                         if result_path and os.path.exists(result_path):
                                             st.success(f"Đã tạo xong: {os.path.basename(result_path)}")
                                             with open(result_path, "rb") as f:
                                                 pdf_data = f.read()
                                             
                                             file_ext = os.path.splitext(result_path)[1]
                                             mime_type = "application/pdf" if file_ext.lower() == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                             
                                             st.download_button(
                                                 label=f"📥 Tải NCR Tổng Hợp",
                                                 data=pdf_data,
                                                 file_name=os.path.basename(result_path),
                                                 mime=mime_type
                                             )
                                         else:
                                             st.error("Không thể tạo file.")
                                     
                                     except Exception as e:
                                         st.error(f"Lỗi khi tạo NCR Gộp: {str(e)}")
                        
                        st.markdown("#### 2. Phân Tích Nguyên Nhân Gốc (Mũi Nhọn)")
                        
                        # Prepare df_roll_visuals based on toggles
                        mask_hide_roll = pd.Series(False, index=df_roll.index)
                        if enable_pack_sep:
                             mask_hide_roll |= df_roll['Loại Lỗi'].astype(str).str.contains("ĐÓNG GÓI|DONG GOI", case=False, regex=True)
                        if enable_xepgiut_sep:
                             mask_hide_roll |= df_roll['Loại Lỗi'].astype(str).str.contains("XẾP GIỰT|XEP GIUT", case=False, regex=True)
                        
                        df_roll_visuals = df_roll[~mask_hide_roll].copy()
                        
                        # SECTION A: Heatmap
                        col_heat_title, col_heat_opt = st.columns([2, 1])
                        with col_heat_title:
                             st.markdown("**A. Bản Đồ Nhiệt (Heatmap)** - *Nhận diện lỗi hệ thống theo dãy*")
                        with col_heat_opt:
                             view_mode = st.radio("Chế độ màu:", ["Số Lượng Lỗi", "Tỷ Lệ Lỗi (%)"], horizontal=True, label_visibility="collapsed")
                        
                        color_mode = 'Rate' if "Tỷ Lệ" in view_mode else 'Count'

                        # Heatmap Data Preparation
                        df_roll['_Key_ID'] = (
                            df_roll['SỐ THỨ TỰ CUỘN'].astype(str) + '_' + 
                            df_roll['SỐ MÁY'].astype(str) + '_' + 
                            df_roll['NGÀY'].astype(str)
                        )
                        df_roll_visuals['_Key_ID'] = (
                            df_roll_visuals['SỐ THỨ TỰ CUỘN'].astype(str) + '_' + 
                            df_roll_visuals['SỐ MÁY'].astype(str) + '_' + 
                            df_roll_visuals['NGÀY'].astype(str)
                        )
                        defect_sum_map = df_roll_visuals.groupby('_Key_ID')['Số Lượng Lỗi'].sum().to_dict()
                        
                        df_heat = df_roll_visuals.groupby(['_Key_ID', 'Loại Lỗi'])['Số Lượng Lỗi'].sum().reset_index()
                        df_heat.rename(columns={'Loại Lỗi': 'Defect_Type', 'Số Lượng Lỗi': 'Count'}, inplace=True)
                        
                        df_heat['Total_Defects_In_Roll'] = df_heat['_Key_ID'].map(defect_sum_map).fillna(0)
                        
                        # [FIX] Get Total Production per Roll for Rate Calculation & Tooltip
                        # KPI_Roll_Production is consistent per Roll (Key_ID)
                        prod_map = df_roll_visuals.drop_duplicates(subset=['_Key_ID']).set_index('_Key_ID')['KPI_Roll_Production'].to_dict()
                        df_heat['KPI_Roll_Production'] = df_heat['_Key_ID'].map(prod_map).fillna(0)

                        def safe_rate_calc(row):
                            d = row['KPI_Roll_Production'] # Rate based on Production
                            c = row['Count']
                            return (c / d * 100) if d > 0 else 0.0
                        df_heat['Rate'] = df_heat.apply(safe_rate_calc, axis=1)
                        
                        def parse_key_label(k_str):
                            try:
                                parts = k_str.split('_')
                                stt, may, date_raw = parts[0], parts[1], "_".join(parts[2:])
                                d_disp = date_raw
                                if '-' in date_raw:
                                     d_parts = date_raw.split(' ')[0].split('-')
                                     if len(d_parts) == 3: d_disp = f"{d_parts[2]}/{d_parts[1]}"
                                return f"C.{stt} (M{may} - {d_disp})"
                            except: return k_str
                        df_heat['Roll_Name'] = df_heat['_Key_ID'].apply(parse_key_label)
                        
                        top_defects = df_heat.groupby('Defect_Type')['Count'].sum().sort_values(ascending=False).head(10).index
                        df_heat_filtered = df_heat[df_heat['Defect_Type'].isin(top_defects)].copy()
                        
                        st.plotly_chart(visualizer.draw_heatmap(df_heat_filtered, color_by=color_mode, total_col_name="Tổng Lỗi"), use_container_width=True, key="heatmap_group")
                        
                        # SECTION B: Group Pareto
                        st.markdown(f"**B. Lỗi Mũi Nhọn (Pareto Nhóm)**")
                        df_nested = df_roll_visuals.groupby('Loại Lỗi')['Số Lượng Lỗi'].sum().reset_index().sort_values('Số Lượng Lỗi', ascending=False)
                        if not df_nested.empty:
                            total_nested = df_nested['Số Lượng Lỗi'].sum()
                            df_nested['Cumulative %'] = 100 * df_nested['Số Lượng Lỗi'].cumsum() / total_nested
                            top_contributors = df_nested[df_nested['Cumulative %'] <= 85]
                            if top_contributors.empty: top_contributors = df_nested.head(1)
                            top_names = ", ".join(top_contributors['Loại Lỗi'].tolist())
                            
                            st.success(f"📌 **Lỗi Mũi Nhọn:** {top_names} (Chiếm ~{top_contributors['Cumulative %'].max():.0f}% tổng lỗi)")
                            st.plotly_chart(visualizer.draw_pareto_main(df_nested), use_container_width=True, key="pareto_group")
            else: st.warning("Không tìm thấy dữ liệu cho các lựa chọn này.")

    # --- TAB 3: CHI TIẾT THEO MÁY ---
    with tab_machines:
        st.markdown("### Phân Tích Chi Tiết Theo Máy")
        if 'SỐ MÁY' in df_visuals.columns:
            for machine in sorted(df_visuals['SỐ MÁY'].unique()):
                with st.expander(f"🚜 MÁY: {machine}", expanded=False):
                    df_m = df_visuals[df_visuals['SỐ MÁY'] == machine]
                    df_chart_m = df_m.groupby('Loại Lỗi')['Số Lượng Lỗi'].sum().reset_index().sort_values(by='Số Lượng Lỗi', ascending=True)
                    dynamic_height = max(400, len(df_chart_m) * 35 + 100)
                    
                    st.plotly_chart(visualizer.draw_machine_chart(df_chart_m, dynamic_height), use_container_width=True)
                    st.write("Dữ liệu chi tiết:"); st.dataframe(df_m[['NGÀY', 'SỐ THỨ TỰ CUỘN', 'Loại Lỗi', 'Số Lượng Lỗi']].style.format({"NGÀY": lambda x: x.strftime("%d/%m/%Y") if pd.notnull(x) else "", "Số Lượng Lỗi": "{:,.0f}"}), use_container_width=True, height=300, hide_index=True)

    # --- TAB 4: DỮ LIỆU GỐC ---
    with tab_raw_data:
        st.markdown("### Dữ Liệu Chi Tiết Gốc")
        display_df = df_filtered.drop(columns=['Unique_Row_Key', 'GHI CHÚ_RAW', '__Temp_ID', 'KPI_Roll_Production', 'KPI_Roll_Fail', 'KPI_Roll_Repair'], errors='ignore').copy()
        format_dict = {}
        for col in display_df.columns:
            if "NGÀY" in str(col).upper():
                format_dict[col] = lambda x: x.strftime("%d/%m/%Y") if (pd.notnull(x) and hasattr(x, 'strftime')) else ""
            elif pd.api.types.is_numeric_dtype(display_df[col]):
                format_dict[col] = "{:,.2f}%" if "%" in str(col) or "TỶ LỆ" in str(col).upper() else "{:,.0f}"
        st.dataframe(display_df.style.format(format_dict), use_container_width=True, height=600, hide_index=True)
        
        # DOWNLOAD
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            st.session_state.nf_df_result.to_excel(writer, index=False, sheet_name='Data_All')
            df_pareto.to_excel(writer, index=False, sheet_name='Pareto_Analysis')
        
        st.download_button("📥 Tải Báo Cáo (Excel)", data=buffer.getvalue(), file_name="Bao_Cao_New_Form.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- DEBUG SECTION (BOTTOM) ---
    with st.expander("🛠️ Kiểm Tra Logic (DEBUG)", expanded=False):
        c_dbg1, c_dbg2 = st.columns(2)
        with c_dbg1:
            st.write("**Thông Tin Gốc (Raw):**")
            st.write(f"- Fail Raw (Excel): {grand_fail_raw:,.0f}")
            st.write(f"- Waste Raw (Excel): {grand_waste_raw:,.0f}")
            st.write(f"- Repair Raw (Excel): {grand_repair_raw:,.0f}")
        with c_dbg2:
            st.write("**Thông Tin KPI (Display):**")
            st.write(f"- Mode Pack: {'ON' if enable_pack_sep else 'OFF'}")
            st.write(f"- Mode XepGiut: {'ON' if enable_xepgiut_sep else 'OFF'}")
            st.write(f"- KPI Pack: {kpi_pack:,.0f}")
            st.write(f"- KPI XepGiut: {kpi_xepgiut:,.0f}")
            st.write(f"- KPI Fail: {kpi_fail:,.0f}")
            st.write(f"- KPI OK: {kpi_ok:,.0f}")

elif not uploaded_files: st.info("👈 Vui lòng tải file Excel (New Form) để bắt đầu phân tích.")