from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from app import db
from app.models import Dokumen, SearchHistory, SearchResult, ModelEvaluation, PreprocessingResult
from app.services.search_engine import search

pencarian_bp = Blueprint('pencarian', __name__)


@pencarian_bp.route('/')
@login_required
def home():
    total_dokumen = Dokumen.query.count()
    total_kategori = db.session.query(Dokumen.kategori).distinct().count()
    total_pencarian = SearchHistory.query.filter_by(user_id=current_user.id).count()

    # Category distribution
    kategori_stats = db.session.query(
        Dokumen.kategori, db.func.count(Dokumen.id)
    ).group_by(Dokumen.kategori).all()

    # Recent searches
    recent_searches = SearchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(SearchHistory.search_date.desc()).limit(5).all()

    # --- Evaluasi Model Logic ---
    dokumens = Dokumen.query.all()
    eval_data = {}
    if dokumens:
        data = []
        for d in dokumens:
            prep = PreprocessingResult.query.filter_by(dokumen_id=d.id).first()
            text = d.isi_dokumen or d.judul
            if prep and prep.stemming:
                try:
                    import json
                    stem_arr = json.loads(prep.stemming)
                    text = " ".join(stem_arr)
                except:
                    pass
            if not text or not text.strip():
                text = d.judul
            data.append({'id': d.id, 'text': text, 'kategori': d.kategori})
            
        df = pd.DataFrame(data)
        df = df[df['text'].str.strip().astype(bool)].reset_index(drop=True)
        
        if len(df) >= 2:
            X = df['text'].values
            y = df['kategori'].values
            doc_ids = df['id'].values
            
            try:
                X_train, X_test, y_train, y_test, id_train, id_test = train_test_split(X, y, doc_ids, test_size=0.2, random_state=42, stratify=y)
            except ValueError:
                X_train, X_test, y_train, y_test, id_train, id_test = train_test_split(X, y, doc_ids, test_size=0.2, random_state=42)
                
            eval_data['total_data'] = len(df)
            eval_data['train_data'] = len(X_train)
            eval_data['test_data'] = len(X_test)
            
            # Export data distribution for the thesis
            eval_data['train_docs'] = [{'id': i, 'kategori': k} for i, k in zip(id_train, y_train)]
            eval_data['test_docs'] = [{'id': i, 'kategori': k} for i, k in zip(id_test, y_test)]
            
            vectorizer = TfidfVectorizer(max_features=5000)
            X_train_tfidf = vectorizer.fit_transform(X_train)
            X_test_tfidf = vectorizer.transform(X_test)
            # ── PENANGANAN IMBALANCED DATA (OVERSAMPLING) ──
            # Karena distribusi 9 kategori tidak seimbang (imbalanced), kita lakukan Random Oversampling
            # pada data latih agar model Naive Bayes tidak bias ke kategori mayoritas.
            from collections import Counter
            from scipy.sparse import vstack
            import numpy as np

            counts = Counter(y_train)
            if counts:
                max_count = max(counts.values())
                
                X_train_resampled_list = [X_train_tfidf]
                y_train_resampled_list = [y_train]
                
                for cls, count in counts.items():
                    if count < max_count:
                        num_to_add = max_count - count
                        indices = np.where(y_train == cls)[0]
                        if len(indices) > 0:
                            # Duplikasi data secara acak untuk kategori minoritas
                            resampled_indices = np.random.choice(indices, size=num_to_add, replace=True)
                            X_train_resampled_list.append(X_train_tfidf[resampled_indices])
                            y_train_resampled_list.append(y_train[resampled_indices])
                            
                X_train_tfidf_balanced = vstack(X_train_resampled_list)
                y_train_balanced = np.concatenate(y_train_resampled_list)
            else:
                X_train_tfidf_balanced = X_train_tfidf
                y_train_balanced = y_train

            eval_data['train_data_balanced'] = len(y_train_balanced)

            nb = MultinomialNB(alpha=1.0)
            nb.fit(X_train_tfidf_balanced, y_train_balanced)
            y_pred = nb.predict(X_test_tfidf)
            
            labels = sorted(set(y_test) | set(y_pred))
            cm = confusion_matrix(y_test, y_pred, labels=labels)
            
            cm_data = []
            for i, true_label in enumerate(labels):
                row = {'true_label': true_label, 'preds': []}
                for j, pred_label in enumerate(labels):
                    row['preds'].append({
                        'value': cm[i][j],
                        'is_correct': (i == j),
                        'pred_label': pred_label
                    })
                cm_data.append(row)
                
            eval_data['labels'] = labels
            eval_data['cm_data'] = cm_data
            eval_data['accuracy'] = accuracy_score(y_test, y_pred)
            eval_data['report'] = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

            # Hitung rata-rata response time dari SearchHistory
            avg_rt = db.session.query(db.func.avg(SearchHistory.response_time_ms)).scalar()
            eval_data['avg_response_time'] = round(avg_rt, 2) if avg_rt else 50.0

            # ── Perbandingan SEBELUM vs SESUDAH ──
            from sklearn.metrics.pairwise import cosine_similarity as cos_sim
            import numpy as np

            # SEBELUM: Hanya TF-IDF + Cosine Similarity (tanpa klasifikasi NB)
            # Untuk setiap dokumen uji, cari dokumen terdekat di data latih berdasarkan cosine similarity
            # lalu ambil kategori dari dokumen latih terdekat (nearest neighbor)
            similarities_before = cos_sim(X_test_tfidf, X_train_tfidf)
            y_pred_before = []
            for i in range(len(X_test)):
                nearest_idx = np.argmax(similarities_before[i])
                y_pred_before.append(y_train[nearest_idx])
            y_pred_before = np.array(y_pred_before)

            acc_before = accuracy_score(y_test, y_pred_before)
            report_before = classification_report(y_test, y_pred_before, output_dict=True, zero_division=0)

            # SESUDAH: TF-IDF + Naive Bayes (sudah dihitung di atas)
            acc_after = eval_data['accuracy']
            report_after = eval_data['report']

            # Hitung peningkatan
            peningkatan = acc_after - acc_before
            persen_peningkatan = (peningkatan / acc_before * 100) if acc_before > 0 else 0

            eval_data['comparison'] = {
                'before': {
                    'method': 'TF-IDF + Cosine Similarity (Tanpa Naive Bayes)',
                    'accuracy': acc_before,
                    'precision': report_before.get('weighted avg', {}).get('precision', 0),
                    'recall': report_before.get('weighted avg', {}).get('recall', 0),
                    'f1': report_before.get('weighted avg', {}).get('f1-score', 0),
                },
                'after': {
                    'method': 'TF-IDF + Naive Bayes + Cosine Similarity (AI Boosting)',
                    'accuracy': acc_after,
                    'precision': report_after.get('weighted avg', {}).get('precision', 0),
                    'recall': report_after.get('weighted avg', {}).get('recall', 0),
                    'f1': report_after.get('weighted avg', {}).get('f1-score', 0),
                },
                'peningkatan': peningkatan,
                'persen_peningkatan': persen_peningkatan,
            }

            # ── DATA LATIH SPESIFIK (Revisi #4) ──
            # Sample dokumen per kategori untuk ditampilkan di Dashboard
            sample_docs = {}
            kategori_list = db.session.query(Dokumen.kategori).distinct().all()
            for kat_tuple in kategori_list:
                kat = kat_tuple[0]
                docs_sample = Dokumen.query.filter_by(kategori=kat).limit(3).all()
                sample_docs[kat] = [{'id': d.id, 'judul': d.judul, 'isi_preview': (d.isi_dokumen or '')[:120]} for d in docs_sample]
            eval_data['sample_docs'] = sample_docs

            # Distribusi detail per kategori (jumlah per kategori)
            kategori_counts = {}
            for kat_tuple in kategori_list:
                kat = kat_tuple[0]
                kategori_counts[kat] = Dokumen.query.filter_by(kategori=kat).count()
            eval_data['kategori_counts'] = kategori_counts

            # ── EFISIENSI PENCARIAN (Revisi #5) ──
            all_search_times = db.session.query(SearchHistory.response_time_ms).all()
            if all_search_times:
                times = [t[0] for t in all_search_times if t[0] and t[0] > 0]
                if times:
                    avg_ms = sum(times) / len(times)
                    eval_data['efficiency'] = {
                        'avg_ms': round(avg_ms, 2),
                        'min_ms': min(times),
                        'max_ms': max(times),
                        'total_searches': len(times),
                        'speed_factor': round(900000 / avg_ms, 0) if avg_ms > 0 else 0,
                        'all_times': times[-20:],  # 20 terakhir untuk chart
                    }

            # ── SKENARIO UJI PENCARIAN OTOMATIS (Revisi #7) ──
            from app.services.search_engine import search as run_search
            test_scenarios = [
                {'query': 'surat keputusan pengangkatan guru', 'expected': 'Surat Keputusan'},
                {'query': 'laporan kegiatan inklusi semester', 'expected': 'Laporan'},
                {'query': 'surat tugas mengajar', 'expected': 'Kepegawaian & Tugas'},
                {'query': 'pengumuman libur sekolah', 'expected': 'Pengumuman & Edaran'},
                {'query': 'surat keterangan siswa', 'expected': 'Surat Umum'},
            ]
            test_results = []
            for scenario in test_scenarios:
                try:
                    result = run_search(scenario['query'], top_n=10)
                    predicted = result.get('predicted_kategori', '-')
                    is_correct = predicted == scenario['expected']

                    # Hitung Precision@5: berapa dari top-5 hasil yang kategorinya = expected
                    top5 = result.get('results', [])[:5]
                    top10 = result.get('results', [])[:10]
                    relevant_5 = 0
                    relevant_10 = 0
                    for r in top5:
                        dok = Dokumen.query.get(r['dokumen_id'])
                        if dok and dok.kategori == scenario['expected']:
                            relevant_5 += 1
                    for r in top10:
                        dok = Dokumen.query.get(r['dokumen_id'])
                        if dok and dok.kategori == scenario['expected']:
                            relevant_10 += 1

                    test_results.append({
                        'query': scenario['query'],
                        'expected': scenario['expected'],
                        'predicted': predicted,
                        'is_correct': is_correct,
                        'results_count': result.get('results_count', 0),
                        'response_time_ms': result.get('response_time_ms', 0),
                        'precision_at_5': round(relevant_5 / min(len(top5), 5), 2) if top5 else 0,
                        'precision_at_10': round(relevant_10 / min(len(top10), 10), 2) if top10 else 0,
                    })
                except Exception:
                    test_results.append({
                        'query': scenario['query'],
                        'expected': scenario['expected'],
                        'predicted': '-',
                        'is_correct': False,
                        'results_count': 0,
                        'response_time_ms': 0,
                        'precision_at_5': 0,
                        'precision_at_10': 0,
                    })

            eval_data['test_scenarios'] = test_results
            # Hitung rata-rata precision
            if test_results:
                eval_data['avg_precision_5'] = round(sum(t['precision_at_5'] for t in test_results) / len(test_results), 2)
                eval_data['avg_precision_10'] = round(sum(t['precision_at_10'] for t in test_results) / len(test_results), 2)
                eval_data['test_accuracy'] = round(sum(1 for t in test_results if t['is_correct']) / len(test_results), 2)

    # --- Perhitungan Manual Logic ---
    manual_calc_data = None
    test_query = request.args.get('test_query', '').strip()
    
    if test_query:
        from app.services import preprocess_text
        from app.services.tfidf_service import tfidf_service
        from app.services.naive_bayes_service import nb_service
        
        prep_query = preprocess_text(test_query)
        if prep_query and tfidf_service.vectorizer and nb_service.model:
            # 1. TF-IDF Calculation Breakdown
            vectorizer = tfidf_service.vectorizer
            feature_names = vectorizer.get_feature_names_out()
            idf_scores = vectorizer.idf_
            
            query_matrix = vectorizer.transform([prep_query]).tocoo()
            
            tfidf_details = []
            for col_idx, tfidf_val in zip(query_matrix.col, query_matrix.data):
                term = feature_names[col_idx]
                idf_val = idf_scores[col_idx]
                # Reconstruct TF (approximate for demonstration)
                tf_val = tfidf_val / idf_val if idf_val > 0 else 0
                
                tfidf_details.append({
                    'term': term,
                    'tf': tf_val,
                    'idf': idf_val,
                    'tfidf': tfidf_val
                })
            
            # Sort by TF-IDF score
            tfidf_details.sort(key=lambda x: x['tfidf'], reverse=True)
            
            # 2. Naive Bayes Calculation Breakdown
            nb = nb_service.model
            classes = nb.classes_
            
            # Prior probabilities (log format converted to percentage/probability)
            import numpy as np
            priors = np.exp(nb.class_log_prior_)
            
            # Calculate posterior for the query
            query_dense = query_matrix.toarray()
            # The log proba gives us the final score per class
            posteriors = nb.predict_proba(query_dense)[0]
            
            nb_details = []
            for i, class_name in enumerate(classes):
                nb_details.append({
                    'kategori': class_name,
                    'prior': priors[i],
                    'posterior': posteriors[i]
                })
                
            nb_details.sort(key=lambda x: x['posterior'], reverse=True)
            
            manual_calc_data = {
                'query': test_query,
                'prep_query': prep_query,
                'tfidf_details': tfidf_details,
                'nb_details': nb_details,
                'predicted': nb_details[0]['kategori'] if nb_details else '-'
            }

    return render_template('home.html',
                           total_dokumen=total_dokumen,
                           total_kategori=total_kategori,
                           total_pencarian=total_pencarian,
                           kategori_stats=kategori_stats,
                           recent_searches=recent_searches,
                           eval_data=eval_data,
                           manual_calc_data=manual_calc_data)


@pencarian_bp.route('/pencarian', methods=['GET', 'POST'])
@login_required
def pencarian():
    results_data = None

    if request.method == 'POST':
        query_text = request.form.get('query', '').strip()
        if query_text:
            # Run search
            results_data = search(query_text)

            # Save search history
            history = SearchHistory(
                user_id=current_user.id,
                query_text=query_text,
                preprocessed_query=results_data['preprocessed_query'],
                predicted_kategori=results_data['predicted_kategori'],
                results_count=results_data['results_count'],
                response_time_ms=results_data['response_time_ms']
            )
            db.session.add(history)
            db.session.commit()

            # Save search results
            for r in results_data['results']:
                sr = SearchResult(
                    search_id=history.id,
                    dokumen_id=r['dokumen_id'],
                    similarity_score=r['similarity_score'],
                    ranking=results_data['results'].index(r) + 1
                )
                db.session.add(sr)
            db.session.commit()

            # Enrich results with dokumen data
            for r in results_data['results']:
                dok = Dokumen.query.get(r['dokumen_id'])
                if dok:
                    r['dokumen'] = dok

            return render_template('pencarian/hasil.html', data=results_data)

    return render_template('pencarian/pencarian.html')


@pencarian_bp.route('/hasil/<int:search_id>')
@login_required
def hasil_detail(search_id):
    history = SearchHistory.query.get_or_404(search_id)
    search_results = SearchResult.query.filter_by(
        search_id=search_id
    ).order_by(SearchResult.ranking).all()

    # Enrich with dokumen data
    for sr in search_results:
        sr.dok = Dokumen.query.get(sr.dokumen_id)

    return render_template('pencarian/hasil_detail.html',
                           history=history, search_results=search_results)
