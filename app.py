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

# --- CSS INJECTION AESTHETIC PINK FLORAL ---
st.markdown("""
<style>
/* Background app dengan warna pink pastel dan pattern bunga/kelopak tipis */
[data-testid="stAppViewContainer"] {
    background-color: #fff0f5; /* LavenderBlush */
    background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffb6c1' fill-opacity='0.3'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}

/* Sidebar estetik pink */
[data-testid="stSidebar"] {
    background-color: #ffe4e1; /* MistyRose */
    border-right: 3px solid #ffb6c1;
}

/* Mengubah warna teks judul menjadi pink gelap yang elegan */
h1, h2, h3 {
    color: #c2185b !important;
    font-family: 'Georgia', serif;
}

/* Style tombol utama menjadi pink mencolok dengan efek hover */
.stButton>button {
    background-color: #ff69b4 !important; /* HotPink */
    color: white !important;
    border-radius: 30px !important;
    border: none !important;
    box-shadow: 0 4px 6px rgba(255, 105, 180, 0.4) !important;
    transition: all 0.3s ease;
}
.stButton>button:hover {
    background-color: #ff1493 !important; /* DeepPink */
    box-shadow: 0 6px 12px rgba(255, 20, 147, 0.5) !important;
    transform: translateY(-2px);
}

/* Style kotak kontainer agar tampak transparan elegan (Glassmorphism ringan) */
div[data-testid="stVerticalBlock"] > div[style*="border"] {
    background: rgba(255, 255, 255, 0.6);
    backdrop-filter: blur(5px);
    border: 2px solid #ffb6c1 !important;
    border-radius: 15px !important;
}

/* Mengganti header default Streamlit agar transparan */
[data-testid="stHeader"] {
    background: transparent;
}
</style>
""", unsafe_allow_html=True)
# -------------------------------------------

def clean_currency(text):
    """
    Fungsi inti membaca PDF dengan pendekatan Text-Regex (Line by Line).
    Sangat ampuh untuk mengatasi tabel borderless, teks berantakan, 
    dan spasi berlebih pada rekening koran (BCA/Mandiri).
    """
    all_transactions = []
    
    try:
        kwargs = {}
        if password:
            kwargs['password'] = password
            
        with pdfplumber.open(pdf_file, **kwargs) as pdf:
            for page_num, page in enumerate(pdf.pages):
                
                # Ekstrak seluruh teks mentah di halaman tersebut
                text = page.extract_text()
                if not text: continue
                    
                lines = text.split('\n')
                current_trx = None
                
                for line in lines:
                    line = line.strip()
                    if not line: continue
                        
                    # 1. FILTERING: Abaikan baris header/footer (seperti alamat, "BANDUNG 4", "INDONESIA")
                    lower_line = line.lower()
                    if any(keyword in lower_line for keyword in [
                        "halaman", "lanjutan", "saldo", "mutasi", "keterangan", 
                        "cabang", "tanggal", "bandung", "indonesia", "rekening ini", "mata uang"
                    ]):
                        continue
                        
                    # 2. DETEKSI TRANSAKSI BARU: Cek apakah baris diawali TANGGAL (Pola: DD/MM atau DD/MM/YYYY)
                    date_match = re.match(r'^(\d{2}[/-]\d{2}(?:[/-]\d{2,4})?)\s+(.*)', line)
                    
                    if date_match:
                        # Simpan transaksi sebelumnya (jika ada) sebelum memulai yang baru
                        if current_trx:
                            all_transactions.append(current_trx)
                            
                        date_str = date_match.group(1)
                        rest_of_line = date_match.group(2)
                        
                        # 3. PEMISAHAN KETERANGAN & NOMINAL (Cari angka uang dari belakang kalimat)
                        parts = rest_of_line.split()
                        keterangan_parts = []
                        nominal_parts = []
                        
                        for part in reversed(parts):
                            # Deteksi apakah ini angka nominal (ada digit & titik/koma) atau kode mutasi (DB/CR/dll)
                            is_money = re.search(r'\d', part) and ('.' in part or ',' in part)
                            is_code = part in ['DB', 'CR', 'D', 'C', 'Dr', 'Cr']
                            
                            if is_money or is_code:
                                nominal_parts.insert(0, part)
                            else:
                                keterangan_parts.insert(0, part)
                                break # Berhenti ketika ketemu teks huruf biasa
                                
                        # Gabungkan semua sisa part menjadi kalimat keterangan yang rapi
                        idx_sisa = len(parts) - len(nominal_parts) - len(keterangan_parts)
                        keterangan_fix = " ".join(parts[:idx_sisa] + keterangan_parts)
                        nominal_fix = " ".join(nominal_parts)
                        
                        current_trx = {
                            "Tanggal": date_str,
                            "Keterangan": keterangan_fix,
                            "Mutasi & Saldo": nominal_fix
                        }
                    elif current_trx:
                        # 4. GABUNGKAN BARIS MULTI-LINE: Jika tidak diawali tanggal, berarti ini lanjutan Keterangan
                        current_trx["Keterangan"] += "\n" + line
                        
                # Simpan transaksi terakhir yang terbaca di halaman tersebut
                if current_trx:
                    all_transactions.append(current_trx)

        if not all_transactions:
             return None, "Tidak ada data transaksi yang ditemukan. Pastikan format PDF benar (bukan hasil scan)."

        # 5. POST-PROCESSING: Memisahkan Kolom Mutasi & Saldo menjadi Debit, Kredit, Saldo
        final_transactions = []
        for trx in all_transactions:
            tanggal = trx["Tanggal"]
            keterangan = trx["Keterangan"]
            mutasi_saldo = trx["Mutasi & Saldo"]
            
            debit = ""
            kredit = ""
            saldo = ""
            
            parts = mutasi_saldo.split()
            
            # Mengelompokkan angka dan kode (DB/CR)
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
                    
            # Menentukan angka Mutasi (Debit/Kredit) dan angka Saldo akhir
            if len(numbers) >= 2:
                mutasi = numbers[0]
                saldo = numbers[-1]
            elif len(numbers) == 1:
                mutasi = numbers[0]
                
                # Coba cari saldo yang mungkin jatuh ke baris terakhir Keterangan
                ket_lines = keterangan.split('\n')
                last_ket = ket_lines[-1].strip() if ket_lines else ""
                
                # Cek apakah baris terakhir Keterangan murni berupa angka saldo
                if re.match(r'^-?[\d\.,]+-?$', last_ket) and ('.' in last_ket or ',' in last_ket):
                    saldo = last_ket
                    keterangan = "\n".join(ket_lines[:-1]) # Hapus saldo dari keterangan agar bersih
            else:
                mutasi = ""
                
            # Logika Penempatan Debit atau Kredit
            if is_db:
                debit = mutasi
            elif is_cr:
                kredit = mutasi
            elif mutasi: 
                # Jika tidak ada kode DB/CR (biasanya terjadi di BCA), defaultnya adalah uang masuk (Kredit)
                kredit = mutasi
                
            final_transactions.append({
                "Tanggal": tanggal,
                "Keterangan": keterangan.strip(),
                "Nilai Debit": debit,
                "Nilai Kredit": kredit,
                "Saldo": saldo
            })

        # Buat DataFrame dari hasil yang sudah dipisah kolomnya
        df = pd.DataFrame(final_transactions)
        return df, None

    except pdfplumber.password.PasswordError:
         return None, "Password PDF salah atau PDF terkunci namun password tidak dimasukkan."
    except Exception as e:
        return None, f"Terjadi kesalahan saat memproses file: {e}"

def convert_df_to_excel(df):
    """
    Mengonversi DataFrame ke format Excel (BytesIO) agar bisa di-download.
    """
    output = io.BytesIO()
    # Menggunakan engine xlsxwriter
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rekening_Koran')
        
        # Auto-adjust column width untuk Excel yang lebih rapi
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

    # Container untuk input form
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

    # Logika ketika tombol proses ditekan
    if process_btn:
        if uploaded_file is not None:
            with st.spinner('Sedang mengekstrak data dari PDF... Mohon tunggu...'):
                
                # Panggil fungsi ekstraksi
                df, error_msg = extract_data_from_pdf(uploaded_file, bank_choice, pdf_password)
                
                if error_msg:
                    st.error(error_msg)
                elif df is not None:
                    st.success("Berhasil mengekstrak data!")
                    
                    st.subheader("Preview Data")
                    st.dataframe(df, use_container_width=True)
                    
                    # Tombol Download
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

elif menu == "▶︎ Pilih Sampel / Panduan":
    st.title("📖 Panduan Penggunaan")
    st.markdown("""
    ### Cara Menggunakan Aplikasi Ini
    1. Siapkan file e-statement (Rekening Koran) Anda dalam format **PDF**.
    2. Pastikan Anda mengetahui **Password** file tersebut (jika ada).
    3. Kembali ke menu utama **"Sedot Rekening Koran"**.
    4. Pilih nama Bank yang sesuai.
    5. Masukkan password PDF.
    6. Unggah file PDF Anda.
    7. Klik **Proses Konversi** dan tunggu hingga tabel muncul.
    8. Klik **Download File Excel** untuk menyimpan hasilnya.
    
    ### Catatan Penting:
    - Aplikasi ini dirancang untuk membaca **dokumen PDF asli (e-statement)** hasil download dari internet banking/email, BUKAN hasil scan atau foto (gambar).
    - Format tabel setiap bank mungkin berbeda. Jika hasil ekstraksi kurang rapi, Anda mungkin perlu melakukan sedikit penyesuaian manual di dalam file Excel-nya.
    """)

elif menu == "💌 Tentang":
    st.title("Tentang Aplikasi 💮")
    
    st.markdown("""
    <div style='text-align: center; margin-top: 50px; padding: 30px; background-color: rgba(255, 182, 193, 0.4); border-radius: 15px; border: 2px solid #ffb6c1; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>
        <h2 style='color: #c2185b;'>Dibuat dengan ❤️ oleh Griffin dan Septiana 🌷</h2>
    </div>
    """, unsafe_allow_html=True)
