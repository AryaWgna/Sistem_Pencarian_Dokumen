-- ============================================
-- DATABASE SCHEMA: Sistem Pencarian Dokumen SLB
-- TF-IDF + Naive Bayes | Flask Python
-- Import ke phpMyAdmin (XAMPP)
-- ============================================

CREATE DATABASE IF NOT EXISTS db_pencarian_dokumen_slb
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE db_pencarian_dokumen_slb;

-- ============================================
-- Tabel 1: users (Autentikasi pengguna)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- Tabel 2: dokumen (Data dokumen utama)
-- ============================================
CREATE TABLE IF NOT EXISTS dokumen (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nomor_dokumen VARCHAR(100),
    judul VARCHAR(255) NOT NULL,
    kategori VARCHAR(50) NOT NULL,
    jenis_surat VARCHAR(50),
    tanggal_dokumen DATE,
    pengirim_tujuan VARCHAR(255),
    isi_dokumen TEXT,
    kata_kunci TEXT,
    file_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_kategori (kategori),
    INDEX idx_tanggal (tanggal_dokumen)
) ENGINE=InnoDB;

-- ============================================
-- Tabel 3: preprocessing_results (Hasil preprocessing)
-- ============================================
CREATE TABLE IF NOT EXISTS preprocessing_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dokumen_id INT NOT NULL,
    original_text TEXT,
    case_folding TEXT,
    tokenizing TEXT,
    filtering TEXT,
    stemming TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dokumen_id) REFERENCES dokumen(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- Tabel 4: tfidf_scores (Bobot TF-IDF per dokumen)
-- ============================================
CREATE TABLE IF NOT EXISTS tfidf_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dokumen_id INT NOT NULL,
    term VARCHAR(100) NOT NULL,
    tf_score DOUBLE DEFAULT 0,
    idf_score DOUBLE DEFAULT 0,
    tfidf_score DOUBLE DEFAULT 0,
    FOREIGN KEY (dokumen_id) REFERENCES dokumen(id) ON DELETE CASCADE,
    INDEX idx_term (term),
    INDEX idx_dokumen (dokumen_id)
) ENGINE=InnoDB;

-- ============================================
-- Tabel 5: classification_results (Hasil klasifikasi NB)
-- ============================================
CREATE TABLE IF NOT EXISTS classification_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dokumen_id INT NOT NULL,
    predicted_kategori VARCHAR(50) NOT NULL,
    confidence_score DOUBLE DEFAULT 0,
    is_correct TINYINT(1) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dokumen_id) REFERENCES dokumen(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- Tabel 6: search_history (Riwayat pencarian)
-- ============================================
CREATE TABLE IF NOT EXISTS search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    query_text TEXT NOT NULL,
    preprocessed_query TEXT,
    predicted_kategori VARCHAR(50),
    results_count INT DEFAULT 0,
    response_time_ms INT DEFAULT 0,
    search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- Tabel 7: search_results (Detail hasil pencarian)
-- ============================================
CREATE TABLE IF NOT EXISTS search_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    search_id INT NOT NULL,
    dokumen_id INT NOT NULL,
    similarity_score DOUBLE DEFAULT 0,
    ranking INT DEFAULT 0,
    FOREIGN KEY (search_id) REFERENCES search_history(id) ON DELETE CASCADE,
    FOREIGN KEY (dokumen_id) REFERENCES dokumen(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- Tabel 8: model_evaluation (Hasil evaluasi model)
-- ============================================
CREATE TABLE IF NOT EXISTS model_evaluation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kategori VARCHAR(50) NOT NULL,
    precision_score DOUBLE DEFAULT 0,
    recall_score DOUBLE DEFAULT 0,
    f1_score DOUBLE DEFAULT 0,
    support INT DEFAULT 0,
    accuracy DOUBLE DEFAULT 0,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
