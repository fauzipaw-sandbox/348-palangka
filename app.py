import streamlit as st
import pandas as pd
import requests

# Konfigurasi halaman agar fullscreen dan rapi
st.set_page_config(layout="wide", page_title="Task Force Dashboard NOP")

# --- HELPER FUNCTION: Konversi Link GDrive agar bisa tampil sebagai gambar ---
def konversi_link_gdrive(url_mentah):
    if not url_mentah or not isinstance(url_mentah, str):
        return None
    if "open?id=" in url_mentah:
        return url_mentah.replace("open?id=", "uc?export=download&id=")
    if "Uc?id=" in url_mentah or "uc?id=" in url_mentah:
        return url_mentah.replace("Uc?id=", "uc?export=download&id=").replace("uc?id=", "uc?export=download&id=")
    return url_mentah

# --- SIMULASI FUNGSI PULL DATA FROM APPSHEET ---
# Nanti tinggal lo sambungin ke REST API AppSheet lo yang kemarin ya, Zi!
@st.cache_data(ttl=600) # Data bakal otomatis refresh tiap 10 menit
def load_data_from_appsheet():
    # --- ISI DENGAN DATA DARI LANGKAH 1 ---
    APP_ID = "d3525213-95f5-4dff-9eb3-62842c4964f0"
    ACCESS_KEY = "V2-AmIzq-oOhfP-aWkgR-jRkRK-fyAiW-1mj3s-3yfYj-o18dt"
    TABLE_NAME = "List"
    
    url = f"https://api.appsheet.com/api/v2/apps/{APP_ID}/tables/{TABLE_NAME}/Action"
    
    headers = {
        'ApplicationAccessKey': ACCESS_KEY,
        'Content-Type': 'application/json'
    }
    
    # Payload 'Find' tanpa isi Rows untuk narik SEMUA baris data
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
            data_json = response.json()
            # Otomatis jadi DataFrame
            return pd.DataFrame(data_json)
        else:
            st.error(f"Gagal terhubung ke AppSheet API (Status: {response.status_code})")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Terjadi error koneksi: {e}")
        return pd.DataFrame()

# Load data
df = load_data_from_appsheet()

# --- HEADER WEB DASHBOARD ---
st.markdown("<h2 style='text-align: center; color: #d32f2f;'>Task Force 347 | KKP226 | NOP PALANGKARAYA</h2>", unsafe_allow_html=True)
st.write(f"<p style='text-align: center;'>Data Update Terakhir: {df['Timestamp'].iloc[0]}</p>", unsafe_allow_html=True)

st.divider()

# --- FILTER SIDEBAR / TOP BAR ---
# Tinggal ganti-ganti Site ID di sini, data di bawah otomatis ngikut semua
site_pilihan = st.selectbox("Pilih Site ID:", df['Site_ID'].unique())
data_site = df[df['Site_ID'] == site_pilihan].iloc[0]

# --- SAKLAR FITUR CUSTOMIZE FOTO (UNTUK SCREENSHOT) ---
st.sidebar.header("⚙️ Dashboard Controller")
show_photos = st.sidebar.checkbox("Tampilkan Foto Dokumentasi", value=True, 
                                  help="Uncheck ini kalau lo mau ngilangin semua foto sementara waktu biar layar bersih pas mau screenshot laporannya.")

# --- LAYOUTING UTAMA (Mirroring Template PPT lo) ---
col_basic, col_finding = st.columns([1, 1.2])

# ================= KOLOM KIRI: BASIC INFORMATION =================
with col_basic:
    st.markdown("<h3 style='background-color: #1e3d59; color: white; padding: 8px; border-radius: 5px;'>Basic Information</h3>", unsafe_allow_html=True)
    
    # Bikin tabel data infomasi dasar
    info_dasar = {
        "Parameter": ["Area", "Regional", "NOP", "Phase PLN", "Daya PLN"],
        "Value": [data_site['Area'], data_site['Regional'], data_site['NOP'], data_site['Phase_PLN'], data_site['Daya_PLN']]
    }
    st.table(pd.DataFrame(info_dasar))
    
    st.markdown("<h4 style='color: #1e3d59;'>Kondisi Kelistrikan & Power</h4>", unsafe_allow_html=True)
    col_v, col_i = st.columns(2)
    with col_v:
        st.metric(label="Tegangan R-N", value=f"{data_site['Teg_RN']} V")
        st.metric(label="Tegangan S-N", value=f"{data_site['Teg_SN']} V")
        st.metric(label="Tegangan T-N", value=f"{data_site['Teg_TN']} V")
        st.metric(label="G-N Grounding", value=f"{data_site['G_N_Grounding']} V")
    with col_i:
        st.metric(label="Arus / Beban R", value=f"{data_site['Beban_R']} A")
        st.metric(label="Arus / Beban S", value=f"{data_site['Beban_S']} A")
        st.metric(label="Arus / Beban T", value=f"{data_site['Beban_T']} A")

# ================= KOLOM KANAN: FINDING & FOTO =================
with col_finding:
    st.markdown("<h3 style='background-color: #ffc13b; color: #1e3d59; padding: 8px; border-radius: 5px;'>Findings & Hardware Status</h3>", unsafe_allow_html=True)
    
    st.write(f"**Tipe Rectifier:** {data_site['Type_Rectifier']}")
    st.write(f"**Total Arus Rectifier:** {data_site['Rectifier_Current']} A")
    st.write(f"**Jumlah Modul Eksisting:** {data_site['Jumlah_Module']} Modul (Faulty: {data_site['Total_Module_Faulty']})")
    st.write(f"**Backup Time Battery:** {data_site['BBT_Backup']}")
    
    st.markdown("---")
    st.markdown("**Detail Pengecekan Lapangan:**")
    st.caption("1. Enva validation & Simulation -> OK\n"
               "2. Pengecekan Koneksi Kabel -> OK\n"
               "3. Arrester Rectifier -> OKE\n"
               "4. Fan Rectifier & BTS -> OK")
    
    st.markdown("---")
    
    # Logika Saklar Foto: Kalau di-uncheck via sidebar, bagian ini kosong (bersih buat di-screenshot)
    if show_photos:
        st.markdown("**📸 Foto Dokumentasi Lapangan (Real-time GDrive)**")
        
        # Susun foto bersebelahan biar ga makan tempat ke bawah
        f_col1, f_col2 = st.columns(2)
        
        with f_col1:
            url_kwh = konversi_link_gdrive(data_site['Foto_KWH'])
            if url_kwh:
                st.image(url_kwh, caption="KWH Meter & MCB PLN", use_column_width=True)
                
            url_recti = konversi_link_gdrive(data_site['Foto_Rectifier'])
            if url_recti:
                st.image(url_recti, caption="Kondisi Rectifier", use_column_width=True)
                
        with f_col2:
            url_modul = konversi_link_gdrive(data_site['Foto_Modul'])
            if url_modul:
                st.image(url_modul, caption="Kondisi Modul ZTE", use_column_width=True)
                
            url_batt = konversi_link_gdrive(data_site['Foto_Battery_Pack'])
            if url_batt:
                st.image(url_batt, caption="Battery Pack Lithium", use_column_width=True)
    else:
        st.warning("⚠️ Mode Screenshot Aktif: Foto dokumentasi disembunyikan sementara dari layar dashboard web.")
