import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
# Layout harus centered biar ga error di HP
st.set_page_config(page_title="Basket Payment Tracker", layout="centered")

# PENTING: Pakai /tmp/ biar Streamlit Cloud mengizinkan kita tulis file (walaupun sementara)
DATA_FILE = "/tmp/basket_data.csv"

# --- FUNCTIONS ---
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Date", "Field_Name", "Player_Name", "Status", "Timestamp"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- APP UI ---
st.title("🏀 Basket Payment Tracker")

# TABS
tab1, tab2 = st.tabs(["📝 Player Checklist", "⚙️ Admin Setup"])

# --- TAB 1: PLAYER CHECKLIST ---
with tab1:
    st.header("Cek & Bayar")
    
    df = load_data()
    
    if df.empty:
        st.info("⚠️ Belum ada data match.")
        st.write("👉 Masuk ke tab 'Admin Setup' di atas buat bikin match baru.")
    else:
        # Ambil tanggal-tanggal yang ada
        match_dates = df['Date'].unique()
        # Urutkan dari yang terbaru
        match_dates = sorted(match_dates, reverse=True)
        
        selected_date = st.selectbox("Pilih Tanggal Match:", match_dates)
        
        # Ambil info lapangan
        field_name = df[df['Date'] == selected_date]['Field_Name'].iloc[0]
        st.info(f"📍 **Lokasi:** {field_name} | 📅 **Tanggal:** {selected_date}")
        
        # Filter Data
        match_data = df[df['Date'] == selected_date].copy()
        
        # Tampilkan Tabel Editor
        st.write("👇 **Cari namamu & Update Status:**")
        
        edited_df = st.data_editor(
            match_data[["Player_Name", "Status"]],
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status Pembayaran",
                    options=["Belum", "Cash", "Transfer"],
                    required=True
                ),
                "Player_Name": st.column_config.TextColumn("Nama Pemain", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            key="editor"
        )
        
        # Tombol Simpan Perubahan Player
        if st.button("💾 UPDATE STATUS SAYA", type="primary"):
            # Logika Update
            # 1. Buang data lama tanggal ini
            df_others = df[df['Date'] != selected_date]
            
            # 2. Siapkan data baru hasil edit
            edited_df['Date'] = selected_date
            edited_df['Field_Name'] = field_name
            # Pertahankan timestamp lama atau update baru (disini kita update baru biar tau kapan terakhir edit)
            edited_df['Timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 3. Gabung lagi
            final_df = pd.concat([df_others, edited_df], ignore_index=True)
            save_data(final_df)
            
            st.toast("✅ Data berhasil disimpan!", icon="🔥")
            time.sleep(1)
            st.rerun()

        # Upload Bukti
        st.divider()
        st.caption("Kalau transfer, upload bukti di sini:")
        with st.expander("📤 Upload Bukti Transfer"):
            uploader_name = st.selectbox("Nama Kamu:", match_data['Player_Name'].unique())
            uploaded_file = st.file_uploader("Pilih Screenshot", type=['png', 'jpg', 'jpeg'])
            if uploaded_file is not None:
                st.success(f"Mantap {uploader_name}, bukti diterima! (Sistem Trust-Based)")

# --- TAB 2: ADMIN SETUP ---
with tab2:
    st.header("Admin Setup")
    st.write("Buat jadwal main baru di sini.")
    
    with st.form("new_match_form"):
        match_date = st.date_input("Tanggal Main")
        field_input = st.text_input("Nama Lapangan", "GOR Basket")
        raw_names = st.text_area("Paste List Nama dari WA", height=200, placeholder="Contoh:\n1. Budi\n2. Anto\n3. ...")
        
        submitted = st.form_submit_button("🚀 Buat Match Baru")
        
        if submitted:
            if not raw_names:
                st.error("⚠️ List nama masih kosong! Paste dulu dari WA.")
            else:
                # Parse names logic
                lines = raw_names.split('\n')
                clean_names = []
                for line in lines:
                    # Bersihkan angka dan titik (misal "1. Budi" jadi "Budi")
                    clean_name = ''.join([i for i in line if not i.isdigit() and i != '.']).strip()
                    # Hapus simbol aneh jika ada
                    clean_name = clean_name.replace("-", "").strip()
                    
                    if clean_name:
                        clean_names.append(clean_name)
                
                if clean_names:
                    # Buat DataFrame baru
                    new_data = pd.DataFrame({
                        "Date": [str(match_date)] * len(clean_names),
                        "Field_Name": [field_input] * len(clean_names),
                        "Player_Name": clean_names,
                        "Status": ["Belum"] * len(clean_names),
                        "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * len(clean_names)
                    })
                    
                    # Load existing & Append
                    current_df = load_data()
                    combined_df = pd.concat([current_df, new_data], ignore_index=True)
                    save_data(combined_df)
                    
                    st.success(f"✅ Sukses! Match tanggal {match_date} berhasil dibuat.")
                    time.sleep(1)
                    st.rerun() # <-- INI PENTING: Paksa refresh halaman biar pindah tab otomatis
                else:
                    st.warning("⚠️ Gagal membaca nama. Pastikan formatnya per baris ya.")

    # Tombol Reset Darurat
    st.divider()
    if st.button("🗑️ Reset Semua Data (Hati-hati)"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.error("Data sudah dihapus bersih.")
            time.sleep(1)
            st.rerun()
