import streamlit as st
import pandas as pd
import pdfplumber
import io

st.set_page_config(
    page_title="Sedot Rekening Koran",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

def extract_data_from_pdf(pdf_file, bank_choice, password=None):
    """
    Fungsi inti untuk membaca PDF dan mengubahnya menjadi DataFrame Pandas.
    Termasuk sistem pembersihan data otomatis.
    """
    all_data = []
    
    try:
        # Membuka PDF, menggunakan password jika diberikan
        kwargs = {}
        if password:
            kwargs['password'] = password
            
        with pdfplumber.open(pdf_file, **kwargs) as pdf:
            for page_num, page in enumerate(pdf.pages):
                
                # PERBAIKAN UTAMA: Gunakan strategi "text" sebagai PRIORITAS.
                # Karena mayoritas rekening koran (seperti BCA, Mandiri) borderless.
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 3,
                })
                
                # Fallback: Jika "text" gagal total, coba pakai "lines" (garis)
                if not tables:
                     tables = page.extract_tables(table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                    })

                if tables:
                    for table in tables:
                        for row in table:
                            # 1. CLEANING: Rapatkan data ke kiri (hilangkan None di tengah)
                            # Ini mengatasi masalah "staircase effect" / tangga
                            cleaned_row = [str(cell).strip() for cell in row if cell is not None and str(cell).strip() != '']
                            
                            # Jika baris tidak kosong setelah dibersihkan
                            if cleaned_row:
                                # 2. FILTERING HEADER: Abaikan baris yang berisi kata-kata header bawaan PDF
                                # Kita gabungkan semua teks di baris menjadi satu string (lowercase) untuk dicek
                                row_text = "".join(cleaned_row).lower()
                                
                                # Daftar kata kunci header yang sering muncul dan mengganggu
                                header_keywords = ["tanggal", "keterangan", "saldo", "mutasi", "cabang", "tarikan", "setoran"]
                                
                                # Jika baris ini BUKAN header, masukkan ke all_data
                                if not any(keyword in row_text for keyword in header_keywords):
                                     all_data.append(cleaned_row)
                                     
        if not all_data:
             return None, "Tidak ada data transaksi yang ditemukan. Pastikan format PDF benar atau coba cek manual filenya."

        # Membuat DataFrame dari list data yang sudah bersih
        df = pd.DataFrame(all_data)
        
        # 3. INJECT HEADER RAPI: Menyesuaikan jumlah kolom hasil ekstraksi
        num_columns = len(df.columns)
        
        # Contoh sederhana penetapan header (Bisa disesuaikan lebih lanjut per bank nanti)
        if num_columns == 4:
            df.columns = ["Tanggal", "Keterangan", "Mutasi", "Saldo"]
        elif num_columns == 5:
             df.columns = ["Tanggal", "Keterangan", "Cabang", "Mutasi", "Saldo"]
        elif num_columns == 6:
             df.columns = ["Tanggal", "Keterangan", "Cabang", "Debet", "Kredit", "Saldo"]
        else:
            # Jika jumlah kolom aneh, biarkan pakai angka, tapi beri prefix "Kolom_"
            df.columns = [f"Kolom_{i}" for i in range(num_columns)]

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
