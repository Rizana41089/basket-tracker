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
target_date_param = query_params.get("date")

is_player_mode = (view_mode == "player")
df = load_data()

# --- 1. ADMIN SIDEBAR -----------------------------------------------
if not is_player_mode:
    with st.sidebar:
        st.header("⚙️ Admin Dashboard")
        adm_tab1, adm_tab2 = st.tabs(["📝 Buat Baru", "📂 Manage/Foto"])
        
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
                st.markdown("👇 **Link Khusus Tanggal Ini:**")
                link_text = f"?view=player&date={selected_history}"
                st.code(link_text, language="text")

                st.divider()
                if os.path.exists(match_folder) and len(os.listdir(match_folder)) > 0:
                    shutil.make_archive(match_folder, 'zip', match_folder)
                    with open(match_folder + ".zip", "rb") as fp:
                        st.download_button("📦 Download ZIP Bukti", fp, f"Bukti_{selected_history}.zip", "application/zip")
                
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
                
                st.divider()
                st.warning("⚠️ Zona Bahaya")
                if st.button(f"🗑️ Hapus Match {selected_history}", type="secondary"):
                    new_df = df[df['Date'] != selected_history]
                    save_data(new_df)
                    if os.path.exists(match_folder):
                        shutil.rmtree(match_folder)
                    st.error("Match Terhapus!")
                    time.sleep(1)
                    st.rerun()

# --- 2. PLAYER VIEW -------------------------------------------------

if df.empty:
    st.info("👋 Belum ada match aktif.")
else:
    available_dates = sorted(df['Date'].unique(), reverse=True)
    if target_date_param and target_date_param in available_dates:
        selected_date = target_date_param
    else:
        col_sel, _ = st.columns([2,1])
        with col_sel:
            selected_date = st.selectbox("📅 Pilih Jadwal Main:", available_dates)

    current_match = df[df['Date'] == selected_date].copy()
    field_name = current_match['Field_Name'].iloc[0]
    current_folder = get_match_folder(selected_date, field_name)

    # Locking Logic (FIXED)
    current_match['is_locked'] = False 
    for index, row in current_match.iterrows():
        fname = get_proof_filename(current_folder, row['Player_Name'])
        if os.path.exists(fname):
            current_match.at[index, 'is_locked'] = True
            current_match.at[index, 'Status'] = "💳 Transfer"

    st.subheader(f"🏀 {field_name}")
    st.divider()

    # --- TABEL EDITOR ---
    st.caption("👇 Klik 2x pada kolom Status untuk mengubah:")
    
    # PERBAIKAN: Gunakan key yang stabil
    edited_df = st.data_editor(
        current_match[["Player_Name", "Status", "is_locked"]],
        column_config={
            "Player_Name": st.column_config.TextColumn("Nama Pemain", disabled=True),
            "Status": st.column_config.SelectboxColumn(
                "Status Bayar 🔽", 
                options=["❌ Belum", "💵 Cash", "💳 Transfer"], 
                required=True,
                disabled="is_locked" # Kolom status mati jika is_locked = True
            ),
            "is_locked": None # Sembunyikan kolom bantuan
        },
        hide_index=True, 
        use_container_width=True, 
        key=f"editor_main" 
    )

    # --- LOGIC TOMBOL UPLOAD ---
    # Muncul jika ada yang status Transfer tapi BELUM di-lock (belum upload)
    upload_candidates = edited_df[
        (edited_df["Status"] == "💳 Transfer") & 
        (edited_df["is_locked"] == False)
    ]["Player_Name"].unique()

    if len(upload_candidates) > 0:
        st.info("💡 Kamu memilih Transfer. Harap upload bukti di bawah.")
        if st.button("📤 Upload Bukti Sekarang", type="primary"):
            show_upload_modal(upload_candidates, selected_date, field_name)

    # --- TOMBOL SAVE ---
    st.write("")
    if st.button("💾 Simpan Perubahan Status"):
        df_others = df[df['Date'] != selected_date]
        save_batch = edited_df.drop(columns=['is_locked']).copy()
        save_batch['Date'] = selected_date
        save_batch['Field_Name'] = field_name
        save_batch['Timestamp'] = datetime.now().strftime("%Y-%m-%d")
        final_df = pd.concat([df_others, save_batch], ignore_index=True)
        save_data(final_df)
        st.toast("Data Berhasil Disimpan!", icon="✅")
        time.sleep(0.5)
        st.rerun()

    # --- LIST LUNAS ---
    done_players = current_match[current_match['is_locked'] == True]['Player_Name'].tolist()
    if done_players:
        st.divider()
        st.caption(f"✅ Lunas & Terkunci: {', '.join(done_players)}")
