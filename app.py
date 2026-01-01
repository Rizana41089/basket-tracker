import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Basket Payment Tracker", layout="centered")
DATA_FILE = "/tmp/basket_data.csv"

# --- FUNCTIONS ---
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        # Create empty dataframe if not exists
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
        st.info("Belum ada match yang dibuat Admin. Cek lagi nanti ya!")
    else:
        # Filter to show mostly recent match (optional logic, showing all for now)
        match_dates = df['Date'].unique()
        selected_date = st.selectbox("Pilih Tanggal Match:", match_dates)
        
        # Show Field Name
        field_name = df[df['Date'] == selected_date]['Field_Name'].iloc[0]
        st.caption(f"📍 Lokasi: {field_name}")
        
        # Filter Data
        match_data = df[df['Date'] == selected_date].copy()
        
        # Display Interactive Editor
        # Player can change their status here
        st.write("Cari namamu dan update status:")
        
        edited_df = st.data_editor(
            match_data[["Player_Name", "Status"]],
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status Pembayaran",
                    options=["Belum", "Cash", "Transfer"],
                    required=True
                )
            },
            hide_index=True,
            use_container_width=True,
            key="editor"
        )
        
        # Save Button logic (Simplification for CSV)
        # In data_editor, we need to capture changes. 
        # But for simple MVP, let's use a button to commit changes if needed 
        # OR usually data_editor updates state. 
        
        # Let's simplify: Just show list and individual update buttons if editor is tricky?
        # No, Data Editor is best. Let's merge changes.
        
        if st.button("💾 Simpan Perubahan Status"):
            # Update main DF with changes from editor
            # This is a bit tricky in pandas logic, so let's keep it simple:
            # We overwrite the rows for this date
            
            # 1. Drop old rows for this date
            df = df[df['Date'] != selected_date]
            
            # 2. Add back the edited rows (adding back the missing columns)
            edited_df['Date'] = selected_date
            edited_df['Field_Name'] = field_name
            edited_df['Timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            final_df = pd.concat([df, edited_df], ignore_index=True)
            save_data(final_df)
            st.success("Data berhasil diupdate! Makasih udah lapor.")
            st.rerun()

        # Upload Proof Section
        st.divider()
        st.subheader("Upload Bukti Transfer")
        uploader_name = st.selectbox("Nama Kamu:", match_data['Player_Name'].unique())
        uploaded_file = st.file_uploader("Upload screenshot (Opsional)", type=['png', 'jpg', 'jpeg'])
        if uploaded_file is not None:
            st.success(f"Mantap {uploader_name}, bukti transfer diterima! (Disimpan sementara)")

# --- TAB 2: ADMIN SETUP ---
with tab2:
    st.header("Admin Setup")
    
    with st.form("new_match_form"):
        match_date = st.date_input("Tanggal Main")
        field_input = st.text_input("Nama Lapangan", "GOR Basket")
        raw_names = st.text_area("Paste List Nama dari WA", height=200, placeholder="1. Budi\n2. Anto\n3. ...")
        
        submitted = st.form_submit_button("Buat Match Baru")
        
        if submitted and raw_names:
            # Parse names
            lines = raw_names.split('\n')
            clean_names = []
            for line in lines:
                # Remove numbers like "1. " or "2."
                clean_name = ''.join([i for i in line if not i.isdigit() and i != '.']).strip()
                if clean_name:
                    clean_names.append(clean_name)
            
            if clean_names:
                # Create new dataframe rows
                new_data = pd.DataFrame({
                    "Date": [str(match_date)] * len(clean_names),
                    "Field_Name": [field_input] * len(clean_names),
                    "Player_Name": clean_names,
                    "Status": ["Belum"] * len(clean_names),
                    "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * len(clean_names)
                })
                
                # Append to existing CSV
                current_df = load_data()
                combined_df = pd.concat([current_df, new_data], ignore_index=True)
                save_data(combined_df)
                
                st.success(f"Match tanggal {match_date} berhasil dibuat dengan {len(clean_names)} pemain!")
            else:
                st.error("Gagal baca nama. Pastikan formatnya bener ya.")

    # Reset Data Button
    st.divider()
    if st.button("⚠️ Hapus Semua Data (Reset)"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.warning("Data bersih kembali seperti baru.")
            st.rerun()
