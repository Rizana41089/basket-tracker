import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIG ---------------------------------------------------------
st.set_page_config(page_title="Basket Payment", layout="centered")
DATA_FILE = "/tmp/basket_data.csv"

# --- FUNCTIONS ------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Date", "Field_Name", "Player_Name", "Status", "Timestamp"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- STYLE CSS (Biar Tampilan Rapi) ---------------------------------
st.markdown("""
    <style>
    .stApp {max-width: 600px; margin: 0 auto;}
    .block-container {padding-top: 2rem; padding-bottom: 5rem;}
    </style>
    """, unsafe_allow_html=True)

# --- MAIN LOGIC (ADMIN VS PLAYER) -----------------------------------

# Cek apakah ada parameter "?view=player" di Link URL
query_params = st.query_params
is_player_mode = query_params.get("view") == "player"

# --- 1. ADMIN SIDEBAR (Hanya muncul jika BUKAN mode player) ---------
if not is_player_mode:
    with st.sidebar:
        st.header("⚙️ Admin Dashboard")
        st.info("Menu ini hanya terlihat oleh Admin.")
        
        # --- GENERATE LINK SECTION ---
        st.divider()
        st.subheader("🔗 Link untuk Grup")
        st.write("Copy link di bawah ini dan share ke WA. (Menu Admin ini akan hilang saat dibuka player).")
        
        # Tips: Karena Streamlit susah tau URL aslinya sendiri secara otomatis, 
        # kita kasih instruksi manual tapi jelas.
        st.code("?view=player", language="text")
        st.caption("👆 Tambahkan tulisan di atas ke akhir link website kamu.")
        
        st.divider()
        
        # --- CREATE MATCH FORM ---
        st.write("📝 **Buat Match Baru**")
        with st.form("new_match"):
            date_in = st.date_input("Tanggal")
            field_in = st.text_input("Lapangan", "GOR Basket")
            names_in = st.text_area("List Nama (Paste dari WA)", height=150)
            
            if st.form_submit_button("🚀 Buat Match"):
                if names_in:
                    lines = names_in.split('\n')
                    clean_names = [line.strip() for line in lines if line.strip()]
                    # Remove numbers like "1. "
                    clean_names = [''.join([i for i in n if not i.isdigit() and i != '.']).strip() for n in clean_names]
                    
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
                        st.success("Match Berhasil Dibuat!")
                        time.sleep(1)
                        st.rerun()

# --- 2. PLAYER VIEW (TAMPILAN UTAMA) --------------------------------

df = load_data()

if df.empty:
    st.info("👋 Belum ada match aktif. Admin harap buat match dulu.")
else:
    # Ambil match paling baru
    latest_date = sorted(df['Date'].unique(), reverse=True)[0]
    current_match = df[df['Date'] == latest_date].copy()
    field_name = current_match['Field_Name'].iloc[0]

    # Header
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader(f"🏀 {field_name}")
    with col_b:
        st.caption(f"📅 {latest_date}")

    st.divider()

    # Tabel Editor
    edited_df = st.data_editor(
        current_match[["Player_Name", "Status"]],
        column_config={
            "Player_Name": st.column_config.TextColumn("Nama Pemain", disabled=True),
            "Status": st.column_config.SelectboxColumn(
                "Status Bayar",
                options=["❌ Belum", "💵 Cash", "💳 Transfer"],
                required=True,
                width="medium"
            )
        },
        hide_index=True,
        use_container_width=True,
        key="player_editor"
    )

    # Tombol Simpan
    col_save, col_info = st.columns([1, 1])
    with col_save:
        if st.button("💾 Update Status", type="primary", use_container_width=True):
            df_others = df[df['Date'] != latest_date]
            edited_df['Date'] = latest_date
            edited_df['Field_Name'] = field_name
            edited_df['Timestamp'] = datetime.now().strftime("%Y-%m-%d")
            final_df = pd.concat([df_others, edited_df], ignore_index=True)
            save_data(final_df)
            st.toast("Status tersimpan!", icon="✅")
            time.sleep(0.5)
            st.rerun()

    # Logic Upload Transfer
    transfer_players = edited_df[edited_df["Status"] == "💳 Transfer"]
    
    if not transfer_players.empty:
        st.markdown("---")
        st.info("📤 **Upload Bukti Transfer**")
        
        who_is_transferring = st.selectbox(
            "Siapa yang mau upload?", 
            options=transfer_players["Player_Name"].unique()
        )
        
        uploaded_file = st.file_uploader(f"Upload bukti {who_is_transferring}", type=['jpg','png'])
        
        if uploaded_file:
            st.success(f"Bukti {who_is_transferring} diterima! ✅")
