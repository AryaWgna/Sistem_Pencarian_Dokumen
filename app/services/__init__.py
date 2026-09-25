"""Text Preprocessing untuk Bahasa Indonesia
4 Tahap: Case Folding → Tokenizing → Filtering → Stemming
"""
import re
import json
import nltk
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# Download NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Initialize stemmer (singleton — expensive to create)
_stemmer_factory = StemmerFactory()
_stemmer = _stemmer_factory.create_stemmer()

# Indonesian stopwords from NLTK + custom additions
STOPWORDS_ID = set(stopwords.words('indonesian'))
STOPWORDS_ID.update([
    'yang', 'dan', 'di', 'ke', 'dari', 'ini', 'itu', 'dengan', 'untuk',
    'pada', 'adalah', 'akan', 'juga', 'tidak', 'saya', 'kami', 'kita',
    'mereka', 'ada', 'oleh', 'telah', 'atau', 'bahwa', 'serta', 'bagi',
    'dalam', 'lain', 'hal', 'tersebut', 'sebagai', 'dapat', 'sudah',
    'agar', 'jika', 'maka', 'saat', 'secara', 'hanya', 'namun', 'lebih',
    'antara', 'setiap', 'terhadap', 'bersama', 'melalui', 'tentang',
    'kepada', 'yth', 'hormat', 'demikian', 'atas', 'mohon',
    'nomor', 'tanggal', 'tahun', 'bulan', 'hari',
])


def case_folding(text):
    """Step 1: Convert to lowercase, remove numbers, punctuation, extra whitespace"""
    text = text.lower()
    text = re.sub(r'[^a-z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def tokenizing(text):
    """Step 2: Split text into word tokens"""
    return word_tokenize(text)


def filtering(tokens):
    """Step 3: Remove stopwords and short tokens"""
    return [t for t in tokens if t not in STOPWORDS_ID and len(t) > 2]


def stemming(tokens):
    """Step 4: Reduce words to root form using Sastrawi (Nazief-Adriani algorithm)"""
    return [_stemmer.stem(t) for t in tokens]


def preprocess(text):
    """Full preprocessing pipeline. Returns dict with each step's result."""
    step1 = case_folding(text)
    step2 = tokenizing(step1)
    step3 = filtering(step2)
    step4 = stemming(step3)
    return {
        'original': text,
        'case_folding': step1,
        'tokenizing': json.dumps(step2, ensure_ascii=False),
        'filtering': json.dumps(step3, ensure_ascii=False),
        'stemming': json.dumps(step4, ensure_ascii=False),
        'result': ' '.join(step4)  # Final preprocessed text as string
    }


def preprocess_text(text):
    """Convenience: returns final preprocessed string only"""
    return preprocess(text)['result']
