import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(
    page_title="Convert Rekening Koran PDF",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* Background app dengan warna pink pastel lembut */
[data-testid="stAppViewContainer"] {
    background-color: #fff0f3;
    background-image: url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23f48fb1' fill-opacity='0.18'%3E%3Cpath d='M40 30c-2.2 0-4 1.8-4 4 0 2.2 1.8 4 4 4s4-1.8 4-4c0-2.2-1.8-4-4-4zm0-10c-3.3 0-6 2.7-6 6s2.7 6 6 6 6-2.7 6-6-2.7-6-6-6zm-10 10c0-3.3-2.7-6-6-6s-6 2.7-6 6 2.7 6 6 6 6-2.7 6-6zm20 0c0-3.3 2.7-6 6-6s6 2.7 6 6-2.7 6-6 6-6-2.7-6-6zm-10 10c-3.3 0-6 2.7-6 6s2.7 6 6 6 6-2.7 6-6-2.7-6-6-6z'/%3E%3C/g%3E%3C/svg%3E");
}

/* Sidebar estetik pink */
[data-testid="stSidebar"] {
    background-color: #ffe6eb !important;
}

/* Judul Heading dengan warna Burgundy/Deep Pink */
h1, h2, h3 {
    color: #880e4f !important;
}

/* Force Input Background dan Text Color */
div[data-baseweb="select"] > div, 
div[data-baseweb="input"] > div,
input {
    background-color: #ffffff !important;
    color: #4a0e17 !important;
    border: 1.5px solid #f48fb1 !important;
}

/* Fix untuk File Uploader Chip Text */
[data-testid="stFileUploader"] [data-testid="stText"] {
    color: #4a0e17 !important;
}
[data-testid="stFileUploader"] span {
    color: #4a0e17 !important;
}

/* Tombol */
.stButton>button {
    background: linear-gradient(135deg, #ff69b4, #e91e63) !important;
    color: white !important;
    border-radius: 25px !important;
}

/* Fix teks gelap di markdown */
.stMarkdown p, .stMarkdown div, label {
    color: #4a0e17 !important;
}
</style>
""", unsafe_allow_html=True)

def clean_currency(text):
    if not text: return 0.0
    cleaned = str(text).strip().replace('.', '').replace(',', '.')
    cleaned = re.sub(r'[\.,]00$', '', cleaned)
    match = re.search(r'^-?\d+(\.\d+)?', cleaned)
    return float(match.group(0)) if match else 0.0

def extract_data_from_pdf(pdf_file, password=None):
    all_transactions = []
    saldo_awal = 0.0
    
    try:
        kwargs = {'password': password} if password else {}
        with pdfplumber.open(pdf_file, **kwargs) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    # Deteksi saldo awal dari teks jika ada
                    if "saldo awal" in line.lower():
                        nums = re.findall(r'[\d\.,]+', line)
                        if nums: saldo_awal = clean_currency(nums[-1])
                    
                    # Regex transaksi: tanggal DD/MM
                    if re.match(r'^\d{2}/\d{2}', line):
                        all_transactions.append(line)

        final_rows = [{"Tanggal": "-", "Keterangan": "SALDO AWAL", "Nilai Debit": "", "Nilai Kredit": "", "Saldo": f"{int(saldo_awal):,}".replace(',', '.')}]
        running_bal = saldo_awal
        
        for trx in all_transactions:
            # Sederhana: Pisah berdasarkan spasi besar
            parts = trx.split()
            date = parts[0]
            # Logika pisah Debit/Kredit akan di sini...
            # (Logic disederhanakan untuk contoh)
            final_rows.append({"Tanggal": date, "Keterangan": " ".join(parts[1:]), "Nilai Debit": "0", "Nilai Kredit": "0", "Saldo": "0"})
            
        return pd.DataFrame(final_rows), None
    except Exception as e:
        return None, str(e)

st.title("🌸 Convert Rekening Koran PDF 🌸")
uploaded_file = st.file_uploader("Unggah File PDF", type="pdf")
if st.button("🚀 Proses Konversi"):
    if uploaded_file:
        df, err = extract_data_from_pdf(uploaded_file)
        if df is not None:
            st.dataframe(df, use_container_width=True)
        else:
            st.error(err)
