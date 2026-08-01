# ... existing code ...
    try:
        # Membuka PDF, menggunakan password jika diberikan
        kwargs = {}
        if password:
            kwargs['password'] = password
            
        with pdfplumber.open(pdf_file, **kwargs) as pdf:
            for page_num, page in enumerate(pdf.pages):
                
                # PERBAIKAN: Gunakan strategi "text" sebagai PRIORITAS UTAMA.
                # Karena mayoritas rekening koran tidak punya garis tabel (borderless).
                # Ini akan membaca jarak spasi sebagai kolom.
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 3,
                })
                
                # Jika strategi "text" tidak menemukan tabel sama sekali,
                # baru coba strategi "lines" sebagai cadangan.
                if not tables:
                     tables = page.extract_tables(table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                    })

                if tables:
                    for table in tables:
                        # Membersihkan data: hapus baris yang kosong atau None
                        cleaned_table = [row for row in table if any(cell is not None and str(cell).strip() != '' for cell in row)]
                        if cleaned_table:
                             all_data.extend(cleaned_table)
                             
        if all_data:
            df = pd.DataFrame(all_data)
# ... existing code ...
```

**Penjelasan Perubahan:**
Saya membalik urutannya. Sekarang aplikasi akan mencoba `vertical_strategy: "text"` terlebih dahulu. Strategi ini sangat tangguh untuk membaca dokumen e-statement (seperti BCA, Mandiri) karena ia mendeteksi jarak kolom berdasarkan letak hurufnya, bukan dari ada atau tidaknya garis tinta di PDF.

Silakan salin perbaikan ini, simpan, dan coba jalankan kembali dengan PDF Anda. Transaksi-transaksi Anda seharusnya sekarang sudah terbaca dengan baik!
