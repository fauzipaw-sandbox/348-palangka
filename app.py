import streamlit as st
import pandas as pd
import requests
import re
import difflib

# 1. SETUP PAGE
st.set_page_config(layout="wide", page_title="Task Force 348 Dashboard")

# --- KREDENSIAL & DATA SOURCE MASTER ---
GOOGLE_SHEET_ID = "1FGKOzWoUrbf3PXN_ahgG1t-83JZT4H4sioQepePbBxM"

# ⚠️ GANTI PAKAI URL APPS SCRIPT LO
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxCQUGt5_Jybed2AwFP4xXFru6GxuMoSwQpUZ63aK9o0WlUFnumOoseRWwgRmxZZ9XYtQ/exec"

# ⚠️ GANTI PAKAI KREDENSIAL SUPABASE LO
SUPABASE_URL = "https://sfyfijndolnwqklqnpmj.supabase.co"
SUPABASE_KEY = "sb_publishable_digs5GILs-TEe4lEpPj4qQ_VRrQ7FCm"
SUPABASE_TABLE_DAPOT = "dapot_data"
SUPABASE_TABLE_INAP = "inap_data"

# --- FUNGSI STANDARISASI SITE ID (SUPER STRICT) ---
def format_site_id(site_id):
    if pd.isna(site_id) or str(site_id).strip() == "": return "-"
    # Hapus spasi, strip, underscore, dan ubah ke uppercase
    s = str(site_id).strip().upper()
    s = re.sub(r'[^A-Z0-9]', '', s)
    # Ambil 6 digit pertama jika polanya 3 huruf 3 angka (misal KKP326)
    match = re.search(r'[A-Z]{3}\d{3}', s)
    if match: return match.group(0)
    return s

def clean_label_name(name):
    if "Log Rectifier" in name: return "Log Recty"
    return re.sub(r'\s*\(.*?\)\s*', '', str(name)).strip()

def cari_site_terdekat(site_id, list_site):
    if site_id == "-": return None
    cocok = difflib.get_close_matches(site_id, list_site, n=1, cutoff=0.6)
    return cocok[0] if cocok else None

def konversi_link_gdrive(url_tunggal):
    if not url_tunggal or str(url_tunggal).strip() == "": return None, None, None, None
    link = str(url_tunggal).strip()
    fid = None
    if "id=" in link: fid = re.search(r'id=([a-zA-Z0-9_-]+)', link).group(1) if re.search(r'id=([a-zA-Z0-9_-]+)', link) else None
    elif "file/d/" in link: fid = re.search(r'/file/d/([a-zA-Z0-9_-]+)', link).group(1) if re.search(r'/file/d/([a-zA-Z0-9_-]+)', link) else None
    if fid:
        return f"https://drive.google.com/thumbnail?id={fid}&sz=w400", f"https://drive.google.com/thumbnail?id={fid}&sz=w1600", f"https://drive.google.com/uc?export=download&id={fid}", f"https://drive.google.com/file/d/{fid}/preview"
    return link, link, link, None

# --- FUNGSI PUSH DATA ---
def update_rekomendasi_gsheet(site_id, teks):
    if "GANTI_PAKE" in APPS_SCRIPT_URL: return False, "URL Apps Script Kosong"
    try:
        response = requests.post(APPS_SCRIPT_URL, json={"site_id": site_id, "rekomendasi": teks}, timeout=10)
        return (True, "Sukses") if "Sukses" in response.text else (False, response.text)
    except Exception as e: return False, str(e)

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_gsheet():
    try: return pd.read_csv(f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv")
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_supabase(table):
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?select=*", headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
        return pd.DataFrame(resp.json()) if resp.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

df_sheet = load_gsheet()
df_dapot = load_supabase(SUPABASE_TABLE_DAPOT)
df_inap = load_supabase(SUPABASE_TABLE_INAP)

if df_sheet.empty or df_dapot.empty:
    st.error("Gagal memuat data utama. Pastikan link GSheet & API Key Supabase sudah benar.")
else:
    # Matching Logic
    kolom_site_s = 'Site' if 'Site' in df_sheet.columns else df_sheet.columns[0]
    df_sheet['site_clean'] = df_sheet[kolom_site_s].apply(format_site_id)
    df_dapot['site_clean'] = df_dapot['site_id'].apply(format_site_id)
    
    list_sup = df_dapot['site_clean'].unique().tolist()
    mapping = {s: (s if s in list_sup else cari_site_terdekat(s, list_sup)) for s in df_sheet['site_clean'].unique()}
    df_sheet['matched_id'] = df_sheet['site_clean'].map(mapping)
    df_merged = pd.merge(df_sheet, df_dapot, left_on='matched_id', right_on='site_clean', how='left', suffixes=('', '_dapot'))

    # UI HEADER
    st.markdown("""<style>
    .block-container { padding-top: 3.5rem !important; }
    .card-blue { background: #1E3D59; padding: 10px; border-radius: 8px; border-left: 5px solid #FFC13B; margin-bottom: 10px; }
    .card-gold { background: #FFC13B; color: #1E3D59; padding: 10px; border-radius: 8px; border-left: 5px solid #1E3D59; margin-bottom: 10px; }
    .lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 9999999; justify-content: center; align-items: center; flex-direction: column; }
    .lightbox:target { display: flex; }
    .lightbox img, .lightbox iframe { max-width: 80%; max-height: 70%; border-radius: 10px; }
    .lightbox .caption { color: #FFC13B; font-size: 20px; font-weight: 700; margin-top: 20px; font-family: 'DM Sans'; }
    .nav-arrow { position: absolute; top: 50%; color: #FFF; font-size: 60px; text-decoration: none; padding: 20px; z-index: 10000000; }
    .prev-arrow { left: 30px; } .next-arrow { right: 30px; }
    .close-lightbox { position: absolute; top: 70px; right: 40px; color: #FFF; font-size: 50px; text-decoration: none; }
    .gallery-container { display: flex; gap: 10px; overflow-x: auto; padding: 10px; background: #111; border-radius: 10px; }
    .photo-card { min-width: 110px; height: 80px; position: relative; cursor: pointer; border-radius: 5px; border: 1px solid #444; }
    .video-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(232,30,40,0.8); border-radius: 50%; width: 25px; height: 25px; text-align: center; color: #FFF; font-size: 12px; line-height: 25px; }
    </style>""", unsafe_allow_html=True)

    c_h1, c_h2 = st.columns([2, 1])
    with c_h1:
        st.markdown("<div style='background: linear-gradient(135deg, #E81E28 0%, #B71C1C 60%, #1A1A1A 100%); padding: 15px; border-radius: 8px; border-left: 6px solid #FFC13B;'><h2 style='margin:0; color:#FFF;'>🚀 TASKFORCE 348 | NOP Palangkaraya</h2></div>", unsafe_allow_html=True)
    with c_h2:
        sel_label = st.selectbox("Target Site:", sorted(df_merged.apply(lambda r: f"[{r['matched_id'] if pd.notna(r['matched_id']) else r['site_clean']}] ➔ {r.get('site_name','UNK')}", axis=1).unique()))
    
    data_site = df_merged[df_merged.apply(lambda r: f"[{r['matched_id'] if pd.notna(r['matched_id']) else r['site_clean']}] ➔ {r.get('site_name','UNK')}", axis=1) == sel_label].iloc[0]

    # MAIN CONTENT (4 COLUMNS)
    c1, c2, c3, c4 = st.columns([1, 1.2, 1.2, 1])

    with c1:
        st.markdown("<div class='card-blue'><b>📋 Site Master</b></div>", unsafe_allow_html=True)
        m_list = {"Param": ["ID", "Name", "Class", "Grid", "Hub", "Phase"], "Val": [data_site.get('site_id','-'), data_site.get('site_name','-'), data_site.get('site_class','-'), data_site.get('grid_category_new','-'), data_site.get('hub_site','-'), data_site.get('Phase PLN','-')]}
        st.table(pd.DataFrame(m_list).set_index('Param'))

    with c2:
        st.markdown("<div class='card-blue'><b>⚙️ Technical Detail</b></div>", unsafe_allow_html=True)
        t_map = [("Main Power","Main Power"), ("Daya PLN","Daya PLN"), ("MCB Cap","Kapasitas MCB"), ("V R-N","Tegangan PLN (R-N)"), ("V S-N","Tegangan PLN (S-N)"), ("V T-N","Tegangan PLN (T-N)"), ("A R","Beban PLN (R)"), ("A S","Beban PLN (S)"), ("A T","Beban PLN (T)"), ("Recti 1","Type Rectifier"), ("Mod 1","Jumlah Module"), ("Batt 1","Type Battery"), ("Qty B1","Jumlah Battery"), ("DC V1","DC Voltage"), ("Load 1","Rectifier Current"), ("Recti 2","Type Rectifier 2"), ("Mod 2","Jumlah Module 2"), ("Batt 2","Type Battery 2"), ("Qty B2","Jumlah Battery 2"), ("Load 2","Load current recti 2")]
        st.dataframe(pd.DataFrame({"Parameter": [x[0] for x in t_map], "Value": [data_site.get(x[1], '-') for x in t_map]}), hide_index=True, use_container_width=True, height=300)

    with c3:
        st.markdown("<div class='card-gold'><b>🔍 Findings & Trends</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='background:#262730; padding:10px; border-radius:5px; font-size:12px;'><b>Arus:</b> {data_site.get('Rectifier Current','-')} A | <b>Modul:</b> {data_site.get('Jumlah Module','-')} (F:{data_site.get('Total Module faulty','0')})<br><b>BBT:</b> {data_site.get('BBT >4 Jam','-')} | <b>Arrester:</b> {data_site.get('Arrester Rectifier','-')}</div>", unsafe_allow_html=True)
        
        # TREND LOGIC
        if not df_inap.empty:
            df_inap['sc'] = df_inap['site_id'].astype(str).apply(format_site_id)
            d_trend = df_inap[df_inap['sc'] == data_site['site_clean']]
            if not d_trend.empty:
                cw = [c for c in d_trend.columns if any(x in c.lower() for x in ['week','minggu','date'])][0]
                cp = [c for c in d_trend.columns if any(x in c.lower() for x in ['power','pwr'])][0]
                ct = [c for c in d_trend.columns if any(x in c.lower() for x in ['transport','trans'])][0]
                chart_data = d_trend[[cw, cp, ct]].copy()
                chart_data.columns = ['Week', 'Power (%)', 'Transport (%)']
                st.line_chart(chart_data.sort_values('Week').set_index('Week'), height=150)
            else: st.caption("ℹ️ Trend site ini tidak ditemukan.")

    with c4:
        st.markdown("<div class='card-gold'><b>📝 Action Plan</b></div>", unsafe_allow_html=True)
        cur_reko = data_site.get('Rekomendasi Perbaikan', '')
        in_reko = st.text_area("Reko:", value=str(cur_reko) if pd.notna(cur_reko) else "", height=150, label_visibility="collapsed")
        
        @st.dialog("Konfirmasi")
        def pop(t):
            st.write(f"Simpan untuk **{data_site[kolom_site_s]}**?")
            st.info(f"📝 {t}")
            b1, b2 = st.columns(2)
            if b1.button("Ya"):
                with st.spinner("Saving..."):
                    ok, msg = update_rekomendasi_gsheet(data_site[kolom_site_s], t)
                    if ok: st.success("OK!"); st.cache_data.clear(); st.rerun()
                    else: st.error(msg)
            if b2.button("Tidak"): st.rerun()

        if st.button("💾 Save to GSheet", use_container_width=True):
            if in_reko.strip(): pop(in_reko)
            else: st.warning("Kosong!")

    # EVIDENCE SECTION
    st.markdown("<div style='margin-top:10px;'><b>📁 Evidence</b></div>", unsafe_allow_html=True)
    all_ev, all_csv = [], []
    v_col = [c for c in df_sheet.columns if "voltage" in c.lower() and "backup" in c.lower()]
    
    for c in df_sheet.columns:
        val = data_site.get(c)
        if pd.notna(val) and "http" in str(val):
            urls = re.findall(r'(https?://[^\s,"\'\}]+)', str(val))
            for i, u in enumerate(urls):
                thumb, zoom, dl, embed = konversi_link_gdrive(u)
                is_vid = (v_col and c == v_col[0]) or ".mp4" in u.lower() or ".mov" in u.lower()
                lbl = f"{clean_label_name(c)} #{i+1}" if len(urls)>1 else clean_label_name(c)
                if thumb and (".csv" not in u.lower() and ".xlsx" not in u.lower()):
                    all_ev.append({'lbl': lbl, 'col': c, 'idx': i, 'thumb': thumb, 'zoom': zoom, 'is_vid': is_vid, 'embed': embed})
                else: all_csv.append({'lbl': lbl, 'url': dl if dl else u})

    bc, bg = st.columns([0.8, 2.2])
    with bc:
        for f in all_csv: st.link_button(f"📥 {f['lbl']}", f['url'], use_container_width=True)
    with bg:
        h_str = ""
        tot = len(all_ev)
        for i, p in enumerate(all_ev):
            sid = re.sub(r'[^a-z0-9]', '', f"{p['col']}{p['idx']}")
            prev = re.sub(r'[^a-z0-9]', '', f"{all_ev[(i-1)%tot]['col']}{all_ev[(i-1)%tot]['idx']}")
            nxt = re.sub(r'[^a-z0-9]', '', f"{all_ev[(i+1)%tot]['col']}{all_ev[(i+1)%tot]['idx']}")
            nav = f'<a href="#lightbox-{prev}" class="nav-arrow prev-arrow">❮</a><a href="#lightbox-{nxt}" class="nav-arrow next-arrow">❯</a>'
            cnt = f'<iframe src="{p["embed"]}" width="80%" height="70%" allow="autoplay"></iframe>' if p['is_vid'] else f'<img src="{p["zoom"]}">'
            h_str += f'<div class="photo-card" style="background-image:url(\'{p["thumb"]}\');" onclick="location.href=\'#lightbox-{sid}\'">{"<div class=\"video-overlay\">▶</div>" if p["is_vid"] else ""}</div><div id="lightbox-{sid}" class="lightbox"><a href="#" class="close-lightbox">&times;</a>{nav}{cnt}<div class="caption">{p["lbl"]}</div></div>'
        st.markdown(f'<div class="gallery-container">{h_str}</div>', unsafe_allow_html=True)

    st.markdown("<div class='custom-footer'>© 2026 | Created with ❤️ by Fauzi Ramdani - 97122</div>", unsafe_allow_html=True)
