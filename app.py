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

# --- MODAL UPDATE STATUS (ANTI-MACET) -------------------------------
@st.dialog("📝 Update Status Bayar")
def show_update_modal(player_list, match_date, field_name):
    st.write(f"Update untuk match: **{match_date}**")
    
    # Pilih Nama
    who = st.selectbox("Pilih Namamu:", player_list)
    
    # Pilih Status
    method = st.radio("Metode Pembayaran:", ["💵 Cash", "💳 Transfer"])
    
    uploaded_file = None
    if method == "💳 Transfer":
        uploaded_file = st.file_uploader("Upload Bukti Transfer", type=['jpg','png','jpeg'])
    
    if st.button("Simpan & Konfirmasi", type="primary"):
        # Logic simpan
        df = load_data()
        mask = (df['Date'] == match_date) & (df['Player_Name'] == who)
        df.loc[mask, 'Status'] = method
        df.loc[mask, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d")
        
        # Jika transfer, simpan gambarnya
        if method == "💳 Transfer" and uploaded_file:
            folder = get_match_folder(match_date, field_name)
            file_path = get_proof_filename(folder, who)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        
        save_data(df)
        st.success(f"Berhasil! Status {who} sudah diupdate.")
        time.sleep(1)
        st.rerun()

@st.dialog("🔍 Detail Bukti")
def show_image_preview(image_path, player_name):
    st.image(image_path, use_container_width=True, caption=player_name)

# --- STYLE CSS ------------------------------------------------------
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 5rem;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC ----------------------------------------------------------
query_params = st.query_params
view_mode = query_params.get("view")
target_date_param = query_params.get("date")
is_player_mode = (view_mode == "player")
df = load_data()

# --- 1. ADMIN SIDEBAR -----------------------------------------------
if not is_player_mode:
    with st.sidebar:
        st.header("⚙️ Admin Menu")
        tab_a, tab_b = st.tabs(["Buat", "Manage"])
        
        with tab_a:
            with st.form("new"):
                d_in = st.date_input("Tanggal")
                f_in = st.text_input("Lapangan", "GOR")
                n_in = st.text_area("List Nama")
                if st.form_submit_button("🚀 Buat"):
                    names = [''.join([i for i in l if not i.isdigit() and i != '.']).strip() for l in n_in.split('\n') if l.strip()]
                    new_df = pd.DataFrame({"Date": [str(d_in)]*len(names), "Field_Name": [f_in]*len(names), "Player_Name": names, "Status": ["❌ Belum"]*len(names), "Timestamp": [datetime.now().strftime("%Y-%m-%d")]*len(names)})
                    save_data(pd.concat([load_data(), new_df], ignore_index=True))
                    st.rerun()
        
        with tab_b:
            if not df.empty:
                sel_h = st.selectbox("Pilih Match:", sorted(df['Date'].unique(), reverse=True))
                st.code(f"?view=player&date={sel_h}")
                if st.button(f"🗑️ Hapus {sel_h}", type="secondary"):
                    save_data(df[df['Date'] != sel_h])
                    st.rerun()

# --- 2. PLAYER VIEW -------------------------------------------------
if df.empty:
    st.info("Belum ada match.")
else:
    available_dates = sorted(df['Date'].unique(), reverse=True)
    selected_date = target_date_param if (target_date_param in available_dates) else st.selectbox("📅 Jadwal:", available_dates)
    
    curr = df[df['Date'] == selected_date].copy()
    f_name = curr['Field_Name'].iloc[0]
    folder = get_match_folder(selected_date, f_name)

    # Pendeteksi Bukti (Locking)
    curr['Lunas'] = False
    for i, r in curr.iterrows():
        if os.path.exists(get_proof_filename(folder, r['Player_Name'])) or r['Status'] == "💵 Cash":
            curr.at[i, 'Lunas'] = True

    st.subheader(f"🏀 {f_name}")
    st.caption(f"Tanggal: {selected_date}")

    # TOMBOL UTAMA (Gantiin Dropdown yang macet)
    # Filter: Orang yang belum lunas
    yet_to_pay = curr[curr['Lunas'] == False]['Player_Name'].tolist()
    
    if yet_to_pay:
        if st.button("💳 LAPOR BAYAR SEKARANG", type="primary", use_container_width=True):
            show_update_modal(yet_to_pay, selected_date, f_name)
    else:
        st.success("🎉 Semua pemain sudah lunas!")

    st.divider()

    # TAMPILAN TABEL (Read Only - Lebih Stabil)
    st.write("📋 **Daftar Pembayaran:**")
    
    # Bikin versi tampilan (Pake Icon)
    display_df = curr[["Player_Name", "Status"]].copy()
    
    st.dataframe(
        display_df,
        column_config={
            "Player_Name": "Nama Pemain",
            "Status": "Status"
        },
        hide_index=True,
        use_container_width=True
    )

    # INFO BUKTI UNTUK ADMIN/PLAYER
    with st.expander("🖼️ Lihat Bukti Transfer"):
        paid_transfer = curr[curr['Status'] == "💳 Transfer"]['Player_Name'].tolist()
        if not paid_transfer:
            st.write("Belum ada bukti.")
        else:
            cols = st.columns(3)
            for idx, p in enumerate(paid_transfer):
                f_path = get_proof_filename(folder, p)
                if os.path.exists(f_path):
                    with cols[idx % 3]:
                        st.image(f_path, use_container_width=True)
                        if st.button("🔍", key=f"v_{p}"):
                            show_image_preview(f_path, p)
