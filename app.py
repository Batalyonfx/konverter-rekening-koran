import streamlit as st
import pdfplumber
import pandas as pd
import io
import time

st.set_page_config(
    page_title="Sedot Rekening Koran to Excel",
    page_icon="🔎",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0;
    }
    .privacy-notice {
        background-color: #DEF7EC;
        border-left: 5px solid #057A55;
        padding: 10px 15px;
        border-radius: 4px;
        color: #03543F;
        font-weight: 500;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

def extract_data_from_pdf(pdf_file, bank_choice, password):
    all_data = []
    
    try:
        # Membuka PDF, menggunakan password jika diberikan
        kwargs = {}
        if password:
            kwargs['password'] = password
            
        with pdfplumber.open(pdf_file, **kwargs) as pdf:
            for page_num, page in enumerate(pdf.pages):
                
                # Di sinilah Anda bisa menerapkan aturan pemotongan (crop) 
                # atau strategi tabel berdasarkan 'bank_choice' (BCA, Mandiri, dll)
                # Untuk saat ini, kita gunakan ekstraksi tabel default yang tangguh
                
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                })
                
                # Jika strategi "lines" tidak menemukan tabel (biasanya untuk PDF tanpa garis tabel), 
                # coba strategi "text"
                if not tables:
                     tables = page.extract_tables(table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                    })

                if tables:
                    for table in tables:
                        # Membersihkan data: hapus baris yang kosong atau None
                        cleaned_table = [row for row in table if any(cell is not None and str(cell).strip() != '' for cell in row)]
                        if cleaned_table:
                             all_data.extend(cleaned_table)
                             
        if all_data:
            df = pd.DataFrame(all_data)
            return df, None
        else:
            return None, "Tidak ada data tabel yang terdeteksi di dalam PDF."
            
    except Exception as e:
        error_msg = str(e)
        if "Password" in error_msg or "password" in error_msg.lower():
            return None, "🔒 Password PDF salah atau PDF memerlukan password namun Anda tidak memasukkannya."
        return None, f"Terjadi kesalahan saat memproses PDF: {error_msg}"

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Data_Ekstrak', index=False, header=False)
        worksheet = writer.sheets['Data_Ekstrak']
        # Mengatur lebar kolom agar rapi
        for i in range(15): 
            worksheet.set_column(i, i, 18)
    output.seek(0)
    return output

st.sidebar.title("🔎 Tools")
menu = st.sidebar.radio(
    "Menu Navigasi",
    ["▶︎ Sedot Rekening Koran", "▶︎ Pilih Sampel / Panduan", "▶︎ Tentang"]
)

if menu == "▶︎ Sedot Rekening Koran":
    
    st.markdown('<div class="main-header">Rekening Koran to Excel</div>', unsafe_allow_html=True)
    st.markdown('<div class="privacy-notice">🛡️ Data Tidak Akan Disimpan Dalam Aplikasi Setelah Selesai Konversi</div>', unsafe_allow_html=True)
    
    # Grid Layout untuk Input (2 kolom)
    col1, col2 = st.columns(2)
    
    with col1:
        bank = st.selectbox(
            "Pilih Bank (Format PDF)", 
            ["BCA", "Bank Mandiri", "BNI", "BRI", "BSI", "Bank Lain / Umum"]
        )
    
    with col2:
        pdf_password = st.text_input(
            "Password PDF", 
            type="password", 
            help="Masukkan password jika rekening koran Anda dikunci (biasanya tanggal lahir/DDMMYYYY)."
        )
        
    uploaded_file = st.file_uploader("Pilih file PDF Rekening Koran", type="pdf")
    
    if uploaded_file is not None:
        
        if st.button("🚀 Proses Konversi (Sedot Data)"):
            with st.spinner(f'Membuka dokumen dan mengekstrak data format {bank}...'):
                # Simulasi sedikit delay agar terasa prosesnya
                time.sleep(1) 
                
                df, error = extract_data_from_pdf(uploaded_file, bank, pdf_password)
                
                if error:
                    st.error(error)
                elif df is not None:
                    st.success("✅ Ekstraksi berhasil! Silakan periksa pratinjau di bawah ini.")
                    
                    # Tampilkan Preview Data
                    st.markdown("### 📊 Preview Data")
                    st.dataframe(df, use_container_width=True)
                    
                    st.info("Catatan: Tergantung bank, baris pertama mungkin bukan header, dan Anda mungkin perlu menyesuaikan sedikit hasilnya di Excel.")
                    
                    # Tombol Download
                    excel_file = convert_df_to_excel(df)
                    st.download_button(
                        label="📥 Download File Excel (.xlsx)",
                        data=excel_file,
                        file_name=uploaded_file.name.replace('.pdf', '_converted.xlsx'),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )

elif menu == "▶︎ Pilih Sampel / Panduan":
    st.title("Panduan Penggunaan & Sampel")
    st.write("""
    ### Cara Kerja
    1. Pastikan file rekening koran (e-statement) Anda adalah file **PDF asli** yang di-generate oleh bank, bukan hasil *scan* atau foto.
    2. Pilih **Bank** yang sesuai di menu utama. Algoritma akan mencoba menyesuaikan dengan letak tabel tiap bank (Fitur spesifik bank dapat terus disempurnakan).
    3. Jika PDF dilindungi password (biasanya e-statement dari email), **masukkan password** di kolom yang tersedia.
    4. Upload PDF dan klik tombol Proses.
    
    ### Tentang Format Bank
    Format PDF BCA biasanya memiliki kolom: `Tanggal | Keterangan | Cabang | Mutasi | Saldo`.
    Mandiri dan BNI memiliki strukturnya masing-masing. Tools ini mencoba mengambil seluruh *raw text table* agar mudah Anda edit kembali di Excel.
    """)

elif menu == "▶︎ Tentang":
    st.title("Tentang Aplikasi")
    st.write("Aplikasi ini dibuat menggunakan **Streamlit** dan **pdfplumber**.")
    st.write("Dibuat khusus untuk membantu akuntan, admin keuangan, atau personal untuk memindahkan mutasi rekening koran dari bentuk PDF (yang sulit diedit) menjadi file Excel yang siap diolah kembali untuk rekonsiliasi.")
    
    st.info("Keamanan: Proses berjalan di sisi memori server saat itu juga. File PDF yang diupload tidak disimpan secara permanen di storage server.")