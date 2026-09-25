from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import SearchHistory, SearchResult, Dokumen
from app.services.search_engine import search

riwayat_bp = Blueprint('riwayat', __name__)


@riwayat_bp.route('/riwayat')
@login_required
def riwayat():
    page = request.args.get('page', 1, type=int)
    pagination = SearchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(
        SearchHistory.search_date.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    return render_template('riwayat/riwayat.html',
                           searches=pagination.items,
                           pagination=pagination)


@riwayat_bp.route('/riwayat/cari-ulang/<int:id>')
@login_required
def cari_ulang(id):
    """Klik riwayat → jalankan ulang pencarian dengan query yang sama."""
    history = SearchHistory.query.get_or_404(id)

    if history.user_id != current_user.id:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('riwayat.riwayat'))

    # Jalankan pencarian ulang menggunakan query lama
    results_data = search(history.query_text)

    # Tambahkan data dokumen ke hasil
    for r in results_data['results']:
        dok = Dokumen.query.get(r['dokumen_id'])
        if dok:
            r['dokumen'] = dok

    return render_template('pencarian/hasil.html', data=results_data)


@riwayat_bp.route('/riwayat/hapus/<int:id>', methods=['POST'])
@login_required
def hapus(id):
    history = SearchHistory.query.get_or_404(id)
    if history.user_id == current_user.id:
        # Hapus search_results terkait dulu (foreign key)
        SearchResult.query.filter_by(search_id=id).delete()
        db.session.delete(history)
        db.session.commit()
        flash('Satu riwayat pencarian berhasil dihapus.', 'success')
    return redirect(url_for('riwayat.riwayat'))


@riwayat_bp.route('/riwayat/hapus_semua', methods=['POST'])
@login_required
def hapus_semua():
    # Ambil semua search_id milik user ini
    user_histories = SearchHistory.query.filter_by(user_id=current_user.id).all()
    history_ids = [h.id for h in user_histories]

    # Hapus search_results terkait dulu
    if history_ids:
        SearchResult.query.filter(SearchResult.search_id.in_(history_ids)).delete(synchronize_session=False)

    # Baru hapus history-nya
    SearchHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Seluruh riwayat pencarian berhasil dibersihkan.', 'success')
    return redirect(url_for('riwayat.riwayat'))
