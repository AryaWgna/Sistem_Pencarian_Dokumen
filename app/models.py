from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    searches = db.relationship('SearchHistory', backref='user', lazy=True)


class Dokumen(db.Model):
    __tablename__ = 'dokumen'
    id = db.Column(db.Integer, primary_key=True)
    nomor_dokumen = db.Column(db.String(100))
    judul = db.Column(db.String(255), nullable=False)
    kategori = db.Column(db.String(50), nullable=False, index=True)
    jenis_surat = db.Column(db.String(50))
    tanggal_dokumen = db.Column(db.Date, index=True)
    pengirim_tujuan = db.Column(db.String(255))
    isi_dokumen = db.Column(db.Text)
    kata_kunci = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    preprocessing = db.relationship('PreprocessingResult', backref='dokumen', uselist=False, cascade='all, delete-orphan')
    classifications = db.relationship('ClassificationResult', backref='dokumen', lazy=True, cascade='all, delete-orphan')


class PreprocessingResult(db.Model):
    __tablename__ = 'preprocessing_results'
    id = db.Column(db.Integer, primary_key=True)
    dokumen_id = db.Column(db.Integer, db.ForeignKey('dokumen.id', ondelete='CASCADE'), nullable=False)
    original_text = db.Column(db.Text)
    case_folding = db.Column(db.Text)
    tokenizing = db.Column(db.Text)
    filtering = db.Column(db.Text)
    stemming = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TfidfScore(db.Model):
    __tablename__ = 'tfidf_scores'
    id = db.Column(db.Integer, primary_key=True)
    dokumen_id = db.Column(db.Integer, db.ForeignKey('dokumen.id', ondelete='CASCADE'), nullable=False)
    term = db.Column(db.String(100), nullable=False, index=True)
    tf_score = db.Column(db.Float, default=0)
    idf_score = db.Column(db.Float, default=0)
    tfidf_score = db.Column(db.Float, default=0)


class ClassificationResult(db.Model):
    __tablename__ = 'classification_results'
    id = db.Column(db.Integer, primary_key=True)
    dokumen_id = db.Column(db.Integer, db.ForeignKey('dokumen.id', ondelete='CASCADE'), nullable=False)
    predicted_kategori = db.Column(db.String(50), nullable=False)
    confidence_score = db.Column(db.Float, default=0)
    is_correct = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    query_text = db.Column(db.Text, nullable=False)
    preprocessed_query = db.Column(db.Text)
    predicted_kategori = db.Column(db.String(50))
    results_count = db.Column(db.Integer, default=0)
    response_time_ms = db.Column(db.Integer, default=0)
    search_date = db.Column(db.DateTime, default=datetime.utcnow)

    results = db.relationship('SearchResult', backref='search', lazy=True, cascade='all, delete-orphan')


class SearchResult(db.Model):
    __tablename__ = 'search_results'
    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey('search_history.id', ondelete='CASCADE'), nullable=False)
    dokumen_id = db.Column(db.Integer, db.ForeignKey('dokumen.id', ondelete='CASCADE'), nullable=False)
    similarity_score = db.Column(db.Float, default=0)
    ranking = db.Column(db.Integer, default=0)

    dokumen = db.relationship('Dokumen', lazy=True)


class ModelEvaluation(db.Model):
    __tablename__ = 'model_evaluation'
    id = db.Column(db.Integer, primary_key=True)
    kategori = db.Column(db.String(50), nullable=False)
    precision_score = db.Column(db.Float, default=0)
    recall_score = db.Column(db.Float, default=0)
    f1_score = db.Column(db.Float, default=0)
    support = db.Column(db.Integer, default=0)
    accuracy = db.Column(db.Float, default=0)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)
