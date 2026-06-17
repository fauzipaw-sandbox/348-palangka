import streamlit as st
import pandas as pd
import requests
import re

# Konfigurasi halaman agar fullscreen dan rapi
st.set_page_config(layout="wide", page_title="Task Force Dashboard NOP")

# Kredensial AppSheet API Global
APP_ID = "d3525213-95f5-4dff-9eb3-62842c4964f0"
ACCESS_KEY = "V2-AmIzq-oOhfP-aWkgR-jRkRK-fyAiW-1mj3s-3yfYj-o18dt"
TABLE_NAME = "List"

# --- INITIALIZE SESSION STATE ---
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
        
    link_inter = match.group(1).strip()
    
    if "open?id=" in link_inter:
        return link_inter.replace("open?id=", "uc?export=download&id=")
    if "Uc?id=" in link_inter or "uc?id=" in link_inter:
        return link_inter.replace("Uc?id=", "uc?export=download&id=").replace("uc?id=", "uc?export=download&id=")
        
    return link_inter

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

# --- FUNGSI PUSH/UPDATE DATA KE APPSHEET API ---
def update_rekomendasi_appsheet(site_id, nama_kolom_site, teks_rekomendasi):
    url = f"https://api.appsheet.com/api/v2/apps/{APP_ID}/tables/{TABLE_NAME}/Action"
    headers = {
        'ApplicationAccessKey': ACCESS_KEY,
        'Content-Type': 'application/json'
    }
    # Payload Edit untuk mengupdate baris data secara spesifik
    payload = {
        "Action": "Edit",
        "Properties": {"Locale": "id-ID", "Timezone": "Asia/Jakarta"},
        "Rows": [
            {
                nama_kolom_site: site_id, # Sebagai Key Row penentu baris
                "Rekomendasi Koordinator": teks_rekomendasi # Kolom baru yang diupdate
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code == 200
    except:
        return False

# Load data asli
df = load_data_from_appsheet()

if df.empty:
    st.warning("Data kosong atau belum terhubung dengan bener ke AppSheet.")
else:
    # --- HEADER DASHBOARD ---
    st.markdown("<h2 style='text-align: center; color: #d32f2f;'>Task Force 347 | NOP PALANGKARAYA</h2>", unsafe_allow_html=True)
    st.divider()

    # --- DROPDOWN SITE ID ---
    kolom_site = 'Site' if 'Site' in df.columns else ([c for c in df.columns if "site" in c.lower() or "id" in c.lower()] + [df.columns[0]])[0]
    
    col_select, col_reset = st.columns([3, 1])
    with col_select:
        site_pilihan = st.selectbox("🎯 Pilih Site ID:", df[kolom_site].unique())
    with col_reset:
        st.write(" ")
        st.write(" ")
        if st.session_state.foto_dihapus:
            if st.button("🔄 Tampilkan Kembali Semua Foto", use_container_width=True):
                st.session_state.foto_dihapus.clear()
                st.rerun()

    # Filter data berdasarkan site yang dipilih
    data_site = df[df[kolom_site] == site_pilihan].iloc[0]

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

    # ================= KOLOM KANAN: FINDINGS & INPUT REKOMENDASI =================
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
        
        # 🆕 SEKSI INPUT REKOMENDASI KORLAP (TERSIMPAN KE DATA)
        st.markdown("---")
        st.markdown("<h4 style='color: #ffc13b;'>📝 Rekomendasi Koordinator Lapangan</h4>", unsafe_allow_html=True)
        
        # Mengambil data rekomendasi yang sudah ada di data (jika ada)
        rekomendasi_sekarang = data_site.get('Rekomendasi Koordinator', '')
        if pd.isna(rekomendasi_sekarang):
            rekomendasi_sekarang = ""
            
        # Form input Text Area
        rekomendasi_input = st.text_area("Input Rekomendasi Tim Korlap di Sini:", 
                                          value=str(rekomendasi_sekarang), 
                                          placeholder="Contoh: Replace Arrester Recty, Swap 3p Battery faulty...",
                                          key="input_rekomendasi")
        
        if st.button("💾 Simpan Rekomendasi ke AppSheet", use_container_width=True):
            if rekomendasi_input.strip() == "":
                st.warning("Isi kolom rekomendasi terlebih dahulu sebelum disimpan, Zi.")
            else:
                with st.spinner("Sedang menyimpan data ke AppSheet..."):
                    sukses = update_rekomendasi_appsheet(site_pilihan, kolom_site, rekomendasi_input)
                    if sukses:
                        st.success(f"Rekomendasi untuk Site {site_pilihan} berhasil disimpan!")
                        # Clear cache agar web otomatis narik data terbaru pas reload
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Gagal menyimpan ke AppSheet. Pastikan kolom 'Rekomendasi Koordinator' sudah ditambahkan di AppSheet Database lo.")

        st.markdown("---")
        st.markdown("**📸 Foto Dokumentasi Lapangan (GDrive)**")
        
        # --- FUNGSI REDER FOTO RESPONSIF + TOMBOL DELETE TEMPORER ---
        def render_responsive_image(col_name, label):
            if col_name in st.session_state.foto_dihapus:
                return
                
            url_mentah = data_site.get(col_name)
            url_bersih = konversi_link_gdrive(url_mentah)
            
            if url_bersih:
                img_bytes = fetch_image_from_gdrive(url_bersih)
                if img_bytes:
                    st.image(img_bytes, caption=label, width="stretch")
                    if st.button(f"❌ Sembunyikan {label}", key=f"btn_{col_name}"):
                        st.session_state.foto_dihapus.add(col_name)
                        st.rerun()
                else:
                    st.caption(f"⚠️ {label} gagal ditarik dari Drive")

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            render_responsive_image('KWH Meter', "KWH Meter")
            render_responsive_image('Foto Rectifier', "Foto Rectifier")
            render_responsive_image('MCB PLN', "MCB PLN")
                
        with f_col2:
            render_responsive_image('Foto Modul', "Foto Modul")
            render_responsive_image('Battery (Total Pack)', "Battery Total Pack")
            render_responsive_image('Foto Material (Menggunakan Timestemp)', "Foto Material Timestamp")
