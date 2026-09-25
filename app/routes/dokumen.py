import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, send_from_directory
from flask_login import login_required
from werkzeug.utils import secure_filename
from app import db
from app.models import Dokumen, PreprocessingResult
from app.services import preprocess

dokumen_bp = Blueprint('dokumen', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'xlsx', 'xls', 'txt', 'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@dokumen_bp.route('/kelola')
@login_required
def kelola():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    kategori_filter = request.args.get('kategori', '')

    query = Dokumen.query
    if search:
        query = query.filter(Dokumen.judul.contains(search) | Dokumen.isi_dokumen.contains(search))
    if kategori_filter:
        query = query.filter_by(kategori=kategori_filter)

    pagination = query.order_by(Dokumen.id.desc()).paginate(page=page, per_page=15, error_out=False)
    kategoris = db.session.query(Dokumen.kategori).distinct().all()
    kategori_list = sorted([k[0] for k in kategoris])

    return render_template('dokumen/kelola.html',
                           dokumen_list=pagination.items,
                           pagination=pagination,
                           search=search,
                           kategori_filter=kategori_filter,
                           kategori_list=kategori_list)


@dokumen_bp.route('/kelola/tambah', methods=['GET', 'POST'])
@login_required
def tambah():
    if request.method == 'POST':
        judul = request.form.get('judul', '').strip()
        nomor = request.form.get('nomor_dokumen', '').strip()
        jenis = request.form.get('jenis_surat', '').strip()
        tanggal = request.form.get('tanggal_dokumen', '')
        pengirim = request.form.get('pengirim_tujuan', '').strip()
        isi = request.form.get('isi_dokumen', '').strip()
        kata_kunci = request.form.get('kata_kunci', '').strip()

        if not judul:
            flash('Judul wajib diisi.', 'danger')
            return render_template('dokumen/tambah.html')

        # === AI CATEGORY PREDICTION ===
        from app.services.tfidf_service import tfidf_service
        from app.services.naive_bayes_service import nb_service
        
        text_for_ai = f"{judul} {isi} {kata_kunci}"
        try:
            # Transform and predict
            X_new = tfidf_service.vectorizer.transform([text_for_ai])
            predicted_kategori = nb_service.predict(X_new)
        except Exception as e:
            flash('Error saat memprediksi kategori AI. Pastikan AI sudah di-training!', 'danger')
            return redirect(url_for('dokumen.kelola'))

        file_path = ''
        file = request.files.get('file')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join('uploads', filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        from datetime import datetime
        tgl = datetime.utcnow().date()
        if tanggal:
            try:
                tgl = datetime.strptime(tanggal, '%Y-%m-%d').date()
            except ValueError:
                pass

        dokumen = Dokumen(
            judul=judul, kategori=predicted_kategori, nomor_dokumen=nomor,
            jenis_surat=jenis or predicted_kategori, tanggal_dokumen=tgl,
            pengirim_tujuan=pengirim, isi_dokumen=isi,
            kata_kunci=kata_kunci, file_path=file_path
        )
        db.session.add(dokumen)
        db.session.commit()

        # Run preprocessing
        text = f"{judul} {isi} {kata_kunci}"
        prep = preprocess(text)
        pr = PreprocessingResult(
            dokumen_id=dokumen.id,
            original_text=text,
            case_folding=prep['case_folding'],
            tokenizing=prep['tokenizing'],
            filtering=prep['filtering'],
            stemming=prep['stemming']
        )
        db.session.add(pr)
        db.session.commit()

        # Update search engine models
        from app.services.search_engine import update_models
        update_models()

        flash('Dokumen berhasil ditambahkan.', 'success')
        return redirect(url_for('dokumen.kelola'))

    return render_template('dokumen/tambah.html')


@dokumen_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    dokumen = Dokumen.query.get_or_404(id)

    if request.method == 'POST':
        dokumen.judul = request.form.get('judul', '').strip()
        dokumen.kategori = request.form.get('kategori', '').strip()
        dokumen.nomor_dokumen = request.form.get('nomor_dokumen', '').strip()
        dokumen.jenis_surat = request.form.get('jenis_surat', '').strip() or dokumen.kategori
        dokumen.pengirim_tujuan = request.form.get('pengirim_tujuan', '').strip()
        dokumen.isi_dokumen = request.form.get('isi_dokumen', '').strip()
        dokumen.kata_kunci = request.form.get('kata_kunci', '').strip()

        tanggal = request.form.get('tanggal_dokumen', '')
        from datetime import datetime
        if tanggal:
            try:
                dokumen.tanggal_dokumen = datetime.strptime(tanggal, '%Y-%m-%d').date()
            except ValueError:
                pass
        else:
            if not dokumen.tanggal_dokumen:
                dokumen.tanggal_dokumen = datetime.utcnow().date()

        db.session.commit()

        # Update preprocessing
        text = f"{dokumen.judul} {dokumen.isi_dokumen} {dokumen.kata_kunci}"
        prep = preprocess(text)
        pr = PreprocessingResult.query.filter_by(dokumen_id=dokumen.id).first()
        if pr:
            pr.original_text = text
            pr.case_folding = prep['case_folding']
            pr.tokenizing = prep['tokenizing']
            pr.filtering = prep['filtering']
            pr.stemming = prep['stemming']
        else:
            pr = PreprocessingResult(
                dokumen_id=dokumen.id, original_text=text,
                case_folding=prep['case_folding'], tokenizing=prep['tokenizing'],
                filtering=prep['filtering'], stemming=prep['stemming']
            )
            db.session.add(pr)
        db.session.commit()

        # Update search engine models
        from app.services.search_engine import update_models
        update_models()

        flash('Dokumen berhasil diupdate.', 'success')
        return redirect(url_for('dokumen.kelola'))

    return render_template('dokumen/edit.html', dokumen=dokumen)


@dokumen_bp.route('/<int:id>/hapus', methods=['POST'])
@login_required
def hapus(id):
    d = Dokumen.query.get_or_404(id)
    
    # Hapus file jika ada
    if d.file_path:
        filename = os.path.basename(d.file_path)
        actual_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(actual_path):
            try:
                os.remove(actual_path)
            except:
                pass
        elif os.path.exists(d.file_path): # fallback if it's already an absolute path elsewhere
            try:
                os.remove(d.file_path)
            except:
                pass

    # Hapus hasil preprocessing dan evaluasi terkait
    PreprocessingResult.query.filter_by(dokumen_id=id).delete()
    
    db.session.delete(d)
    db.session.commit()
    
    # Update search engine models
    from app.services.search_engine import update_models
    update_models()

    flash('Dokumen berhasil dihapus!', 'success')
    return redirect(url_for('dokumen.kelola'))

@dokumen_bp.route('/<int:id>/detail', methods=['GET'])
@login_required
def detail(id):
    d = Dokumen.query.get_or_404(id)
    prep = PreprocessingResult.query.filter_by(dokumen_id=id).first()
    stemmed_text = ""
    if prep and prep.stemming:
        import json
        try:
            stemmed_text = " ".join(json.loads(prep.stemming))
        except:
            pass
    return render_template('dokumen/detail.html', d=d, prep=prep, stemmed_text=stemmed_text)

@dokumen_bp.route('/<int:id>/unduh', methods=['GET'])
@login_required
def unduh(id):
    d = Dokumen.query.get_or_404(id)
    if d.file_path:
        filename = os.path.basename(d.file_path)
        directory = current_app.config['UPLOAD_FOLDER']
        actual_path = os.path.join(directory, filename)
        
        if os.path.exists(actual_path):
            return send_from_directory(directory, filename, as_attachment=True)
        elif os.path.exists(d.file_path):
            return send_from_directory(os.path.dirname(d.file_path), filename, as_attachment=True)
            
    flash('File fisik tidak ditemukan di server.', 'danger')
    return redirect(url_for('dokumen.detail', id=id))

from flask import jsonify

@dokumen_bp.route('/kelola/extract_text', methods=['POST'])
@login_required
def extract_text():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Tidak ada file yang diunggah'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nama file kosong'})
        
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Format file tidak didukung. Harap gunakan PDF atau DOCX'})
        
    try:
        ext = file.filename.rsplit('.', 1)[1].lower()
        extracted_text = ''
        
        if ext == 'pdf':
            import fitz # PyMuPDF
            pdf_document = fitz.open(stream=file.read(), filetype='pdf')
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                extracted_text += page.get_text()
            pdf_document.close()
            
        elif ext in ['docx', 'doc']:
            import docx
            from io import BytesIO
            doc = docx.Document(BytesIO(file.read()))
            extracted_text = '\n'.join([para.text for para in doc.paragraphs])
            
        elif ext == 'txt':
            extracted_text = file.read().decode('utf-8', errors='ignore')
            
        else:
            return jsonify({'success': False, 'error': 'Tipe file ini tidak didukung untuk ekstraksi otomatis.'})
            
        import re
        extracted = extracted_text.strip()
        
        # RegEx untuk Nomor
        match_nomor = re.search(r'(?i)(?:nomor|no)\s*(?::|.)?\s*([A-Za-z0-9/.-]+)', extracted)
        nomor = match_nomor.group(1).strip() if match_nomor else ''
        
        # RegEx untuk Pengirim/Tujuan
        match_tujuan = re.search(r'(?i)kepada\s*(?:yth\.?|:)?\s*([^\n]+)', extracted)
        tujuan = match_tujuan.group(1).strip() if match_tujuan else ''
        
        # RegEx untuk Tanggal (Bulan teks atau DD-MM-YYYY)
        match_tanggal = re.search(r'(?i)\b(\d{1,2}\s+(?:januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s+\d{4})\b', extracted)
        tanggal = match_tanggal.group(1).strip() if match_tanggal else ''
        
        # Konversi bulan teks ke format YYYY-MM-DD agar masuk ke form tipe date HTML
        tgl_format_html = ''
        if tanggal:
            bulan_map = {'januari':'01', 'februari':'02', 'maret':'03', 'april':'04', 'mei':'05', 'juni':'06', 'juli':'07', 'agustus':'08', 'september':'09', 'oktober':'10', 'november':'11', 'desember':'12'}
            parts = tanggal.lower().split()
            if len(parts) == 3:
                try:
                    d = str(int(parts[0])).zfill(2)
                    m = bulan_map.get(parts[1], '01')
                    y = parts[2]
                    tgl_format_html = f'{y}-{m}-{d}'
                except: pass
        
        if not tgl_format_html:
            match_tanggal_angka = re.search(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b', extracted)
            if match_tanggal_angka:
                try:
                    d = str(int(match_tanggal_angka.group(1))).zfill(2)
                    m = str(int(match_tanggal_angka.group(2))).zfill(2)
                    y = match_tanggal_angka.group(3)
                    tgl_format_html = f'{y}-{m}-{d}'
                except: pass
        
        return jsonify({'success': True, 'text': extracted, 'nomor': nomor, 'tujuan': tujuan, 'tanggal': tgl_format_html})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
