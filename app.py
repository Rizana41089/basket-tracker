import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIG ---------------------------------------------------------
st.set_page_config(page_title="Basket Payment", layout="centered")
DATA_FILE = "/tmp/basket_data.csv"
PROOF_DIR = "/tmp"

# --- FUNCTIONS ------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Date", "Field_Name", "Player_Name", "Status", "Timestamp"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def get_proof_filename(player_name, date):
    safe_name = "".join([c for c in player_name if c.isalnum()])
    return f"{PROOF_DIR}/proof_{safe_name}_{date}.png"

# --- MODAL POP-UP (DIALOG) ------------------------------------------
@st.dialog("📤 Upload Bukti Transfer")
def show_upload_modal(player_list, match_date):
    st.write(f"Match: {match_date}")
    
    who = st.selectbox("Siapa yang mau upload?", player_list)
    uploaded_file = st.file_uploader("Pilih Screenshot Bukti", type=['jpg','png','jpeg'])
    
    if uploaded_file:
        if st.button("Kirim & Kunci Data", type="primary"):
            file_path = get_proof_filename(who, match_date)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Update Status di CSV jadi 'Transfer' (Locking logic)
            df = load_data()
            mask = (df['Date'] == match_date) & (df['Player_Name'] == who)
            df.loc[mask, 'Status'] = "💳 Transfer"
            df.loc[mask, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d")
            save_data(df)

            st.success("✅ Berhasil! Status kamu sekarang TERKUNCI.")
            time.sleep(1.5)
            st.rerun()

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
is_player_mode = query_params.get("view") == "player"
df = load_data()

# --- 1. ADMIN SIDEBAR -----------------------------------------------
if not is_player_mode:
    with st.sidebar:
        st.header("⚙️ Admin Dashboard")
        
        # --- TAB MENU ADMIN ---
        # Biar rapi, kita bagi jadi 2 tab di sidebar
        adm_tab1, adm_tab2 = st.tabs(["📝 Buat Baru", "📂 History & Edit"])
        
        # TAB 1: BUAT MATCH BARU
        with adm_tab1:
            st.write("**Buat Match Baru**")
            with st.form("new_match"):
                date_in = st.date_input("Tanggal")
                field_in = st.text_input("Lapangan", "GOR Basket")
                names_in = st.text_area("Paste Nama", height=100)
                if st.form_submit_button("🚀 Buat"):
                    if names_in:
                        lines = names_in.split('\n')
                        clean_names = [''.join([i for i in l if not i.isdigit() and i != '.']).strip() for l in lines if l.strip()]
                        if clean_names:
                            # Cek duplikat tanggal (Opsional, tapi biar aman)
                            # Disini kita allow multiple match same date beda lapangan, 
                            # tapi untuk simplifikasi kita anggap tanggal = unik ID match.
                            
                            new_df = pd.DataFrame({
                                "Date": [str(date_in)] * len(clean_names),
                                "Field_Name": [field_in] * len(clean_names),
                                "Player_Name": clean_names,
                                "Status": ["❌ Belum"] * len(clean_names),
                                "Timestamp": [datetime.now().strftime("%Y-%m-%d")] * len(clean_names)
                            })
                            combined = pd.concat([load_data(), new_df], ignore_index=True)
                            save_data(combined)
                            st.success("Match Created!")
                            time.sleep(1)
                            st.rerun()

        # TAB 2: HISTORY & MANAGEMENT
        with adm_tab2:
            if df.empty:
                st.info("Belum ada data match.")
            else:
                # Ambil list tanggal unik
                all_dates = sorted(df['Date'].unique(), reverse=True)
                selected_history = st.selectbox("Pilih Match utk dikelola:", all_dates)
                
                # Filter data
                hist_data = df[df['Date'] == selected_history]
                field_hist = hist_data['Field_Name'].iloc[0]
                total_p = len(hist_data)
                paid_count = len(hist_data[hist_data['Status'] != "❌ Belum"])
                
                st.info(f"📍 {field_hist}\n\n✅ Lunas: {paid_count}/{total_p} Pemain")
                
                # Fitur DELETE MATCH
                st.write("")
                if st.button(f"🗑️ Hapus Match {selected_history}", type="secondary"):
                    # Logic Delete
                    new_df_after_delete = df[df['Date'] != selected_history]
                    save_data(new_df_after_delete)
                    st.error(f"Match {selected_history} dihapus!")
                    time.sleep(1)
                    st.rerun()

        st.divider()
        # --- GALERI BUKTI (GLOBAL) ---
        with st.expander("📸 Cek Galeri Bukti", expanded=False):
            if df.empty:
                st.write("Data kosong.")
            else:
                # Cek file fisik untuk tanggal yg dipilih di History (kalau ada), atau latest
                check_date = st.selectbox("Cek Galeri Tanggal:", sorted(df['Date'].unique(), reverse=True))
                
                players = df[df['Date'] == check_date
