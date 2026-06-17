import streamlit as st
import pandas as pd
import requests
import re
import difflib  # Library bawaan Python untuk mencocokkan karakter yang mendekati

# Konfigurasi halaman agar fullscreen dan rapi
st.set_page_config(layout="wide", page_title="Task Force Dashboard NOP")

# --- KREDENSIAL MASTER ---
APP_ID = "d3525213-95f5-4dff-9eb3-62842c4964f0"
ACCESS_KEY = "V2-AmIzq-oOhfP-aWkgR-jRkRK-fyAiW-1mj3s-3yfYj-o18dt"
TABLE_NAME = "List"

# ⚠️ ISI KREDENSIAL SUPABASE LO DI SINI, ZI!
SUPABASE_URL = "https://sfyfijndolnwqklqnpmj.supabase.co"
SUPABASE_KEY = "sb_publishable_digs5GILs-TEe4lEpPj4qQ_VRrQ7FCm"
SUPABASE_TABLE = "dapot_data"

# --- Fungsi Standarisasi Format Site ID ---
def format_site_id(site_id):
    if pd.isna(site_id) or str(site_id).strip() == "":
        return "-"
    s = str(site_id).strip().upper().replace(" ", "").replace("-", "").replace("_", "")
    s = re.sub(r'^K+P', 'KKP', s)
    return s

# --- Fungsi Fuzzy Matching Karakter Mendekati ---
def cari_site_terdekat(site_appsheet, list_site_supabase):
    if site_appsheet == "-":
        return None
    # Nyari 1 yang paling mendekati dengan akurasi kemiripan minimal 60% (cutoff=0.6)
    cocok = difflib.get_close_matches(site_appsheet, list_site_supabase, n=1, cutoff=0.6)
    return cocok[0] if cocok else None

# --- Fungsi Ekstraksi ID GDrive & Konversi ke Endpoint Thumbnail ---
def konversi_link_gdrive(url_tunggal):
    if not url_tunggal or str(url_tunggal).strip() == "":
        return None, None
        
    link_bersih = str(url_tunggal).strip()
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
        direct_download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        return thumb_url, zoom_url, direct_download_url
        
    return link_inter := link_bersih, link_inter, link_inter

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

# --- FUNGSI PULL DATA DARI SUPABASE REST API ---
@st.cache_data(ttl=600)
def load_data_from_supabase():
    # Menggunakan REST API bawaan Supabase (PostgREST) via requests agar enteng
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- FUNGSI PUSH/UPDATE DATA KE APPSHEET API ---
def update_rekomendasi_appsheet(site_id_asli, nama_kolom_site, teks_rekomendasi):
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
                nama_kolom_site: site_id_asli,
                "Rekomendasi Koordinator": teks_rekomendasi
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code == 200
    except:
        return False

# Load kedua sumber data asli
df_app = load_data_from_appsheet()
df_sup = load_data_from_supabase()

if df_app.empty:
    st.warning("Data AppSheet kosong atau belum terhubung dengan bener.")
elif df_sup.empty:
    st.warning("Data Supabase dapot_data gagal ditarik. Pastikan URL dan KEY Supabase lo udah bener, Zi.")
else:
    # 1. Deteksi kolom acuan site di AppSheet
    kolom_site_app = 'Site' if 'Site' in df_app.columns else ([c for c in df_app.columns if "site" in c.lower() or "id" in c.lower()] + [df_app.columns[0]])[0]
    
    # 2. Standarisasi karakter id site untuk proses matching
    df_app['site_clean_app'] = df_app[kolom_site_app].apply(format_site_id)
    df_sup['site_clean_sup'] = df_sup['site_id'].apply(format_site_id)
    
    # 3. Proses Fuzzy Matching karakter yang mendekati sama
    list_site_sup = df_sup['site_clean_sup'].dropna().unique().tolist()
    mapping_fuzzy = {}
    for site_a in df_app['site_clean_app'].unique():
        if site_a in list_site_sup:
            mapping_fuzzy[site_a] = site_a # Match exact
        else:
            match_terdekat = cari_site_terdekat(site_a, list_site_sup)
            if match_terdekat:
                mapping_fuzzy[site_a] = match_terdekat
                
    df_app['matched_site_sup'] = df_app['site_clean_app'].map(mapping_fuzzy)
    
    # 4. Merge Dataframe AppSheet dengan Supabase dapot_data
    df_merged = pd.merge(df_app, df_sup, left_on='matched_site_sup', right_on='site_clean_sup', how='left', suffixes=('', '_dapot'))

    # 5. Bikin Format Naming Dropdown: site_id | site_name | site_class | grid_category_new | hub_site
    def susun_nama_dropdown(row):
        s_id = row['matched_site_sup'] if pd.notna(row['matched_site_sup']) else row['site_clean_app']
        s_name = row.get('site_name', 'UNKNOWN NAME')
        s_class = row.get('site_class', '-')
        s_grid = row.get('grid_category_new', '-')
        s_hub = row.get('hub_site', '-')
        return f"{s_id} | {s_name} | {s_class} | {s_grid} | {s_hub}"
        
    df_merged['dropdown_label'] = df_merged.apply(susun_nama_dropdown, axis=1)

    # --- HEADER DASHBOARD MASTER TASK FORCE 348 ---
    st.markdown("<h2 style='text-align: center; color: #d32f2f;'>Task Force 348 | NOP PALANGKARAYA</h2>", unsafe_allow_html=True)
    st.divider()

    # --- DROPDOWN SITE ID DENGAN FORMAT BARU ---
    label_pilihan = st.selectbox("🎯 Pilih Site (Format: ID | Name | Class | Grid | Hub):", sorted(df_merged['dropdown_label'].unique()))

    # Filter data baris berdasarkan label yang dipilih user
    data_site = df_merged[df_merged['dropdown_label'] == label_pilihan].iloc[0]

    st.write(f"<p style='text-align: center;'><b>Last Data:</b> {data_site.get('Timestamp', '-')}</p>", unsafe_allow_html=True)
    st.divider()

    # --- LAYOUTING UTAMA ---
    col_basic, col_finding = st.columns([1, 1.2])

    # ================= KOLOM KIRI: BASIC INFORMATION =================
    with col_basic:
        st.markdown("<h3 style='background-color: #1e3d59; color: white; padding: 8px; border-radius: 5px;'>Basic Information</h3>", unsafe_allow_html=True)
        
        info_dasar = {
            "Parameter": ["Site ID (Dapot)", "Site Name", "Site Class", "Grid Category", "Hub Site", "Phase PLN", "Grounding KWH"],
            "Value": [
                data_site.get('site_id', '-'),
                data_site.get('site_name', '-'),
                data_site.get('site_class', '-'),
                data_site.get('grid_category_new', '-'),
                data_site.get('hub_site', '-'),
                data_site.get('Phase PLN', '-'),
                data_site.get('Grounding KWH', '-')
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
                    # Ambil ID Asli bawaan baris AppSheet untuk dikirim balik sebagai key data
                    site_id_asli_appsheet = data_site[kolom_site_app]
                    sukses = update_rekomendasi_appsheet(site_id_asli_appsheet, kolom_site_app, rekomendasi_input)
                    if sukses:
                        st.success("Rekomendasi berhasil disimpan!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Gagal menyimpan data ke AppSheet.")

        # --- DYNAMIC GALLERY SCANNER & CSV DOWNLOADS ---
        st.markdown("---")
        
        st.markdown("""<style>
        .gallery-container { display: flex; overflow-x: auto; padding: 15px; background-color: #151515; border-radius: 10px; border: 1px solid #333; margin-top: 5px; scroll-behavior: smooth; }
        .photo-card { flex: 0 0 auto; width: 140px; margin-right: 15px; text-align: center; position: relative; }
        .hide-checkbox { display: none; }
        .hide-checkbox:checked + .photo-card { display: none; }
        .exclude-btn { position: absolute; top: 2px; right: 12px; background: rgba(211, 47, 47, 0.9); color: white; border-radius: 50%; width: 18px; height: 18px; font-size: 11px; line-height: 18px; cursor: pointer; font-weight: bold; z-index: 10; box-shadow: 0px 2px 4px rgba(0,0,0,0.5); }
        .exclude-btn:hover { background: #b71c1c; }
        .lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.95); z-index: 99999; justify-content: center; align-items: center; }
        .lightbox:target { display: flex; }
        .lightbox img { max-width: 85%; max-height: 85%; border-radius: 6px; box-shadow: 0px 0px 25px rgba(255,255,255,0.2); }
        .lightbox .close-lightbox { position: absolute; top: 30px; right: 40px; color: #fff; font-size: 45px; text-decoration: none; font-weight: bold; }
        </style>""", unsafe_allow_html=True)
        
        all_detected_photos = []
        all_detected_csvs = []
        seen_urls = set()
        
        for col_name in df_app.columns:
            val = data_site.get(col_name)
            if pd.isna(val) or not val:
                continue
                
            urls = re.findall(r'(https?://[^\s,"\'\}]+)', str(val))
            
            for idx, url in enumerate(urls):
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                is_csv = "csv" in col_name.lower() or ".csv" in url.lower() or "data" in col_name.lower()
                thumb_url, zoom_url, download_url = konversi_link_gdrive(url)
                label = f"{col_name} #{idx+1}" if len(urls) > 1 else col_name
                
                if thumb_url and not is_csv:
                    all_detected_photos.append({
                        'label': label, 'col_name': col_name, 'idx': idx, 'thumb_url': thumb_url, 'zoom_url': zoom_url
                    })
                elif is_csv:
                    all_detected_csvs.append({
                        'label': label, 'download_url': download_url
                    })

        if all_detected_csvs:
            st.markdown("#### 📊 File Data & CSV Uploads")
            for csv_file in all_detected_csvs:
                st.link_button(f"📥 Download {csv_file['label']}", csv_file['download_url'], use_container_width=True)
            st.markdown("---")

        st.markdown("**📸 Foto Dokumentasi Lapangan (Horizontal Scroll & Click to Pop-up)**")
        html_items = []
        for p in all_detected_photos:
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', f"{p['col_name']}{p['idx']}")
            
            item_html = f"""<input type="checkbox" id="hide-{safe_id}" class="hide-checkbox">
<div class="photo-card">
<label for="hide-{safe_id}" class="exclude-btn" title="Sembunyikan Foto">&times;</label>
<a href="#lightbox-{safe_id}" title="Klik untuk Pop-up Zoom">
<img src="{p['thumb_url']}" style="width: 130px; height: 130px; object-fit: cover; border-radius: 8px; box-shadow: 0px 4px 8px rgba(0,0,0,0.4); border: 2px solid #444; cursor: pointer;"/>
</a>
<div style="font-size: 11px; margin-top: 6px; color: #e0e0e0; white-space: normal; line-height: 1.2;">{p['label']}</div>
</div>
<div id="lightbox-{safe_id}" class="lightbox">
<a href="#" class="close-lightbox">&times;</a>
<img src="{p['zoom_url']}">
</div>"""
            html_items.append(item_html)
                    
        if html_items:
            semua_item = "".join(html_items)
            gallery_html = f"""<div class="gallery-container">
{semua_item}
</div>"""
            st.markdown(gallery_html, unsafe_allow_html=True)
            st.caption("💡 *Tips: Scroll ke kanan untuk melihat semua foto unik. Klik tombol bulat 'X' merah di atas foto untuk menyembunyikan sementara. Klik gambar untuk Pop-up Zoom.*")
        else:
            st.info("Tidak ada dokumentasi foto unik yang ditemukan untuk site ini.")
