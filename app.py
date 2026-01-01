import streamlit as st
import pandas as pd
import os
import time
import shutil
from datetime import datetime

# --- CONFIG ---------------------------------------------------------
st.set_page_config(page_title="BIB Checklist Payment", layout="centered")
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
        df = load_data()
        mask = (df['Date'] == match_date) & (df['Player_Name'] == who)
        df.loc[mask, 'Status'] = method
        df.loc[mask, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d")
        
        if method == "💳 Transfer" and uploaded_file:
            folder = get_match_folder(match_date, field_name)
            file_path = get_proof_filename(folder, who)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        
        save_data(df)
        st.success(f"Berhasil! Terima kasih {who}.")
        time.sleep(1)
        st.rerun()

# --- MODAL PREVIEW (ADMIN ONLY) -------------------------------------
@st.dialog("🔍 Detail Bukti")
def show_image_preview(image_path, player_name):
    st.image(image_path, use_container_width=True, caption=f"Bukti Transfer: {player_name}")

# --- STYLE CSS ------------------------------------------------------
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 5rem;}
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
        
        # Tombol Refresh Manual
        if st.button("🔄 Refresh Data App", use_container_width=True):
            st.rerun()
            
        st.divider()

        # Pastikan variabel t_a dan t_b didefinisikan di sini
        t_a, t_b = st.tabs(["➕ Buat Match", "📂 Manage & Bukti"])
        
        with t_a:
            with st.form("new"):
                d_in = st.date_input("Tanggal")
                f_in = st.text_input("Lapangan", "GOR")
                n_in = st.text_area("List Nama (Paste WA)")
                if st.form_submit_button("🚀 Generate Match"):
                    names = [''.join([i for i in l if not i.isdigit() and i != '.']).strip() for l in n_in.split('\n') if l.strip()]
                    new_rows = pd.DataFrame({"Date": [str(d_in)]*len(names), "Field_Name": [f_in]*len(names), "Player_Name": names, "Status": ["❌ Belum"]*len(names), "Timestamp": [datetime.now().strftime("%Y-%m-%d")]*len(names)})
                    save_data(pd.concat([load_data(), new_rows], ignore_index=True))
                    st.success("Berhasil dibuat!")
                    time.sleep(1)
                    st.rerun()
        
        with t_b:
            if not df.empty:
                all_d = sorted(df['Date'].unique(), reverse=True)
                sel_h = st.selectbox("Pilih Jadwal:", all_d)
                
                # Link Khusus Player
                st.caption("🔗 Link untuk dibagikan ke grup:")
                st.code(f"?view=player&date={sel_h}")
                
                st.divider()
                
                # Galeri Foto Admin
                st.write("📸 **Galeri Bukti Transfer**")
                h_data = df[df['Date'] == sel_h]
                f_h_name = h_data['Field_Name'].iloc[0]
                m_folder = get_match_folder(sel_h, f_h_name)
                
                p_transfer = h_data[h_data['Status'] == "💳 Transfer"]['Player_Name'].tolist()
                
                if p_transfer:
                    if os.path.exists(m_folder) and len(os.listdir(m_folder)) > 0:
                        shutil.make_archive(m_folder, 'zip', m_folder)
                        with open(m_folder + ".zip", "rb") as fp:
                            st.download_button("📦 Download Semua (.ZIP)", fp, f"Bukti_{sel_h}.zip", "application/zip")
                    
                    cols = st.columns(3)
                    for idx, p in enumerate(p_transfer):
                        f_p = get_proof_filename(m_folder, p)
                        if os.path.exists(f_p):
                            with cols[idx % 3]:
                                st.image(f_p, use_container_width=True)
                                if st.button("🔍", key=f"adm_{p}"):
                                    show_image_preview(f_p, p)
                else:
                    st.write("Belum ada bukti.")

                st.divider()
                if st.button(f"🗑️ Hapus Jadwal {sel_h}", type="secondary", use_container_width=True):
                    save_data(df[df['Date'] != sel_h])
                    if os.path.exists(m_folder): shutil.rmtree(m_folder)
                    st.rerun()

# --- 2. PLAYER VIEW (TAMPILAN DEPAN) --------------------------------
if df.empty:
    st.info("👋 Belum ada match aktif.")
else:
    available_dates = sorted(df['Date'].unique(), reverse=True)
    
    if target_date_param and target_date_param in available_dates:
        selected_date = target_date_param
    else:
        col_s, _ = st.columns([2,1])
        with col_s:
            selected_date = st.selectbox("📅 Jadwal Main:", available_dates)
    
    curr = df[df['Date'] == selected_date].copy()
    f_name = curr['Field_Name'].iloc[0]
    folder = get_match_folder(selected_date, f_name)

    # --- BAGIAN JUDUL (Sinkron dengan Page Title) ---
    # Kita ambil judul dari config di paling atas (Basket Payment)
    page_title_name = "BIB Checklist Payment" 
    st.title(f"🏀 {page_title_name}")
    st.caption(f"📍 Lapangan: {f_name} | 📅 Tanggal: {selected_date}")
    # ------------------------------------------------

    # Locking Detection
    curr['Lunas'] = False
    for i, r in curr.iterrows():
        if os.path.exists(get_proof_filename(folder, r['Player_Name'])) or r['Status'] == "💵 Cash":
            curr.at[i, 'Lunas'] = True

    # TOMBOL LAPOR
    yet_to_pay = curr[curr['Lunas'] == False]['Player_Name'].tolist()
    if yet_to_pay:
        if st.button("💳 LAPOR BAYAR / UPLOAD BUKTI", type="primary", use_container_width=True):
            show_update_modal(yet_to_pay, selected_date, f_name)
    else:
        st.success("🎉 Semua pemain di jadwal ini sudah lunas!")

    st.divider()

    # TABEL STATUS
    st.write("📋 **Status Pembayaran:**")
    st.dataframe(
        curr[["Player_Name", "Status"]],
        column_config={"Player_Name": "Nama Pemain", "Status": "Status"},
        hide_index=True,
        use_container_width=True
    )
    
    # INFO LUNAS (Footer)
    done = curr[curr['Lunas'] == True]['Player_Name'].tolist()
    if done:
        st.caption(f"✅ Terverifikasi: {', '.join(done)}")
