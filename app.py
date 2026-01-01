import streamlit as st
import pandas as pd
import os
import time
import shutil
from datetime import datetime

# --- CONFIG ---------------------------------------------------------
st.set_page_config(page_title="Basket Payment", layout="centered")
base_tmp_dir = "/tmp/basket_app_files"
DATA_FILE = f"{base_tmp_dir}/basket_data.csv"

# Pastikan folder dasar ada
if not os.path.exists(base_tmp_dir):
    os.makedirs(base_tmp_dir)

# --- FUNCTIONS ------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Date", "Field_Name", "Player_Name", "Status", "Timestamp"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def get_match_folder(date_str, field_name):
    # Buat nama folder aman: "2023-10-01_GOR_Basket"
    safe_date = str(date_str).replace("/", "-")
    safe_field = "".join([c for c in field_name if c.isalnum() or c == " "]).replace(" ", "_")
    folder_path = f"{base_tmp_dir}/{safe_date}_{safe_field}"
    
    # Bikin foldernya kalau belum ada
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def get_proof_filename(folder_path, player_name):
    safe_name = "".join([c for c in player_name if c.isalnum()])
    return f"{folder_path}/{safe_name}.png"

# --- MODAL POP-UP (DIALOG) ------------------------------------------

# 1. Dialog Upload (Player)
@st.dialog("📤 Upload Bukti Transfer")
def show_upload_modal(player_list, match_date, field_name):
    st.write(f"Match: {match_date} @ {field_name}")
    
    who = st.selectbox("Siapa yang mau upload?", player_list)
    uploaded_file = st.file_uploader("Pilih Screenshot", type=['jpg','png','jpeg'])
    
    if uploaded_file:
        if st.button("Kirim & Kunci Data", type="primary"):
            # Tentukan folder
            folder = get_match_folder(match_date, field_name)
            file_path = get_proof_filename(folder, who)
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Update CSV
            df = load_data()
            mask = (df['Date'] == match_date) & (df['Player_Name'] == who)
            df.loc[mask, 'Status'] = "💳 Transfer"
            df.loc[mask, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d")
            save_data(df)

            st.success("✅ Terkirim! Status dikunci.")
            time.sleep(1.5)
            st.rerun()

# 2. Dialog Preview Gambar (Admin)
@st.dialog("🔍 Detail Bukti Transfer")
def show_image_preview(image_path, player_name):
    st.header(player_name)
    st.image(image_path, use_container_width=True)

# --- STYLE CSS ------------------------------------------------------
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 5rem;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div.stButton > button:first-child { width: 100%; }
    /* Style card kecil buat gambar */
    .img-card {border: 1px solid #ddd; padding: 5px; border-radius: 5px; margin-bottom: 10px;}
    </style>
    """, unsafe_allow_html=True)

# --- MAIN LOGIC -----------------------------------------------------

query_params = st.query_params
is_player_mode = query_params.get("view") == "player"
df = load_data()

# --- 1. ADMIN SIDEBAR -----------------------------------------------
if not is_player_mode:
    with st.sidebar:
        st.header("⚙️ Admin Dashboard")
        
        adm_tab1, adm_tab2 = st.tabs(["📝 Buat Baru", "📂 History/Foto"])
        
        # TAB 1: BUAT MATCH
        with adm_tab1:
            with st.form("new_match"):
                st.write("**Buat Match Baru**")
                date_in = st.date_input("Tanggal")
                field_in = st.text_input("Lapangan", "GOR Basket")
                names_in = st.text_area("Paste Nama", height=100)
                if st.form_submit_button("🚀 Buat"):
                    if names_in:
                        lines = names_in.split('\n')
                        clean_names = [''.join([i for i in l if not i.isdigit() and i != '.']).strip() for l in lines if l.strip()]
                        if clean_names:
                            new_df = pd.DataFrame({
                                "Date": [str(date_in)] * len(clean_names),
                                "Field_Name": [field_in] * len(clean_names),
                                "Player_Name": clean_names,
                                "Status": ["❌ Belum"] * len(clean_names),
                                "Timestamp": [datetime.now().strftime("%Y-%m-%d")] * len(clean_names)
                            })
                            combined = pd.concat([load_data(), new_df], ignore_index=True)
                            save_data(combined)
                            # Bikin folder kosong buat persiapan
                            get_match_folder(str(date_in), field_in)
                            st.success("Match Created!")
                            time.sleep(1)
                            st.rerun()

        # TAB 2: HISTORY & GALERI GRID
        with adm_tab2:
            if df.empty:
                st.info("Data kosong.")
            else:
                all_dates = sorted(df['Date'].unique(), reverse=True)
                selected_history = st.selectbox("Pilih Match:", all_dates)
                
                # Get info
                hist_data = df[df['Date'] == selected_history]
                field_hist = hist_data['Field_Name'].iloc[0]
                
                # Folder Path
                match_folder = get_match_folder(selected_history, field_hist)
                
                st.divider()
                st.write(f"📂 **{selected_history} - {field_hist}**")
                
                # --- FITUR DOWNLOAD ZIP ---
                # Cek apakah ada file di folder
                if os.path.exists(match_folder) and len(os.listdir(match_folder)) > 0:
                    shutil.make_archive(match_folder, 'zip', match_folder) # Create ZIP
                    zip_path = match_folder + ".zip"
                    
                    with open(zip_path, "rb") as fp:
                        btn = st.download_button(
                            label="📦 Download Semua Bukti (.ZIP)",
                            data=fp,
                            file_name=f"Bukti_{selected_history}_{field_hist}.zip",
                            mime="application/zip",
                            type="primary"
                        )
                else:
                    st.caption("Belum ada file upload.")

                st.divider()
                st.write("📸 **Galeri Bukti (Grid)**")
                
                # Grid Layout Logic
                # Ambil list pemain yg statusnya transfer
                transfer_p = hist_data[hist_data['Status'] == "💳 Transfer"]['Player_Name'].tolist()
                
                if not transfer_p:
                    st.info("Belum ada yang transfer.")
                else:
                    # Bikin Grid 3 Kolom
                    cols = st.columns(3)
                    found_any = False
                    
                    for idx, p_name in enumerate(transfer_p):
                        fname = get_proof_filename(match_folder, p_name)
                        
                        if os.path.exists(fname):
                            found_any = True
                            # Tentukan kolom (0, 1, atau 2)
                            with cols[idx % 3]:
                                # Tampilkan Thumbnail Kecil
                                st.image(fname, use_container_width=True)
                                st.caption(f"**{p_name}**")
                                # Tombol View Modal
                                if st.button("🔍 Cek", key=f"btn_{p_name}_{selected_history}"):
                                    show_image_preview(fname, p_name)
                        
                    if not found_any:
                        st.caption("Status transfer, tapi file belum ada.")

                # DELETE BUTTON
                st.divider()
                with st.expander("🗑️ Hapus Data Match Ini"):
                    if st.button("Hapus Permanen", type="secondary"):
                        new_df = df[df['Date'] != selected_history]
                        save_data(new_df)
                        # Hapus foldernya juga kalau ada
                        if os.path.exists(match_folder):
                            shutil.rmtree(match_folder)
                        st.error("Terhapus.")
                        time.sleep(1)
                        st.rerun()

        st.divider()
        st.subheader("🔗 Link Grup")
        st.code("?view=player", language="text")

# --- 2. PLAYER VIEW (MAIN) ------------------------------------------

if df.empty:
    st.info("👋 Belum ada match aktif.")
else:
    available_dates = sorted(df['Date'].unique(), reverse=True)
    col_sel, col_empty = st.columns([2,1])
    with col_sel:
        selected_date = st.selectbox("📅 Pilih Jadwal Main:", available_dates)

    current_match = df[df['Date'] == selected_date].copy()
    field_name = current_match['Field_Name'].iloc[0]
    
    # Ambil folder path untuk match ini
    current_folder = get_match_folder(selected_date, field_name)

    #
