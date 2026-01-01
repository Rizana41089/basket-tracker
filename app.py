import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIG ---------------------------------------------------------
st.set_page_config(page_title="Basket Payment", layout="centered")
DATA_FILE = "/tmp/basket_data.csv"
PROOF_DIR = "/tmp"  # Lokasi simpan gambar sementara

# --- FUNCTIONS ------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Date", "Field_Name", "Player_Name", "Status", "Timestamp"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def get_proof_filename(player_name, date):
    # Buat nama file unik: proof_Budi_2023-10-01.png
    safe_name = "".join([c for c in player_name if c.isalnum()])
    return f"{PROOF_DIR}/proof_{safe_name}_{date}.png"

# --- STYLE CSS ------------------------------------------------------
st.markdown("""
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 5rem;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- MAIN LOGIC -----------------------------------------------------

# Cek parameter URL
query_params = st.query_params
is_player_mode = query_params.get("view") == "player"
df = load_data()

# --- 1. ADMIN SIDEBAR -----------------------------------------------
if not is_player_mode:
    with st.sidebar:
        st.header("⚙️ Admin Dashboard")
        
        # --- FITUR BARU: CEK BUKTI TRANSFER ---
        st.info("👇 Cek bukti transfer disini")
        with st.expander("📸 Galeri Bukti Transfer", expanded=True):
            if df.empty:
                st.write("Belum ada data.")
            else:
                # Cari data transfer di tanggal terbaru
                latest_date = sorted(df['Date'].unique(), reverse=True)[0]
                transfers = df[(df['Date'] == latest_date) & (df['Status'] == "💳 Transfer")]
                
                if transfers.empty:
                    st.write("Belum ada yang pilih Transfer hari ini.")
                else:
                    st.write(f"**Match: {latest_date}**")
                    for index, row in transfers.iterrows():
                        p_name = row['Player_Name']
                        fname = get_proof_filename(p_name, latest_date)
                        
                        st.markdown(f"**👤 {p_name}**")
                        if os.path.exists(fname):
                            st.image(fname, caption=f"Bukti {p_name}", use_container_width=True)
                        else:
                            st.warning("Sudah pilih transfer, tapi belum upload gambar.")
                        st.markdown("---")

        st.divider()
        st.subheader("🔗 Link Grup")
        st.code("?view=player", language="text")
        
        st.divider()
        st.write("📝 **Buat Match Baru**")
        with st.form("new_match"):
            date_in = st.date_input("Tanggal")
            field_in = st.text_input("Lapangan", "GOR Basket")
            names_in = st.text_area("List Nama", height=150)
            if st.form_submit_button("🚀 Buat Match"):
                if names_in:
                    lines = names_in.split('\n')
                    clean_names = [''.join([i for i in line if not i.isdigit() and i != '.']).strip() for line in lines if line.strip()]
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

# --- 2. PLAYER VIEW -------------------------------------------------

if df.empty:
    st.info("👋 Belum ada match aktif.")
else:
    latest_date = sorted(df['Date'].unique(), reverse=True)[0]
    current_match = df[df['Date'] == latest_date].copy()
    field_name = current_match['Field_Name'].iloc[0]

    col_a, col_b = st.columns([2, 1])
    with col_a: st.subheader(f"🏀 {field_name}")
    with col_b: st.caption(f"📅 {latest_date}")
    st.divider()
    
    st.caption("👇 Klik 2x status untuk ubah.")

    edited_df = st.data_editor(
        current_match[["Player_Name", "Status"]],
        column_config={
            "Player_Name": st.column_config.TextColumn("Nama", disabled=True),
            "Status": st.column_config.SelectboxColumn(
                "Status (Pilih 🔽)",
                options=["❌ Belum", "💵 Cash", "💳 Transfer"],
                required=True,
                width="medium"
            )
        },
        hide_index=True,
        use_container_width=True,
        key="player_editor"
    )

    col_save, col_info = st.columns([1, 1])
    with col_save:
        if st.button("💾 Update Status", type="primary", use_container_width=True):
            df_others = df[df['Date'] != latest_date]
            edited_df['Date'] = latest_date
            edited_df['Field_Name'] = field_name
            edited_df['Timestamp'] = datetime.now().strftime("%Y-%m-%d")
            final_df = pd.concat([df_others, edited_df], ignore_index=True)
            save_data(final_df)
            st.toast("Tersimpan!", icon="✅")
            time.sleep(0.5)
            st.rerun()

    # --- LOGIC UPLOAD & SIMPAN GAMBAR ---
    transfer_players = edited_df[edited_df["Status"] == "💳 Transfer"]
    
    if not transfer_players.empty:
        st.markdown("---")
        st.info("📤 **Upload Bukti Transfer**")
        
        who_is_transferring = st.selectbox("Siapa yang mau upload?", options=transfer_players["Player_Name"].unique())
        uploaded_file = st.file_uploader(f"Upload bukti {who_is_transferring}", type=['jpg','png','jpeg'])
        
        if uploaded_file:
            # SIMPAN FILE KE FOLDER /tmp/
            file_path = get_proof_filename(who_is_transferring, latest_date)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✅ Bukti {who_is_transferring} berhasil dikirim ke Admin!")
            # Opsional: Tampilkan preview kecil buat user
            st.image(uploaded_file, width=150)
