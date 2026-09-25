"""Naive Bayes Classification Service using Scikit-learn MultinomialNB"""
import os
import joblib
import numpy as np
from sklearn.naive_bayes import MultinomialNB
from app.config import Config


class NaiveBayesService:
    def __init__(self):
        self.model = None
        self.classes = []
        self._load_model()

    def _load_model(self):
        if os.path.exists(Config.NB_MODEL_PATH):
            data = joblib.load(Config.NB_MODEL_PATH)
            self.model = data['model']
            self.classes = data['classes']

    def train(self, X_train, y_train):
        """Train Naive Bayes model.
        X_train: TF-IDF sparse matrix
        y_train: list/array of category labels
        """
        # Set fit_prior=False agar kelas dengan jumlah dokumen terbanyak (seperti Surat Umum)
        # tidak mendominasi prediksi pada query pencarian yang pendek.
        self.model = MultinomialNB(alpha=1.0, fit_prior=False)
        self.model.fit(X_train, y_train)
        self.classes = self.model.classes_.tolist()
        self._save_model()

    def predict(self, X):
        """Predict category for TF-IDF vector(s)"""
        if self.model is None:
            raise RuntimeError("NB model not trained. Run train_model.py first.")
        return self.model.predict(X)[0]

    def predict_proba(self, X):
        """Get prediction probabilities for each category"""
        if self.model is None:
            raise RuntimeError("NB model not trained. Run train_model.py first.")
        probs = self.model.predict_proba(X)[0]
        return dict(zip(self.classes, [round(p, 4) for p in probs]))

    def get_confidence(self, X):
        """Get the confidence score (max probability) for prediction"""
        probs = self.model.predict_proba(X)[0]
        return round(float(np.max(probs)), 4)

    def _save_model(self):
        os.makedirs(os.path.dirname(Config.NB_MODEL_PATH), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'classes': self.classes
        }, Config.NB_MODEL_PATH)


# Singleton
nb_service = NaiveBayesService()
