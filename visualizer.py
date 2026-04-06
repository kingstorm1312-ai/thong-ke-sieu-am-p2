CURRENT_MODEL_NAME = "gemini-2.5-flash"

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import streamlit as st  # Dùng cho Debug Tool

# --- CÁC HÀM PHỤ TRỢ ---
def shorten_label(text, max_len=15):
    """Cắt ngắn nhãn nếu quá dài, thêm '...'"""
    s = str(text)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s

# --- CÁC HÀM VẼ BIỂU ĐỒ ---

def draw_sunburst(labels, parents, values, text_labels, percents):
    """Vẽ biểu đồ Sunburst phân bổ chất lượng"""
    colors = ["#2E86C1", "#27AE60", "#C0392B", "#F39C12", "#922B21", "#8E44AD"]
    fig = go.Figure(go.Sunburst(
        labels=labels, parents=parents, values=values, branchvalues="total",
        textinfo="label+value+percent root", 
        texttemplate='<b>%{label}</b><br>%{value:,.0f}<br>%{percentRoot:.2%}',
        marker=dict(colors=colors), 
        hovertemplate='<b>%{label}</b><br>SL: %{value:,.0f}<br>Tỷ lệ/Tổng SX: %{percentRoot:.2%}<extra></extra>'
    ))
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=450, font=dict(family="Arial, sans-serif", size=14))
    return fig

def draw_combo_daily_trend(df_daily_top15):
    """Vẽ biểu đồ Combo (Cột + Line) xu hướng ngày - KHÔI PHỤC HÀM NÀY"""
    fig = go.Figure()
    # Cột: Số lượng lỗi
    fig.add_trace(go.Bar(
        x=df_daily_top15['Ngày_Str'], 
        y=df_daily_top15['Tổng Lỗi'],
        name='Tổng Không Đạt',
        marker_color='#C0392B',
        yaxis='y',
        text=df_daily_top15['Tổng Lỗi'],
        texttemplate='%{text:,.0f}',
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>❌ SL: %{y:,.0f}<extra></extra>' 
    ))
    # Đường: Tỷ lệ %
    fig.add_trace(go.Scatter(
        x=df_daily_top15['Ngày_Str'],
        y=df_daily_top15['Tỷ Lệ Lỗi %'],
        name='Tỷ Lệ Lỗi (%)',
        mode='lines+markers',
        yaxis='y2',
        line=dict(color='#2E86C1', width=3),
        marker=dict(size=8),
        hovertemplate='<b>%{x}</b><br>📉 Tỷ lệ: %{y:,.2f}%<extra></extra>' 
    ))
    fig.update_layout(
        xaxis=dict(type='category', automargin=True, title=""),
        yaxis=dict(title='Số Lượng Lỗi', side='left', showgrid=False),
        yaxis2=dict(title='Tỷ Lệ %', side='right', overlaying='y', showgrid=True),
        legend=dict(orientation="h", y=1.1),
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family="Arial, sans-serif")
    )
    return fig

def draw_heatmap(df_heatmap, color_by='Count', total_col_name="Tổng Túi"):
    """
    Vẽ Heatmap dùng Graph Objects (go.Heatmap)
    UPDATE: Thêm cột Tổng (Total Defects hoặc Production) vào cuối bằng Subplots.
    """
    # 1. CLEAN DATA
    df_clean = df_heatmap.copy()
    if 'Count' not in df_clean.columns: df_clean['Count'] = 0
    if 'Rate' not in df_clean.columns: df_clean['Rate'] = 0.0
    
    # Determine Denominator Column (Product or Defects)
    # If 'Total_Defects_In_Roll' exists, use it. Else fallback to 'KPI_Roll_Production'
    if 'Total_Defects_In_Roll' in df_clean.columns:
        denom_col = 'Total_Defects_In_Roll'
        denom_label = "Tổng Lỗi"
    else:
        denom_col = 'KPI_Roll_Production'
        if 'KPI_Roll_Production' not in df_clean.columns: df_clean['KPI_Roll_Production'] = 0
        denom_label = "Tổng SX"

    # 2. TẠO TOOLTIP STRING (VECTORIZED - FASTER)
    # Format number columns first
    s_denom = df_clean[denom_col].apply(lambda x: f"{x:,.0f}" if x > 0 else "N/A")
    
    # Always format production for tooltip (if exists)
    if 'KPI_Roll_Production' not in df_clean.columns: df_clean['KPI_Roll_Production'] = 0
    s_prod = df_clean['KPI_Roll_Production'].apply(lambda x: f"{x:,.0f}" if x > 0 else "N/A")
    
    s_count = df_clean['Count'].map('{:,.0f}'.format)
    s_rate = df_clean['Rate'].map('{:.2f}%'.format)
    
    # Build Tooltip (Concatenate Series)
    # Note: We must use '+' for vectorized string concatenation in Pandas
    
    t_str = (
        "<b>" + df_clean['Roll_Name'].astype(str) + "</b><br>" +
        "Loại lỗi: " + df_clean['Defect_Type'].astype(str) + "<br>" +
        "❌ SL: " + s_count + "<br>" +
        "🏭 Tổng SX: " + s_prod
    )
    
    # Conditional append for Denominator if it's NOT Total SX (avoid duplicate)
    if denom_label != "Tổng SX":
         t_str = t_str + "<br>📋 " + denom_label + ": " + s_denom
         
    t_str = t_str + "<br>📉 Tỷ lệ: " + s_rate
    
    df_clean['Tooltip_Str'] = t_str

    # 3. XÁC ĐỊNH KHUNG XƯƠNG (SKELETON) - SORT ALPHABET
    y_labels = sorted(df_clean['Roll_Name'].unique().tolist())      
    x_labels_full = sorted(df_clean['Defect_Type'].unique().tolist()) 

    # 4. PIVOT DATA THEO KHUNG CỐ ĐỊNH (DEFECTS)
    val_col = 'Rate' if color_by == 'Rate' else 'Count'
    
    matrix_z = df_clean.pivot(index='Roll_Name', columns='Defect_Type', values=val_col)
    matrix_z = matrix_z.reindex(index=y_labels, columns=x_labels_full).fillna(0)
    
    matrix_hover = df_clean.pivot(index='Roll_Name', columns='Defect_Type', values='Tooltip_Str')
    matrix_hover = matrix_hover.reindex(index=y_labels, columns=x_labels_full).fillna("Không có lỗi")

    # 5. DATA CHO CỘT TỔNG (TOTAL COLUMN)
    # Lấy định mức cho từng RolName (Mỗi RoleName chỉ có 1 giá trị Total)
    prod_map = df_clean.groupby('Roll_Name')[denom_col].max()
    prod_values = [prod_map.get(lbl, 0) for lbl in y_labels]
    z_prod = [[v] for v in prod_values] # Shape (N, 1) cho Heatmap
    text_prod = [[f"{v:,.0f}"] for v in prod_values]

    # 6. VẼ BẰNG SUBPLOTS (2 CỘT: 85% HEATMAP, 15% TOTAL)
    dyn_height = max(450, 250 + len(y_labels) * 50)
    
    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.85, 0.15],
        shared_yaxes=True,
        horizontal_spacing=0.03,
        subplot_titles=("Chi Tiết Lỗi", total_col_name)
    )

    # Trace 1: Defect Heatmap
    x_labels_short = [shorten_label(l) for l in x_labels_full]
    
    fig.add_trace(go.Heatmap(
        z=matrix_z.values,
        x=x_labels_full,
        y=y_labels,
        customdata=matrix_hover.values,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale='Reds',
        text=matrix_z.values,
        texttemplate="%{text:.0f}" if color_by == 'Count' else "%{text:.1f}",
        showscale=False
    ), row=1, col=1)

    # Trace 2: Total Column
    fig.add_trace(go.Heatmap(
        z=z_prod,
        x=[total_col_name],
        y=y_labels,
        text=text_prod,
        texttemplate="%{text}",
        colorscale='Blues',
        showscale=False,
        hovertemplate=f'<b>%{{y}}</b><br>{total_col_name}: %{{text}}<extra></extra>'
    ), row=1, col=2)

    # 7. LAYOUT & TRỤC
    fig.update_layout(
        title=dict(text=f"Bản Đồ Nhiệt: {('Tỷ Lệ Lỗi' if color_by == 'Rate' else 'Số Lượng Lỗi')}", 
                   y=0.98, x=0.5, xanchor='center', yanchor='top'),
        height=dyn_height,
        margin=dict(t=80, b=100, l=50, r=50),
        font=dict(family="Arial, sans-serif"),
    )
    
    # Update Axis 1 (Defects)
    fig.update_xaxes(
        side="top", 
        tickangle=-45,
        tickmode='array',
        tickvals=x_labels_full,
        ticktext=x_labels_short,
        row=1, col=1
    )
    
    # Update Axis 2 (Total Prod/Defect)
    fig.update_xaxes(
        side="top",
        showticklabels=False, 
        row=1, col=2
    )

    # 8. DEBUG TOOL
    with st.expander("🛠️ TOOL DEBUG HEATMAP (Check lệch cột)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Ma trận MÀU (Cột đầu: {x_labels_full[0] if x_labels_full else 'N/A'})**")
            st.dataframe(matrix_z.iloc[:, :3], use_container_width=True)
        with c2:
            st.write(f"**Ma trận TOOLTIP (Cột đầu: {x_labels_full[0] if x_labels_full else 'N/A'})**")
            st.dataframe(matrix_hover.iloc[:, :3], use_container_width=True)

    return fig

def draw_pareto_main(df_pareto):
    """Vẽ Pareto - Fix Sort"""
    df_pareto = df_pareto.sort_values(by='Số Lượng Lỗi', ascending=False).copy()
    total_err = df_pareto['Số Lượng Lỗi'].sum()
    df_pareto['Cumulative %'] = 100 * df_pareto['Số Lượng Lỗi'].cumsum() / total_err if total_err > 0 else 0
    df_pareto['Short_Name'] = df_pareto['Loại Lỗi'].apply(lambda x: shorten_label(x, 15))
    
    colors = ['#C0392B' if i == 0 else '#2E86C1' for i in range(len(df_pareto))]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_pareto['Loại Lỗi'], y=df_pareto['Số Lượng Lỗi'], name='Số Lượng', 
        marker_color=colors, text=df_pareto['Số Lượng Lỗi'], texttemplate='%{text:,.0f}', textposition='outside',
        hovertemplate='<b>%{x}</b><br>SL: %{y:,.0f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=df_pareto['Loại Lỗi'], y=df_pareto['Cumulative %'], name='% Tích Lũy', 
        yaxis='y2', mode='lines+markers', marker=dict(color='#F39C12'), line=dict(width=2),
        hovertemplate='%{y:.2f}%<extra></extra>'
    ))
    fig.add_hline(y=80, line_dash="dash", line_color="gray", annotation_text="80% Cutoff")
    
    fig.update_layout(
        title=dict(text="Biểu đồ Pareto (Lỗi Mũi Nhọn = Đỏ)", y=0.95, x=0.5, xanchor='center', yanchor='top'),
        yaxis=dict(title='Số Lỗi'), 
        yaxis2=dict(title='% Tích Lũy', overlaying='y', side='right', range=[0, 105], showgrid=False),
        xaxis=dict(tickangle=-45, automargin=True, 
                   categoryorder='array', categoryarray=df_pareto['Loại Lỗi'].tolist(),
                   tickmode='array', tickvals=df_pareto['Loại Lỗi'].tolist(), ticktext=df_pareto['Short_Name'].tolist()), 
        height=550, margin=dict(t=100, b=150, l=50, r=50), font=dict(family="Arial, sans-serif"),
        legend=dict(orientation="h", y=1.02, xanchor="right", x=1)
    )
    return fig

def draw_roll_pareto(df_roll_pareto, s_roll):
    """Vẽ Pareto Cuộn - Fix Sort"""
    df_roll_pareto = df_roll_pareto.sort_values(by='Số Lượng Lỗi', ascending=False).copy()
    total_err = df_roll_pareto['Số Lượng Lỗi'].sum()
    df_roll_pareto['Cumulative %'] = 100 * df_roll_pareto['Số Lượng Lỗi'].cumsum() / total_err if total_err > 0 else 0
    df_roll_pareto['Short_Name'] = df_roll_pareto['Loại Lỗi'].apply(lambda x: shorten_label(x, 15))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_roll_pareto['Short_Name'], y=df_roll_pareto['Số Lượng Lỗi'],
        name='Số Lượng', marker_color='orange', 
        text=df_roll_pareto['Số Lượng Lỗi'], texttemplate='%{text:,.0f}', textposition='outside',
        customdata=df_roll_pareto[['Loại Lỗi', '% Trên Tổng Túi']].values,
        hovertemplate='<b>%{customdata[0]}</b><br>SL: %{y:,.0f}<br>📉 % Tổng túi: %{customdata[1]:,.2f}%<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=df_roll_pareto['Short_Name'], y=df_roll_pareto['Cumulative %'],
        name='% Tích Lũy', yaxis='y2', mode='lines+markers', marker=dict(color='#C0392B'), line=dict(width=2),
        hovertemplate='%{y:.2f}%<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text=f"Biểu đồ Pareto Lỗi - Cuộn {s_roll}", y=0.95, x=0.5, xanchor='center', yanchor='top'),
        yaxis=dict(title='Số Lỗi'), 
        yaxis2=dict(title='% Tích Lũy', overlaying='y', side='right', range=[0, 105], showgrid=False),
        xaxis=dict(tickangle=-45, automargin=True, categoryorder='array', categoryarray=df_roll_pareto['Short_Name'].tolist()), 
        height=550, margin=dict(l=50, r=50, t=100, b=150), font=dict(family="Arial, sans-serif"),
        legend=dict(orientation="h", y=1.02, xanchor="right", x=1)
    )
    return fig

def draw_comparative_bar_with_reference(df, avg_val):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['Display_Name'], y=df['Rate'], text=df['Rate'], texttemplate='%{text:.2f}%', textposition='outside',
        marker_color='#2E86C1', name='Tỷ Lệ Lỗi'
    ))
    fig.add_hline(y=avg_val, line_dash="dash", line_color="#E74C3C", annotation_text=f"TB Lịch Sử: {avg_val:.2f}%", annotation_position="top right")
    fig.update_layout(
        title="So Sánh Tỷ Lệ Lỗi (Kèm Đường Tham Chiếu Lịch Sử)", xaxis_title="Cuộn", yaxis_title="% Lỗi",
        height=400, margin=dict(t=40, b=40, l=40, r=40), font=dict(family="Arial, sans-serif")
    )
    return fig

def draw_horizontal_rate_chart(df_rate_chart):
    fig = px.bar(
        df_rate_chart, x='Rate_On_Prod', y='Loại Lỗi', orientation='h',
        text='Rate_On_Prod', title='Top 20 Lỗi có Tỷ lệ cao nhất trên Tổng Sản Lượng',
        color='Rate_On_Prod', color_continuous_scale='OrRd',
        labels={'Rate_On_Prod': 'Tỷ lệ lỗi (%)', 'Loại Lỗi': 'Loại Lỗi'} 
    )
    fig.update_traces(texttemplate='%{text:,.2f}%', textposition='outside', hovertemplate='<b>%{y}</b><br>Tỷ lệ: %{x:,.2f}%<extra></extra>')
    fig.update_layout(xaxis_title="% trên Tổng Sản Lượng", yaxis_title="", height=max(400, len(df_rate_chart)*30), font=dict(family="Arial, sans-serif"), xaxis=dict(automargin=True))
    return fig

def draw_pie_chart(vital_few_df):
    fig = px.pie(vital_few_df, values='Số Lượng Lỗi', names='Loại Lỗi', hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism)
    fig.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>%{label}</b><br>SL: %{value:,.0f}<br>Tỷ lệ: %{percent}<extra></extra>')
    fig.update_layout(showlegend=True, height=450, margin=dict(t=20, b=20), font=dict(family="Arial, sans-serif"))
    return fig

def draw_machine_chart(df_chart_m, dynamic_height):
    fig = px.bar(
        df_chart_m, x='Số Lượng Lỗi', y='Loại Lỗi', orientation='h', 
        text='Số Lượng Lỗi', color='Số Lượng Lỗi', color_continuous_scale='Teal',
        labels={'Số Lượng Lỗi': 'Số Lượng', 'Loại Lỗi': 'Loại Lỗi'}
    )
    fig.update_traces(texttemplate='%{text:,.0f}', hovertemplate='<b>%{y}</b><br>Số lượng: %{x:,.0f}<extra></extra>')
    fig.update_layout(height=dynamic_height, yaxis_title="", margin=dict(l=0, t=10, b=10), xaxis=dict(automargin=True), font=dict(size=16, family="Arial"))
    return fig