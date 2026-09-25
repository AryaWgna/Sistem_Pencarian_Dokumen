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
        kategori = request.form.get('kategori', '').strip()
        nomor = request.form.get('nomor_dokumen', '').strip()
        jenis = request.form.get('jenis_surat', '').strip()
        tanggal = request.form.get('tanggal_dokumen', '')
        pengirim = request.form.get('pengirim_tujuan', '').strip()
        isi = request.form.get('isi_dokumen', '').strip()
        kata_kunci = request.form.get('kata_kunci', '').strip()

        if not judul or not kategori:
            flash('Judul dan Kategori wajib diisi.', 'danger')
            return render_template('dokumen/tambah.html')

        file_path = ''
        file = request.files.get('file')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join('uploads', filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        from datetime import datetime
        tgl = None
        if tanggal:
            try:
                tgl = datetime.strptime(tanggal, '%Y-%m-%d').date()
            except ValueError:
                pass

        dokumen = Dokumen(
            judul=judul, kategori=kategori, nomor_dokumen=nomor,
            jenis_surat=jenis or kategori, tanggal_dokumen=tgl,
            pengirim_tujuan=pengirim, isi_dokumen=isi,
            kata_kunci=kata_kunci, file_path=file_path
        )
        db.session.add(dokumen)
        db.session.commit()

        # Run preprocessing
        text = f"{judul} {isi}"
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
        if tanggal:
            from datetime import datetime
            try:
                dokumen.tanggal_dokumen = datetime.strptime(tanggal, '%Y-%m-%d').date()
            except ValueError:
                pass

        db.session.commit()

        # Update preprocessing
        text = f"{dokumen.judul} {dokumen.isi_dokumen}"
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
