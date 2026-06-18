import streamlit as st
import pandas as pd
import requests
import re
import difflib

# Konfigurasi halaman agar fullscreen, responsif, dan rapi ala slide PPT
st.set_page_config(layout="wide", page_title="Task Force 348 Dashboard")

# --- KREDENSIAL & DATA SOURCE MASTER ---
GOOGLE_SHEET_ID = "1FGKOzWoUrbf3PXN_ahgG1t-83JZT4H4sioQepePbBxM"

# ⚠️ PASTIKAN URL APPS SCRIPT LO TETAP TERPASANG DI SINI!
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxCQUGt5_Jybed2AwFP4xXFru6GxuMoSwQpUZ63aK9o0WlUFnumOoseRWwgRmxZZ9XYtQ/exec"

# ⚠️ PASTIKAN URL DAN KEY SUPABASE LO TETAP TERPASApplication SEPERTI SEBELUMNYA!
SUPABASE_URL = "https://sfyfijndolnwqklqnpmj.supabase.co"
SUPABASE_KEY = "sb_publishable_digs5GILs-TEe4lEpPj4qQ_VRrQ7FCm"
SUPABASE_TABLE_DAPOT = "dapot_data"
SUPABASE_TABLE_INAP = "inap_data"  # Tabel baru untuk tren mingguan availability

# --- Fungsi Standarisasi & Ekstraksi Format Site ID ---
def format_site_id(site_id):
    if pd.isna(site_id) or str(site_id).strip() == "": return "-"
    s = str(site_id).strip().upper().replace(" ", "").replace("-", "").replace("_", "")
    match = re.search(r'[A-Z]{3}\d{3}', s)
    if match: return match.group(0)
    return re.sub(r'^K+P', 'KKP', s)

def clean_label_name(name):
    if "Log Rectifier" in name: return "Log Recty"
    return re.sub(r'\s*\(.*?\)\s*', '', str(name)).strip()

def cari_site_terdekat(site_appsheet, list_site_supabase):
    if site_appsheet == "-": return None
    cocok = difflib.get_close_matches(site_appsheet, list_site_supabase, n=1, cutoff=0.6)
    return cocok[0] if cocok else None

def konversi_link_gdrive(url_tunggal):
    if not url_tunggal or str(url_tunggal).strip() == "": return None, None, None, None
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
        dl_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        embed_url = f"https://drive.google.com/file/d/{file_id}/preview"
        return thumb_url, zoom_url, dl_url, embed_url
    return link_bersih, link_bersih, link_bersih, None

# --- Fungsi Kirim Update Rekomendasi ke Google Sheet ---
def update_rekomendasi_gsheet(site_id_asli, teks_rekomendasi):
    if "GANTI_PAKE_URL" in APPS_SCRIPT_URL: return False, "URL Web App Apps Script belum lo pasang di code, Zi!"
    try:
        payload = {"site_id": str(site_id_asli).strip(), "rekomendasi": str(teks_rekomendasi).strip()}
        response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
        if response.status_code == 200 and "Sukses" in response.text: return True, "Sukses"
        return False, response.text
    except Exception as e: return False, str(e)

# --- FUNGSI DATA FETCHING (GSHEET & SUPABASE) ---
@st.cache_data(ttl=60)
def load_data_from_google_sheets():
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"
    try: return pd.read_csv(url)
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_data_from_supabase(table_name):
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=*"
    headers = { "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}" }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200: return pd.DataFrame(response.json())
        return pd.DataFrame()
    except: return pd.DataFrame()

df_sheet = load_data_from_google_sheets()
df_sup_dapot = load_data_from_supabase(SUPABASE_TABLE_DAPOT)
df_sup_inap = load_data_from_supabase(SUPABASE_TABLE_INAP) # Tarik master data inap_data untuk grafik trend

if df_sheet.empty or df_sup_dapot.empty:
    st.error("🚨 Gagal sinkronisasi data! Cek kembali setting share Google Sheet lo atau kredensial Supabase-nya.")
else:
    # Processing Data Core
    kolom_site_sheet = 'Site' if 'Site' in df_sheet.columns else ([c for c in df_sheet.columns if "site" in c.lower() or "id" in c.lower()] + [df_sheet.columns[0]])[0]
    df_sheet['site_clean_sheet'] = df_sheet[kolom_site_sheet].apply(format_site_id)
    df_sup_dapot['site_clean_sup'] = df_sup_dapot['site_id'].apply(format_site_id)
    
    list_site_sup = df_sup_dapot['site_clean_sup'].dropna().unique().tolist()
    mapping_fuzzy = {site_s: (site_s if site_s in list_site_sup else cari_site_terdekat(site_s, list_site_sup)) for site_s in df_sheet['site_clean_sheet'].unique()}
    df_sheet['matched_site_sup'] = df_sheet['site_clean_sheet'].map(mapping_fuzzy)
    df_merged = pd.merge(df_sheet, df_sup_dpot := df_sup_dapot, left_on='matched_site_sup', right_on='site_clean_sup', how='left', suffixes=('', '_dapot'))

    def susun_nama_dropdown(row):
        s_id = row['matched_site_sup'] if pd.notna(row['matched_site_sup']) else row['site_clean_sheet']
        s_name = row['site_name'] if pd.notna(row.get('site_name')) else 'UNKNOWN NAME'
        s_class = row['site_class'] if pd.notna(row.get('site_class')) else '-'
        s_grid = row['grid_category_new'] if pd.notna(row.get('grid_category_new')) else '-'
        s_hub = row['hub_site'] if pd.notna(row.get('hub_site')) else '-'
        return f"[{s_id}] ➔ {s_name} ({s_class} • {s_grid} • {s_hub})"
        
    df_merged['dropdown_label'] = df_merged.apply(susun_nama_dropdown, axis=1)

    # --- INJECT CSS CUSTOM UNTUK SLIDE & NAVIGASI FOTO ---
    st.markdown("""<style>
    .block-container { padding-top: 3.5rem !important; padding-bottom: 1rem !important; }
    .ppt-card-blue { background-color: #1e3d59; color: white; padding: 10px; border-radius: 6px; margin-bottom: 8px; border-left: 5px solid #ffc13b; }
    .ppt-card-gold { background-color: #ffc13b; color: #1e3d59; padding: 10px; border-radius: 6px; margin-bottom: 8px; border-left: 5px solid #1e3d59; }
    .gallery-container { display: flex; overflow-x: auto; padding: 10px; background-color: #111; border-radius: 8px; border: 1px solid #333; }
    .photo-card { flex: 0 0 auto; width: 110px; margin-right: 12px; text-align: center; position: relative; }
    .hide-checkbox { display: none; }
    .hide-checkbox:checked + .photo-card { display: none; }
    .exclude-btn { position: absolute; top: 1px; right: 8px; background: rgba(211,47,47,0.9); color: white; border-radius: 50%; width: 16px; height: 16px; font-size: 10px; line-height: 16px; cursor: pointer; font-weight: bold; z-index: 10; }
    
    /* FIX POPUP LIGHTBOX DENGAN TOMBOL NAVIGASI KANAN KIRI */
    .lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.96); z-index: 99999999 !important; justify-content: center; align-items: center; }
    .lightbox:target { display: flex; }
    .lightbox img, .lightbox iframe { max-width: 80%; max-height: 80%; border-radius: 6px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
    .lightbox .close-lightbox { position: absolute; top: 65px; right: 40px; color: #fff; font-size: 45px; text-decoration: none; font-weight: bold; z-index: 99999999 !important; text-shadow: 0px 2px 4px rgba(0,0,0,0.8); }
    
    /* REQ 3: CSS Tombol Panah Geser Kanan-Kiri */
    .lightbox .nav-arrow { position: absolute; top: 50%; color: #fff; font-size: 50px; font-weight: bold; text-decoration: none; transform: translateY(-50%); padding: 20px; z-index: 99999999 !important; text-shadow: 0px 2px 8px rgba(0,0,0,0.9); transition: 0.2s; user-select: none; }
    .lightbox .nav-arrow:hover { color: #ed1c24; scale: 1.1; }
    .lightbox .prev-arrow { left: 40px; }
    .lightbox .next-arrow { right: 40px; }
    
    div[data-testid="stMetric"] { background-color: #262730; padding: 4px 8px; border-radius: 4px; border: 1px solid #444; }
    .findings-grid { display: grid; grid-template-columns: auto auto; gap: 6px 12px; background-color: #262730; padding: 10px; border-radius: 6px; font-size: 12px; margin-bottom: 5px; border: 1px solid #444; }
    .f-item { display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 2px; }
    .custom-footer { text-align: center; font-size: 11px; color: #666; margin-top: 15px; border-top: 1px solid #222; padding-top: 6px; }
    .video-overlay-btn { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(211, 47, 47, 0.85); color: white; border-radius: 50%; width: 26px; height: 24px; line-height: 24px; font-size: 11px; font-weight: bold; pointer-events: none; }
    </style>""", unsafe_allow_html=True)

    # --- ROW 1: BANNER SLIDE ---
    col_head_title, col_head_select = st.columns([1.8, 1.2])
    with col_head_title:
        st.markdown("""<div style='background: linear-gradient(135deg, #ed1c24 0%, #b71c1c 50%, #1a1a1a 100%); padding: 12px 20px; border-radius: 6px; color: white; border-left: 6px solid #ffc13b; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'><h3 style='margin:0; font-size:22px; font-weight:900; letter-spacing: 0.5px;'>🚀 TASK FORCE 348 <span style='color: #ffc13b;'>|</span> NOP PALANGKARAYA</h3><p style='margin: 2px 0 0 0; font-size: 12px; opacity: 0.9; font-weight: 500;'>TELECOMMUNICATION & NETWORK OPERATION DASHBOARD</p></div>""", unsafe_allow_html=True)
    with col_head_select:
        label_pilihan = st.selectbox("🎯 Target Monitoring Site ID:", sorted(df_merged['dropdown_label'].unique()), label_visibility="collapsed")

    data_site = df_merged[df_merged['dropdown_label'] == label_pilihan].iloc[0]
    st.markdown(f"<p style='text-align: right; margin: -5px 5px 8px 0; font-size: 13px;'><b>Last Data:</b> {data_site.get('Timestamp', '-')}</p>", unsafe_allow_html=True)

    # --- ROW 2: PRESENTATION GRID (4 COLUMNS FLAT DESIGN) ---
    col1, col2, col3, col4 = st.columns([1, 1, 1.1, 1.1])

    # ================= KOLOM 1: BASIC INFO MASTER =================
    with col1:
        st.markdown("<div class='ppt-card-blue'><b style='font-size:14px;'>📋 Site Master Specification</b></div>", unsafe_allow_html=True)
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

    # ================= KOLOM 2: METRIS KELISTRIKAN & CARD SETTING 🔋 =================
    with col2:
        st.markdown("<div class='ppt-card-blue'><b style='font-size:14px;'>⚡ Kelistrikan Grid</b></div>", unsafe_allow_html=True)
        vm1, vm2 = st.columns(2)
        with vm1:
            st.metric(label="Tegangan R-N", value=f"{data_site.get('Tegangan PLN (R-N)', '-')} V")
            st.metric(label="Tegangan S-N", value=f"{data_site.get('Tegangan PLN (S-N)', '-')} V")
        with vm2:
            st.metric(label="Tegangan T-N", value=f"{data_site.get('Tegangan PLN (T-N)', '-')} V")
            st.metric(label="G-N Grounding", value=f"{data_site.get('G-N Grounding ke Netral', '-')} V")
            
        # REQ 4: Penambahan Card Setting Prio Disconnect & Charging Tegangan Battery
        st.markdown("<div class='ppt-card-blue' style='margin-top:10px; background-color:#152a3a;'><b style='font-size:13px;'>🔋 Battery & Disconnect Settings</b></div>", unsafe_allow_html=True)
        
        # Deteksi dinamis kolom setting dari spreadsheet
        prio_val = "-"
        for c in df_sheet.columns:
            if 'prio' in c.lower() or 'discon' in c.lower():
                if pd.notna(data_site.get(c)) and str(data_site.get(c)).strip() != "":
                    prio_val = str(data_site.get(c))
                    break
        
        charge_val = "-"
        for c in df_sheet.columns:
            if 'charg' in c.lower() or ('tegang' in c.lower() and 'batt' in c.lower()):
                if pd.notna(data_site.get(c)) and str(data_site.get(c)).strip() != "":
                    charge_val = str(data_site.get(c))
                    break
                    
        st.markdown(f"""
        <div style='background-color:#262730; padding:10px; border-radius:4px; font-size:12px; border:1px solid #444; line-height:1.5;'>
            • <b>Prio Disconnect:</b> <span style='color:#ffc13b; font-weight:bold;'>{prio_val}</span><br>
            • <b>Charging Tegangan:</b> <span style='color:#ffc13b; font-weight:bold;'>{charge_val}</span>
        </div>
        """, unsafe_allow_html=True)

    # ================= KOLOM 3: FINDINGS & REQ 2: GRAFIK TREND AVAILABILITY 📈 =================
    with col3:
        st.markdown("<div class='ppt-card-gold'><b style='font-size:14px;'>🔍 Field Findings</b></div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='findings-grid'><div class='f-item'><b>Arus Recty:</b> <span>{data_site.get('Rectifier Current', '-')} A</span></div><div class='f-item'><b>Modul:</b> <span>{data_site.get('Jumlah Module', '-')} <span style='color:#ff5252;'>(F: {data_site.get('Total Module faulty', '-')})</span></span></div><div class='f-item'><b>BBT:</b> <span>{data_site.get('BBT >4 Jam', '-')}</span></div><div class='f-item'><b>Enva Val:</b> <span>{data_site.get('Enva Validasi', '-')}</span></div><div class='f-item'><b>LPU Enva:</b> <span>{data_site.get('Kondisi Modul Enva LPU', '-')}</span></div><div class='f-item'><b>Arrester:</b> <span>{data_site.get('Arrester Rectifier', '-')}</span></div></div>""", unsafe_allow_html=True)
        
        # REQ 2: Render Grafik Trend Availability secara Weekly dari table inap_data Supabase
        st.markdown("<b style='font-size:11px; color:#aaa;'>📈 Weekly Availability Trend (Power & Transport)</b>", unsafe_allow_html=True)
        if not df_sup_inap.empty:
            df_sup_inap['site_clean'] = df_sup_inap['site_id'].apply(format_site_id)
            df_site_avail = df_sup_inap[df_sup_inap['site_clean'] == data_site['site_clean_sheet']]
            
            # Deteksi otomatis nama kolom di inap_data
            col_w = [c for c in df_site_avail.columns if 'week' in c.lower() or 'minggu' in c.lower() or 'date' in c.lower()]
            col_p = [c for c in df_site_avail.columns if 'power' in c.lower() or 'pwr' in c.lower()]
            col_t = [c for c in df_site_avail.columns if 'transport' in c.lower() or 'trans' in c.lower()]
            
            if col_w and col_p and col_t and not df_site_avail.empty:
                df_chart = df_site_avail[[col_w[0], col_p[0], col_t[0]]].copy()
                df_chart.columns = ['Week', 'Power Avail', 'Transport Avail']
                df_chart = df_chart.sort_values(by='Week')
                df_chart.set_index('Week', inplace=True)
                st.line_chart(df_chart, height=95)
            else:
                st.caption("ℹ️ *Data trend availability site ini belum ada di inap_data.*")
        else:
            st.caption("ℹ️ *Gagal memuat table inap_data.*")

    # ================= KOLOM 4: REQ 1: INPUT & DISPLAY IMPROVEMENT RECOMMENDATION ✏️ =================
    with col4:
        st.markdown("<div class='ppt-card-gold'><b style='font-size:14px;'>📝 Action Log Plan</b></div>", unsafe_allow_html=True)
        st.markdown("<b style='font-size:12px; color:#aaa;'>✏️ Improvement Recommendation:</b>", unsafe_allow_html=True)
        
        # REQ 1: Menampilkan data rekomendasi perbaikan yang sudah eksis di web
        rekomendasi_sekarang = data_site.get('Rekomendasi Perbaikan', '')
        if pd.isna(rekomendasi_sekarang): rekomendasi_sekarang = ""
        
        rekomendasi_input = st.text_area("Kolom Input Rekomendasi Korlap:", value=str(rekomendasi_sekarang), placeholder="Ketik rekomendasi perbaikan di sini, Zi...", key="input_rekomendasi", height=110, label_visibility="collapsed")
        
        @st.dialog("Konfirmasi Pengiriman")
        def popup_konfirmasi(teks_reko):
            st.markdown(f"Apakah lo beneran yakin ingin menyimpan rekomendasi untuk site **{data_site[kolom_site_sheet]}** ini?")
            st.info(f"📝 *{teks_reko}*")
            st.write("")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("👍 Ya, Simpan", use_container_width=True):
                    with st.spinner("Mengupdate Google Sheet..."):
                        sukses, pesan = update_rekomendasi_gsheet(data_site[kolom_site_sheet], teks_reko)
                        if sukses:
                            st.success("Data berhasil terupdate ke Google Sheet!")
                            st.cache_data.clear()
                            st.rerun()
                        else: st.error(f"Gagal menyimpan: {pesan}")
            with btn_col2:
                if st.button("❌ Tidak", use_container_width=True): st.rerun()

        if st.button("💾 Push Update Data", use_container_width=True):
            if rekomendasi_input.strip() == "": st.warning("Isi kolom rekomendasi terlebih dahulu!")
            else: popup_konfirmasi(rekomendasi_input)

    # --- ROW 3: FOOTER PRESENTASI (REQ 3: EVIDENCE GALLERY & INTERACTIVE LIGHTBOX) ---
    st.markdown("<div style='margin-top: 5px; margin-bottom: 2px; font-size:14px;'><b>📁 Evidence & Dokumentasi Slide</b></div>", unsafe_allow_html=True)
    
    all_detected_photos, all_detected_csvs, seen_urls = [], [], set()
    kolom_video = [c for c in df_sheet.columns if "voltage" in c.lower() and "backup" in c.lower()]
    
    for col_name in df_sheet.columns:
        val = data_site.get(col_name)
        if pd.isna(val) or not val: continue
        urls = re.findall(r'(https?://[^\s,"\'\}]+)', str(val))
        
        for idx, url in enumerate(urls):
            if url in seen_urls: continue
            seen_urls.add(url)
            is_csv = "csv" in col_name.lower() or ".csv" in url.lower() or "data" in col_name.lower()
            is_video = kolom_video and col_name == kolom_video[0] or ".mp4" in url.lower() or ".mov" in url.lower()
            
            thumb_url, zoom_url, download_url, embed_video_url = konversi_link_gdrive(url)
            base_label = clean_label_name(col_name)
            final_label = f"{base_label} #{idx+1}" if len(urls) > 1 else base_label
            
            if thumb_url and not is_csv:
                all_detected_photos.append({ 'label': final_label, 'col_name': col_name, 'idx': idx, 'thumb_url': thumb_url, 'zoom_url': zoom_url, 'is_video': is_video, 'embed_video_url': embed_video_url })
            elif is_csv:
                all_detected_csvs.append({ 'label': final_label, 'download_url': download_url })

    bot_csv, bot_gal = st.columns([0.8, 2.2])
    with bot_csv:
        if all_detected_csvs:
            for csv_file in all_detected_csvs: st.link_button(f"📥 {csv_file['label']}", csv_file['download_url'], use_container_width=True)
        else: st.caption("No CSV Data uploaded.")

    with bot_gal:
        html_items = []
        total_photos = len(all_detected_photos)
        
        for idx, p in enumerate(all_detected_photos):
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', f"{p['col_name']}{p['idx']}")
            
            # REQ 3: Hitung ID target sebelum (prev) dan sesudah (next) untuk memicu geser foto
            prev_p = all_detected_photos[(idx - 1) % total_photos]
            next_p = all_detected_photos[(idx + 1) % total_photos]
            safe_id_prev = re.sub(r'[^a-zA-Z0-9]', '', f"{prev_p['col_name']}{prev_p['idx']}")
            safe_id_next = re.sub(r'[^a-zA-Z0-9]', '', f"{next_p['col_name']}{next_p['idx']}")
            
            # Navigasi panah HTML rapi
            arrows_html = f'<a href="#lightbox-{safe_id_prev}" class="nav-arrow prev-arrow">❮</a><a href="#lightbox-{safe_id_next}" class="nav-arrow next-arrow">❯</a>'
            
            if p['is_video'] and p['embed_video_url']:
                item_html = f'<input type="checkbox" id="hide-{safe_id}" class="hide-checkbox"><div class="photo-card"><label for="hide-{safe_id}" class="exclude-btn" title="Hide">&times;</label><a href="#lightbox-{safe_id}"><div style="position: relative; width: 100px; height: 75px;"><img src="{p["thumb_url"]}" style="width: 100px; height: 75px; object-fit: cover; border-radius: 4px; border: 1px solid #555; opacity: 0.7;"/><div class="video-overlay-btn">▶</div></div></a><div style="font-size: 10px; margin-top: 4px; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{p["label"]}</div></div><div id="lightbox-{safe_id}" class="lightbox"><a href="#" class="close-lightbox">&times;</a>{arrows_html}<iframe src="{p["embed_video_url"]}" width="80%" height="80%" style="border:none; background:#000; border-radius:6px;" allow="autoplay"></iframe></div>'
            else:
                item_html = f'<input type="checkbox" id="hide-{safe_id}" class="hide-checkbox"><div class="photo-card"><label for="hide-{safe_id}" class="exclude-btn" title="Hide">&times;</label><a href="#lightbox-{safe_id}"><img src="{p["thumb_url"]}" style="width: 100px; height: 75px; object-fit: cover; border-radius: 4px; border: 1px solid #555;"/></a><div style="font-size: 10px; margin-top: 4px; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{p["label"]}</div></div><div id="lightbox-{safe_id}" class="lightbox"><a href="#" class="close-lightbox">&times;</a>{arrows_html}<img src="{p["zoom_url"]}"></div>'
            html_items.append(item_html)
                
        if html_items: st.markdown(f'<div class="gallery-container">{"".join(html_items)}</div>', unsafe_allow_html=True)
        else: st.caption("No unique documentation photos found.")

    st.markdown("<div class='custom-footer'>© 2026 | Created with ❤️ by Fauzi Ramdani - 97122</div>", unsafe_allow_html=True)
