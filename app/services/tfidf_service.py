"""TF-IDF Vectorization Service using Scikit-learn"""
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from app.config import Config


class TfidfService:
    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.doc_ids = []
        self._load_model()

    def _load_model(self):
        if os.path.exists(Config.TFIDF_MODEL_PATH):
            data = joblib.load(Config.TFIDF_MODEL_PATH)
            self.vectorizer = data['vectorizer']
            self.tfidf_matrix = data['matrix']
            self.doc_ids = data['doc_ids']

    def fit(self, documents, doc_ids):
        """Build TF-IDF matrix from preprocessed documents.
        documents: list of preprocessed text strings
        doc_ids: list of corresponding document IDs
        """
        self.vectorizer = TfidfVectorizer(max_features=5000)
        self.tfidf_matrix = self.vectorizer.fit_transform(documents)
        self.doc_ids = doc_ids
        self._save_model()

    def transform(self, text):
        """Transform a query text into TF-IDF vector"""
        if self.vectorizer is None:
            raise RuntimeError("TF-IDF model not trained. Run train_model.py first.")
        return self.vectorizer.transform([text])

    def get_feature_names(self):
        if self.vectorizer is None:
            return []
        return self.vectorizer.get_feature_names_out().tolist()

    def get_tfidf_details(self, text):
        """Get TF-IDF scores for each term in the text"""
        vec = self.transform(text)
        feature_names = self.get_feature_names()
        scores = {}
        cx = vec.tocoo()
        for _, col, val in zip(cx.row, cx.col, cx.data):
            scores[feature_names[col]] = round(val, 4)
        return dict(sorted(scores.items(), key=lambda x: -x[1]))

    def _save_model(self):
        os.makedirs(os.path.dirname(Config.TFIDF_MODEL_PATH), exist_ok=True)
        joblib.dump({
            'vectorizer': self.vectorizer,
            'matrix': self.tfidf_matrix,
            'doc_ids': self.doc_ids
        }, Config.TFIDF_MODEL_PATH)


# Singleton
tfidf_service = TfidfService()
