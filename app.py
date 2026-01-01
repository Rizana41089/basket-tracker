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
    safe_date = str(date_str).replace("/", "-")
    safe_field = "".join([c for c in field_name if c.isalnum() or c == " "]).replace(" ", "_")
    folder_path = f"{base_tmp_dir}/{safe_date}_{safe_field}"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def get_proof_filename(folder_path, player_name):
    safe_name = "".join([c for c in player_name if c.isalnum()])
    return f"{folder_path}/{safe_name}.png"

# --- MODAL POP-UP ---------------------------------------------------
@st.dialog("📤 Upload Bukti Transfer")
def show_upload_modal(player_list, match_date, field_name):
    st.write(f"Match: {match_date} @ {field_name}")
    who = st.selectbox("Siapa yang mau upload?", player_list)
    uploaded_file = st.file_uploader("Pilih Screenshot", type=['jpg','png','jpeg'])
    
    if uploaded_file:
        if st.button("Kirim & Kunci Data", type="primary"):
            folder = get_match_folder(match_date, field_name)
            file_path = get_proof_filename(folder, who)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            df = load_data()
            mask = (df['Date'] == match_date) & (df['Player_Name'] == who)
            df.loc[mask, 'Status'] = "💳 Transfer"
            df.loc[mask, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d")
            save_data(df)

            st.success("✅ Terkirim!")
            time.sleep(1.5)
            st.rerun()

@st.dialog("🔍 Detail Bukti")
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
    </style>
    """, unsafe_allow_html=True)

# --- MAIN LOGIC -----------------------------------------------------

query_params = st.query_params
view_mode = query_params.get("view")
target_date_param = query_params.get("date") # Ambil parameter tanggal dr link

is_player_mode = (view_mode == "player")
df = load_data()

# --- 1. ADMIN SIDEBAR -----------------------------------------------
if not is_player_mode:
    with st.sidebar:
        st.header("⚙️ Admin Dashboard")
        
        adm_tab1, adm_tab2 = st.tabs(["📝 Buat Baru", "📂 Manage/Foto"])
        
        # TAB 1: CREATE
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
                            get_match_folder(str(date_in), field_in)
                            st.success("Match Created!")
                            time.sleep(1)
                            st.rerun()

        # TAB 2: HISTORY & DELETE
        with adm_tab2:
            if df.empty:
                st.info("Data kosong.")
            else:
                all_dates = sorted(df['Date'].unique(), reverse=True)
                selected_history = st.selectbox("Pilih Match:", all_dates)
                
                hist_data = df[df['Date'] == selected_history]
                field_hist = hist_data['Field_Name'].iloc[0]
                match_folder = get_match_folder(selected_history, field_hist)
                
                st.divider()
                st.write(f"📂 **{selected_history}**")
                
                # --- GENERATE LINK SPESIFIK ---
                st.markdown("👇 **Link Khusus Tanggal Ini:**")
                # Kita bikin link manual
                link_text = f"?view=player&date={selected_history}"
                st.code(link_text, language="text")
                st.caption("Copy kode di atas ke belakang URL aplikasimu.")

                st.divider()
                # --- DOWNLOAD ZIP ---
                if os.path.exists(match_folder) and len(os.listdir(match_folder)) > 0:
                    shutil.make_archive(match_folder, 'zip', match_folder)
                    with open(match_folder + ".zip", "rb") as fp:
                        st.download_button(
                            "📦 Download ZIP Bukti", fp, 
                            f"Bukti_{selected_history}.zip", "application/zip", type="primary"
                        )
                
                # --- GALERI GRID ---
                st.write("📸 **Galeri Foto**")
                transfer_p = hist_data[hist_data['Status'] == "💳 Transfer"]['Player_Name'].tolist()
                if transfer_p:
                    cols = st.columns(3)
                    for idx, p_name in enumerate(transfer_p):
                        fname = get_proof_filename(match_folder, p_name)
                        if os.path.exists(fname):
                            with cols[idx % 3]:
                                st.image(fname, use_container_width=True)
                                if st.button("🔍", key=f"btn_{p_name}_{selected_history}"):
                                    show_image_preview(fname, p_name)
                else:
                    st.caption("Belum ada foto.")

                # --- DELETE BUTTON (YANG KAMU CARI) ---
                st.divider()
                st.warning("⚠️ Zona Bahaya")
                if st.button(f"🗑️ Hapus Match {selected_history}", type="secondary", use_container_width=True):
                    # Logic Hapus
                    new_df = df[df['Date'] != selected_history]
                    save_data(new_df)
                    if os.path.exists(match_folder):
                        shutil.rmtree(match_folder) # Hapus folder foto
                    st.error("Match Terhapus!")
                    time.sleep(1)
                    st.rerun()

# --- 2. PLAYER VIEW -------------------------------------------------

if df.empty:
    st.info("👋 Belum ada match aktif.")
else:
    available_dates = sorted(df['Date'].unique(), reverse=True)
    
    # --- LOGIC TANGGAL SPESIFIK ---
    # Jika ada parameter date di URL (misal &date=2023-10-25)
    if target_date_param and target_date_param in available_dates:
        # Paksa pilih tanggal itu & SEMBUNYIKAN DROPDOWN
        selected_date = target_date_param
        # Tampilkan info kecil bahwa ini view khusus
        st.toast(f"🔒 Menampilkan jadwal khusus: {selected_date}", icon="🔒")
    else:
        # Kalau gak ada parameter tanggal, tampilkan Dropdown biasa
        col_sel, _ = st.columns([2,1])
        with col_sel:
            selected_date = st.selectbox("📅 Pilih Jadwal Main:", available_dates)

    # Load Data Match Terpilih
    current_match = df[df['Date'] == selected_date].copy()
    field_name = current_match['Field_Name'].iloc[0]
    current_folder = get_match_folder(selected_date, field_name)

    # Locking Logic
    current_match['locked'] = False 
    for index, row in current_match.iterrows():
        fname = get_proof_filename(current_folder, row['Player_Name'])
        if os.path.exists(fname):
            current_match.at[index, 'locked'] = True
            current_match.at[index, 'Status'] = "💳 Transfer"

    st.subheader(f"🏀 {field_name}")
    if not target_date_param: # Tampilkan tanggal cuma kalau bukan view khusus (opsional, biar gak dobel)
        st.caption(f"📅 {selected_date}")
        
    st.divider()

    # Table Editor
    st.caption("👇 Update statusmu:")
    edited_df = st.data_editor(
        current_match[["Player_Name", "Status", "locked"]],
        column_config={
            "Player_Name": st.column_config.TextColumn("Nama", disabled=True),
            "Status": st.column_config.SelectboxColumn(
                "Status (Pilih 🔽)", options=["❌ Belum", "💵 Cash", "💳 Transfer"], required=True, disabled="locked"
            ),
            "locked": None
        },
        hide_index=True, use_container_width=True, key=f"editor_{selected_date}"
    )

    # Upload Button
    candidates = edited_df[(edited_df["Status"] == "💳 Transfer") & (edited_df["locked"] == False)]
    upload_candidates = candidates["Player_Name"].unique()

    if len(upload_candidates) > 0:
        st.info("💡 Klik tombol di bawah untuk upload bukti.")
        if st.button("📤 Upload Bukti Sekarang", type="primary"):
            show_upload_modal(upload_candidates, selected_date, field_name)

    # Save Button
    st.write("")
    if st.button("💾 Simpan Perubahan"):
        df_others = df[df['Date'] != selected_date]
        save_batch = edited_df.drop(columns=['locked'])
        save_batch['Date'] = selected_date
        save_batch['Field_Name'] = field_name
        save_batch['Timestamp'] = datetime.now().strftime("%Y-%m-%d")
        final_df = pd.concat([df_others, save_batch], ignore_index=True)
        save_data(final_df)
        st.toast("Tersimpan!", icon="✅")
        time.sleep(0.5)
        st.rerun()

    # Lunas Info
    done_players = current_match[current_match['locked'] == True]['Player_Name'].tolist()
    if done_players:
        st.divider()
        st.caption(f"✅ Lunas: {', '.join(done_players)}")
