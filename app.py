import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import time
import shutil
from datetime import datetime

# --- CONFIG ---------------------------------------------------------
PAGE_TITLE = "BIB Checklist Payment"
st.set_page_config(page_title=PAGE_TITLE, layout="centered")

base_tmp_dir = "/tmp/basket_app_files"
if not os.path.exists(base_tmp_dir):
    os.makedirs(base_tmp_dir)

# --- GOOGLE SHEETS CONFIG (FIX HTTP 302 ERROR) ----------------------
SHEET_ID = "1hd4yQ0-OfK7SbOMqdgWycb7kB2oNjzOPvfr8vveS-fM"
CSV_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# --- LOAD DATA FROM GOOGLE SHEETS -----------------------------------
@st.cache_data(ttl=300)
def load_data():
    """Load data dari Google Sheets menggunakan CSV export URL"""
    try:
        response = requests.get(CSV_EXPORT_URL, timeout=10)
        response.raise_for_status()
        return pd.read_csv(StringIO(response.text))
    except Exception as e:
        st.error(f"Gagal membaca Google Sheets: {e}")
        st.info("💡 Pastikan:\n1. Google Sheet sudah di-share (public)\n2. SHEET_ID benar\n3. Internet connection stabil")
        return pd.DataFrame(columns=["Date", "Field_Name", "Player_Name", "Status", "Timestamp"])

def save_data(df):
    """Simpan data ke CSV lokal (temporary solution)"""
    try:
        csv_path = f"{base_tmp_dir}/data.csv"
        df.to_csv(csv_path, index=False)
        st.success("✅ Data disimpan ke storage lokal")
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ Gagal menyimpan: {e}")
        return False

# --- FILE & FOTO FUNCTIONS ------------------------------------------
def get_match_folder(date_str, field_name):
    safe_date = str(date_str).replace("/", "-")
    safe_field = "".join([c for c in field_name if c.isalnum() or c == " "]).replace(" ", "_")
    folder_path = f"{base_tmp_dir}/{safe_date}_{safe_field}"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def get_proof_filename(folder_path, player_name):
    safe_name = "".join([c for c in player_name if c.isalnum()])
    return f"{folder_path}/{safe_name}.png"

# --- MODAL UPDATE STATUS (PLAYER) -----------------------------------
@st.dialog("📝 Update Status Bayar")
def show_update_modal(player_list, match_date, field_name):
    st.write(f"Lapor bayar untuk match: **{match_date}**")
    who = st.selectbox("Pilih Namamu:", player_list)
    method = st.radio("Metode Pembayaran:", ["💵 Cash", "💳 Transfer"])
    
    uploaded_file = None
    if method == "💳 Transfer":
        uploaded_file = st.file_uploader("Upload Bukti Transfer", type=['jpg','png','jpeg'])
    
    if st.button("Konfirmasi Pembayaran", type="primary"):
        df_all = load_data()
        mask = (df_all['Date'] == match_date) & (df_all['Player_Name'] == who)
        df_all.loc[mask, 'Status'] = method
        df_all.loc[mask, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d")
        
        if method == "💳 Transfer" and uploaded_file:
            folder = get_match_folder(match_date, field_name)
            file_path = get_proof_filename(folder, who)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        
        if save_data(df_all):
            st.success(f"Berhasil! Terima kasih {who}.")
            time.sleep(1)
            st.rerun()

# --- MODAL KONFIRMASI HAPUS (ADMIN) ---------------------------------
@st.dialog("⚠️ Konfirmasi Hapus")
def confirm_delete_modal(match_date, field_name):
    st.warning(f"Apakah Anda yakin ingin menghapus jadwal **{match_date}**?")
    if st.button("Ya, Hapus Permanen", type="primary", use_container_width=True):
        df_all = load_data()
        new_df = df_all[df_all['Date'] != match_date]
        if save_data(new_df):
            m_folder = get_match_folder(match_date, field_name)
            if os.path.exists(m_folder):
                shutil.rmtree(m_folder)
            st.success("Jadwal dihapus!")
            time.sleep(1)
            st.rerun()
    if st.button("Batal", use_container_width=True):
        st.rerun()

# --- MODAL PREVIEW BUKTI --------------------------------------------
@st.dialog("🔍 Detail Bukti")
def show_image_preview(image_path, player_name):
    st.image(image_path, use_container_width=True, caption=f"Bukti Transfer: {player_name}")

# --- MAIN LOGIC ---
query_params = st.query_params
view_mode = query_params.get("view")
target_date_param = query_params.get("date")
is_player_mode = (view_mode == "player")

df = load_data()

# --- 1. ADMIN SIDEBAR ---
if not is_player_mode:
    with st.sidebar:
        st.header("⚙️ Admin Dashboard")
        if st.button("🔄 Refresh Data App", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()

        t_a, t_b = st.tabs(["➕ Buat Match", "📂 Manage & Bukti"])
        
        with t_a:
            with st.form("new"):
                d_in = st.date_input("Tanggal")
                f_in = st.text_input("Lapangan", "GOR")
                n_in = st.text_area("List Nama (Paste WA)")
                if st.form_submit_button("🚀 Generate Match"):
                    if n_in:
                        lines = n_in.split('\n')
                        names = [''.join([i for i in l if not i.isdigit() and i != '.']).strip() for l in lines if l.strip()]
                        new_rows = pd.DataFrame({
                            "Date": [str(d_in)]*len(names), 
                            "Field_Name": [f_in]*len(names), 
                            "Player_Name": names, 
                            "Status": ["❌ Belum"]*len(names), 
                            "Timestamp": [datetime.now().strftime("%Y-%m-%d")]*len(names)
                        })
                        combined_df = pd.concat([df, new_rows], ignore_index=True)
                        if save_data(combined_df):
                            st.success("Berhasil disimpan ke Cloud!")
                            time.sleep(1)
                            st.rerun()
        
        with t_b:
            if not df.empty:
                all_d = sorted(df['Date'].unique(), reverse=True)
                sel_h = st.selectbox("Pilih Jadwal:", all_d)
                st.code(f"?view=player&date={sel_h}")
                st.divider()
                
                h_data = df[df['Date'] == sel_h]
                f_h_name = h_data['Field_Name'].iloc[0]
                m_folder = get_match_folder(sel_h, f_h_name)
                p_transfer = h_data[h_data['Status'] == "💳 Transfer"]['Player_Name'].tolist()
                
                if p_transfer:
                    cols = st.columns(3)
                    for idx, p in enumerate(p_transfer):
                        f_p = get_proof_filename(m_folder, p)
                        if os.path.exists(f_p):
                            with cols[idx % 3]:
                                st.image(f_p)
                                if st.button("🔍", key=f"adm_{p}"):
                                    show_image_preview(f_p, p)
                
                if st.button(f"🗑️ Hapus Jadwal {sel_h}", type="secondary", use_container_width=True):
                    confirm_delete_modal(sel_h, f_h_name)

# --- 2. PLAYER VIEW ---
if df.empty:
    st.info("👋 Belum ada match aktif.")
else:
    available_dates = sorted(df['Date'].unique(), reverse=True)
    selected_date = target_date_param if (target_date_param in available_dates) else st.selectbox("📅 Jadwal:", available_dates)
    
    curr = df[df['Date'] == selected_date].copy()
    f_name = curr['Field_Name'].iloc[0]
    folder = get_match_folder(selected_date, f_name)

    st.title(f"🏀 {PAGE_TITLE}")
    st.caption(f"📍 Lapangan: {f_name} | 📅 Tanggal: {selected_date}")

    # Detect Lunas
    curr['Lunas'] = False
    for i, r in curr.iterrows():
        if os.path.exists(get_proof_filename(folder, r['Player_Name'])) or r['Status'] == "💵 Cash":
            curr.at[i, 'Lunas'] = True

    yet_to_pay = curr[curr['Lunas'] == False]['Player_Name'].tolist()
    if yet_to_pay:
        if st.button("💳 LAPOR BAYAR / UPLOAD BUKTI", type="primary", use_container_width=True):
            show_update_modal(yet_to_pay, selected_date, f_name)
    else:
        st.success("🎉 Semua pemain lunas!")

    st.dataframe(curr[["Player_Name", "Status"]], hide_index=True, use_container_width=True)
