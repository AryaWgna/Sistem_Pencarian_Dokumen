"""Train Naive Bayes model and evaluate with Precision, Recall, F1-Score"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import preprocessing
from app.services import preprocess_text

print("=" * 60)
print("TRAINING NAIVE BAYES MODEL")
print("Sistem Pencarian Dokumen Digital SLB")
print("TF-IDF + Naive Bayes")
print("=" * 60)

# Load dataset dari database
from app import create_app
from app.models import Dokumen

app = create_app()
with app.app_context():
    docs = Dokumen.query.all()
    data = []
    for d in docs:
        data.append({
            'id': d.id,
            'kategori': d.kategori,
            'judul': d.judul,
            'isi_dokumen': d.isi_dokumen
        })
    df = pd.DataFrame(data)
print(f"\nDataset: {len(df)} dokumen, {df['kategori'].nunique()} kategori")
print(f"\nDistribusi kategori:")
print(df['kategori'].value_counts().to_string())

# Combine judul + isi for richer text
df['text'] = df['judul'].fillna('') + ' ' + df['isi_dokumen'].fillna('')

# Preprocess all documents
print("\nPreprocessing dokumen...")
df['preprocessed'] = df['text'].apply(preprocess_text)
print(f"Preprocessing selesai.")

# Remove empty preprocessed texts
df = df[df['preprocessed'].str.strip().astype(bool)].reset_index(drop=True)
print(f"Dokumen setelah filter: {len(df)}")

# Train/Test Split (80:20, stratified)
X = df['preprocessed'].values
y = df['kategori'].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nSplit: {len(X_train)} training, {len(X_test)} testing")

# TF-IDF Vectorization
print("\nTF-IDF Vectorization...")
tfidf_vectorizer = TfidfVectorizer(max_features=5000)
X_train_tfidf = tfidf_vectorizer.fit_transform(X_train)
X_test_tfidf = tfidf_vectorizer.transform(X_test)
print(f"Vocabulary size: {len(tfidf_vectorizer.vocabulary_)}")

# Train Naive Bayes
print("\nTraining Multinomial Naive Bayes...")
nb_model = MultinomialNB(alpha=1.0)
nb_model.fit(X_train_tfidf, y_train)

# Predict on test set
y_pred = nb_model.predict(X_test_tfidf)

# Evaluation
print("\n" + "=" * 60)
print("HASIL EVALUASI MODEL")
print("=" * 60)

accuracy = accuracy_score(y_test, y_pred)
print(f"\nAccuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")

print(f"\n{'='*60}")
print("CLASSIFICATION REPORT")
print("=" * 60)
report = classification_report(y_test, y_pred, zero_division=0)
print(report)

print(f"{'='*60}")
print("CONFUSION MATRIX")
print("=" * 60)
labels = sorted(set(y_test) | set(y_pred))
cm = confusion_matrix(y_test, y_pred, labels=labels)
print(f"\nLabels: {labels}")
print(cm)

# Save models
os.makedirs('models', exist_ok=True)

# Save TF-IDF (with full dataset matrix for search)
print("\nRebuilding TF-IDF on full dataset for search engine...")
X_all_tfidf = tfidf_vectorizer.fit_transform(df['preprocessed'].values)
doc_ids = df['id'].values.tolist()

joblib.dump({
    'vectorizer': tfidf_vectorizer,
    'matrix': X_all_tfidf,
    'doc_ids': doc_ids
}, 'models/tfidf_vectorizer.pkl')
print(f"Saved: models/tfidf_vectorizer.pkl")

# Save NB model (retrain on full dataset)
nb_model_full = MultinomialNB(alpha=1.0)
nb_model_full.fit(X_all_tfidf, df['kategori'].values)
joblib.dump({
    'model': nb_model_full,
    'classes': nb_model_full.classes_.tolist()
}, 'models/naive_bayes_model.pkl')
print(f"Saved: models/naive_bayes_model.pkl")

# Save evaluation results for DB import
report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
eval_results = []
for label in labels:
    if label in report_dict:
        eval_results.append({
            'kategori': label,
            'precision': report_dict[label]['precision'],
            'recall': report_dict[label]['recall'],
            'f1_score': report_dict[label]['f1-score'],
            'support': report_dict[label]['support'],
            'accuracy': accuracy
        })
pd.DataFrame(eval_results).to_csv('dataset/model_evaluation.csv', index=False)
print(f"Saved: dataset/model_evaluation.csv")

print(f"\n{'='*60}")
print("TRAINING SELESAI!")
print(f"{'='*60}")
