import streamlit as st
import pandas as pd
import requests
import re
import difflib

# Konfigurasi halaman agar fullscreen, responsif, dan rapi ala slide PPT
st.set_page_config(layout="wide", page_title="Task Force 348 Dashboard")

# --- KREDENSIAL & DATA SOURCE MASTER ---
GOOGLE_SHEET_ID = "1FGKOzWoUrbf3PXN_ahgG1t-83JZT4H4sioQepePbBxM"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxCQUGt5_Jybed2AwFP4xXFru6GxuMoSwQpUZ63aK9o0WlUFnumOoseRWwgRmxZZ9XYtQ/exec"

SUPABASE_URL = "https://sfyfijndolnwqklqnpmj.supabase.co"
SUPABASE_KEY = "sb_publishable_digs5GILs-TEe4lEpPj4qQ_VRrQ7FCm"
SUPABASE_TABLE_DAPOT = "dapot_data"
SUPABASE_TABLE_INAP = "inap_data"

# --- Fungsi Standarisasi & Ekstraksi Format Site ID ---
def format_site_id(site_id):
    if pd.isna(site_id) or str(site_id).strip() == "": return "-"
    s = str(site_id).strip().upper().replace(" ", "").replace("-", "").replace("_", "")
    match = re.search(r'([A-Z]{2,4})(\d+)', s)
    if match: return f"{match.group(1)}{match.group(2).zfill(3)}"
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

def dapatkan_nilai_teknis(row, kolom_sheet, kolom_supabase):
    val_sheet = row.get(kolom_sheet)
    if pd.notna(val_sheet) and str(val_sheet).strip() not in ["", "-", "nan"]:
        return str(val_sheet).strip()
    
    val_sup = row.get(f"{kolom_supabase}_dapot") if f"{kolom_supabase}_dapot" in row else row.get(kolom_supabase)
    if pd.notna(val_sup) and str(val_sup).strip() not in ["", "-", "nan"]:
        return str(val_sup).strip()
    return "-"

def update_rekomendasi_gsheet(site_id_asli, teks_rekomendasi):
    try:
        payload = {"site_id": str(site_id_asli).strip(), "rekomendasi": str(teks_rekomendasi).strip()}
        response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
        if response.status_code == 200 and "Sukses" in response.text: return True, "Sukses"
        return False, response.text
    except Exception as e: return False, str(e)

# --- FUNGSI PULL DATA UTAMA ---
@st.cache_data(ttl=60)
def load_data_from_google_sheets():
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"
    try: return pd.read_csv(url)
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_data_from_supabase_dapot():
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE_DAPOT}?select=*&limit=5000"
    headers = { "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}" }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200: return pd.DataFrame(response.json())
        return pd.DataFrame()
    except: return pd.DataFrame()

# FITUR: Pencarian Multi-Varian (KKN075 & KKN75 sekaligus)
def fetch_inap_for_site(site_clean, site_asli):
    variations = set([str(site_clean).strip(), str(site_asli).strip()])
    
    # Kalau polanya ada 0 di tengah (Contoh: KKN075), bikin variasi tanpa 0 (KKN75)
    if site_clean:
        match = re.search(r'([A-Z]+)0+(\d+)', site_clean)
        if match: variations.add(f"{match.group(1)}{match.group(2)}")
            
    valid_vars = [v for v in variations if v not in ["", "-", "nan"]]
    if not valid_vars: return pd.DataFrame()
    
    # Bikin filter "ATAU" untuk menembak semua kemungkinan nama ID di Supabase
    filters = ",".join([f"site_id.ilike.*{v}*" for v in valid_vars])
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE_INAP}?or=({filters})&limit=1000"
    headers = { "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}" }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200: return pd.DataFrame(res.json())
    except: pass
    return pd.DataFrame()

df_sheet = load_data_from_google_sheets()
df_sup_dapot = load_data_from_supabase_dapot()

if df_sheet.empty or df_sup_dapot.empty:
    st.error("🚨 Gagal memuat data utama! Cek koneksi Google Sheet (Geser tab ke paling kiri) & Supabase Credentials.")
else:
    kolom_site_sheet = 'Site' if 'Site' in df_sheet.columns else ([c for c in df_sheet.columns if "site" in c.lower() or "id" in c.lower()] + [df_sheet.columns[0]])[0]
    df_sheet['site_clean_sheet'] = df_sheet[kolom_site_sheet].apply(format_site_id)
    df_sup_dapot['site_clean_sup'] = df_sup_dapot['site_id'].apply(format_site_id)
    
    list_site_sup = df_sup_dapot['site_clean_sup'].dropna().unique().tolist()
    mapping_fuzzy = {site_s: (site_s if site_s in list_site_sup else cari_site_terdekat(site_s, list_site_sup)) for site_s in df_sheet['site_clean_sheet'].unique()}
    df_sheet['matched_site_sup'] = df_sheet['site_clean_sheet'].map(mapping_fuzzy)
    df_merged = pd.merge(df_sheet, df_sup_dapot, left_on='matched_site_sup', right_on='site_clean_sup', how='left', suffixes=('', '_dapot'))

    def susun_nama_dropdown(row):
        s_id = row['matched_site_sup'] if pd.notna(row['matched_site_sup']) else row['site_clean_sheet']
        s_name = row['site_name'] if pd.notna(row.get('site_name')) else 'UNKNOWN NAME'
        return f"[{s_id}] ➔ {s_name}"
        
    df_merged['dropdown_label'] = df_merged.apply(susun_nama_dropdown, axis=1)

    # --- CSS CUSTOM ---
    st.markdown("""<style>
    .block-container { padding-top: 3.2rem !important; padding-bottom: 1rem !important; }
    .ppt-card-blue { background-color: #1e3d59; color: white; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 5px solid #ffc13b; }
    .ppt-card-gold { background-color: #ffc13b; color: #1e3d59; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 5px solid #1e3d59; }
    .gallery-container { display: flex; overflow-x: auto; padding: 10px; background-color: #111; border-radius: 8px; border: 1px solid #333; }
    .photo-card { flex: 0 0 auto; width: 110px; margin-right: 12px; text-align: center; position: relative; cursor: pointer; }
    .hide-checkbox { display: none; }
    .hide-checkbox:checked + .photo-card { display: none; }
    .exclude-btn { position: absolute; top: 1px; right: 8px; background: rgba(211,47,47,0.9); color: white; border-radius: 50%; width: 16px; height: 16px; font-size: 10px; line-height: 16px; cursor: pointer; font-weight: bold; z-index: 10; }
    .lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 9999999; justify-content: center; align-items: center; }
    .lightbox:target { display: flex; }
    .lightbox img, .lightbox iframe { max-width: 80%; max-height: 80%; border-radius: 6px; box-shadow: 0px 5px 25px rgba(0,0,0,0.5); }
    .lightbox .close-lightbox { position: absolute; top: 20px; right: 40px; color: #fff; font-size: 40px; text-decoration: none; font-weight: bold; z-index: 99999999; text-shadow: 0px 2px 5px #000; }
    .lightbox .nav-arrow { position: absolute; top: 50%; color: #fff; font-size: 50px; font-weight: bold; text-decoration: none; transform: translateY(-50%); padding: 20px; z-index: 99999999; text-shadow: 0px 2px 8px #000; }
    .lightbox .prev-arrow { left: 40px; } .lightbox .next-arrow { right: 40px; }
    .lightbox .caption-text { position: absolute; bottom: 30px; color: #ffc13b; font-size: 18px; font-weight: bold; text-align: center; width: 100%; text-shadow: 0px 2px 4px rgba(0,0,0,0.8); z-index: 99999999; font-family: sans-serif; letter-spacing: 0.5px; }
    .video-overlay-btn { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(211, 47, 47, 0.85); color: white; border-radius: 50%; width: 26px; height: 24px; line-height: 24px; font-size: 11px; font-weight: bold; pointer-events: none; box-shadow: 0px 2px 5px rgba(0,0,0,0.5); }
    div[data-testid="stMetric"] { background-color: #262730; padding: 5px 10px; border-radius: 4px; border: 1px solid #444; }
    .findings-grid { display: grid; grid-template-columns: auto auto; gap: 8px 15px; background-color: #262730; padding: 12px; border-radius: 6px; font-size: 13px; margin-bottom: 10px; border: 1px solid #444; }
    .f-item { display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 4px; }
    .custom-footer { text-align: center; font-size: 12px; color: #888; margin-top: 30px; border-top: 1px solid #333; padding-top: 10px; }
    </style>""", unsafe_allow_html=True)

    # --- ROW 1: HEADER ---
    col_head_title, col_head_select = st.columns([1.8, 1.2])
    with col_head_title:
        st.markdown("""<div style='background: linear-gradient(135deg, #ed1c24 0%, #b71c1c 50%, #1a1a1a 100%); padding: 12px 20px; border-radius: 6px; color: white; border-left: 6px solid #ffc13b; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'><h3 style='margin:0; font-size:22px; font-weight:900; letter-spacing: 0.5px;'>🚀 TASK FORCE 348 <span style='color: #ffc13b;'>|</span> NOP PALANGKARAYA</h3><p style='margin: 2px 0 0 0; font-size: 12px; opacity: 0.9; font-weight: 500;'>TELECOMMUNICATION & NETWORK OPERATION DASHBOARD</p></div>""", unsafe_allow_html=True)
    with col_head_select:
        label_pilihan = st.selectbox("🎯 Target Monitoring:", sorted(df_merged['dropdown_label'].unique()), label_visibility="collapsed")

    data_site = df_merged[df_merged['dropdown_label'] == label_pilihan].iloc[0]
    st.markdown(f"<p style='text-align: right; margin: -10px 5px 8px 0; font-size: 13px;'><b>Last Data:</b> {data_site.get('Timestamp', '-')}</p>", unsafe_allow_html=True)

    # --- ROW 2: MAIN GRID (4 COLUMNS) ---
    c1, c2, c3, c4 = st.columns([1, 1.2, 1.2, 1])

    with c1:
        st.markdown("<div class='ppt-card-blue'><b style='font-size:14px;'>📋 Site Master Specification</b></div>", unsafe_allow_html=True)
        master_list = {
            "Parameter": ["Site ID", "Site Name", "Class", "Grid", "Hub", "Phase", "Grounding KWH"],
            "Value": [
                data_site.get('site_id', '-'), data_site.get('site_name', '-'),
                data_site.get('site_class', '-'), data_site.get('grid_category_new', '-'),
                data_site.get('hub_site', '-'), data_site.get('Phase PLN', '-'),
                data_site.get('Grounding KWH', '-')
            ]
        }
        st.dataframe(pd.DataFrame(master_list), hide_index=True, use_container_width=True, height=350)

    with c2:
        st.markdown("<div class='ppt-card-blue'><b style='font-size:14px;'>⚙️ Site Technical Detailed Specs</b></div>", unsafe_allow_html=True)
        tech_mapping = [
            ("Main Power", "Main Power", "Main Power"), ("Daya PLN", "Daya PLN", "Daya PLN"), ("Kapasitas MCB", "Kapasitas MCB", "Kapasitas MCB"),
            ("Tegangan R - N", "Tegangan PLN (R-N)", "Tegangan PLN (R-N)"), ("Tegangan S - N", "Tegangan PLN (S-N)", "Tegangan PLN (S-N)"), ("Tegangan T - N", "Tegangan PLN (T-N)", "Tegangan PLN (T-N)"),
            ("Arus R", "Beban PLN (R)", "Beban PLN (R)"), ("Arus S", "Beban PLN (S)", "Beban PLN (S)"), ("Arus T", "Beban PLN (T)", "Beban PLN (T)"),
            ("Type recti 1", "Type Rectifier", "Type Rectifier"), ("Jumlah Module 1", "Jumlah Module", "Jumlah Module"), ("Type batt 1", "Type Battery", "Type Battery"),
            ("Jumlah batt 1", "Jumlah Battery", "Jumlah Battery"), ("DC Voltage 1", "DC Voltage", "DC Voltage"), ("Load Current 1", "Rectifier Current", "Rectifier Current"),
            ("Type recti 2", "Type Rectifier 2", "Type Rectifier 2"), ("Jumlah Module 2", "Jumlah Module 2", "Jumlah Module 2"), ("Type batt 2", "Type Battery 2", "Type Battery 2"),
            ("Jumlah batt 2", "Jumlah Battery 2", "Jumlah Battery 2"), ("Load current recti 2", "Load current recti 2", "Load current recti 2")
        ]
        tech_rows = [{"Detail Parameter": l, "Value": dapatkan_nilai_teknis(data_site, cs, csb)} for l, cs, csb in tech_mapping]
        st.dataframe(pd.DataFrame(tech_rows), hide_index=True, use_container_width=True, height=350)

    # KOLOM 3: FINDINGS & GRAPH (FIX TANGGAL EXCEL 1969 & WEEKLY AGGREGATION)
    with c3:
        st.markdown("<div class='ppt-card-gold'><b style='font-size:14px;'>🔍 Field Findings</b></div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='findings-grid'><div class='f-item'><b>Arus Recty:</b> <span>{data_site.get('Rectifier Current', '-')} A</span></div><div class='f-item'><b>Modul:</b> <span>{data_site.get('Jumlah Module', '-')} <span style='color:#ff5252;'>(F: {data_site.get('Total Module faulty', '-')})</span></span></div><div class='f-item'><b>BBT:</b> <span>{data_site.get('BBT >4 Jam', '-')}</span></div><div class='f-item'><b>Enva Val:</b> <span>{data_site.get('Enva Validasi', '-')}</span></div><div class='f-item'><b>LPU Enva:</b> <span>{data_site.get('Kondisi Modul Enva LPU', '-')}</span></div><div class='f-item'><b>Arrester:</b> <span>{data_site.get('Arrester Rectifier', '-')}</span></div></div>""", unsafe_allow_html=True)
        
        st.markdown("<b style='font-size:11px; color:#aaa;'>📈 Weekly Availability Trend</b>", unsafe_allow_html=True)
        
        t_id_asli = str(data_site.get('site_id', '')).strip()
        t_id_clean = str(data_site.get('site_clean_sheet', '')).strip()
        
        # Eksekusi pencarian Supabase Multi-Varian
        df_trend = fetch_inap_for_site(t_id_clean, t_id_asli)
            
        if not df_trend.empty:
            col_date = next((c for c in df_trend.columns if any(k in str(c).lower() for k in ['date', 'waktu', 'periode', 'tgl', 'tanggal', 'time', 'timestamp'])), None)
            if not col_date and len(df_trend.columns) > 0: col_date = df_trend.columns[0]
            
            # Deteksi Kolom Availability (Cuma ambil 1 line)
            col_avail = None
            for c in df_trend.columns:
                c_lower = str(c).lower()
                if 'avail' in c_lower and 'power' not in c_lower and 'pwr' not in c_lower and 'trans' not in c_lower:
                    col_avail = c
                    break
            
            if not col_avail:
                col_avail = next((c for c in df_trend.columns if 'avail' in str(c).lower()), None)
            if not col_avail and len(df_trend.columns) > 1:
                col_avail = df_trend.columns[1] if df_trend.columns[1] != col_date else df_trend.columns[0]

            if col_date and col_avail:
                chart_data = df_trend[[col_date, col_avail]].copy()
                
                # --- FUNGSI PEMBERSIH TANGGAL (MEMBLOKIR TAHUN 1969/1970) ---
                def bersihkan_tanggal(val):
                    v_str = str(val).strip()
                    # Deteksi kalau datanya cuma berisi angka Excel (misal: 45000)
                    if v_str.replace('.', '', 1).isdigit():
                        try: return pd.to_datetime(float(v_str), unit='D', origin='1899-12-30')
                        except: return pd.NaT
                    return pd.to_datetime(v_str, errors='coerce', dayfirst=True)
                
                chart_data[col_date] = chart_data[col_date].apply(bersihkan_tanggal)
                chart_data = chart_data.dropna(subset=[col_date])
                
                # Filter ekstrem: Buang tanggal yang tahunnya masih di bawah 2000 (Menghapus bug tahun 1969 Epoch)
                chart_data = chart_data[chart_data[col_date].dt.year > 2000]
                
                # --- PEMBERSIH ANGKA KETERSEDIAAN ---
                chart_data[col_avail] = chart_data[col_avail].astype(str).str.replace('%', '').str.replace(',', '.')
                chart_data[col_avail] = pd.to_numeric(chart_data[col_avail], errors='coerce')
                chart_data = chart_data.dropna(subset=[col_avail])
                
                if not chart_data.empty:
                    # Rata-rata Mingguan (Hitung dari Senin)
                    chart_data['Week'] = chart_data[col_date].dt.to_period('W').apply(lambda r: r.start_time)
                    weekly_chart = chart_data.groupby('Week')[col_avail].mean().reset_index()
                    
                    # Ubah format sumbu X jadi "14 Jun 2026"
                    weekly_chart['Week'] = weekly_chart['Week'].dt.strftime('%d %b %Y')
                    weekly_chart.set_index('Week', inplace=True)
                    weekly_chart.columns = ['Availability (%)']
                    
                    st.line_chart(weekly_chart, height=155)
                else:
                    st.caption("ℹ️ Data angka ketersediaan atau tanggal pada site ini kosong/tidak valid.")
            else:
                st.caption(f"ℹ️ Format kolom tanggal atau availability tidak ditemukan.")
                
            with st.expander("🛠️ Cek Nama Kolom Asli inap_data"):
                st.write("Kolom database:", df_trend.columns.tolist())
                st.write("Data mentah:", df_trend.head(2))
        else: 
            st.caption(f"ℹ️ Belum ada data mingguan untuk {t_id_clean} di tabel inap_data.")

    # KOLOM 4: RECOMMENDATION
    with c4:
        st.markdown("<div class='ppt-card-gold'><b style='font-size:14px;'>📝 Action Plan</b></div>", unsafe_allow_html=True)
        reko_val = data_site.get('Rekomendasi Perbaikan', '')
        if pd.isna(reko_val): reko_val = ""
        rekomendasi_input = st.text_area("Rekomendasi Perbaikan:", value=str(reko_val), placeholder="Input rekomendasi...", key="input_rekomendasi", height=230, label_visibility="collapsed")
        
        @st.dialog("Konfirmasi")
        def popup_konfirmasi(teks):
            st.write(f"Simpan rekomendasi untuk site **{data_site[kolom_site_sheet]}**?")
            st.info(f"📝 {teks}")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("👍 Ya", use_container_width=True):
                    with st.spinner("Saving..."):
                        s, p = update_rekomendasi_gsheet(data_site[kolom_site_sheet], teks)
                        if s: 
                            st.success("Tersimpan!"); st.cache_data.clear(); st.rerun()
                        else: st.error(f"Gagal: {p}")
            with b2:
                if st.button("❌ Tidak", use_container_width=True): st.rerun()

        if st.button("💾 Push Update", use_container_width=True):
            if rekomendasi_input.strip() == "": st.warning("Isi data!")
            else: popup_konfirmasi(rekomendasi_input)

    # --- ROW 3: EVIDENCE SECURE & CAPTION POPUP ---
    st.markdown("<div style='margin-top:10px; font-size:14px;'><b>📁 Evidence & Dokumentasi Slide</b></div>", unsafe_allow_html=True)
    all_photos, all_csvs, seen_urls = [], [], set()
    
    for col_name in df_sheet.columns:
        val = data_site.get(col_name)
        if pd.isna(val) or not val: continue
        urls = re.findall(r'(https?://[^\s,"\'\}]+)', str(val))
        for idx, url in enumerate(urls):
            if url in seen_urls: continue
            seen_urls.add(url)
            
            is_csv = "csv" in col_name.lower() or ".csv" in url.lower() or "data" in col_name.lower() or ".xlsx" in url.lower()
            is_video = "voltage" in col_name.lower() or "backup" in col_name.lower() or ".mp4" in url.lower() or ".mov" in url.lower()
            
            thumb_url, zoom_url, dl_url, embed_url = konversi_link_gdrive(url)
            label = f"{clean_label_name(col_name)} #{idx+1}" if len(urls) > 1 else clean_label_name(col_name)
            
            if thumb_url and not is_csv:
                all_photos.append({'label': label, 'col': col_name, 'idx': idx, 'thumb': thumb_url, 'zoom': zoom_url, 'is_vid': is_video, 'embed': embed_url})
            elif is_csv: 
                all_csvs.append({'label': label, 'url': dl_url if dl_url else url})

    b_csv, b_gal = st.columns([0.8, 2.2])
    with b_csv:
        if all_csvs:
            for f in all_csvs: st.link_button(f"📥 {f['label']}", f['url'], use_container_width=True)
        else: st.caption("No CSV/Excel Files uploaded.")
        
    with b_gal:
        html_str = ""
        total = len(all_photos)
        for i, p in enumerate(all_photos):
            sid = re.sub(r'[^a-zA-Z0-9]', '', f"{p['col']}{p['idx']}")
            sid_p = re.sub(r'[^a-zA-Z0-9]', '', f"{all_photos[(i-1)%total]['col']}{all_photos[(i-1)%total]['idx']}")
            sid_n = re.sub(r'[^a-zA-Z0-9]', '', f"{all_photos[(i+1)%total]['col']}{all_photos[(i+1)%total]['idx']}")
            nav = f'<a href="#lightbox-{sid_p}" class="nav-arrow prev-arrow">❮</a><a href="#lightbox-{sid_n}" class="nav-arrow next-arrow">❯</a>'
            
            content = f'<iframe src="{p["embed"]}" width="80%" height="80%" style="border:none; background:#000; border-radius:8px;" allow="autoplay"></iframe>' if p['is_vid'] else f'<img src="{p["zoom"]}">'
            ovr = '<div class="video-overlay-btn">▶</div>' if p['is_vid'] else ''
            
            html_str += f'<input type="checkbox" id="hide-{sid}" class="hide-checkbox"><div class="photo-card"><label for="hide-{sid}" class="exclude-btn" title="Hide">&times;</label><a href="#lightbox-{sid}"><div style="position:relative;"><img src="{p["thumb"]}" style="width:100px; height:75px; object-fit:cover; border:1px solid #555; border-radius:4px;"/><div class="video-overlay-btn">{ovr}</div></div></a><div style="font-size:10px; margin-top:4px; color:#ccc; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{p["label"]}</div></div><div id="lightbox-{sid}" class="lightbox"><a href="#" class="close-lightbox">&times;</a>{nav}{content}<div class="caption-text">{p["label"]}</div></div>'
            
        if html_str: st.markdown(f'<div class="gallery-container">{html_str}</div>', unsafe_allow_html=True)
        else: st.caption("No unique documentation photos found.")

    st.markdown("<div class='custom-footer'>© 2026 | Created with ❤️ by Fauzi Ramdani - 97122</div>", unsafe_allow_html=True)
