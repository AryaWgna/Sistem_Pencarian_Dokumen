"""Route untuk halaman Alur Proses & Tahapan Model (Metodologi)
Menampilkan langkah-langkah proses data, perhitungan, dan tahapan model secara visual.
"""
import json
import numpy as np
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app import db
from app.models import Dokumen, PreprocessingResult
from app.services import preprocess, preprocess_text
from app.services.tfidf_service import tfidf_service
from app.services.naive_bayes_service import nb_service

metodologi_bp = Blueprint('metodologi', __name__)


@metodologi_bp.route('/')
@login_required
def alur_proses():
    """Halaman utama Alur Proses & Tahapan Model."""

    # ── 1. Statistik Dataset ──
    total_dokumen = Dokumen.query.count()
    kategori_stats = db.session.query(
        Dokumen.kategori, db.func.count(Dokumen.id)
    ).group_by(Dokumen.kategori).order_by(db.func.count(Dokumen.id).desc()).all()

    # ── 2. Contoh Preprocessing Real (ambil 1 dokumen dari DB) ──
    contoh_prep = None
    sample_doc = Dokumen.query.first()
    if sample_doc:
        sample_text = (sample_doc.judul or "") + " " + (sample_doc.isi_dokumen or "")[:150]
        prep_result = preprocess(sample_text)
        contoh_prep = {
            'original': sample_text[:200],
            'case_folding': prep_result.get('case_folding', '')[:200],
            'tokenizing': prep_result.get('tokenizing', ''),
            'filtering': prep_result.get('filtering', ''),
            'stemming': prep_result.get('stemming', ''),
            'result': prep_result.get('result', ''),
            'doc_judul': sample_doc.judul,
            'doc_kategori': sample_doc.kategori,
        }

    # ── 3. Data TF-IDF dari Model ──
    tfidf_data = {}
    if tfidf_service.vectorizer is not None:
        feature_names = tfidf_service.vectorizer.get_feature_names_out()
        idf_scores = tfidf_service.vectorizer.idf_

        # Top 15 terms berdasarkan IDF tertinggi (kata paling khas/langka)
        top_indices = np.argsort(idf_scores)[-15:][::-1]
        top_terms = []
        for idx in top_indices:
            top_terms.append({
                'term': feature_names[idx],
                'idf': round(float(idf_scores[idx]), 4),
            })

        # Top 15 terms berdasarkan IDF terendah (kata paling umum)
        common_indices = np.argsort(idf_scores)[:15]
        common_terms = []
        for idx in common_indices:
            common_terms.append({
                'term': feature_names[idx],
                'idf': round(float(idf_scores[idx]), 4),
            })

        tfidf_data = {
            'total_vocab': len(feature_names),
            'max_features': 5000,
            'top_terms': top_terms,
            'common_terms': common_terms,
            'matrix_shape': list(tfidf_service.tfidf_matrix.shape) if tfidf_service.tfidf_matrix is not None else [0, 0],
        }

    # ── 4. Data Naïve Bayes dari Model ──
    nb_data = {}
    if nb_service.model is not None:
        classes = nb_service.model.classes_
        priors = np.exp(nb_service.model.class_log_prior_)
        nb_details = []
        for i, class_name in enumerate(classes):
            nb_details.append({
                'kategori': class_name,
                'prior': round(float(priors[i]), 4),
                'prior_pct': round(float(priors[i]) * 100, 2),
            })
        nb_details.sort(key=lambda x: -x['prior'])

        nb_data = {
            'total_classes': len(classes),
            'classes': nb_details,
            'alpha': 1.0,
            'fit_prior': False,
        }

    return render_template('metodologi/metodologi.html',
                           total_dokumen=total_dokumen,
                           kategori_stats=kategori_stats,
                           contoh_prep=contoh_prep,
                           tfidf_data=tfidf_data,
                           nb_data=nb_data)


@metodologi_bp.route('/demo', methods=['POST'])
@login_required
def demo_proses():
    """AJAX endpoint: Demo interaktif — input teks, lihat semua tahap proses."""
    text = request.json.get('text', '').strip()
    if not text:
        return jsonify({'error': 'Teks tidak boleh kosong'}), 400

    # Step 1: Preprocessing
    prep = preprocess(text)

    # Step 2: TF-IDF
    preprocessed = prep['result']
    tfidf_details = []
    nb_result = {}

    if preprocessed.strip() and tfidf_service.vectorizer is not None:
        query_vector = tfidf_service.transform(preprocessed)
        feature_names = tfidf_service.vectorizer.get_feature_names_out()
        idf_scores = tfidf_service.vectorizer.idf_

        cx = query_vector.tocoo()
        for _, col, val in zip(cx.row, cx.col, cx.data):
            term = feature_names[col]
            idf_val = idf_scores[col]
            tf_val = val / idf_val if idf_val > 0 else 0
            tfidf_details.append({
                'term': term,
                'tf': round(float(tf_val), 4),
                'idf': round(float(idf_val), 4),
                'tfidf': round(float(val), 4),
            })
        tfidf_details.sort(key=lambda x: -x['tfidf'])

        # Step 3: Naïve Bayes prediction
        if nb_service.model is not None:
            predicted = nb_service.predict(query_vector)
            confidence = nb_service.get_confidence(query_vector)
            probas = nb_service.predict_proba(query_vector)

            priors = np.exp(nb_service.model.class_log_prior_)
            nb_classes = []
            for i, cls in enumerate(nb_service.model.classes_):
                nb_classes.append({
                    'kategori': cls,
                    'prior': round(float(priors[i]), 4),
                    'posterior': round(float(probas.get(cls, 0)), 6),
                    'is_winner': cls == predicted,
                })
            nb_classes.sort(key=lambda x: -x['posterior'])

            nb_result = {
                'predicted': predicted,
                'confidence': round(float(confidence), 4),
                'classes': nb_classes,
            }

    return jsonify({
        'preprocessing': {
            'original': text,
            'case_folding': prep.get('case_folding', ''),
            'tokenizing': prep.get('tokenizing', ''),
            'filtering': prep.get('filtering', ''),
            'stemming': prep.get('stemming', ''),
            'result': prep.get('result', ''),
        },
        'tfidf': tfidf_details,
        'naive_bayes': nb_result,
    })
