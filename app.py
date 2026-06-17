import streamlit as st
import pandas as pd
import requests
import re

# Konfigurasi halaman
st.set_page_config(layout="wide", page_title="Task Force Dashboard NOP")

# --- HELPER FUNCTION: Konversi Link GDrive ---
def konversi_link_gdrive(url_mentah):
    if pd.isna(url_mentah) or not url_mentah or str(url_mentah).strip() == "":
        return None
        
    url_str = str(url_mentah)
    
    # Mengabaikan tanda kutip (") dan kurung kurawal ({}) dari format JSON AppSheet
    match = re.search(r'(https?://[^\s,"\'\}]+)', url_str)
    if not match:
        return None
        
    link_bersih = match.group(1).strip()
    
    # Konversi ke direct download link Drive
    if "open?id=" in link_bersih:
        return link_bersih.replace("open?id=", "uc?export=download&id=")
    if "Uc?id=" in link_bersih or "uc?id=" in link_bersih:
        return link_bersih.replace("Uc?id=", "uc?export=download&id=").replace("uc?id=", "uc?export=download&id=")
        
    return link_bersih

# --- FUNGSI PULL DATA DARI APPSHEET API ---
@st.cache_data(ttl=300)
def load_data_from_appsheet():
    APP_ID = "d3525213-95f5-4dff-9eb3-62842c4964f0"
    ACCESS_KEY = "V2-AmIzq-oOhfP-aWkgR-jRkRK-fyAiW-1mj3s-3yfYj-o18dt"
    TABLE_NAME = "List"
    
    url = f"https://api.appsheet.com/api/v2/apps/{APP_ID}/tables/{TABLE_NAME}/Action"
    
    headers = {
        'ApplicationAccessKey': ACCESS_KEY,
        'Content-Type': 'application/json'
    }
    
    payload = {
        "Action": "Find",
        "Properties": {
            "Locale": "id-ID",
            "Timezone": "Asia/Jakarta"
        },
        "Rows": []
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# Load data asli
df = load_data_from_appsheet()

if df.empty:
    st.warning("Data kosong atau belum terhubung dengan bener ke AppSheet. Pastikan TABLE_NAME sudah sesuai, Zi.")
else:
    # --- HEADER DASHBOARD ---
    st.markdown("<h2 style='text-align: center; color: #d32f2f;'>Task Force 347 | NOP PALANGKARAYA</h2>", unsafe_allow_html=True)
    st.divider()

    # --- FILTER SIDEBAR & CONTROLLER ---
    st.sidebar.header("⚙️ Dashboard Controller")
    
    # FIX LOGIKA DETEKSI: Cari yang beneran mengandung kata 'site' utuh agar tidak terjebak kata 'kondisi'
    possible_site_cols = [c for c in df.columns if "site" in c.lower()]
    
    # Kalau kolom dengan kata 'site' ga ketemu, cari yang namanya pas 'id' atau pakai kolom pertama
    if possible_site_cols:
        kolom_site = possible_site_cols[0]
    else:
        backup_cols = [c for c in df.columns if c.lower() == 'id' or c.lower() == 'site id']
        kolom_site = backup_cols[0] if backup_cols else df.columns[0]
    
    # Dropdown Site ID asli
    site_pilihan = st.sidebar.selectbox("Pilih Site ID:", df[kolom_site].unique())
    show_photos = st.sidebar.checkbox("Tampilkan Foto Dokumentasi", value=True)

    # MENU DEBUG: Buat mastiin nama kolom yang ketarik dari AppSheet lo
    with st.sidebar.expander("🔍 Debug: List Kolom AppSheet"):
        st.write("Kolom yang dijadikan acuan Site:", kolom_site)
        st.write(df.columns.tolist())

    # Filter data berdasarkan site yang dipilih
    data_site = df[df[kolom_site] == site_pilihan].iloc[0]

    # Timestamp update
    st.write(f"<p style='text-align: center;'><b>Timestamp Data:</b> {data_site.get('Timestamp', '-')}</p>", unsafe_allow_html=True)

    # --- LAYOUTING UTAMA ---
    col_basic, col_finding = st.columns([1, 1.2])

    # ================= KOLOM KIRI: BASIC INFORMATION =================
    with col_basic:
        st.markdown("<h3 style='background-color: #1e3d59; color: white; padding: 8px; border-radius: 5px;'>Basic Information</h3>", unsafe_allow_html=True)
        
        info_dasar = {
            "Parameter": ["Phase PLN", "Grounding KWH", "Type Rectifier", "Arrester", "Kondisi Display Rectifier"],
            "Value": [
                data_site.get('Phase PLN', '-'),
                data_site.get('Grounding KWH', '-'),
                data_site.get('Type Rectifier', '-'),
                data_site.get('Arrester', '-'),
                data_site.get('Kondisi Display Rectifier', '-')
            ]
        }
        st.table(pd.DataFrame(info_dasar))
        
        st.markdown("<h4 style='color: #1e3d59;'>Kondisi Kelistrikan & Power</h4>", unsafe_allow_html=True)
        col_v, col_i = st.columns(2)
        with col_v:
            st.metric(label="Tegangan R-N", value=f"{data_site.get('Tegangan PLN (R-N)', '-')} V")
            st.metric(label="Tegangan S-N", value=f"{data_site.get('Tegangan PLN (S-N)', '-')} V")
            st.metric(label="Tegangan T-N", value=f"{data_site.get('Tegangan PLN (T-N)', '-')} V")
            st.metric(label="G-N Grounding", value=f"{data_site.get('G-N Grounding ke Netral', '-')} V")
        with col_i:
            st.metric(label="Beban PLN (R)", value=f"{data_site.get('Beban PLN (R)', '-')} A")
            st.metric(label="Beban PLN (S)", value=f"{data_site.get('Beban PLN (S)', '-')} A")
            st.metric(label="Beban PLN (T)", value=f"{data_site.get('Beban PLN (T)', '-')} A")

    # ================= KOLOM KANAN: FINDINGS & STATUS HARDWARE =================
    with col_finding:
        st.markdown("<h3 style='background-color: #ffc13b; color: #1e3d59; padding: 8px; border-radius: 5px;'>Findings & Hardware Status</h3>", unsafe_allow_html=True)
        
        st.write(f"**Total Arus Rectifier:** {data_site.get('Rectifier Current', '-')} A")
        st.write(f"**Jumlah Modul Eksisting:** {data_site.get('Jumlah Module', '-')} (Faulty: {data_site.get('Total Module faulty', '-')})")
        st.write(f"**Backup Time Battery (BBT):** {data_site.get('BBT >4 Jam', '-')}")
        st.write(f"**Remark MCB ACPDB:** {data_site.get('Remark Kondisi MCB ACPDB', '-')}")
        
        st.markdown("---")
        st.markdown("**Status Validasi Lapangan:**")
        st.write(f"- Enva Validasi: *{data_site.get('Enva Validasi', '-')}*")
        st.write(f"- Kondisi Modul Enva LPU: *{data_site.get('Kondisi Modul Enva LPU', '-')}*")
        st.write(f"- Arrester Rectifier: *{data_site.get('Arrester Rectifier', '-')}*")
        
        st.markdown("---")
        
        # SAKLAR FOTO SCREENSHOT
        if show_photos:
            st.markdown("**📸 Foto Dokumentasi Lapangan (GDrive)**")
            f_col1, f_col2 = st.columns(2)
            
            with f_col1:
                if url_kwh := konversi_link_gdrive(data_site.get('KWH Meter')):
                    st.image(url_kwh, caption="KWH Meter", width="stretch")
                    
                if url_recti := konversi_link_gdrive(data_site.get('Foto Rectifier')):
                    st.image(url_recti, caption="Foto Rectifier", width="stretch")
                    
                if url_mcb := konversi_link_gdrive(data_site.get('MCB PLN')):
                    st.image(url_mcb, caption="MCB PLN", width="stretch")
                    
            with f_col2:
                if url_modul := konversi_link_gdrive(data_site.get('Foto Modul')):
                    st.image(url_modul, caption="Foto Modul", width="stretch")
                    
                if url_batt := konversi_link_gdrive(data_site.get('Battery (Total Pack)')):
                    st.image(url_batt, caption="Battery Total Pack", width="stretch")
                    
                if url_mat := konversi_link_gdrive(data_site.get('Foto Material (Menggunakan Timestemp)')):
                    st.image(url_mat, caption="Foto Material Timestamp", width="stretch")
        else:
            st.warning("⚠️ Mode Screenshot Aktif: Semua foto disembunyikan sementara dari layar.")
