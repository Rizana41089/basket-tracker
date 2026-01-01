import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from io import BytesIO

# =========================
# GOOGLE SHEETS CONNECTION
# =========================
@st.cache_resource
def connect_gsheet():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open_by_key(st.secrets["gsheet"]["sheet_id"])
    return sh.sheet1  # first worksheet


sheet = connect_gsheet()

COLUMNS = [
    "Date",
    "Field_Name",
    "Player_Name",
    "Status",
    "Timestamp",
    "Proof_Filename"
]

STATUS_OPTIONS = ["Belum", "Cash", "Transfer"]


# =========================
# HELPERS
# =========================
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)


def append_rows(rows: list):
    sheet.append_rows(rows, value_input_option="USER_ENTERED")


def update_cell(row, col_name, value):
    col_index = COLUMNS.index(col_name) + 1
    sheet.update_cell(row, col_index, value)


def download_csv(df):
    return df.to_csv(index=False).encode("utf-8")


# =========================
# UI CONFIG
# =========================
st.set_page_config(
    page_title="Basketball Payment Tracker",
    layout="wide",
)

st.title("🏀 Basketball Community Payment Tracker")
st.caption("Biar main basket, bukan main tebak-tebakan siapa yang belum bayar 😄")

tab_admin, tab_player = st.tabs(["🛠 Admin Setup", "✅ Player Checklist"])


# =========================
# TAB 1 – ADMIN
# =========================
with tab_admin:
    st.subheader("Generate Match")

    col1, col2 = st.columns(2)
    with col1:
        match_date = st.date_input("Tanggal Main", datetime.today())
    with col2:
        field_name = st.text_input("Nama Lapangan")

    raw_names = st.text_area(
        "Paste Nama Pemain (dari WhatsApp)",
        placeholder="Contoh:\nAndi\nBudi\nCharlie\nDoni"
    )

    if st.button("🚀 Generate Match", use_container_width=True):
        if not raw_names.strip():
            st.warning("Nama pemain masih kosong, bro 😅")
        else:
            players = [n.strip() for n in raw_names.splitlines() if n.strip()]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            rows = []
            for p in players:
                rows.append([
                    str(match_date),
                    field_name,
                    p,
                    "Belum",
                    now,
                    ""
                ])

            append_rows(rows)
            st.success(f"✅ {len(players)} pemain berhasil ditambahkan!")

    st.divider()

    st.subheader("Download Data")
    df = load_data()
    if not df.empty:
        st.download_button(
            "⬇️ Download CSV",
            data=download_csv(df),
            file_name="basket_payment_report.csv",
            mime="text/csv"
        )


# =========================
# TAB 2 – PLAYER CHECKLIST
# =========================
with tab_player:
    st.subheader("Checklist Pembayaran")

    df = load_data()
    if df.empty:
        st.info("Belum ada match. Silakan generate dulu di tab Admin.")
        st.stop()

    # Filter match
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.selectbox(
            "Tanggal",
            sorted(df["Date"].unique())
        )
    with col2:
        selected_field = st.selectbox(
            "Lapangan",
            sorted(df[df["Date"] == selected_date]["Field_Name"].unique())
        )

    filtered = df[
        (df["Date"] == selected_date) &
        (df["Field_Name"] == selected_field)
    ].reset_index(drop=True)

    for i, row in filtered.iterrows():
        sheet_row_index = df.index[
            (df["Date"] == row["Date"]) &
            (df["Field_Name"] == row["Field_Name"]) &
            (df["Player_Name"] == row["Player_Name"])
        ][0] + 2  # +2 karena header

        bg_color = ""
        if row["Status"] == "Cash":
            bg_color = "background-color:#d4edda;"
        elif row["Status"] == "Transfer":
            bg_color = "background-color:#fff3cd;"

        st.markdown(
            f"<div style='padding:10px; border-radius:8px; {bg_color}'>",
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns([3, 2, 3])
        with col1:
            st.write(f"👤 **{row['Player_Name']}**")

        with col2:
            new_status = st.selectbox(
                "Status",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(row["Status"]),
                key=f"status_{i}"
            )

        with col3:
            proof_file = None
            if new_status == "Transfer":
                proof_file = st.file_uploader(
                    "Bukti Transfer",
                    type=["jpg", "jpeg", "png"],
                    key=f"proof_{i}"
                )

        # Update logic
        if new_status != row["Status"]:
            update_cell(sheet_row_index, "Status", new_status)
            update_cell(
                sheet_row_index,
                "Timestamp",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            st.toast(f"{row['Player_Name']} updated ke {new_status}")

        if proof_file:
            update_cell(sheet_row_index, "Proof_Filename", proof_file.name)

        st.markdown("</div>", unsafe_allow_html=True)
