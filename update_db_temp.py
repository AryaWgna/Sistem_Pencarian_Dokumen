from app import create_app, db
from app.models import Dokumen
import random

app = create_app()
with app.app_context():
    docs = Dokumen.query.all()
    for d in docs:
        if d.kategori == 'Kepegawaian & Tugas':
            d.kategori = random.choice(['SPPD & Surat Perintah', 'Dokumen Kepegawaian'])
        elif d.kategori == 'Pengumuman & Edaran':
            d.kategori = random.choice(['Surat Edaran', 'Surat Pengumuman', 'Nota Dinas'])
        elif d.kategori == 'Surat Umum':
            d.kategori = random.choice(['Surat Keterangan', 'Surat Biasa'])
    
    db.session.commit()
    print('Database updated to 9 categories successfully.')
