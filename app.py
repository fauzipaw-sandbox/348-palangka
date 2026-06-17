import streamlit as st
import pandas as pd
import requests
import re

# Konfigurasi halaman agar fullscreen dan rapi
st.set_page_config(layout="wide", page_title="Task Force Dashboard NOP")

# --- INITIALIZE SESSION STATE (Untuk simpan daftar foto yang dihapus sementara) ---
if 'foto_dihapus' not in st.session_state:
    st.session_state.foto_dihapus = set()

# --- HELPER 1: Konversi Link GDrive ---
def konversi_link_gdrive(url_mentah):
    if pd.isna(url_mentah) or not url_mentah or str(url_mentah).strip() == "":
        return None
        
    url_str = str(url_mentah)
    match = re.search(r'(https?://[^\s,"\'\}]+)', url_str)
    if not match:
        return None
        
    link_bersih = match.group(1).strip()
    
    if "open?id=" in link_bersih:
        return link_bersih.replace("open?id=", "uc?export=download&id=")
    if "Uc?id=" in link_bersih or "uc?id=" in link_bersih:
        return link_bersih.replace("Uc?id=", "uc?export=download&id=").replace("uc?id=", "uc?export=download&id=")
        
    return link_bersih

# --- HELPER 2: Fetch Gambar dari GDrive ---
@st.cache_data(show_spinner=False, ttl=600)
def fetch_image_from_gdrive(url):
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.content
    except:
        pass
    return None

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
        "Properties": {"Locale": "id-ID", "Timezone": "Asia/Jakarta"},
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
    st.warning("Data kosong atau belum terhubung dengan bener ke AppSheet.")
else:
    # --- HEADER DASHBOARD ---
    st.markdown("<h2 style='text-align: center; color: #d32f2f;'>Task Force 347 | NOP PALANGKARAYA</h2>", unsafe_allow_html=True)
    st.divider()

    # --- DROPDOWN SITE ID (SEKARANG DI HALAMAN UTAMA, BUKAN DI SIDEBAR) ---
    # Nyari nama kolom Site lo secara presisi
    kolom_site = 'Site' if 'Site' in df.columns else ([c for c in df.columns if "site" in c.lower() or "id" in c.lower()] + [df.columns[0]])[0]
    
    col_select, col_reset = st.columns([3, 1])
    with col_select:
        site_pilihan = st.selectbox("🎯 Pilih Site ID:", df[kolom_site].unique())
    with col_reset:
        st.write(" ") # Kasih space kosong biar sejajar tombol
        st.write(" ")
        if st.session_state.foto_dihapus:
            if st.button("🔄 Tampilkan Kembali Semua Foto", use_container_width=True):
                st.session_state.foto_dihapus.clear()
                st.rerun()

    # Filter data berdasarkan site yang dipilih
    data_site = df[df[kolom_site] == site_pilihan].iloc[0]

    # Tampilkan info di bawah dropdown
    st.write(f"<p style='text-align: center;'><b>Timestamp Data:</b> {data_site.get('Timestamp', '-')}</p>", unsafe_allow_html=True)
    st.divider()

    # --- LAYOUTING UTAMA ---
    col_basic, col_finding = st.columns([1, 1.2])

    # ================= KOLOM KIRI: BASIC INFORMATION =================
    with col_basic:
        st.markdown("<h3 style='background-color: #1e3d59; color: white; padding: 8px; border-radius: 5px;'>Basic Information</h3>", unsafe_allow_html=True)
        
        info_dasar = {
            "Parameter": ["Site ID", "Phase PLN", "Grounding KWH", "Type Rectifier", "Arrester", "Kondisi Display Rectifier"],
            "Value": [
                site_pilihan,
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
        st.markdown("**📸 Foto Dokumentasi Lapangan (GDrive)**")
        
        # --- FUNGSI REDER FOTO RESPONSIF + TOMBOL DELETE TEMPORER ---
        def render_responsive_image(col_name, label):
            # Jika foto ada di dalam daftar hapus sementara, jangan di-render
            if col_name in st.session_state.foto_dihapus:
                return
                
            url_mentah = data_site.get(col_name)
            url_bersih = konversi_link_gdrive(url_mentah)
            
            if url_bersih:
                img_bytes = fetch_image_from_gdrive(url_bersih)
                if img_bytes:
                    st.image(img_bytes, caption=label, width="stretch")
                    # Tombol buat ngilangin foto ini dari layar secara temporer
                    if st.button(f"❌ Sembunyikan {label}", key=f"btn_{col_name}"):
                        st.session_state.foto_dihapus.add(col_name)
                        st.rerun()
                else:
                    st.caption(f"⚠️ {label} gagal ditarik dari Drive")

        # Layout foto 2 kolom bersebelahan agar rapi dan responsif
        f_col1, f_col2 = st.columns(2)
        
        with f_col1:
            render_responsive_image('KWH Meter', "KWH Meter")
            render_responsive_image('Foto Rectifier', "Foto Rectifier")
            render_responsive_image('MCB PLN', "MCB PLN")
                
        with f_col2:
            render_responsive_image('Foto Modul', "Foto Modul")
            render_responsive_image('Battery (Total Pack)', "Battery Total Pack")
            render_responsive_image('Foto Material (Menggunakan Timestemp)', "Foto Material Timestamp")
