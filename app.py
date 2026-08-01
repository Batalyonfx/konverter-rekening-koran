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

# --- CSS INJECTION AESTHETIC PINK FLORAL (ENHANCED CONTRAST) ---
st.markdown("""
<style>
/* Background app dengan warna pink pastel lembut dan pola bunga halus */
[data-testid="stAppViewContainer"] {
    background-color: #fff0f3;
    background-image: url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23f48fb1' fill-opacity='0.18'%3E%3Cpath d='M40 30c-2.2 0-4 1.8-4 4 0 2.2 1.8 4 4 4s4-1.8 4-4c0-2.2-1.8-4-4-4zm0-10c-3.3 0-6 2.7-6 6s2.7 6 6 6 6-2.7 6-6-2.7-6-6-6zm-10 10c0-3.3-2.7-6-6-6s-6 2.7-6 6 2.7 6 6 6 6-2.7 6-6zm20 0c0-3.3 2.7-6 6-6s6 2.7 6 6-2.7 6-6 6-6-2.7-6-6zm-10 10c-3.3 0-6 2.7-6 6s2.7 6 6 6 6-2.7 6-6-2.7-6-6-6z'/%3E%3C/g%3E%3C/svg%3E");
}

/* Sidebar estetik pink */
[data-testid="stSidebar"] {
    background-color: #ffe6eb !important;
    border-right: 2px solid #f8bbd0;
}

/* Judul Heading dengan warna Burgundy/Deep Pink */
h1, h2, h3 {
    color: #880e4f !important;
    font-family: 'Georgia', serif;
    font-weight: 700;
}

/* Semua teks biasa, paragraf, label, dan radio button agar terlihat tegas & jelas */
p, span, label, div, .stMarkdown {
    color: #4a0e17 !important;
    font-weight: 500;
}

/* Teks Radio Button di Sidebar */
[data-testid="stRadio"] label p {
    color: #5c061c !important;
    font-size: 15px !important;
    font-weight: 600 !important;
}

/* Styling Input Box, Selectbox, & Text Area agar serasi (Background putih bersih) */
div[data-baseweb="select"] > div, 
div[data-baseweb="input"] > div,
input {
    background-color: #ffffff !important;
    color: #4a0e17 !important;
    border-radius: 12px !important;
    border: 1.5px solid #f48fb1 !important;
}

/* File Uploader styling */
[data-testid="stFileUploadDropzone"] {
    background-color: #ffffff !important;
    border: 2px dashed #f06292 !important;
    border-radius: 15px !important;
}
[data-testid="stFileUploadDropzone"] span, 
[data-testid="stFileUploadDropzone"] div {
    color: #880e4f !important;
}

/* Style tombol utama menjadi pink mencolok dengan efek hover */
.stButton>button {
    background: linear-gradient(135deg, #ff69b4, #e91e63) !important;
    color: white !important;
    font-weight: bold !important;
    font-size: 16px !important;
    border-radius: 25px !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(233, 30, 99, 0.3) !important;
    transition: all 0.3s ease !important;
    padding: 10px 24px !important;
}
.stButton>button:hover {
    background: linear-gradient(135deg, #e91e63, #c2185b) !important;
    box-shadow: 0 6px 16px rgba(194, 24, 91, 0.4) !important;
    transform: translateY(-2px);
}
.stButton>button p {
    color: white !important;
}

/* Style alert/warning box agar kontrasnya bagus */
[data-testid="stAlert"] {
    background-color: #fff3f5 !important;
    border: 1px solid #f48fb1 !important;
    border-radius: 12px !important;
}
[data-testid="stAlert"] p {
    color: #880e4f !important;
}

/* Style container form dengan efek Glassmorphism */
div[data-testid="stVerticalBlock"] > div[style*="border"] {
    background: rgba(255, 255, 255, 0.75);
    backdrop-filter: blur(8px);
    border: 2px solid #f8bbd0 !important;
    border-radius: 18px !important;
    padding: 20px !important;
    box-shadow: 0 8px 20px rgba(244, 143, 177, 0.15) !important;
}

/* Header Streamlit transparan */
[data-testid="stHeader"] {
    background: transparent;
}
</style>
""", unsafe_allow_html=True)
# -------------------------------------------

def clean_currency(text):
    """
    Membersihkan teks nominal uang, membuang desimal .00 atau ,00 di akhir
    serta menghapus karakter non-angka agar siap dihitung/diformat murni.
    """
    if not text:
        return 0.0
    
    # Hapus spasi berlebih
    cleaned = str(text).strip()
    
    # Deteksi dan buang akhiran desimal .00 atau ,00
    cleaned = re.sub(r'[\.,]00$', '', cleaned)
    
    # Pengkondisian pemisah ribuan
    if '.' in cleaned and ',' in cleaned:
        cleaned = cleaned.replace('.', '').replace(',', '.')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '')
    elif '.' in cleaned:
        # Jika ada titik tapi bukan desimal ribuan biasa
        if len(cleaned.split('.')[-1]) == 3:
            cleaned = cleaned.replace('.', '')
            
    # Ambil angka dan tanda minus jika ada
    match = re.search(r'^-?\d+(\.\d+)?', cleaned)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return 0.0
    return 0.0

def extract_data_from_pdf(pdf_file, bank_choice, password=None):
    """
    Fungsi membaca PDF dengan pendekatan Text-Regex (Line by Line).
    Sangat ampuh untuk mengatasi tabel borderless pada rekening koran (BCA/Mandiri).
    """
    all_transactions = []
    
    try:
        kwargs = {}
        if password:
            kwargs['password'] = password
            
        with pdfplumber.open(pdf_file, **kwargs) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text: 
                    continue
                    
                lines = text.split('\n')
                current_trx = None
                
                for line in lines:
                    line = line.strip()
                    if not line: 
                        continue
                        
                    lower_line = line.lower()
                    if any(keyword in lower_line for keyword in [
                        "halaman", "lanjutan", "saldo awal", "mutasi", "keterangan", 
                        "cabang", "tanggal", "bandung", "indonesia", "rekening ini", "mata uang"
                    ]):
                        continue
                        
                    date_match = re.match(r'^(\d{2}[/-]\d{2}(?:[/-]\d{2,4})?)\s+(.*)', line)
                    
                    if date_match:
                        if current_trx:
                            all_transactions.append(current_trx)
                            
                        date_str = date_match.group(1)
                        rest_of_line = date_match.group(2)
                        
                        parts = rest_of_line.split()
                        keterangan_parts = []
                        nominal_parts = []
                        
                        for part in reversed(parts):
                            is_money = re.search(r'\d', part) and ('.' in part or ',' in part)
                            is_code = part in ['DB', 'CR', 'D', 'C', 'Dr', 'Cr']
                            
                            if is_money or is_code:
                                nominal_parts.insert(0, part)
                            else:
                                keterangan_parts.insert(0, part)
                                break
                                
                        idx_sisa = len(parts) - len(nominal_parts) - len(keterangan_parts)
                        keterangan_fix = " ".join(parts[:idx_sisa] + keterangan_parts)
                        nominal_fix = " ".join(nominal_parts)
                        
                        current_trx = {
                            "Tanggal": date_str,
                            "Keterangan": keterangan_fix,
                            "Mutasi & Saldo Raw": nominal_fix
                        }
                    elif current_trx:
                        current_trx["Keterangan"] += "\n" + line
                        
                if current_trx:
                    all_transactions.append(current_trx)

        if not all_transactions:
             return None, "Tidak ada data transaksi yang ditemukan. Pastikan format PDF benar (bukan hasil scan)."

        final_transactions = []
        running_balance = 0.0
        is_first_row = True
        
        for trx in all_transactions:
            tanggal = trx["Tanggal"]
            keterangan = trx["Keterangan"]
            raw_mutasi_saldo = trx["Mutasi & Saldo Raw"]
            
            debit_val = 0.0
            kredit_val = 0.0
            
            parts = raw_mutasi_saldo.split()
            numbers = []
            is_db = False
            is_cr = False
            
            for p in parts:
                if p in ['DB', 'D', 'Dr']:
                    is_db = True
                elif p in ['CR', 'C', 'Cr']:
                    is_cr = True
                elif re.search(r'\d', p) and ('.' in p or ',' in p):
                    numbers.append(p)
                    
            if len(numbers) >= 1:
                mutasi_str = numbers[0]
                val = clean_currency(mutasi_str)
                
                if is_db:
                    debit_val = val
                elif is_cr:
                    kredit_val = val
                else:
                    kredit_val = val
                    
            # Tentukan Saldo Awal jika ini baris pertama
            if is_first_row:
                if len(numbers) >= 2:
                    running_balance = clean_currency(numbers[-1])
                else:
                    running_balance = 0.0
                is_first_row = False
            else:
                running_balance = running_balance + kredit_val - debit_val

            # Format angka menjadi integer bulat tanpa desimal (misal 4.000)
            debit_str = f"{int(debit_val):,}".replace(',', '.') if debit_val > 0 else ""
            kredit_str = f"{int(kredit_val):,}".replace(',', '.') if kredit_val > 0 else ""
            saldo_str = f"{int(running_balance):,}".replace(',', '.')
            
            final_transactions.append({
                "Tanggal": tanggal,
                "Keterangan": keterangan.strip(),
                "Nilai Debit": debit_str,
                "Nilai Kredit": kredit_str,
                "Saldo": saldo_str
            })

        df = pd.DataFrame(final_transactions)
        return df, None

    except pdfplumber.password.PasswordError:
         return None, "Password PDF salah atau PDF terkunci namun password tidak dimasukkan."
    except Exception as e:
        return None, f"Terjadi kesalahan saat memproses file: {e}"

def convert_df_to_excel(df):
    """
    Mengonversi DataFrame ke format Excel (BytesIO) agar siap di-download.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rekening_Koran')
        
        worksheet = writer.sheets['Rekening_Koran']
        for idx, col in enumerate(df):
            series = df[col]
            max_len = max((
                series.astype(str).map(len).max(),
                len(str(series.name))
            )) + 2
            worksheet.set_column(idx, idx, max_len)
            
    return output.getvalue()

st.sidebar.title("🌸 Navigasi")
menu = st.sidebar.radio(
    "Pilih Menu",
    ["🌷 Convert Rekening", "📖 Pilih Sampel / Panduan", "💌 Tentang"]
)

if menu == "🌷 Convert Rekening":
    st.title("🌸 Convert Rekening Koran PDF 🌸")
    st.markdown("Aplikasi web estetik untuk mengubah file PDF e-Statement / Rekening Koran menjadi format Excel (.xlsx) dengan mudah. 🌺✨")
    
    st.warning("🔒 **Privasi Terjamin:** Data Tidak Akan Disimpan Dalam Aplikasi Setelah Selesai Konversi.")

    with st.container(border=True):
        st.subheader("Pengaturan Ekstraksi")
        col1, col2 = st.columns(2)
        
        with col1:
            bank_choice = st.selectbox(
                "Pilih Bank (Penting untuk penyesuaian format):",
                ["BCA", "Bank Mandiri", "BNI", "BRI", "BSI", "Bank Lainnya..."]
            )
            
        with col2:
            pdf_password = st.text_input(
                "Password PDF (Jika file terkunci):", 
                type="password",
                help="Biasanya e-statement menggunakan tanggal lahir (misal: ddmmyyyy atau yyyymmdd) sebagai password."
            )

        uploaded_file = st.file_uploader("Unggah File PDF Rekening Koran", type="pdf")
        
        process_btn = st.button("🚀 Proses Konversi (Sedot Data)", type="primary", use_container_width=True)

    if process_btn:
        if uploaded_file is not None:
            with st.spinner('Sedang mengekstrak data dari PDF... Mohon tunggu...'):
                df, error_msg = extract_data_from_pdf(uploaded_file, bank_choice, pdf_password)
                
                if error_msg:
                    st.error(error_msg)
                elif df is not None:
                    st.success("Berhasil mengekstrak data!")
                    
                    st.subheader("Preview Data")
                    st.dataframe(df, use_container_width=True)
                    
                    excel_data = convert_df_to_excel(df)
                    st.download_button(
                        label="📥 Download File Excel (.xlsx)",
                        data=excel_data,
                        file_name=f"Hasil_Sedot_{bank_choice}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
        else:
             st.warning("⚠️ Silakan unggah file PDF terlebih dahulu sebelum memproses.")

elif menu == "📖 Pilih Sampel / Panduan":
    st.title("📖 Panduan Penggunaan")
    st.markdown("""
    ### Cara Menggunakan Aplikasi Ini
    1. Siapkan file e-statement (Rekening Koran) Anda dalam format **PDF**.
    2. Pastikan Anda mengetahui **Password** file tersebut (jika ada).
    3. Kembali ke menu utama **"Convert Rekening"**.
    4. Pilih nama Bank yang sesuai.
    5. Masukkan password PDF jika ada.
    6. Unggah file PDF Anda.
    7. Klik **Proses Konversi** dan tunggu hingga tabel muncul.
    8. Klik **Download File Excel** untuk menyimpan hasilnya.
    """)

elif menu == "💌 Tentang":
    st.title("Tentang Aplikasi 💮")
    
    st.markdown("""
    <div style='text-align: center; margin-top: 50px; padding: 40px; background-color: rgba(255, 255, 255, 0.8); border-radius: 20px; border: 2px solid #f8bbd0; box-shadow: 0 8px 20px rgba(244, 143, 177, 0.2);'>
        <h2 style='color: #880e4f; font-size: 28px; font-weight: bold;'>Dibuat dengan ❤️ oleh Griffin dan Septiana 🌷</h2>
    </div>
    """, unsafe_allow_html=True)
