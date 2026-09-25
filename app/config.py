import os

class Config:
    # Gunakan environment variable SECRET_KEY di production
    # Fallback ke random key untuk development
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24).hex())
    
    # MySQL via XAMPP (phpMyAdmin)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:@localhost/db_pencarian_dokumen_slb'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Model paths
    MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
    TFIDF_MODEL_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')
    NB_MODEL_PATH = os.path.join(MODEL_DIR, 'naive_bayes_model.pkl')
