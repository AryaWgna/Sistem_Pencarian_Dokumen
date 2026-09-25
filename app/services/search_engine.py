"""Search Engine: TF-IDF + Naive Bayes + Cosine Similarity pipeline"""
import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.services import preprocess, preprocess_text
from app.services.tfidf_service import tfidf_service
from app.services.naive_bayes_service import nb_service
import difflib


def search(query, top_n=20):
    """Full search pipeline (Whitebox — setiap langkah direkam):
    1. Preprocess query
    2. TF-IDF vectorize query
    3. Naive Bayes classify query → predicted category
    4. Cosine Similarity query vs all documents
    5. AI Boosting (kombinasi NB + cosine)
    6. Rank by final score
    
    Returns dict with results, metadata, and detailed 'steps' for whitebox display.
    """
    start_time = time.time()

    # ── LANGKAH 1: PREPROCESSING ──
    prep = preprocess(query)
    preprocessed_query = prep['result']

    if not preprocessed_query.strip():
        return {
            'query': query,
            'preprocessed_query': preprocessed_query,
            'preprocessing_steps': prep,
            'predicted_kategori': None,
            'confidence': 0,
            'results': [],
            'results_count': 0,
            'response_time_ms': 0,
            'steps': None,
        }

    # Typo correction (Spell Checker ringan)
    corrected_query_tokens = []
    vocab = tfidf_service.vectorizer.get_feature_names_out() if tfidf_service.vectorizer else []
    query_tokens = preprocessed_query.split()
    
    for token in query_tokens:
        if token in vocab:
            corrected_query_tokens.append(token)
        else:
            matches = difflib.get_close_matches(token, vocab, n=1, cutoff=0.7)
            if matches:
                corrected_query_tokens.append(matches[0])
            else:
                corrected_query_tokens.append(token)
                
    corrected_query = " ".join(corrected_query_tokens)
    is_corrected = corrected_query != preprocessed_query
    search_query = corrected_query if is_corrected else preprocessed_query

    # ── LANGKAH 2: TF-IDF VECTORIZATION ──
    query_vector = tfidf_service.transform(search_query)
    tfidf_details = tfidf_service.get_tfidf_details(search_query)

    # Rekam detail TF-IDF per term (TF, IDF, TF-IDF) untuk whitebox
    step_tfidf_terms = []
    if tfidf_service.vectorizer:
        feature_names = tfidf_service.vectorizer.get_feature_names_out()
        idf_scores = tfidf_service.vectorizer.idf_
        cx = query_vector.tocoo()
        for _, col, val in zip(cx.row, cx.col, cx.data):
            term = feature_names[col]
            idf_val = idf_scores[col]
            tf_val = val / idf_val if idf_val > 0 else 0
            step_tfidf_terms.append({
                'term': term,
                'tf': round(float(tf_val), 4),
                'idf': round(float(idf_val), 4),
                'tfidf': round(float(val), 4),
            })
        step_tfidf_terms.sort(key=lambda x: -x['tfidf'])

    # ── LANGKAH 3: KLASIFIKASI NAIVE BAYES ──
    predicted_kategori = nb_service.predict(query_vector)
    confidence = nb_service.get_confidence(query_vector)
    category_probs = nb_service.predict_proba(query_vector)

    # Rekam detail NB (prior + posterior) untuk whitebox
    step_nb_details = []
    if nb_service.model:
        priors = np.exp(nb_service.model.class_log_prior_)
        for i, class_name in enumerate(nb_service.model.classes_):
            step_nb_details.append({
                'kategori': class_name,
                'prior': round(float(priors[i]), 4),
                'posterior': round(float(category_probs.get(class_name, 0)), 6),
                'is_winner': class_name == predicted_kategori,
            })
        step_nb_details.sort(key=lambda x: -x['posterior'])

    # ── LANGKAH 4: COSINE SIMILARITY ──
    if tfidf_service.tfidf_matrix is None:
        return {
            'query': query,
            'preprocessed_query': preprocessed_query,
            'predicted_kategori': predicted_kategori,
            'confidence': confidence,
            'results': [],
            'results_count': 0,
            'response_time_ms': 0,
            'steps': None,
        }

    similarities = cosine_similarity(query_vector, tfidf_service.tfidf_matrix).flatten()

    from app.models import Dokumen
    
    doc_scores = list(zip(tfidf_service.doc_ids, similarities))
    doc_scores.sort(key=lambda x: -x[1])
    
    all_docs = Dokumen.query.filter(Dokumen.id.in_([int(d[0]) for d in doc_scores])).all()
    kategori_map = {d.id: d.kategori for d in all_docs}
    judul_map = {d.id: d.judul for d in all_docs}

    # Rekam skor cosine SEBELUM boost (untuk whitebox langkah 4)
    step_cosine_raw = []
    for doc_id, score in doc_scores:
        if score > 0.0 and int(doc_id) in kategori_map:
            step_cosine_raw.append({
                'doc_id': int(doc_id),
                'judul': judul_map.get(int(doc_id), f'Dokumen #{doc_id}'),
                'kategori': kategori_map.get(int(doc_id), '-'),
                'score': round(float(score), 4),
            })

    # ── LANGKAH 5: AI BOOSTING (KOMBINASI ALGORITMA) ──
    results = []
    step_boosting = []
    for doc_id, score in doc_scores:
        if score > 0.0:
            if int(doc_id) not in kategori_map:
                continue
                
            kategori_asli = kategori_map.get(int(doc_id))
            is_boosted = kategori_asli == predicted_kategori
            
            if is_boosted:
                final_score = score + 1.0 
            else:
                final_score = score
                
            results.append({
                'dokumen_id': int(doc_id), 
                'similarity_score': round(float(final_score), 4),
                'is_boosted': is_boosted
            })

            # Rekam detail boosting untuk whitebox (top 10 saja agar tidak terlalu banyak)
            if len(step_boosting) < 10:
                step_boosting.append({
                    'doc_id': int(doc_id),
                    'judul': judul_map.get(int(doc_id), f'Dokumen #{doc_id}'),
                    'kategori': kategori_asli,
                    'score_before': round(float(score), 4),
                    'is_boosted': is_boosted,
                    'boost_amount': 1.0 if is_boosted else 0.0,
                    'score_after': round(float(final_score), 4),
                })
            
    # ── LANGKAH 6: RANKING AKHIR ──
    results.sort(key=lambda x: -x['similarity_score'])
    results = results[:top_n]

    elapsed_ms = int((time.time() - start_time) * 1000)

    # Susun objek 'steps' untuk whitebox display
    steps = {
        'step1_preprocessing': {
            'input': query,
            'case_folding': prep.get('case_folding', ''),
            'tokenizing': prep.get('tokenizing', ''),
            'filtering': prep.get('filtering', ''),
            'stemming': prep.get('stemming', ''),
            'output': preprocessed_query,
            'corrected': corrected_query if is_corrected else None,
        },
        'step2_tfidf': {
            'query_used': search_query,
            'terms': step_tfidf_terms,
            'total_vocab': len(vocab) if hasattr(vocab, '__len__') else 0,
        },
        'step3_nb_classify': {
            'predicted': predicted_kategori,
            'confidence': confidence,
            'probabilities': step_nb_details,
        },
        'step4_cosine': {
            'total_compared': len(step_cosine_raw),
            'top_results': step_cosine_raw[:10],
        },
        'step5_boosting': {
            'predicted_kategori': predicted_kategori,
            'boost_amount': 1.0,
            'details': step_boosting,
        },
        'step6_final_ranking': {
            'total_results': len(results),
            'top_results': [
                {
                    'rank': i + 1,
                    'doc_id': r['dokumen_id'],
                    'score': r['similarity_score'],
                    'is_boosted': r['is_boosted'],
                }
                for i, r in enumerate(results[:10])
            ],
        },
    }

    return {
        'query': query,
        'preprocessed_query': preprocessed_query,
        'corrected_query': corrected_query if is_corrected else None,
        'preprocessing_steps': prep,
        'predicted_kategori': predicted_kategori,
        'confidence': confidence,
        'category_probs': category_probs,
        'results': results,
        'results_count': len(results),
        'response_time_ms': elapsed_ms,
        'tfidf_details': tfidf_details,
        'steps': steps,
    }


def update_models():
    """Retrain TF-IDF dan Naive Bayes dari data DB terkini.
    Dipanggil setelah dokumen ditambah/dihapus agar model tetap sinkron."""
    from app.models import Dokumen

    all_docs = Dokumen.query.all()
    if not all_docs:
        return

    documents_text = []
    doc_ids = []
    labels = []

    for doc in all_docs:
        text_mentah = (doc.judul or "") + " " + (doc.isi_dokumen or "") + " " + (doc.kata_kunci or "")
        teks_bersih = preprocess_text(text_mentah)
        documents_text.append(teks_bersih)
        doc_ids.append(doc.id)
        labels.append(doc.kategori)

    # Retrain TF-IDF
    tfidf_service.fit(documents_text, doc_ids)

    # Retrain Naive Bayes
    X = tfidf_service.tfidf_matrix
    nb_service.train(X, labels)
