import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(
    page_title="Sedot Rekening Koran",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

def extract_data_from_pdf(pdf_file, bank_choice, password=None):
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

        # Buat DataFrame dari hasil yang sudah rapi
        df = pd.DataFrame(all_transactions)
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

st.sidebar.title("Navigasi")
menu = st.sidebar.radio(
    "Pilih Menu",
    ["▶︎ Sedot Rekening Koran", "▶︎ Pilih Sampel / Panduan", "▶︎ Tentang"]
)

if menu == "▶︎ Sedot Rekening Koran":
    st.title("🏦 Rekening Koran Scrape Tools")
    st.markdown("Aplikasi web untuk mengubah file PDF e-Statement / Rekening Koran menjadi format Excel (.xlsx) dengan mudah.")
    
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

elif menu == "▶︎ Tentang":
    st.title("Tentang Aplikasi")
    
    st.markdown("""
    <div style='text-align: center; margin-top: 50px; padding: 30px; background-color: #f0f2f6; border-radius: 10px;'>
        <h2>Dibuat dengan ❤️ oleh Griffin dan Septiana</h2>
    </div>
    """, unsafe_allow_html=True)
