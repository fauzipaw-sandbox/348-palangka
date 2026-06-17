import streamlit as st
import pandas as pd
import requests

# Konfigurasi halaman agar fullscreen dan rapi
st.set_page_config(layout="wide", page_title="Task Force Dashboard NOP")

# --- HELPER FUNCTION: Konversi Link GDrive agar bisa tampil sebagai gambar ---
def konversi_link_gdrive(url_mentah):
    if not url_mentah or not isinstance(url_mentah, str):
        return None
    # Menangani link gdrive yang berjejer kalau ada multiple link
    url_mentah = url_mentah.split(",")[0].strip()
    if "open?id=" in url_mentah:
        return url_mentah.replace("open?id=", "uc?export=download&id=")
    if "open?id=" in url_mentah.lower():
        return url_mentah.replace("id=", "export=download&id=")
    return url_mentah

# --- FUNGSI PULL DATA DARI APPSHEET API ---
@st.cache_data(ttl=300) # Otomatis refresh data dari AppSheet tiap 5 menit
def load_data_from_appsheet():
    # Kredensial asli lo
    APP_ID = "d3525213-95f5-4dff-9eb3-62842c4964f0"
    ACCESS_KEY = "V2-AmIzq-oOhfP-aWkgR-jRkRK-fyAiW-1mj3s-3yfYj-o18dt"
    TABLE_NAME = "MASUKIN_NAMA_TABEL_LO_DISINI" # <--- GANTI INI DENGAN NAMA TABEL DI APPSHEET
    
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
        else:
            st.error(f"Gagal konek ke AppSheet API. Kode Status: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error Koneksi: {e}")
        return pd.DataFrame()

# Load data asli
df = load_data_from_appsheet()

if df.empty:
    st.warning("Data kosong atau belum terhubung dengan bener ke AppSheet. Cek kembali nama Table lo, Zi.")
else:
    # --- HEADER DASHBOARD ---
    st.markdown("<h2 style='text-align: center; color: #d32f2f;'>Task Force 347 | NOP PALANGKARAYA</h2>", unsafe_allow_html=True)
    
    st.divider()

    # --- FILTER SIDEBAR & CONTROLLER ---
    st.sidebar.header("⚙️ Dashboard Controller")
    
    # Pilih kolom acuan site (Ganti 'Site' kalau nama kolom di AppSheet lo beda)
    kolom_site = 'Site' if 'Site' in df.columns else df.columns[1] 
    
    site_pilihan = st.sidebar.selectbox("Pilih Site ID:", df[kolom_site].unique())
    show_photos = st.sidebar.checkbox("Tampilkan Foto Dokumentasi", value=True, 
                                      help="Uncheck ini buat ngilangin foto sementara pas mau screenshot.")

    # Filter data berdasarkan site yang dipilih
    data_site = df[df[kolom_site] == site_pilihan].iloc[0]

    # Menampilkan timestamp update di bawah judul
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
                url_kwh = konversi_link_gdrive(data_site.get('KWH Meter'))
                if url_kwh:
                    st.image(url_kwh, caption="KWH Meter", use_container_width=True)
                    
                url_recti = konversi_link_gdrive(data_site.get('Foto Rectifier'))
                if url_recti:
                    st.image(url_recti, caption="Foto Rectifier", use_container_width=True)
                    
                url_mcb = konversi_link_gdrive(data_site.get('MCB PLN'))
                if url_mcb:
                    st.image(url_mcb, caption="MCB PLN", use_container_width=True)
                    
            with f_col2:
                url_modul = konversi_link_gdrive(data_site.get('Foto Modul'))
                if url_modul:
                    st.image(url_modul, caption="Foto Modul", use_container_width=True)
                    
                url_batt = konversi_link_gdrive(data_site.get('Battery (Total Pack)'))
                if url_batt:
                    st.image(url_batt, caption="Battery Total Pack", use_container_width=True)
                    
                url_mat = konversi_link_gdrive(data_site.get('Foto Material (Menggunakan Timestemp)'))
                if url_mat:
                    st.image(url_mat, caption="Foto Material Timestamp", use_container_width=True)
        else:
            st.warning("⚠️ Mode Screenshot Aktif: Semua foto disembunyikan sementara dari layar.")
