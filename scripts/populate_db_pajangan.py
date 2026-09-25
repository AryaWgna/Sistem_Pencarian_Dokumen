import sys
import os

# Menambahkan root folder ke sys.path agar bisa import module app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Dokumen, TfidfScore, ClassificationResult
from app.services.tfidf_service import tfidf_service
from app.services.naive_bayes_service import nb_service
from app.services import preprocess_text

app = create_app()

def populate_pajangan():
    with app.app_context():
        print("Mulai mengisi tabel pajangan (TfidfScore & ClassificationResult)...")
        
        # Hapus data lama jika ada
        print("Menghapus data lama...")
        db.session.query(TfidfScore).delete()
        db.session.query(ClassificationResult).delete()
        db.session.commit()

        # Ambil semua dokumen
        dokumen_list = Dokumen.query.all()
        print(f"Total {len(dokumen_list)} dokumen ditemukan.")
        
        # Load ulang model jika matrix kosong
        if tfidf_service.vectorizer is None:
            tfidf_service.load_model()
        if nb_service.model is None:
            nb_service.load_model()

        feature_names = tfidf_service.vectorizer.get_feature_names_out()
        idf_scores = tfidf_service.vectorizer.idf_

        for doc in dokumen_list:
            text = (doc.judul or "") + " " + (doc.isi_dokumen or "")
            preprocessed_text = preprocess_text(text)
            
            if not preprocessed_text.strip():
                continue

            # --- 1. POPULATE TF-IDF SCORES ---
            # Menghitung TF-IDF untuk dokumen ini
            matrix = tfidf_service.vectorizer.transform([preprocessed_text])
            
            # Kita ambil index kata yang ada nilainya di dokumen ini (non-zero)
            # Agar database tidak meledak, kita hanya simpan top 20 kata per dokumen
            coo = matrix.tocoo()
            
            # Gabungkan jadi list of tuples (col_index, tfidf_score)
            word_scores = list(zip(coo.col, coo.data))
            # Sort berdasarkan score tertinggi
            word_scores.sort(key=lambda x: x[1], reverse=True)
            
            top_words = word_scores[:20]
            
            for col_idx, tfidf_val in top_words:
                term = feature_names[col_idx]
                idf_val = idf_scores[col_idx]
                
                # TF bisa diperkirakan balik dari TFIDF / IDF (ini hanya pajangan)
                tf_val = tfidf_val / idf_val if idf_val > 0 else 0
                
                skor_baru = TfidfScore(
                    dokumen_id=doc.id,
                    term=term,
                    tf_score=float(tf_val),
                    idf_score=float(idf_val),
                    tfidf_score=float(tfidf_val)
                )
                db.session.add(skor_baru)

            # --- 2. POPULATE CLASSIFICATION RESULTS ---
            predicted_kategori = nb_service.predict(matrix)
            confidence = nb_service.get_confidence(matrix)
            
            is_correct = (predicted_kategori == doc.kategori)
            
            klasifikasi_baru = ClassificationResult(
                dokumen_id=doc.id,
                predicted_kategori=predicted_kategori,
                confidence_score=float(confidence),
                is_correct=is_correct
            )
            db.session.add(klasifikasi_baru)

        print("Menyimpan ke database...")
        db.session.commit()
        print("Selesai! Tabel pajangan berhasil diisi.")

if __name__ == '__main__':
    populate_pajangan()
