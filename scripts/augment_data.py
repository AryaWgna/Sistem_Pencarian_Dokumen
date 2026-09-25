"""Augment dataset to 300+ documents with realistic variations"""
import sys, io, os, csv, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from datetime import datetime, timedelta

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

random.seed(42)

# === Templates for each category ===

INSTANSI = [
    'Kepala Dinas Pendidikan Provinsi Jawa Barat',
    'Kantor Cabang Dinas Pendidikan Wilayah II',
    'Kepala Badan Kepegawaian Daerah Provinsi Jawa Barat',
    'Sekretaris Daerah Provinsi Jawa Barat',
    'Kepala BPKAD Provinsi Jawa Barat',
    'Universitas Pendidikan Indonesia',
    'Universitas Djuanda Bogor',
    'Institut Pertanian Bogor',
    'Universitas Pakuan Bogor',
    'Universitas Binaniaga Indonesia',
    'SDIT Alif Ciawi',
    'SDIT Nusantara',
    'SMAN 2 Kota Bogor',
    'SMAN 4 Kota Bogor',
    'SMKN 1 Kota Bogor',
    'SDN 1 Kota Bogor',
    'SLB Negeri Dharma Wanita',
    'SLB Negeri Taruna Mandiri',
    'Sekolah Alam Indonesia (SAI)',
    'Kemenag Kota Bogor',
    'Dinas Sosial Kota Bogor',
    'Dinas Kesehatan Kota Bogor',
    'BPJS Ketenagakerjaan Cabang Bogor',
    'PT Taspen Persero Cabang Bogor',
    'Bank BJB Cabang Bogor',
    'Kelurahan Rancamaya',
    'Kecamatan Bogor Selatan',
]

TUJUAN_KOTA = [
    'Kantor Cabang Dinas Pendidikan Wilayah II',
    'Dinas Pendidikan Provinsi Jawa Barat',
    'SLBN Dharma Wanita',
    'SMAN 2 Kota Bogor',
    'SMAN 4 Kota Bogor',
    'Aula Bank BJB Cabang Bogor',
    'Hotel Salak Bogor',
    'Royal Hotel Pajajaran',
    'Gedung Sate Bandung',
]

# Perihal templates per category
PERIHAL_TEMPLATES = {
    'Surat Biasa': [
        'Undangan Rapat Koordinasi {topik}',
        'Pemberitahuan Pelaksanaan Kegiatan {topik}',
        'Permohonan Data {topik} Tahun {tahun}',
        'Surat Pengantar Berkas {topik}',
        'Permohonan Kerjasama {topik}',
        'Undangan Sosialisasi {topik}',
        'Pemberitahuan Jadwal {topik}',
        'Surat Permohonan Izin {topik}',
        'Informasi Pelaksanaan {topik}',
        'Himbauan Terkait {topik}',
        'Pemberitahuan Perubahan {topik}',
        'Undangan Workshop {topik}',
        'Surat Balasan Kegiatan {topik}',
        'Permohonan Peserta Kegiatan {topik}',
        'Pemberitahuan Sosialisasi {topik}',
        'Laporan Pertanggungjawaban {topik}',
        'Surat Undangan {topik}',
        'Rekonsiliasi Data {topik}',
        'Pemutakhiran Data {topik}',
        'Percepatan Penyelesaian {topik}',
    ],
    'SPPD & Surat Perintah': [
        'Surat Perintah Perjalanan Dinas ke {tujuan} terkait {topik}',
        'SPPD Menghadiri {topik} di {tujuan}',
        'Surat Perintah Mengikuti Kegiatan {topik}',
        'SPPD Koordinasi {topik} di {tujuan}',
        'Surat Tugas Mengikuti {topik} di {tujuan}',
        'Surat Perintah Pelaksanaan {topik}',
    ],
    'Surat Keputusan': [
        'SK Penetapan {topik} Tahun Ajaran {tahun}',
        'SK Pengangkatan {topik} SLB Negeri 1 Kota Bogor',
        'SK Pembagian Tugas {topik} Tahun Pelajaran {tahun}',
        'SK Penetapan Kriteria {topik}',
        'SK Penunjukan {topik}',
        'SK Pembentukan Tim {topik}',
    ],
    'Surat Keterangan': [
        'Surat Keterangan Aktif Siswa untuk {topik}',
        'Surat Keterangan Mengikuti Kegiatan {topik}',
        'Surat Keterangan Pindah Sekolah Peserta Didik',
        'Surat Keterangan Kelakuan Baik Peserta Didik',
        'Surat Keterangan Masih Bertugas {topik}',
        'Surat Keterangan Domisili Pegawai',
    ],
    'Nota Dinas': [
        'Nota Dinas Pendataan {topik}',
        'Nota Dinas Pelaksanaan {topik}',
        'Nota Dinas Tindak Lanjut {topik}',
        'Nota Dinas Permohonan {topik}',
        'Nota Dinas Pemberitahuan {topik}',
    ],
    'Surat Edaran': [
        'Surat Edaran Tentang {topik}',
        'Edaran Pelaksanaan {topik}',
        'Surat Edaran Larangan {topik}',
        'Edaran Kewajiban {topik}',
        'Surat Edaran Himbauan {topik}',
    ],
    'Laporan': [
        'Laporan Kegiatan {topik}',
        'Laporan Pelaksanaan Program {topik}',
        'Narasi Perubahan Outcome Harvesting {topik}',
        'Laporan Pertanggungjawaban {topik}',
        'LK Budaya Sekolah {topik}',
        'Laporan Hasil Evaluasi {topik}',
    ],
    'Surat Pengumuman': [
        'Pengumuman Pelaksanaan Kegiatan {topik}',
        'Pengumuman Jadwal {topik}',
        'Pengumuman Penerimaan {topik}',
        'Pengumuman Hasil Seleksi {topik}',
        'Pengumuman Libur {topik}',
    ],
    'Dokumen Kepegawaian': [
        'Konversi Predikat Kinerja ke Angka Kredit {topik}',
        'Penetapan Angka Kredit Periode {topik}',
        'Penilaian Kinerja Pegawai {topik}',
        'Kenaikan Pangkat {topik}',
        'Kenaikan Gaji Berkala {topik}',
        'Sasaran Kinerja Pegawai (SKP) {topik}',
    ],
}

TOPIK_SLB = [
    'Pendidikan Inklusif', 'Peserta Didik Berkebutuhan Khusus',
    'Program Pancawaluya', 'BOSP SLB', 'Dapodik',
    'PIP (Program Indonesia Pintar)', 'FLS3N', 'O2SN', 'LKSN',
    'Pembelajaran Kurikulum Merdeka', 'Asesmen Diagnostik',
    'Penguatan Karakter', 'Literasi Digital', 'Gerakan Sekolah Sehat',
    'Perpustakaan Sekolah', 'Sarana Prasarana Pendidikan',
    'Buku Teks Utama', 'Makan Bergizi Gratis (MBG)',
    'Kegiatan Ekstrakulikuler', 'Program Bakti Sosial',
    'Pelatihan Guru', 'Workshop Pendidikan', 'Seminar Nasional',
    'Ujian Akhir Semester', 'Asesmen Sumatif',
    'Pendidikan Pancasila', 'Anti Narkoba (IKAN)',
    'Kesehatan Peserta Didik', 'Imunisasi Campak',
    'Ketertiban Lingkungan Sekolah', 'Kebersihan Sekolah',
    'Guru PPPK', 'Guru Tidak Tetap (GTT)',
    'Tenaga Kependidikan', 'Outsourcing Pegawai',
    'BPJS Pegawai', 'Tabungan Pajak Kendaraan',
    'Beasiswa Garuda', 'Beasiswa Pancawaluya',
    'Pelaksanaan IHT', 'Rapat Dewan Guru',
    'Penerimaan Peserta Didik Baru (PPDB)',
    'Wisuda dan Pelepasan Siswa', 'Kunjungan Edukasi',
    'Koordinasi Kepala Sekolah', 'Evaluasi Program',
    'Peringatan Hari Besar Nasional', 'Ramadan dan Idul Fitri',
    'Halal Bihalal', 'Gratifikasi dan Anti Korupsi',
    'LHKAN (Laporan Harta Kekayaan)', 'Mutasi Pegawai',
    'Pengusulan PLT Kepala Sekolah', 'Serah Terima Jabatan',
    'Pendataan GTK', 'Sertifikasi Guru',
    'Perjalanan Dinas Luar Kota', 'Perjalanan Dinas Dalam Kota',
]

ISI_TEMPLATES = {
    'Surat Biasa': [
        'Dengan hormat, sehubungan dengan pelaksanaan kegiatan {topik} yang akan dilaksanakan pada tahun {tahun}, bersama ini kami sampaikan informasi terkait pelaksanaan kegiatan tersebut di lingkungan SLB Negeri 1 Kota Bogor. Kegiatan ini bertujuan untuk meningkatkan kualitas pelayanan pendidikan bagi peserta didik berkebutuhan khusus. Demikian surat ini disampaikan, atas perhatian dan kerjasamanya diucapkan terima kasih.',
        'Menindaklanjuti surat dari {pengirim} perihal {topik}, dengan ini kami informasikan bahwa SLB Negeri 1 Kota Bogor akan berpartisipasi dalam kegiatan dimaksud. Seluruh guru dan tenaga kependidikan diharapkan dapat mempersiapkan segala sesuatu yang diperlukan. Atas perhatiannya kami ucapkan terima kasih.',
        'Berdasarkan instruksi dari {pengirim}, kami menyampaikan pemberitahuan mengenai {topik}. Hal ini sangat penting untuk diperhatikan oleh seluruh warga sekolah SLB Negeri 1 Kota Bogor demi kelancaran proses pendidikan. Mohon agar informasi ini dapat ditindaklanjuti sebagaimana mestinya.',
    ],
    'SPPD & Surat Perintah': [
        'Dasar: Surat dari {pengirim} tentang {topik}. Kepala Sekolah SLB Negeri 1 Kota Bogor memerintahkan kepada pegawai yang namanya tercantum dalam surat ini untuk melaksanakan perjalanan dinas ke {tujuan}. Lama perjalanan 1 (satu) hari kerja. Biaya perjalanan dinas dibebankan pada anggaran SLB Negeri 1 Kota Bogor.',
    ],
    'Surat Keputusan': [
        'Kepala SLB Negeri 1 Kota Bogor, Menimbang bahwa dalam rangka pelaksanaan {topik} di SLB Negeri 1 Kota Bogor Tahun Ajaran {tahun} perlu ditetapkan Surat Keputusan. Mengingat Undang-Undang Nomor 20 Tahun 2003 tentang Sistem Pendidikan Nasional, Peraturan Pemerintah yang berlaku. MEMUTUSKAN: Menetapkan keputusan ini berlaku sejak tanggal ditetapkan.',
    ],
    'Surat Keterangan': [
        'Yang bertanda tangan di bawah ini, Plt. Kepala SLB Negeri 1 Kota Bogor, menerangkan bahwa peserta didik yang bersangkutan benar-benar terdaftar dan aktif mengikuti kegiatan pembelajaran di SLB Negeri 1 Kota Bogor. Surat keterangan ini dibuat untuk keperluan {topik}. Demikian surat keterangan ini dibuat dengan sebenarnya untuk dipergunakan sebagaimana mestinya.',
    ],
    'Nota Dinas': [
        'Kepada Yth. Kepala SLB Negeri 1 Kota Bogor. Dari: {pengirim}. Sehubungan dengan {topik}, bersama ini disampaikan nota dinas untuk ditindaklanjuti sesuai dengan ketentuan yang berlaku. Mohon agar dilakukan koordinasi dan pelaporan terkait hal tersebut.',
    ],
    'Surat Edaran': [
        'Dalam rangka pelaksanaan {topik} di lingkungan SLB Negeri 1 Kota Bogor, dengan ini diedarkan ketentuan sebagai berikut: Seluruh guru dan tenaga kependidikan wajib mematuhi dan melaksanakan ketentuan yang berlaku. Surat edaran ini berlaku sejak tanggal dikeluarkan hingga ada perubahan lebih lanjut.',
    ],
    'Laporan': [
        'Laporan pelaksanaan kegiatan {topik} di SLB Negeri 1 Kota Bogor. Kegiatan ini dilaksanakan dalam rangka meningkatkan kualitas pendidikan bagi peserta didik berkebutuhan khusus. Tujuan kegiatan adalah {topik}. Sasaran kegiatan meliputi seluruh peserta didik dan tenaga pendidik. Hasil kegiatan menunjukkan perkembangan positif dalam aspek yang ditargetkan.',
    ],
    'Surat Pengumuman': [
        'Diberitahukan kepada seluruh warga sekolah SLB Negeri 1 Kota Bogor bahwa akan dilaksanakan {topik}. Seluruh pihak terkait diharapkan dapat mempersiapkan segala sesuatu yang diperlukan. Informasi lebih lanjut dapat diperoleh melalui tata usaha sekolah.',
    ],
    'Dokumen Kepegawaian': [
        'Berdasarkan ketentuan yang berlaku, dengan ini ditetapkan hasil penilaian kinerja dan konversi angka kredit untuk {topik}. Instansi: Pemerintah Provinsi Jawa Barat. Unit Kerja: SLB Negeri 1 Kota Bogor. Penetapan ini berlaku sejak tanggal ditetapkan.',
    ],
}

def random_date(start_year=2024, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).strftime('%Y-%m-%d')

def random_nomor(counter, tahun='2026'):
    bulan_map = {1:'I',2:'II',3:'III',4:'IV',5:'V',6:'VI',7:'VII',8:'VIII',9:'IX',10:'X',11:'XI',12:'XII'}
    bulan = random.choice(list(bulan_map.values()))
    return f'{counter:03d}/SLBN1/Kot.Bgr/{bulan}/{tahun}'

# Target distribution (ensure min 25 per category)
TARGET = {
    'Surat Biasa': 85,
    'SPPD & Surat Perintah': 35,
    'Surat Keputusan': 30,
    'Surat Keterangan': 30,
    'Nota Dinas': 25,
    'Surat Edaran': 25,
    'Laporan': 30,
    'Surat Pengumuman': 25,
    'Dokumen Kepegawaian': 30,
}

# Read existing data to know current counts
import pandas as pd
existing = []
for csv_file in ['dataset/dokumen_excel.csv', 'dataset/dokumen_files.csv']:
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        existing.extend(df.to_dict('records'))

from collections import Counter
current_counts = Counter(r['kategori'] for r in existing)
print('Current data counts:')
for k, v in current_counts.most_common():
    print(f'  {k}: {v}')
print(f'  Total: {sum(current_counts.values())}')

# Generate augmented data
augmented = []
counter = 100

for kategori, target in TARGET.items():
    current = current_counts.get(kategori, 0)
    needed = max(0, target - current)
    templates = PERIHAL_TEMPLATES[kategori]
    isi_templates = ISI_TEMPLATES[kategori]
    
    for i in range(needed):
        topik = random.choice(TOPIK_SLB)
        tahun = random.choice(['2024/2025', '2025/2026', '2026/2027'])
        pengirim = random.choice(INSTANSI)
        tujuan = random.choice(TUJUAN_KOTA)
        
        template = random.choice(templates)
        judul = template.format(topik=topik, tahun=tahun, tujuan=tujuan)
        
        isi_template = random.choice(isi_templates)
        isi = isi_template.format(topik=topik, tahun=tahun, pengirim=pengirim, tujuan=tujuan)
        
        counter += 1
        tanggal = random_date()
        nomor = random_nomor(counter, tanggal[:4])
        
        augmented.append({
            'judul': judul,
            'kategori': kategori,
            'jenis_surat': kategori,
            'nomor_dokumen': nomor,
            'tanggal_dokumen': tanggal,
            'pengirim_tujuan': pengirim if kategori != 'SPPD & Surat Perintah' else tujuan,
            'isi_dokumen': isi,
            'sumber': 'augmented',
            'file_path': ''
        })

# Write augmented CSV
fieldnames = ['judul', 'kategori', 'jenis_surat', 'nomor_dokumen', 'tanggal_dokumen',
              'pengirim_tujuan', 'isi_dokumen', 'sumber', 'file_path']
with open('dataset/dokumen_augmented.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(augmented)

aug_counts = Counter(r['kategori'] for r in augmented)
print(f'\nAugmented records generated: {len(augmented)}')
for k, v in aug_counts.most_common():
    print(f'  {k}: {v}')
print(f'Saved to dataset/dokumen_augmented.csv')

# Final totals
print(f'\n=== PROJECTED TOTALS ===')
total = 0
for kategori in TARGET:
    c = current_counts.get(kategori, 0) + aug_counts.get(kategori, 0)
    print(f'  {kategori}: {c}')
    total += c
print(f'  TOTAL: {total}')
