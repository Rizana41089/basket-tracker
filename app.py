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

base_tmp_dir = "proof_images"
if not os.path.exists(base_tmp_dir):
    os.makedirs(base_tmp_dir)

# --- PENTING: URL GOOGLE SHEET (WAJIB ADA UNTUK SAVE_DATA) ---
SQL_URL = "https://docs.google.com/spreadsheets/d/1hd4yQ0-OfK7SbOMqdgWycb7kB2oNjzOPvfr8vveS-fM/edit?usp=sharing"

# --- KONEKSI GOOGLE SHEETS ------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Mengambil data terbaru (ttl=0 biar gak cache)
        return conn.read(spreadsheet=SQL_URL, worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame(columns=["Date", "Field_Name", "Player_Name", "Status", "Timestamp"])

def save_data(df):
    try:
        # PERBAIKAN: Menyimpan data spesifik ke Sheet1
        conn.update(spreadsheet=SQL_URL, worksheet="Sheet1", data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Gagal simpan: {e}")
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
        # Pastikan format tanggal string biar cocok
        df_all['Date'] = df_all['Date'].astype(str)
        
        mask = (df_all['Date'] == str(match_date)) & (df_all['Player_Name'] == who)
        
        if not df_all[mask].empty:
            df_all.loc[mask, 'Status'] = method
            df_all.loc[mask, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if method == "💳 Transfer" and uploaded_file:
                folder = get_match_folder(match_date, field_name)
                file_path = get_proof_filename(folder, who)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            
            if save_data(df_all):
                st.success(f"Berhasil! Terima kasih {who}.")
                time.sleep(1)
                st.rerun()
        else:
            st.error("Data pemain tidak ditemukan.")

# --- MODAL KONFIRMASI HAPUS (ADMIN) ---------------------------------
@st.dialog("⚠️ Konfirmasi Hapus")
def confirm_delete_modal(match_date, field_name):
    st.warning(f"Apakah Anda yakin ingin menghapus jadwal **{match_date}**?")
    st.write("Data di Google Sheets dan file bukti transfer akan dihapus permanen.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Hapus", type="primary", use_container_width=True):
            df_all = load_data()
            new_df = df_all[df_all['Date'].astype(str) != str(match_date)]
            
            if save_data(new_df):
                m_folder = get_match_folder(match_date, field_name)
                if os.path.exists(m_folder):
                    shutil.rmtree(m_folder)
                
                st.success("Jadwal dihapus!")
                time.sleep(1)
                st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

# --- MODAL PREVIEW BUKTI --------------------------------------------
@st.dialog("🔍 Detail Bukti")
def show_image_preview(image_path, player_name):
    st.image(image_path, use_container_width=True, caption=f"Bukti Transfer: {player_name}")

# --- STYLE CSS ------------------------------------------------------
st.markdown("""
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 5rem;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- MAIN LOGIC -----------------------------------------------------
query_params = st.query_params
view_mode = query_params.get("view")
target_date_param = query_params.get("date")
is_player_mode = (view_mode == "player")

df = load_data()

# --- 1. ADMIN SIDEBAR (KHUSUS ADMIN) --------------------------------
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
                n_in = st.text_area("List Nama (Paste WA)", help="Satu nama per baris")
                if st.form_submit_button("🚀 Generate Match"):
                    if n_in:
                        lines = n_in.split('\n')
                        names = [''.join([i for i in l if not i.isdigit() and i != '.']).strip() for l in lines if l.strip()]
                        
                        if names:
                            new_rows = pd.DataFrame({
                                "Date": [str(d_in)]*len(names), 
                                "Field_Name": [f_in]*len(names), 
                                "Player_Name": names, 
                                "Status": ["❌ Belum"]*len(names), 
                                "Timestamp": [datetime.now().strftime("%Y-%m-%d")]*len(names)
                            })
                            
                            if df.empty:
                                combined_df = new_rows
                            else:
                                combined_df = pd.concat([df, new_rows], ignore_index=True)
                            
                            if save_data(combined_df):
                                st.success("Berhasil dibuat di Google Sheets!")
                                time.sleep(1)
                                st.rerun()
        
        with t_b:
            if not df.empty and 'Date' in df.columns:
                df['Date'] = df['Date'].astype(str)
                all_d = sorted(df['Date'].unique(), reverse=True)
                sel_h = st.selectbox("Pilih Jadwal:", all_d)
                
                st.caption("🔗 Link untuk dibagikan ke grup:")
                st.code(f"?view=player&date={sel_h}")
                
                st.divider()
                
                # --- BAGIAN INI SAYA PERBAIKI AGAR TABEL MUNCUL ---
                h_data = df[df['Date'] == sel_h]
                st.write(f"📊 **Status Pemain ({len(h_data)} orang)**")
                
                # Highlight Status
                def highlight_status(val):
                    return 'background-color: #d4edda' if val in ["💵 Cash", "💳 Transfer"] else ''

                st.dataframe(
                    h_data[['Player_Name', 'Status', 'Timestamp']].style.applymap(highlight_status, subset=['Status']),
                    use_container_width=True, # Biar tabel lebar penuh (tidak ditengah kecil)
                    hide_index=True
                )
                # --------------------------------------------------
                
                st.divider()
                
                # Galeri Foto Admin
                st.write("📸 **Galeri Bukti Transfer**")
                
                if not h_data.empty:
                    f_h_name = h_data['Field_Name'].iloc[0]
                    m_folder = get_match_folder(sel_h, f_h_name)
                    
                    p_transfer = h_data[h_data['Status'] == "💳 Transfer"]['Player_Name'].tolist()
                    
                    if p_transfer:
                        # Tombol Download Zip
                        if os.path.exists(m_folder) and len(os.listdir(m_folder)) > 0:
                            shutil.make_archive(m_folder, 'zip', m_folder)
                            with open(m_folder + ".zip", "rb") as fp:
                                st.download_button("📦 Download Semua Bukti (ZIP)", fp, f"Bukti_{sel_h}.zip", "application/zip")
                        
                        cols = st.columns(3)
                        for idx, p in enumerate(p_transfer):
                            f_p = get_proof_filename(m_folder, p)
                            if os.path.exists(f_p):
                                with cols[idx % 3]:
                                    st.image(f_p, use_container_width=True)
                                    if st.button("🔍", key=f"adm_{p}"):
                                        show_image_preview(f_p, p)
                    else:
                        st.info("Belum ada yang upload bukti transfer.")

                st.divider()
                st.warning("⚠️ Zona Bahaya")
                if st.button(f"🗑️ Hapus Jadwal {sel_h}", type="secondary", use_container_width=True):
                    confirm_delete_modal(sel_h, f_h_name)
            else:
                st.info("Belum ada data.")

# --- 2. PLAYER VIEW (TAMPILAN DEPAN) --------------------------------
else:
    if df.empty:
        st.info("👋 Belum ada match aktif.")
    else:
        df['Date'] = df['Date'].astype(str)
        available_dates = sorted(df['Date'].unique(), reverse=True)
        
        if target_date_param and target_date_param in available_dates:
            selected_date = target_date_param
        else:
            col_s, _ = st.columns([3,1])
            with col_s:
                selected_date = st.selectbox("📅 Jadwal Main:", available_dates)
        
        curr = df[df['Date'] == selected_date].copy()
        
        if not curr.empty:
            f_name = curr['Field_Name'].iloc[0]
            folder = get_match_folder(selected_date, f_name)

            # Header
            st.title(f"🏀 {PAGE_TITLE}")
            st.caption(f"📍 Lapangan: {f_name} | 📅 Tanggal: {selected_date}")

            # Locking Detection
            curr['Lunas'] = False
            for i, r in curr.iterrows():
                if os.path.exists(get_proof_filename(folder, r['Player_Name'])) or r['Status'] == "💵 Cash":
                    curr.at[i, 'Lunas'] = True

            # Tombol Lapor
            yet_to_pay = curr[curr['Lunas'] == False]['Player_Name'].tolist()
            if yet_to_pay:
                if st.button("💳 LAPOR BAYAR / UPLOAD BUKTI", type="primary", use_container_width=True):
                    show_update_modal(yet_to_pay, selected_date, f_name)
            else:
                st.success("🎉 Semua pemain di jadwal ini sudah lunas!")

            st.divider()

            # Tabel Status
            st.write("📋 **Status Pembayaran:**")
            
            # Styling Tabel Player
            def highlight_row(row):
                return ['background-color: #d4edda']*len(row) if row['Status'] in ["💵 Cash", "💳 Transfer"] else ['']*len(row)

            st.dataframe(
                curr[["Player_Name", "Status"]].style.apply(highlight_row, axis=1),
                column_config={"Player_Name": "Nama Pemain", "Status": "Status"},
                hide_index=True,
                use_container_width=True # KUNCI SUPAYA TABEL FULL WIDTH
            )
            
            # Footer Info
            done = curr[curr['Lunas'] == True]['Player_Name'].tolist()
            if done:
                st.caption(f"✅ Terverifikasi: {len(done)} orang")
