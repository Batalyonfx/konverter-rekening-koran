import streamlit as st
import pandas as pd
import pdfplumber
import re
import io

st.set_page_config(
    page_title="Convert Rekening Koran PDF",
    page_icon="🌸",
    layout="wide"
)

st.markdown("""
<style>
/* Background bunga sakura */
[data-testid="stAppViewContainer"] {
    background-color: #fff0f5;
    background-image: radial-gradient(#f48fb1 1px, transparent 1px);
    background-size: 40px 40px;
}

/* Teks dan judul */
h1, h2, h3, p, label { color: #880e4f !important; }

/* Input area */
div[data-baseweb="select"] > div, 
div[data-baseweb="input"] > div,
[data-testid="stFileUploadDropzone"] {
    background-color: #ffffff !important;
    border: 1.5px solid #f48fb1 !important;
}

/* Fix teks di dalam input */
input, div[data-baseweb="select"] span { color: #4a0e17 !important; }

/* Tombol */
.stButton>button {
    background: linear-gradient(135deg, #ff69b4, #e91e63) !important;
    color: white !important;
    border-radius: 25px !important;
    border: none;
}
</style>
""", unsafe_allow_html=True)

def clean_currency(text):
    if not text: return 0.0
    # Hapus koma/titik ribuan, ambil angka terakhir
    text = str(text).replace(',', '').replace('.', '')
    match = re.search(r'\d+', text)
    return float(match.group(0)) if match else 0.0

def extract_data_from_pdf(pdf_file, password=None):
    transactions = []
    saldo_awal = 0.0
    try:
        with pdfplumber.open(pdf_file, password=password) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                lines = text.split('\n')
                for line in lines:
                    # Deteksi saldo awal
                    if "saldo awal" in line.lower():
                        nums = re.findall(r'[\d\.,]+', line)
                        if nums: saldo_awal = clean_currency(nums[-1])
                    
                    # Deteksi baris transaksi (dimulai tanggal)
                    if re.match(r'^\d{2}/\d{2}', line):
                        parts = line.split()
                        date = parts[0]
                        amount_str = parts[-1]
                        
                        # Sederhana: deteksi DB/CR
                        is_debit = "DB" in line
                        val = clean_currency(amount_str)
                        
                        transactions.append({
                            "Tanggal": date,
                            "Keterangan": " ".join(parts[1:-1]),
                            "Nilai Debit": val if is_debit else 0,
                            "Nilai Kredit": 0 if is_debit else val,
                            "Saldo": 0 # Akan dihitung nanti
                        })
        
        df = pd.DataFrame(transactions)
        if not df.empty:
            # Hitung saldo berjalan
            curr_saldo = saldo_awal
            for i, row in df.iterrows():
                curr_saldo = curr_saldo + row["Nilai Kredit"] - row["Nilai Debit"]
                df.at[i, "Saldo"] = curr_saldo
            
            # Sisipkan baris saldo awal di paling atas
            awal_row = pd.DataFrame([{"Tanggal": "-", "Keterangan": "SALDO AWAL", "Nilai Debit": 0, "Nilai Kredit": 0, "Saldo": saldo_awal}])
            df = pd.concat([awal_row, df], ignore_index=True)
            
        return df, None
    except Exception as e:
        return None, str(e)

st.title("🌸 Convert Rekening Koran PDF 🌸")
uploaded_file = st.file_uploader("Unggah File PDF", type="pdf")
password = st.text_input("Password (jika ada)", type="password")

if st.button("🚀 Proses Konversi"):
    if uploaded_file:
        df, err = extract_data_from_pdf(uploaded_file, password)
        if df is not None:
            st.success("Berhasil!")
            st.dataframe(df, use_container_width=True)
        else:
            st.error(f"Error: {err}")
