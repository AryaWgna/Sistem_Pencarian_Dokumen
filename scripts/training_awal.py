import sys
import os
import pandas as pd

# Menambahkan root folder ke sys.path agar bisa import module app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Dokumen
from app.services.tfidf_service import tfidf_service
from app.services.naive_bayes_service import nb_service
from app.services import preprocess_text
from app.config import Config

app = create_app()

# Mapping kategori ke 5 kategori utama agar akurasi AI maksimal (sesuai best practice)
CATEGORY_MAPPING = {
    'Surat Keputusan': 'Surat Keputusan',
    'Laporan': 'Laporan',
    'Surat Edaran': 'Pengumuman & Edaran',
    'Surat Pengumuman': 'Pengumuman & Edaran',
    'Nota Dinas': 'Pengumuman & Edaran',
    'SPPD & Surat Perintah': 'Kepegawaian & Tugas',
    'Dokumen Kepegawaian': 'Kepegawaian & Tugas',
    'Surat Keterangan': 'Surat Umum',
    'Surat Biasa': 'Surat Umum'
}

def run_training():
    with app.app_context():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dataset_path = os.path.join(base_dir, 'dataset', 'dokumen_final.csv')
        
        if not os.path.exists(dataset_path):
            print(f"❌ Error: Dataset {dataset_path} tidak ditemukan!")
            return

        print("=== Memulai Proses 'Menyekolahkan' AI (Training) ===")
        print("1. Membaca dataset dari dokumen_final.csv...")
        
        df = pd.read_csv(dataset_path)
        
        print("2. Membersihkan database lama (Reset)...")
        # Hanya menghapus dokumen yang ada di db
        db.session.query(Dokumen).delete()
        db.session.commit()

        print("3. Memproses dan menyimpan dokumen ke Database...")
        dokumen_objects = []
        for index, row in df.iterrows():
            kategori_asli = str(row['kategori'])
            # Normalisasi ke 5 kategori
            kategori_baru = CATEGORY_MAPPING.get(kategori_asli, 'Surat Umum')
            
            doc = Dokumen(
                judul=str(row['judul']) if pd.notna(row['judul']) else "",
                kategori=kategori_baru,
                jenis_surat=str(row['jenis_surat']) if pd.notna(row['jenis_surat']) else "",
                nomor_dokumen=str(row['nomor_dokumen']) if pd.notna(row['nomor_dokumen']) else "",
                isi_dokumen=str(row['isi_dokumen']) if pd.notna(row['isi_dokumen']) else "",
                pengirim_tujuan=str(row['pengirim_tujuan']) if pd.notna(row['pengirim_tujuan']) else ""
            )
            db.session.add(doc)
            dokumen_objects.append(doc)
        
        db.session.commit()
        print(f"   [OK] Berhasil menyimpan {len(dokumen_objects)} dokumen ke Database (dengan 5 Kategori Utama).")

        print("4. Melakukan Preprocessing Teks (Pembersihan, Stemming)... (Tunggu sebentar)")
        # Fetch ulang untuk memastikan ID terisi
        all_docs = Dokumen.query.all()
        
        documents_text = []
        doc_ids = []
        labels = []
        
        for doc in all_docs:
            text_mentah = (doc.judul or "") + " " + (doc.isi_dokumen or "") + " " + (doc.kata_kunci or "")
            teks_bersih = preprocess_text(text_mentah)
            documents_text.append(teks_bersih)
            doc_ids.append(doc.id)
            labels.append(doc.kategori)
            
        print("5. Training TF-IDF (Mengubah teks menjadi matriks angka bobot)...")
        tfidf_service.fit(documents_text, doc_ids)
        print("   [OK] Model TF-IDF berhasil disimpan ke models/tfidf_vectorizer.pkl menggunakan Joblib.")
        
        print("6. Training Naive Bayes (Belajar probabilitas kategori)...")
        # Ambil matriks dari tfidf_service
        X = tfidf_service.tfidf_matrix
        y = labels
        nb_service.train(X, y)
        print("   [OK] Model Naive Bayes berhasil disimpan ke models/naive_bayes_model.pkl menggunakan Joblib.")

        # Step 7: Export dataset ke CSV
        print("7. Mengekspor data dokumen ke file CSV...")
        export_data = []
        for doc in all_docs:
            export_data.append({
                'id': doc.id,
                'judul': doc.judul or "",
                'kategori': doc.kategori or "",
                'jenis_surat': doc.jenis_surat or "",
                'nomor_dokumen': doc.nomor_dokumen or "",
                'isi_dokumen': doc.isi_dokumen or "",
                'pengirim_tujuan': doc.pengirim_tujuan or ""
            })

        df_export = pd.DataFrame(export_data)
        csv_path = os.path.join(base_dir, 'dataset', 'dokumen_final.csv')
        df_export.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"   [OK] Dataset berhasil diekspor ke {csv_path} ({len(export_data)} dokumen).")
        
        print("\n=== YEY! Proses Training Selesai 100% ===")
        print("Mesin AI Anda sekarang sudah sangat pintar. Silakan jalankan 'python run.py' untuk mendemonstrasikan aplikasinya.")

if __name__ == '__main__':
    run_training()
