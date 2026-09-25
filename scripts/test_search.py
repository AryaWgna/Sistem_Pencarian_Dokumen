from app import create_app
from app.services.search_engine import tfidf_service
from sklearn.metrics.pairwise import cosine_similarity
from app.models import Dokumen

app = create_app()
with app.app_context():
    query_vector = tfidf_service.transform('surat tugas')
    similarities = cosine_similarity(query_vector, tfidf_service.tfidf_matrix).flatten()
    doc_scores = list(zip(tfidf_service.doc_ids, similarities))
    doc_scores.sort(key=lambda x: -x[1])
    
    top_doc_ids = [int(d[0]) for d in doc_scores if d[1] > 0]
    print('Top matching doc_ids:', top_doc_ids)
    
    if top_doc_ids:
        all_docs = Dokumen.query.filter(Dokumen.id.in_(top_doc_ids)).all()
        kategori_map = {d.id: d.kategori for d in all_docs}
        print('Kategori Map:', kategori_map)
