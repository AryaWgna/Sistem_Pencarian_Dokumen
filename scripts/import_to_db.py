"""Import dataset and model evaluation results into MySQL database"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
from app import create_app, db
from app.models import Dokumen, PreprocessingResult, ModelEvaluation
from app.services import preprocess
from werkzeug.security import generate_password_hash
from app.models import User

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("Tables created.")

    # Create default admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            nama='Admin SLB',
            username='admin',
            password=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created (admin / admin123)")

    # Import documents
    df = pd.read_csv('dataset/dokumen_final.csv')
    existing = Dokumen.query.count()
    if existing > 0:
        print(f"Database already has {existing} documents. Skipping import.")
    else:
        print(f"Importing {len(df)} documents...")
        for _, row in df.iterrows():
            tgl = None
            if pd.notna(row.get('tanggal_dokumen')) and str(row['tanggal_dokumen']).strip():
                try:
                    tgl = datetime.strptime(str(row['tanggal_dokumen'])[:10], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass

            dok = Dokumen(
                nomor_dokumen=str(row.get('nomor_dokumen', '')) if pd.notna(row.get('nomor_dokumen')) else '',
                judul=str(row['judul']),
                kategori=str(row['kategori']),
                jenis_surat=str(row.get('jenis_surat', '')) if pd.notna(row.get('jenis_surat')) else '',
                tanggal_dokumen=tgl,
                pengirim_tujuan=str(row.get('pengirim_tujuan', '')) if pd.notna(row.get('pengirim_tujuan')) else '',
                isi_dokumen=str(row.get('isi_dokumen', '')) if pd.notna(row.get('isi_dokumen')) else '',
                file_path=str(row.get('file_path', '')) if pd.notna(row.get('file_path')) else ''
            )
            db.session.add(dok)
        db.session.commit()
        print(f"Imported {len(df)} documents.")

        # Run preprocessing on all documents
        print("Running preprocessing on all documents...")
        docs = Dokumen.query.all()
        count = 0
        for dok in docs:
            text = f"{dok.judul} {dok.isi_dokumen or ''}"
            prep = preprocess(text)
            pr = PreprocessingResult(
                dokumen_id=dok.id,
                original_text=text,
                case_folding=prep['case_folding'],
                tokenizing=prep['tokenizing'],
                filtering=prep['filtering'],
                stemming=prep['stemming']
            )
            db.session.add(pr)
            count += 1
            if count % 50 == 0:
                db.session.commit()
                print(f"  Preprocessed {count}/{len(docs)}...")
        db.session.commit()
        print(f"  Preprocessed {count}/{len(docs)} documents.")

    # Import model evaluation results
    eval_file = 'dataset/model_evaluation.csv'
    if os.path.exists(eval_file):
        eval_df = pd.read_csv(eval_file)
        # Clear old evaluations
        ModelEvaluation.query.delete()
        for _, row in eval_df.iterrows():
            me = ModelEvaluation(
                kategori=row['kategori'],
                precision_score=row['precision'],
                recall_score=row['recall'],
                f1_score=row['f1_score'],
                support=int(row['support']),
                accuracy=row['accuracy']
            )
            db.session.add(me)
        db.session.commit()
        print(f"Imported {len(eval_df)} evaluation results.")
    else:
        print("No model_evaluation.csv found. Run train_model.py first.")

    print("\nDone! You can now run: python run.py")
