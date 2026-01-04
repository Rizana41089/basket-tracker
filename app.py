import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import time
import shutil  # <-- TAMBAHAN PENTING: Untuk hapus folder
from datetime import datetime

# --- CONFIG ---
NAMA_APLIKASI = "BIB Checklist Payment"
st.set_page_config(page_title=NAMA_APLIKASI, layout="centered")

# --- DEFINISI FOLDER PENYIMPANAN (Supaya tidak error 'not defined') ---
base_tmp_dir = "proof_images"
if not os.path.exists(base_tmp_dir):
    os.makedirs(base_tmp_dir)

# URL Google Sheet kamu (Pastikan URL ini benar dan Sheet-nya tidak dikunci)
SQL_URL = "https://docs.google.com/spreadsheets/d/1hd4yQ0-OfK7SbOMqdgWycb7kB2oNjzOPvfr8vveS-fM/edit?usp=sharing"

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Mengambil data dari Google Sheets (ttl=0 biar tidak cache lama)
        return conn.read(spreadsheet=SQL_URL, worksheet="Sheet1", ttl=0)
    except Exception as e:
        st.error(f"Gagal load data: {e}")
        return pd.DataFrame(columns=["Date", "Field_Name", "Player_Name", "Status", "Timestamp"])

def save_data(df):
    try:
        # Mengupdate data ke Google Sheets
        conn.update(spreadsheet=SQL_URL, worksheet="Sheet1", data=df)
        st.cache_data.clear() # Clear cache internal streamlit
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data! Pastikan Service Account sudah jadi EDITOR di Google Sheet.\nError: {e}")
        return False

# --- FILE & FOTO FUNCTIONS ------------------------------------------
def get_match_folder(date_str, field_name):
    # Membersihkan string agar aman jadi nama folder
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
        
        # Cek apakah data kosong
        if df_all.empty:
            st.error("Data tidak ditemukan atau gagal dimuat.")
            return

        # Update Logic
        mask = (df_all['Date'].astype(str) == str(match_date)) & (df_all['Player_Name'] == who)
        
        if not df_all[mask].empty:
            df_all.loc[mask, 'Status'] = method
            df_all.loc[mask, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Save Image jika Transfer
            if method == "💳 Transfer" and uploaded_file:
                folder = get_match_folder(match_date, field_name)
                file_path = get_proof_filename(folder, who)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            
            # Save Data ke Sheets
            if save_data(df_all):
                st.success(f"Berhasil! Terima kasih {who}.")
                time.sleep(1)
                st.rerun()
        else:
            st.error("Data pemain tidak ditemukan di tanggal tersebut.")

# --- MODAL KONFIRMASI HAPUS (ADMIN) ---------------------------------
@st.dialog("⚠️ Konfirmasi Hapus")
def confirm_delete_modal(match_date, field_name):
    st.warning(f"Apakah Anda yakin ingin menghapus jadwal **{match_date}**?")
    if st.button("Ya, Hapus Permanen", type="primary", use_container_width=True):
        df_all = load_data()
        # Filter data selain tanggal yang dipilih
        new_df = df_all[df_all['Date'].astype(str) != str(match_date)]
        
        if save_data(new_df):
            m_folder = get_match_folder(match_date, field_name)
            if os.path.exists(m_folder):
                shutil.rmtree(m_folder) # Hapus folder foto
            st.success("Jadwal dihapus!")
            time.sleep(1)
            st.rerun()
            
    if st.button("Batal", use_container_width=True):
        st.rerun()

# --- MODAL PREVIEW BUKTI --------------------------------------------
@st.dialog("🔍 Detail Bukti")
def show_image_preview(image_path, player_name):
    if os.path.exists(image_path):
        st.image(image_path, use_container_width=True, caption=f"Bukti Transfer: {player_name}")
    else:
        st.error("File gambar tidak ditemukan (mungkin terhapus server).")

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
                n_in = st.text_area("List Nama (Paste WA)", help="Format: 1. Nama\n2. Nama")
                
                if st.form_submit_button("🚀 Generate Match"):
                    if n_in:
                        # Parsing nama lebih robust
                        lines = n_in.split('\n')
                        names = []
                        for l in lines:
                            # Hapus angka di depan, titik, dan spasi
                            clean_name = ''.join([i for i in l if not i.isdigit() and i != '.']).strip()
                            if clean_name:
                                names.append(clean_name)
                        
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
                                st.success(f"Berhasil membuat jadwal untuk {len(names)} pemain!")
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.warning("Tidak ada nama yang terdeteksi.")
        
        with t_b:
            if not df.empty and 'Date' in df.columns:
                unique_dates = df['Date'].unique()
                # Pastikan tanggal diurutkan
                all_d = sorted(unique_dates, reverse=True)
                
                sel_h = st.selectbox("Pilih Jadwal:", all_d)
                
                # Tampilkan Link untuk dicopy
                # (Di local: localhost, di Cloud: alamat app kamu)
                st.caption("Copy link ini untuk pemain:")
                st.code(f"?view=player&date={sel_h}")
                st.divider()
                
                # Filter data berdasarkan tanggal terpilih
                h_data = df[df['Date'] == sel_h]
                
                if not h_data.empty:
                    f_h_name = h_data['Field_Name'].iloc[0]
                    m_folder = get_match_folder(sel_h, f_h_name)
                    p_transfer = h_data[h_data['Status'] == "💳 Transfer"]['Player_Name'].tolist()
                    
                    if p_transfer:
                        st.write(f"📸 Bukti Transfer ({len(p_transfer)})")
                        cols = st.columns(3)
                        for idx, p in enumerate(p_transfer):
                            f_p = get_proof_filename(m_folder, p)
                            with cols[idx % 3]:
                                if os.path.exists(f_p):
                                    st.image(f_p, caption=p)
                                    if st.button(f"🔍 Zoom {p}", key=f"adm_{p}"):
                                        show_image_preview(f_p, p)
                                else:
                                    st.warning(f"Foto {p} hilang")
                    else:
                        st.info("Belum ada yang upload bukti transfer.")
                
                st.divider()
                if st.button(f"🗑️ Hapus Jadwal {sel_h}", type="secondary", use_container_width=True):
                    confirm_delete_modal(sel_h, f_h_name)
            else:
                st.info("Belum ada data jadwal.")

# --- 2. PLAYER VIEW ---
# Tampilan jika user membuka link khusus
else: 
    if df.empty:
        st.info("👋 Belum ada match aktif.")
    else:
        # Konversi kolom Date ke string untuk pencocokan yang aman
        df['Date'] = df['Date'].astype(str)
        available_dates = sorted(df['Date'].unique(), reverse=True)
        
        # Cek apakah parameter tanggal valid
        if target_date_param in available_dates:
            selected_date = target_date_param
        else:
            selected_date = st.selectbox("📅 Pilih Tanggal Main:", available_dates)
        
        curr = df[df['Date'] == selected_date].copy()
        
        if not curr.empty:
            f_name = curr['Field_Name'].iloc[0]
            folder = get_match_folder(selected_date, f_name)

            st.title(f"🏀 {NAMA_APLIKASI}")
            st.info(f"📍 {f_name} | 📅 {selected_date}")

            # Detect Lunas Logic
            curr['Lunas'] = False
            for i, r in curr.iterrows():
                # Lunas jika upload bukti (ada file) ATAU status Cash/Transfer
                has_proof = os.path.exists(get_proof_filename(folder, r['Player_Name']))
                is_paid_status = r['Status'] in ["💵 Cash", "💳 Transfer"]
                
                if has_proof or is_paid_status:
                    curr.at[i, 'Lunas'] = True

            # Tombol Aksi
            yet_to_pay = curr[curr['Lunas'] == False]['Player_Name'].tolist()
            if yet_to_pay:
                if st.button("💳 LAPOR BAYAR / UPLOAD BUKTI", type="primary", use_container_width=True):
                    show_update_modal(yet_to_pay, selected_date, f_name)
            else:
                st.success("🎉 Wih mantap! Semua pemain sudah lunas!")

            # Tampilkan Tabel Status
            display_df = curr[["Player_Name", "Status"]].reset_index(drop=True)
            
            # Styling sederhana (Highlight status)
            st.dataframe(
                display_df.style.apply(lambda x: ['background-color: #d4edda' if v in ['💵 Cash', '💳 Transfer'] else '' for v in x], subset=['Status']),
                hide_index=True, 
                use_container_width=True
            )
        else:
            st.warning("Data match tanggal ini error.")
