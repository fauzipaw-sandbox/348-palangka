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

# --- FUNGSI STANDARISASI SITE ID ---
def format_site_id(site_id):
    if pd.isna(site_id) or str(site_id).strip() == "":
        return "-"
    s = str(site_id).strip().upper().replace(" ", "")
    s = re.sub(r'^K+P', 'KKP', s)
    return s

# --- FUNGSI KONVERSI LINK GDRIVE KE THUMBNAIL (BYPASS BLOCK) ---
def konversi_link_gdrive(url_mentah):
    if pd.isna(url_mentah) or not url_mentah or str(url_mentah).strip() == "":
        return None, None
        
    url_str = str(url_mentah)
    match = re.search(r'(https?://[^\s,"\'\}]+)', url_str)
    if not match:
        return None, None
        
    link_bersih = match.group(1).strip()
    
    file_id = None
    if "id=" in link_bersih:
        id_match = re.search(r'id=([a-zA-Z0-9_-]+)', link_bersih)
        if id_match:
            file_id = id_match.group(1)
    elif "drive.google.com/file/d/" in link_bersih:
        id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', link_bersih)
        if id_match:
            file_id = id_match.group(1)
            
    if file_id:
        thumb_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
        zoom_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1600"
        return thumb_url, zoom_url
        
    return link_bersih, link_bersih

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
    payload = {
        "Action": "Edit",
        "Properties": {"Locale": "id-ID", "Timezone": "Asia/Jakarta"},
        "Rows": [
            {
                nama_kolom_site: site_id,
                "Rekomendasi Koordinator": teks_rekomendasi
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
    kolom_site = 'Site' if 'Site' in df.columns else ([c for c in df.columns if "site" in c.lower() or "id" in c.lower()] + [df.columns[0]])[0]
    
    df[kolom_site] = df[kolom_site].apply(format_site_id)

    # --- HEADER DASHBOARD ---
    st.markdown("<h2 style='text-align: center; color: #d32f2f;'>Task Force 348 | NOP PALANGKARAYA</h2>", unsafe_allow_html=True)
    st.divider()

    # --- DROPDOWN SITE ID ---
    site_pilihan = st.selectbox("🎯 Pilih Site ID (Format Otomatis Seragam):", sorted(df[kolom_site].unique()))

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
        
        # SEKSI INPUT REKOMENDASI KORLAP
        st.markdown("---")
        st.markdown("<h4 style='color: #ffc13b;'>📝 Rekomendasi Koordinator Lapangan</h4>", unsafe_allow_html=True)
        
        rekomendasi_sekarang = data_site.get('Rekomendasi Koordinator', '')
        if pd.isna(rekomendasi_sekarang):
            rekomendasi_sekarang = ""
            
        rekomendasi_input = st.text_area("Input Rekomendasi Tim Korlap di Sini:", 
                                          value=str(rekomendasi_sekarang), 
                                          placeholder="Contoh: Replace Arrester Recty...",
                                          key="input_rekomendasi")
        
        if st.button("💾 Simpan Rekomendasi ke AppSheet", use_container_width=True):
            if rekomendasi_input.strip() == "":
                st.warning("Isi kolom rekomendasi terlebih dahulu sebelum disimpan, Zi.")
            else:
                with st.spinner("Sedang menyimpan data..."):
                    sukses = update_rekomendasi_appsheet(site_pilihan, kolom_site, rekomendasi_input)
                    if sukses:
                        st.success("Rekomendasi berhasil disimpan!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Gagal menyimpan data ke AppSheet.")

        # --- GALLERY FOTO BERJEJER (HTML Rapat tanpa spasi awal biar ga jadi Code Block) ---
        st.markdown("---")
        st.markdown("**📸 Foto Dokumentasi Lapangan (Horizontal Scroll & Click to Zoom)**")
        
        list_fotos = [
            ('KWH Meter', "KWH Meter"),
            ('Foto Rectifier', "Foto Rectifier"),
            ('MCB PLN', "MCB PLN"),
            ('Foto Modul', "Foto Modul"),
            ('Battery (Total Pack)', "Battery Total Pack"),
            ('Foto Material (Menggunakan Timestemp)', "Foto Material Timestamp")
        ]
        
        labels_aktif = [lbl for _, lbl in list_fotos]
        foto_disembunyikan = st.multiselect("🚫 Sembunyikan foto sementara (untuk kebutuhan screenshot):", labels_aktif)
        
        html_items = []
        for col_name, label in list_fotos:
            if label in foto_disembunyikan:
                continue
                
            url_mentah = data_site.get(col_name)
            thumb_url, zoom_url = konversi_link_gdrive(url_mentah)
            
            if thumb_url:
                # DIBUAT RAPAT TANPA INDENTASI BIAR STREAMLIT GA MENGIRA INI CODE BLOCK
                item_html = f"""<div style="flex: 0 0 auto; width: 140px; margin-right: 15px; text-align: center;">
<a href="{zoom_url}" target="_blank" title="Klik untuk Zoom Resolusi Penuh">
<img src="{thumb_url}" style="width: 130px; height: 130px; object-fit: cover; border-radius: 8px; box-shadow: 0px 4px 8px rgba(0,0,0,0.4); border: 2px solid #444; cursor: pointer; transition: transform 0.2s;"/>
</a>
<div style="font-size: 11px; margin-top: 6px; color: #e0e0e0; white-space: normal; line-height: 1.2;">{label}</div>
</div>"""
                html_items.append(item_html)
                    
        if html_items:
            semua_item = "".join(html_items)
            gallery_html = f"""<div style="display: flex; overflow-x: auto; padding: 15px; background-color: #151515; border-radius: 10px; border: 1px solid #333; margin-top: 5px; scroll-behavior: smooth;">
{semua_item}
</div>"""
            st.markdown(gallery_html, unsafe_allow_html=True)
            st.caption("💡 *Tips: Geser/Scroll ke kanan untuk melihat foto lain. Klik langsung pada gambar untuk memperbesar (zoom) di tab baru.*")
        else:
            st.info("Tidak ada dokumentasi foto yang ditampilkan.")
