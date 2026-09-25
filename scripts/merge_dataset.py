"""Merge all CSV datasets into final dataset and generate SQL seed file"""
import sys, io, os, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs('sql', exist_ok=True)

# Read all CSVs
all_records = []
for csv_file in ['dataset/dokumen_excel.csv', 'dataset/dokumen_files.csv', 'dataset/dokumen_augmented.csv']:
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_records.append(row)

# Assign IDs
for i, r in enumerate(all_records, 1):
    r['id'] = i

# Write final CSV
fieldnames = ['id', 'judul', 'kategori', 'jenis_surat', 'nomor_dokumen', 'tanggal_dokumen',
              'pengirim_tujuan', 'isi_dokumen', 'sumber', 'file_path']
with open('dataset/dokumen_final.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_records)

# Generate SQL seed file
def escape_sql(s):
    if not s:
        return ''
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")

with open('sql/seed_data.sql', 'w', encoding='utf-8') as f:
    f.write("-- =============================================\n")
    f.write("-- SEED DATA: 300+ Dokumen SLB\n")
    f.write("-- Import ke phpMyAdmin setelah create_database.sql\n")
    f.write("-- =============================================\n\n")
    f.write("USE db_pencarian_dokumen_slb;\n\n")
    f.write("-- Hapus data lama jika ada\n")
    f.write("TRUNCATE TABLE search_results;\n")
    f.write("TRUNCATE TABLE search_history;\n")
    f.write("TRUNCATE TABLE model_evaluation;\n")
    f.write("TRUNCATE TABLE classification_results;\n")
    f.write("TRUNCATE TABLE tfidf_scores;\n")
    f.write("TRUNCATE TABLE preprocessing_results;\n")
    f.write("DELETE FROM dokumen;\n")
    f.write("ALTER TABLE dokumen AUTO_INCREMENT = 1;\n\n")
    
    f.write("-- Insert dokumen\n")
    for r in all_records:
        judul = escape_sql(r['judul'])
        kategori = escape_sql(r['kategori'])
        jenis = escape_sql(r.get('jenis_surat', ''))
        nomor = escape_sql(r.get('nomor_dokumen', ''))
        tanggal = r.get('tanggal_dokumen', '')
        if not tanggal or tanggal == 'nan' or tanggal == '':
            tanggal = 'NULL'
        else:
            tanggal = f"'{tanggal}'"
        pengirim = escape_sql(r.get('pengirim_tujuan', ''))
        isi = escape_sql(r.get('isi_dokumen', ''))
        file_path = escape_sql(r.get('file_path', ''))
        
        f.write(f"INSERT INTO dokumen (nomor_dokumen, judul, kategori, jenis_surat, tanggal_dokumen, pengirim_tujuan, isi_dokumen, file_path) VALUES ('{nomor}', '{judul}', '{kategori}', '{jenis}', {tanggal}, '{pengirim}', '{isi}', '{file_path}');\n")
    
    f.write(f"\n-- Total: {len(all_records)} dokumen inserted\n")

from collections import Counter
cats = Counter(r['kategori'] for r in all_records)
print(f'=== FINAL DATASET ===')
print(f'Total documents: {len(all_records)}')
print(f'\nDistribution:')
for cat, count in cats.most_common():
    print(f'  {cat}: {count}')
print(f'\nSaved to:')
print(f'  dataset/dokumen_final.csv')
print(f'  sql/seed_data.sql')
