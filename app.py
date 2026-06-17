import streamlit as st
import pandas as pd
import requests
import re
import difflib

# Konfigurasi halaman agar fullscreen, responsif, dan rapi ala slide PPT
st.set_page_config(layout="wide", page_title="Task Force 348 Dashboard")

# --- KREDENSIAL MASTER ---
APP_ID = "d3525213-95f5-4dff-9eb3-62842c4964f0"
ACCESS_KEY = "V2-AmIzq-oOhfP-aWkgR-jRkRK-fyAiW-1mj3s-3yfYj-o18dt"
TABLE_NAME = "List"

# ⚠️ PASTIKAN URL DAN KEY SUPABASE LO YANG SUDAH JALAN TETAP TERPASANG DI SINI!
SUPABASE_URL = "https://sfyfijndolnwqklqnpmj.supabase.co"
SUPABASE_KEY = "sb_publishable_digs5GILs-TEe4lEpPj4qQ_VRrQ7FCm"
SUPABASE_TABLE = "dapot_data"

# --- Fungsi Standarisasi & Ekstraksi Format Site ID ---
def format_site_id(site_id):
    if pd.isna(site_id) or str(site_id).strip() == "":
        return "-"
    s = str(site_id).strip().upper().replace(" ", "").replace("-", "").replace("_", "")
    match = re.search(r'[A-Z]{3}\d{3}', s)
    if match:
        return match.group(0)
    s = re.sub(r'^K+P', 'KKP', s)
    return s

# --- Fungsi Pembersih Nama Label Lampiran/Foto ---
def clean_label_name(name):
    if "Log Rectifier" in name: 
        return "Log Recty"
    name_clean = re.sub(r'\s*\(.*?\)\s*', '', str(name))
    return name_clean.strip()

# --- Fungsi Fuzzy Matching ---
def cari_site_terdekat(site_appsheet, list_site_supabase):
    if site_appsheet == "-":
        return None
    cocok = difflib.get_close_matches(site_appsheet, list_site_supabase, n=1, cutoff=0.6)
    return cocok[0] if cocok else None

# --- Fungsi Ekstraksi ID GDrive & Konversi ke Endpoint Thumbnail ---
def konversi_link_gdrive(url_tunggal):
    if not url_tunggal or str(url_tunggal).strip() == "":
        return None, None, None
        
    link_bersih = str(url_tunggal).strip()
    file_id = None
    
    if "id=" in link_bersih:
        id_match = re.search(r'id=([a-zA-Z0-9_-]+)', link_bersih)
        if id_match: file_id = id_match.group(1)
    elif "drive.google.com/file/d/" in link_bersih:
        id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', link_bersih)
        if id_match: file_id = id_match.group(1)
            
    if file_id:
        thumb_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
        zoom_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1600"
        direct_download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        return thumb_url, zoom_url, direct_download_url
        
    return link_bersih, link_bersih, link_bersih

# --- FUNGSI PULL DATA DARI APPSHEET API ---
@st.cache_data(ttl=300)
def load_data_from_appsheet():
    url = f"https://api.appsheet.com/api/v2/apps/{APP_ID}/tables/{TABLE_NAME}/Action"
    headers = { 'ApplicationAccessKey': ACCESS_KEY, 'Content-Type': 'application/json' }
    payload = {
        "Action": "Find",
        "Properties": {"Locale": "id-ID", "Timezone": "Asia/Jakarta"},
        "Rows": []
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200: return pd.DataFrame(response.json())
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- FUNGSI PULL DATA DARI SUPABASE ---
@st.cache_data(ttl=600)
def load_data_from_supabase():
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?select=*"
    headers = { "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}" }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200: return pd.DataFrame(response.json())
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- FUNGSI PUSH DATA KE APPSHEET ---
def update_rekomendasi_appsheet(site_id_asli, nama_kolom_site, teks_rekomendasi):
    url = f"https://api.appsheet.com/api/v2/apps/{APP_ID}/tables/{TABLE_NAME}/Action"
    headers = { 'ApplicationAccessKey': ACCESS_KEY, 'Content-Type': 'application/json' }
    payload = {
        "Action": "Edit",
        "Properties": {"Locale": "id-ID", "Timezone": "Asia/Jakarta"},
        "Rows": [{ nama_kolom_site: site_id_asli, "Rekomendasi Koordinator": teks_rekomendasi }]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code == 200
    except:
        return False

# Load Data
df_app = load_data_from_appsheet()
df_sup = load_data_from_supabase()

if df_app.empty or df_sup.empty:
    st.warning("Gagal memuat data. Periksa koneksi database lo, Zi.")
else:
    # Processing & Merge Data
    kolom_site_app = 'Site' if 'Site' in df_app.columns else ([c for c in df_app.columns if "site" in c.lower() or "id" in c.lower()] + [df_app.columns[0]])[0]
    df_app['site_clean_app'] = df_app[kolom_site_app].apply(format_site_id)
    df_sup['site_clean_sup'] = df_sup['site_id'].apply(format_site_id)
    
    list_site_sup = df_sup['site_clean_sup'].dropna().unique().tolist()
    mapping_fuzzy = {site_a: (site_a if site_a in list_site_sup else cari_site_terdekat(site_a, list_site_sup)) for site_a in df_app['site_clean_app'].unique()}
    df_app['matched_site_sup'] = df_app['site_clean_app'].map(mapping_fuzzy)
    df_merged = pd.merge(df_app, df_sup, left_on='matched_site_sup', right_on='site_clean_sup', how='left', suffixes=('', '_dapot'))

    # Dropdown Formatting
    def susun_nama_dropdown(row):
        s_id = row['matched_site_sup'] if pd.notna(row['matched_site_sup']) else row['site_clean_app']
        s_name = row['site_name'] if pd.notna(row.get('site_name')) else 'UNKNOWN NAME'
        s_class = row['site_class'] if pd.notna(row.get('site_class')) else '-'
        s_grid = row['grid_category_new'] if pd.notna(row.get('grid_category_new')) else '-'
        s_hub = row['hub_site'] if pd.notna(row.get('hub_site')) else '-'
        return f"[{s_id}] ➔ {s_name} ({s_class} • {s_grid} • {s_hub})"
        
    df_merged['dropdown_label'] = df_merged.apply(susun_nama_dropdown, axis=1)

    # --- INJECT CSS CUSTOM UNTUK STYLING PPT PRESENTASI COMPACT ---
    st.markdown("""<style>
    .block-container { padding-top: 3.2rem !important; padding-bottom: 1rem !important; }
    .ppt-header { background-color: #d32f2f; padding: 10px 20px; border-radius: 8px; margin-bottom: 15px; color: white; display: flex; justify-content: space-between; align-items: center; }
    .ppt-card-blue { background-color: #1e3d59; color: white; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 5px solid #ffc13b; }
    .ppt-card-gold { background-color: #ffc13b; color: #1e3d59; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 5px solid #1e3d59; }
    .gallery-container { display: flex; overflow-x: auto; padding: 10px; background-color: #111; border-radius: 8px; border: 1px solid #333; }
    .photo-card { flex: 0 0 auto; width: 110px; margin-right: 12px; text-align: center; position: relative; }
    .hide-checkbox { display: none; }
    .hide-checkbox:checked + .photo-card { display: none; }
    .exclude-btn { position: absolute; top: 1px; right: 8px; background: rgba(211,47,47,0.9); color: white; border-radius: 50%; width: 16px; height: 16px; font-size: 10px; line-height: 16px; cursor: pointer; font-weight: bold; z-index: 10; }
    .lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 99999; justify-content: center; align-items: center; }
    .lightbox:target { display: flex; }
    .lightbox img { max-width: 80%; max-height: 80%; border-radius: 4px; }
    .lightbox .close-lightbox { position: absolute; top: 20px; right: 30px; color: #fff; font-size: 40px; text-decoration: none; }
    div[data-testid="stMetric"] { background-color: #262730; padding: 5px 10px; border-radius: 4px; border: 1px solid #444; }
    .findings-grid { display: grid; grid-template-columns: auto auto; gap: 8px 15px; background-color: #262730; padding: 12px; border-radius: 6px; font-size: 13px; margin-bottom: 10px; border: 1px solid #444; }
    .f-item { display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 4px; }
    /* CSS Footer Personal */
    .custom-footer { text-align: center; font-size: 12px; color: #888; margin-top: 30px; border-top: 1px solid #333; padding-top: 10px; }
    </style>""", unsafe_allow_html=True)

    # --- ROW 1: TOP BAR TITLE SLIDE (PPT HEADER) ---
    col_head_title, col_head_select = st.columns([1.8, 1.2])
    with col_head_title:
        st.markdown("""<div style='background-color: #d32f2f; padding: 8px 15px; border-radius: 6px; color: white;'>
            <h3 style='margin:0; font-size:20px; font-weight:bold;'>Task Force 348 | NOP PALANGKARAYA</h3>
        </div>""", unsafe_allow_html=True)
    with col_head_select:
        label_pilihan = st.selectbox("🎯 Target Monitoring Site ID:", sorted(df_merged['dropdown_label'].unique()), label_visibility="collapsed")

    data_site = df_merged[df_merged['dropdown_label'] == label_pilihan].iloc[0]
    
    # Horizontal Sub-bar untuk Last Data Timestamp
    st.markdown(f"<p style='text-align: right; margin: -10px 5px 10px 0; font-size: 13px;'><b>Last Data:</b> {data_site.get('Timestamp', '-')}</p>", unsafe_allow_html=True)

    # --- ROW 2: MAIN PRESENTATION GRID (3 COLUMNS SPLIT) ---
    col1, col2, col3 = st.columns([1, 0.9, 1.3])

    # ================= SLIDE ELEMENT 1: BASIC INFO MASTER =================
    with col1:
        st.markdown("<div class='ppt-card-blue'><b style='font-size:15px;'>📋 Site Master Specification</b></div>", unsafe_allow_html=True)
        info_dasar = {
            "Parameter": ["Site ID", "Site Name", "Class", "Grid", "Hub", "Phase", "Grounding KWH"],
            "Value": [
                data_site['site_id'] if pd.notna(data_site.get('site_id')) else '-',
                data_site['site_name'] if pd.notna(data_site.get('site_name')) else '-',
                data_site['site_class'] if pd.notna(data_site.get('site_class')) else '-',
                data_site['grid_category_new'] if pd.notna(data_site.get('grid_category_new')) else '-',
                data_site['hub_site'] if pd.notna(data_site.get('hub_site')) else '-',
                data_site.get('Phase PLN', '-'),
                data_site.get('Grounding KWH', '-')
            ]
        }
        st.dataframe(pd.DataFrame(info_dasar), hide_index=True, use_container_width=True, height=245)

    # ================= SLIDE ELEMENT 2: POWER GRID METRICS =================
    with col2:
        st.markdown("<div class='ppt-card-blue'><b style='font-size:15px;'>⚡ Kelistrikan & Power Grid</b></div>", unsafe_allow_html=True)
        
        vm1, vm2 = st.columns(2)
        with vm1:
            st.metric(label="Tegangan R-N", value=f"{data_site.get('Tegangan PLN (R-N)', '-')} V")
            st.metric(label="Tegangan S-N", value=f"{data_site.get('Tegangan PLN (S-N)', '-')} V")
            st.metric(label="Tegangan T-N", value=f"{data_site.get('Tegangan PLN (T-N)', '-')} V")
            st.metric(label="G-N Grounding", value=f"{data_site.get('G-N Grounding ke Netral', '-')} V")
        with vm2:
            st.metric(label="Beban PLN (R)", value=f"{data_site.get('Beban PLN (R)', '-')} A")
            st.metric(label="Beban PLN (S)", value=f"{data_site.get('Beban PLN (S)', '-')} A")
            st.metric(label="Beban PLN (T)", value=f"{data_site.get('Beban PLN (T)', '-')} A")

    # ================= SLIDE ELEMENT 3: OPERATIONAL FINDINGS & LOG REKOMENDASI =================
    with col3:
        st.markdown("<div class='ppt-card-gold'><b>🔍 Field Findings & Action Log</b></div>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='findings-grid'>
            <div class='f-item'><b>Arus Recty:</b> <span>{data_site.get('Rectifier Current', '-')} A</span></div>
            <div class='f-item'><b>Modul:</b> <span>{data_site.get('Jumlah Module', '-')} <span style='color:#ff5252;'>(Faulty: {data_site.get('Total Module faulty', '-')})</span></span></div>
            <div class='f-item'><b>BBT:</b> <span>{data_site.get('BBT >4 Jam', '-')}</span></div>
            <div class='f-item'><b>Enva Val:</b> <span>{data_site.get('Enva Validasi', '-')}</span></div>
            <div class='f-item'><b>LPU Enva:</b> <span>{data_site.get('Kondisi Modul Enva LPU', '-')}</span></div>
            <div class='f-item'><b>Arrester:</b> <span>{data_site.get('Arrester Rectifier', '-')}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        rekomendasi_sekarang = data_site.get('Rekomendasi Koordinator', '')
        if pd.isna(rekomendasi_sekarang): rekomendasi_sekarang = ""
            
        rekomendasi_input = st.text_area("Rekomendasi Koordinator Lapangan:", value=str(rekomendasi_sekarang), placeholder="Input tindakan di sini...", key="input_rekomendasi", height=68, label_visibility="collapsed")
        
        if st.button("💾 Push Update Data", use_container_width=True):
            if rekomendasi_input.strip() != "":
                with st.spinner("Pushing..."):
                    if update_rekomendasi_appsheet(data_site[kolom_site_app], kolom_site_app, rekomendasi_input):
                        st.cache_data.clear()
                        st.rerun()

    # --- ROW 3: FOOTER ROW (GALLERY SCANNER & FILE ATTACHMENTS) ---
    all_detected_photos = []
    all_detected_csvs = []
    seen_urls = set()
    
    for col_name in df_app.columns:
        val = data_site.get(col_name)
        if pd.isna(val) or not val: continue
        urls = re.findall(r'(https?://[^\s,"\'\}]+)', str(val))
        
        for idx, url in enumerate(urls):
            if url in seen_urls: continue
            seen_urls.add(url)
            
            is_csv = "csv" in col_name.lower() or ".csv" in url.lower() or "data" in col_name.lower()
            thumb_url, zoom_url, download_url = konversi_link_gdrive(url)
            
            base_label = clean_label_name(col_name)
            final_label = f"{base_label} #{idx+1}" if len(urls) > 1 else base_label
            
            if thumb_url and not is_csv:
                all_detected_photos.append({ 'label': final_label, 'col_name': col_name, 'idx': idx, 'thumb_url': thumb_url, 'zoom_url': zoom_url })
            elif is_csv:
                all_detected_csvs.append({ 'label': final_label, 'download_url': download_url })

    st.markdown("<div style='margin-top: 5px; margin-bottom: 2px; font-size:14px;'><b>📁 Attachments & Dokumentasi Slide</b></div>", unsafe_allow_html=True)
    
    bot_csv, bot_gal = st.columns([0.8, 2.2])
    
    with bot_csv:
        if all_detected_csvs:
            for csv_file in all_detected_csvs:
                st.link_button(f"📥 {csv_file['label']}", csv_file['download_url'], use_container_width=True)
        else:
            st.caption("No CSV Data uploaded.")

    with bot_gal:
        html_items = []
        for p in all_detected_photos:
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', f"{p['col_name']}{p['idx']}")
            item_html = f"""<input type="checkbox" id="hide-{safe_id}" class="hide-checkbox">
<div class="photo-card">
<label for="hide-{safe_id}" class="exclude-btn" title="Hide">&times;</label>
<a href="#lightbox-{safe_id}"><img src="{p['thumb_url']}" style="width: 100px; height: 75px; object-fit: cover; border-radius: 4px; border: 1px solid #555;"/></a>
<div style="font-size: 10px; margin-top: 4px; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{p['label']}</div>
</div>
<div id="lightbox-{safe_id}" class="lightbox"><a href="#" class="close-lightbox">&times;</a><img src="{p['zoom_url']}"></div>"""
            html_items.append(item_html)
                
        if html_items:
            st.markdown(f"""<div class="gallery-container">{"".join(html_items)}</div>""", unsafe_allow_html=True)
        else:
            st.caption("No unique documentation photos found.")

    # --- WATERMARK FOOTER ---
    st.markdown("<div class='custom-footer'>© 2026 | Created with ❤️ by Fauzi Ramdani - 97122</div>", unsafe_allow_html=True)
