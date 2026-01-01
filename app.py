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
# Ini fungsi khusus buat bikin jendela melayang
@st.dialog("📤 Upload Bukti Transfer")
def show_upload_modal(player_list, match_date):
    st.write(f"Match: {match_date}")
    
    # Pilih nama (hanya yg statusnya transfer yg muncul disini nanti)
    who = st.selectbox("Siapa yang sudah transfer?", player_list)
    
    uploaded_file = st.file_uploader("Pilih Screenshot Bukti", type=['jpg','png','jpeg'])
    
    if uploaded_file:
        if st.button("Kirim Bukti", type="primary"):
            # Simpan File
            file_path = get_proof_filename(who, match_date)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success("Berhasil terkirim! Jendela ini akan tertutup.")
            time.sleep(1.5)
            st.rerun()

# --- STYLE CSS ------------------------------------------------------
st.markdown("""
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 5rem;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Bikin tombol upload lebih menonjol */
    div.stButton > button:first-child {
        width: 100%;
    }
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
        
        # GALERI BUKTI
        with st.expander("📸 Cek Galeri Bukti", expanded=False):
            if df.empty:
                st.write("Data kosong.")
            else:
                latest_date = sorted(df['Date'].unique(), reverse=True)[0]
                transfers = df[(df['Date'] == latest_date) & (df['Status'] == "💳 Transfer")]
                if transfers.empty:
                    st.caption("Belum ada transfer.")
                else:
                    for index, row in transfers.iterrows():
                        p_name = row['Player_Name']
                        fname = get_proof_filename(p_name, latest_date)
                        if os.path.exists(fname):
                            st.markdown(f"**{p_name}**")
                            st.image(fname)
                        else:
                            st.caption(f"{p_name}: Belum upload")

        st.divider()
        st.subheader("🔗 Link Grup")
        st.code("?view=player", language="text")
        
        st.divider()
        with st.form("new_match"):
            st.write("📝 **Buat Match Baru**")
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
                        st.success("Match Created!")
                        time.sleep(1)
                        st.rerun()

# --- 2. PLAYER VIEW (MAIN) ------------------------------------------

if df.empty:
    st.info("👋 Belum ada match aktif.")
else:
    # DATA SETUP
    latest_date = sorted(df['Date'].unique(), reverse=True)[0]
    current_match = df[df['Date'] == latest_date].copy()
    field_name = current_match['Field_Name'].iloc[0]

    # --- HEADER AREA ---
    col_head1, col_head2 = st.columns([2, 1])
    with col_head1: st.subheader(f"🏀 {field_name}")
    with col_head2: st.caption(f"📅 {latest_date}")
    
    st.divider()

    # --- ACTION BAR (TOMBOL UPLOAD DI ATAS) ---
    # Kita cari siapa aja yang statusnya Transfer buat ngisi list di modal
    transfer_players = current_match[current_match["Status"] == "💳 Transfer"]["Player_Name"].unique()
    
    # Tampilkan tombol Pop-up HANYA jika ada yang pilih Transfer
    if len(transfer_players) > 0:
        col_msg, col_btn = st.columns([1.5, 1])
        with col_msg:
            st.info(f"💡 Ada {len(transfer_players)} orang bayar via Transfer.")
        with col_btn:
            if st.button("📤 Upload Bukti", type="primary"):
                show_upload_modal(transfer_players, latest_date)
    
    # --- TABLE EDITOR ---
    st.caption("👇 Update statusmu di tabel ini:")
    
    edited_df = st.data_editor(
        current_match[["Player_Name", "Status"]],
        column_config={
            "Player_Name": st.column_config.TextColumn("Nama", disabled=True),
            "Status": st.column_config.SelectboxColumn(
                "Status (Pilih 🔽)",
                options=["❌ Belum", "💵 Cash", "💳 Transfer"],
                required=True
            )
        },
        hide_index=True,
        use_container_width=True,
        key="player_editor"
    )

    # --- SAVE BUTTON ---
    # Tombol simpan tetap di bawah tabel agar flow-nya: Cek Nama -> Ganti Status -> Simpan
    if st.button("💾 Simpan Perubahan Status"):
        df_others = df[df['Date'] != latest_date]
        edited_df['Date'] = latest_date
        edited_df['Field_Name'] = field_name
        edited_df['Timestamp'] = datetime.now().strftime("%Y-%m-%d")
        final_df = pd.concat([df_others, edited_df], ignore_index=True)
        save_data(final_df)
        st.toast("Data tersimpan!", icon="✅")
        time.sleep(0.5)
        st.rerun()
