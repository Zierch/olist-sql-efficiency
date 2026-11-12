#!/usr/bin/env python3
"""
Bagian ekor terjemahan Indonesia: Bagian 4.6-4.9, Kesimpulan (Bagian 5), dan
back matter (Ucapan Terima Kasih, Pernyataan, Ketersediaan Data dan Perangkat
Lunak, Lampiran A).

Semua helper, tabel, dan angka diambil dari build_paper_id.py sehingga
penyusunannya konsisten dengan bagian depan paper.
"""
from __future__ import annotations

import build_paper_id as B


# ==========================================================================
# 4.6 - 4.9
# ==========================================================================
def results_tail(r: "B.Results") -> str:
    p = []

    # ---- 4.6 -----------------------------------------------------------
    p.append(B.h2("4.6 Workload Multi-Tabel dan Analitik"))
    a, b = "W6.1 flat JOIN", "W6.2 derived table"
    ra, rb = r.med("C4_covering", a) or 0, r.med("C4_covering", b) or 0
    p.append(B.body(
        f"Workload yang paling berat justru kebal terhadap indeksasi. W6.1 "
        f"menggabungkan orders, customers, dan order items lalu mengelompokkan "
        f"hasilnya berdasarkan provinsi dan bulan, dengan biaya "
        f"{B.msu(r.med('C0_zero', a))} di C0 dan {B.msu(ra)} di C4, artinya "
        f"percepatan sebesar {B.xx(r.speedup('C4_covering', a))} dan jadi "
        f"kemunduran kecil, bukan perbaikan. W7.1, yang merangking seller di "
        f"dalam tiap provinsi memakai window function di atas sebuah agregat, "
        f"membaik hanya di konfigurasi komposit, dari "
        f"{B.msu(r.med('C0_zero', 'W7.1'))} ke "
        f"{B.msu(r.med('C3_composite', 'W7.1'))}. "
        f"Index yang menurunkan biaya mencari baris tidak mungkin menurunkan "
        f"biaya dasar untuk menggabungkan dan mengelompokkannya, dan untuk "
        f"sebuah query yang baris yang lolos predikatnya adalah sebagian besar "
        f"isi relasi, "
        f"tidak ada yang bisa dicari lebih murah."))
    ratios = {}
    for cfg in B.CONFIG_ORDER:
        fa, de = r.med(cfg, a), r.med(cfg, b)
        if fa and de:
            ratios[cfg] = de / fa
    faster = [c for c, v in ratios.items() if v < 1.0]
    p.append(B.body(
        f"W6.2 menghitung hasil yang sama dengan W6.1, hanya join-nya dinaikkan "
        f"ke dalam sebuah derived table, dan sengaja dimasukkan untuk menguji "
        f"apakah penulisan ulang bentuknya menolong. Dua pernyataan itu secara "
        f"semantik setara, jadi selisih di antaranya bisa dikaitkan ke cara "
        f"optimizer memperlakukan derived table itu, bukan ke pekerjaan yang "
        f"perlu dilakukan. Di lima konfigurasi, rasio bentuk derived terhadap "
        f"bentuk datar adalah " +
        ", ".join(f"{B.CONFIG_SHORT[c]} {B.n_dec(v)}" for c, v in ratios.items()) +
        f". Semua selisihnya di bawah "
        f"{B.n_dec(max(abs(1 - v) for v in ratios.values()) * 100, 0)} persen, "
        f"dan tandanya tidak stabil: bentuk derived lebih cepat di "
        f"{len(faster)} dari {len(ratios)} konfigurasi dan lebih lambat di "
        f"{len(ratios) - len(faster)}. Jadi menulis ulang sebuah query ekuivalen "
        f"tidak memberi efek yang andal di sini, dan praktisi yang mengukurnya "
        f"di satu set index lalu menggeneralisasikannya akan sampai pada "
        f"kesimpulan yang "
        f"ditolak empat konfigurasi lainnya. Ini kesimpulan yang sama seperti yang "
        f"ditemukan untuk formulasi join di Bagian 4.4, hanya sampai dari "
        f"arah berbeda: hasil sebuah penulisan ulang ditentukan oleh rencana "
        f"yang dipicunya di bawah index yang benar-benar ada, jadi tidak bisa "
        f"diprediksi dari penulisan ulang itu saja."))

    # ---- 4.7 -----------------------------------------------------------
    p.append(B.h2("4.7 Di Mana Indeksasi Tidak Membantu"))
    regress = [(q, r.speedup("C4_covering", q)) for q in B.QUERY_ORDER]
    regress = [(q, s) for q, s in regress if s is not None and s < 1.05]
    regress.sort(key=lambda t: t[1])
    p.append(B.body(
        f"Indeksasi biasanya dilaporkan sebagai keuntungan yang seragam, dan "
        f"studi yang hanya melaporkan keberhasilan akan salah menggambarkan ruang "
        f"desainnya. Dibandingkan dengan C0, konfigurasi terindeks penuh C4 "
        f"meninggalkan {len(regress)} dari {B.n_int(B.NQ)} query tanpa perbaikan atau "
        f"justru lebih buruk dalam rentang variasi antar eksekusi: " +
        ", ".join(f"{q} sebesar {B.n_dec(s)}x" for q, s in regress) + "."))
    p.append(B.body(
        f"Penjelasannya sama untuk semuanya, dan itu adalah rasio baris yang "
        f"diperiksa terhadap baris yang dikembalikan yang dibuat jadi bisa "
        f"dioperasionalkan. Kalau baris yang memenuhi predikat adalah sebagian besar "
        f"isi relasi, server harus membaca sebagian besar baris struktur apa pun "
        f"yang "
        f"dipakainya, jadi index hanya mengubah biaya kolom yang tidak "
        f"di-cover-nya. Kalau sebuah query harus agregasi atau join dulu sebelum "
        f"bisa menghasilkan baris apa pun, index sama sekali tidak bisa "
        f"menghapus pekerjaan itu. Jadi memrediksi apakah sebuah index layak "
        f"dibuat praktis sama dengan memperkirakan rasio tersebut, dan itulah "
        f"persis besaran yang dicoba diprediksi oleh metode estimasi keuntungan "
        f"index tanpa pengukuran [12]. Studi ini menawarkan diagnosis sederhana "
        f"untuk estimasi itu: sebuah index kandidat layak diharapkan memberi "
        f"manfaat hanya kalau predikat yang dilayaninya selektif, dan rencana "
        f"yang direkam di sini membuat syarat itu bisa diamati langsung."))
    p.append(B.body(
        f"Keterbatasan kedua melekat pada desainnya, bukan pada datanya. Tiap "
        f"konfigurasi dinilai hanya dari latensi baca, jadi biaya tulis dan biaya "
        f"simpan dari sebelas index di C2 dan tujuh index di C4 tidak terukur. "
        f"Karena setiap index sekunder harus dipelihara pada setiap insert dan "
        f"update, dan karena workload ini didominasi pembacaan analitik atas "
        f"dataset yang tidak sedang ditulis selama pengukuran, konfigurasi yang "
        f"kinerjanya paling baik di sini justru pilihan terburuk untuk jalur "
        f"tulis sebuah sistem transaksional yang hidup. Rekomendasi index untuk "
        f"produksi harus menggabungkan pengukuran yang dilaporkan di sini dengan "
        f"pengukuran throughput tulis dan ruang penyimpanan, dan studi ini tidak "
        f"berklaim menyediakannya."))

    # ---- 4.8 -----------------------------------------------------------
    p.append(B.h2("4.8 Interpretasi pada Platform Acuan"))
    p.append(B.body(
        "Platform acuan untuk pekerjaan ini adalah ThinkPad L14 dengan delapan "
        "core, memori 16 GB, dan penyimpanan NVMe. Pengukuran di Tabel 5 diambil "
        "di platform kalibrasi Tabel 4, dan keduanya berbeda. Daripada "
        "mendeskripsikan sebuah konversi yang tidak terukur, bagian ini "
        "memisahkan besaran yang dilaporkan menjadi yang bergantung platform dan "
        "yang tidak."))
    p.append(B.body(
        "Waktu eksekusi absolut dalam milidetik bergantung platform dan akan "
        "berbeda di platform acuan. Rasio percepatan di Tabel 5 sampai 9 sebagian "
        "besar tidak. Percepatan adalah rasio dari dua waktu yang dihasilkan "
        "engine yang sama atas data yang sama dengan rencana yang sama, berbeda "
        "hanya pada ketersediaan index, dan kedua sukunya ditentukan oleh jumlah "
        "baris yang harus diperiksa engine, yang merupakan properti data dan jalur "
        "akses, bukan properti prosesor. Penskalaan perangkat keras mengalikan "
        "pembilang dan penyebut sekaligus sehingga saling meniadakan. Jadi kesimpulan "
        "kualitatif Bagian 4.2 sampai 4.7 sebaiknya juga berlaku di platform acuan "
        "meskipun waktu absolumnya tidak, dan pembaca sebaiknya memperlakukan "
        "temuan di level rencana, yaitu pernyataan tentang jalur akses mana yang "
        "dipilih optimizer, sebagai hasil yang bisa dipindahkan. Justru itulah isi "
        "utama paper ini, karena temuan itu tidak bergantung pada besar kecilnya "
        "waktu mana pun."))
    p.append(B.body(
        "Satu catatan penting perlu disebut. Urutan relatif dua rencana secara prinsip "
        "bisa berubah dengan perangkat keras kalau satu rencana terikat I/O dan yang "
        "lain terikat CPU, sebab penyimpanan NVMe di platform acuan jauh lebih cepat "
        "daripada media penyimpanan platform kalibrasi. Konfigurasi yang dibandingkan "
        "di sini berbeda pada jalur akses baris, bukan pada paralelisme I/O, jadi "
        "efeknya diperkirakan kecil, tapi tidak disingkirkan oleh pengukuran. Karena "
        "itulah Tabel 10 memberi konfigurasi terindeks dalam skala untuk rentang faktor "
        "perangkat keras, bukan pada satu konversi yang diasumsikan, dengan baris "
        "terukurnya adalah platform kalibrasi itu sendiri."))
    p.append(B.caption("Tabel", "10. Kepekaan waktu konfigurasi terindeks terhadap "
                                "faktor penskalaan perangkat keras."))
    p.append(B.table_sensitivity(r))
    p.append(B.body(
        "Karena paket reproduksi sudah memuat definisi schema, loader, definisi "
        "query, dan benchmark harness, menjalankan ulang seluruh sapuan di platform "
        "acuan akan membangkitkan ulang kolom absolut secara langsung dan "
        "menghilangkan kebutuhan mengasumsikan faktor penskalaan sama sekali. Harness "
        "membangun ulang tiap konfigurasi dari satu baseline yang sama dan melaporkan "
        "median, simpangan baku, dan rencana yang dipilih untuk setiap sel, jadi "
        "hasil pembangkitan ulang itu bisa dibandingkan dengan Tabel 5 sel demi sel."))

    # ---- 4.9 -----------------------------------------------------------
    p.append(B.h2("4.9 Ancaman terhadap Validitas"))
    p.append(B.body(
        "Empat keterbatasan yang mengikat kesimpulan. Pertama, dan paling "
        "berpengaruh untuk hasil indeksasi, datasetnya kecil. Tabel terbesar berisi "
        "99.441 baris dan seluruh working set kecil dibanding buffer pool, jadi full "
        "scan sudah murah dan ruang gerak yang bisa direbut indeksasi juga ikut "
        "kecil. Keuntungan absolut yang dilaporkan di sini jangan diekstrapolasi ke "
        "dataset satu orde besaran lebih besar atau lebih, karena di sana rasio "
        "pekerjaan dengan bantuan index terhadap full scan tidak berubah tetapi biaya "
        "absolut full scan jauh lebih tinggi. Kesimpulan di level rencana tidak "
        "terpengaruh; kesimpulan tentang besarnya yang terpengaruh."))
    p.append(B.body(
        "Kedua, studi ini hanya mencakup satu engine. MariaDB dipakai karena "
        "mengimplementasikan antarmuka MySQL dan sakelar optimizer yang diteliti, "
        "dan MySQL 8.x mengimplementasikan transformasi semijoin, materialisasi, "
        "dan derived-merge yang sama, tapi kedua engine berbeda pada detail model "
        "biaya, pada ambang tempat optimizer mengubah sebuah subquery menjadi "
        "semi-join, dan pada tipe index yang tersedia. Ambang konversi spesifik "
        "yang dilaporkan di sini jangan dianggap berlaku persis di engine atau versi "
        "lain. Ini batas validitas eksternal yang nyata, bukan yang bersifat "
        "presentasi."))
    p.append(B.body(
        f"Ketiga, set workload-nya adalah {B.n_int(B.NQ)} query yang diambil dari {B.n_int(B.NF)} "
        f"keluarga, dirancang untuk mencakup pola akses analitik e-commerce, bukan "
        f"untuk mewakili query mix aplikasi tertentu. Rata-rata geometris di Tabel 6 "
        f"memberi bobot sama pada setiap keluarga, yang hanya bisa dibenarkan bila "
        f"tidak ada distribusi workload yang bisa dibenarkan juga; komposisi yang "
        f"berbeda akan menghasilkan agregat yang berbeda, meskipun pengukuran "
        f"per-query-nya sendiri tidak terpengaruh."))
    p.append(B.body(
        f"Keempat, noise pengukuran dikendalikan tapi tidak dihilangkan. Di seluruh "
        f"sel, koefisien variasi median adalah "
        f"{B.n_dec(r.median_cv() * 100, 1)} persen, dengan maksimum "
        f"{B.n_dec(r.worst_cv()[0] * 100, 1)} persen. Selisih yang lebih kecil dari "
        f"sekitar dua kali angka median itu tidak boleh dibaca sebagai efek "
        f"urutan, dan ini berlaku khusus untuk selisih kecil yang dibahas di Bagian "
        f"4.6 dan 4.7. Satu sel, yaitu W5.1 pada C2, melampaui batas pernyataan 45 "
        f"detik dan dilaporkan sebagai terpotong; sel itu dikeluarkan dari semua "
        f"agregat."))
    return "".join(p)


# ==========================================================================
# 5. Kesimpulan
# ==========================================================================
def conclusion(r: "B.Results") -> str:
    p = []
    g2 = r.geomean_speedup("C2_single") or 0
    g3 = r.geomean_speedup("C3_composite") or 0
    g4 = r.geomean_speedup("C4_covering") or 0
    w5 = [(r.med("C0_zero", q) or 0) for q in
          ("W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS")]
    s5 = max(w5) / min(w5) if min(w5) > 0 else float("nan")
    c4 = [(r.med("C4_covering", q) or 0) for q in
          ("W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS")]
    s5c4 = max(c4) / min(c4) if min(c4) > 0 else float("nan")
    p.append(B.h1("5. Kesimpulan"))
    p.append(B.body(
        f"Studi ini memisahkan dua keputusan yang menentukan efisiensi eksekusi "
        f"SQL, yaitu desain index dan formulasi query, lalu mengukurnya masing-masing "
        f"secara independen pada schema ternormalisasi sembilan tabel yang dibangun "
        f"dari {B.n_int(B.SCHEMA_ROWS)} baris data transaksi marketplace sungguhan. "
        f"Dihitung ulang atas {len(B.QUERY_ORDER) - 1} query non-outlier, tiga "
        f"konfigurasi index yang memang dirancang dengan sengaja mencapai percepatan "
        f"rata-rata geometris terhadap baseline tanpa index sebesar {B.xx(g2)} untuk "
        f"set kolom tunggal yang luas, {B.xx(g3)} untuk set komposit, dan "
        f"{B.xx(g4)} untuk set komposit ditambah covering. Kalau dibaca sendiri, "
        f"angka-angka itu saja sebenarnya mendukung saran konvensional: indeksasi "
        f"secara luas lalu berhenti. Dibaca bersama hasil per-query dan rencana yang "
        f"direkam, angka itu mendukung sekumpulan kesimpulan yang berbeda dan lebih "
        f"spesifik."))
    p.append(B.body(
        f"Pertama, percepatan agregat adalah panduan yang buruk untuk desain index, "
        f"dan pada workload ini angka itu justru menyesatkan. Konfigurasi yang "
        f"dirancang menjadi yang paling matang secara teknis justru yang hasilnya "
        f"paling "
        f"buruk. Alasannya, urutan kolom di dalam sebuah index menentukan "
        f"query mana yang sama sekali bisa dilayaninya: index komposit tidak bisa "
        f"memecahkan predikat atau urutan pada kolom trailing-nya selama kolom "
        f"leading-nya tidak dibatasi. Mengganti index kolom tunggal dengan index "
        f"komposit pada kolom yang sama memberi satu query faktor "
        f"{B.n_dec((r.med('C4_covering', 'W8.1') or 0) / max(r.med('C2_single', 'W8.1') or 1e-9, 1e-9), 0)} "
        f"dan query lain faktor "
        f"{B.n_dec((r.med('C4_covering', 'W2.2 SARG month') or 0) / max(r.med('C2_single', 'W2.2 SARG month') or 1e-9, 1e-9), 0)}. "
        f"Index komposit itu bukan tanpa guna; mereka satu-satunya konfigurasi yang "
        f"memperbaiki workload window function W7.1. Kesimpulannya bukan bahwa satu "
        f"desain menang, melainkan bahwa tidak ada set index terbaik yang universal, "
        f"dan bahwa pertanyaan yang harus ditanyakan bukan berapa banyak index yang "
        f"perlu dibuat, melainkan apakah kolom leading setiap index adalah kolom yang "
        f"dibatasi, diurutkan, atau dikelompokkan oleh query."))
    p.append(B.body(
        f"Kedua, biaya relatif antara sintaks JOIN dan subquery adalah properti "
        f"rencana, bukan properti sintaks, dan tandanya tidak stabil. Untuk satu "
        f"anti-join, bentuk subquery lebih cepat {B.n_dec(s5, 0)}x daripada bentuk LEFT JOIN "
        f"sebelum indeksasi, dan {B.n_dec(s5c4, 1)}x lebih lambat setelah sebuah "
        f"index ditambahkan pada kolom join. Itulah sebabnya rules of thumb berbentuk "
        f"selalu pilih join, atau selalu pilih EXISTS, tidak mungkin benar: aturan "
        f"seperti itu mengunci sebuah asumsi tentang rencana yang ditentukan "
        f"optimizer, bukan penulisnya. Implikasi operasionalnya murah. Periksa "
        f"rencana sebelum menulis ulang, karena penulisan ulang yang dibenarkan "
        f"sebuah rules of thumb bisa rugi tiga orde besaran ke satu arah dan "
        f"menghematnya di arah lain."))
    p.append(B.body(
        f"Ketiga, bentuk predikat dan desain index juga bukan dua keputusan yang "
        f"independen. Menulis ulang sebuah pemanggilan fungsi menjadi predikat rentang "
        f"bernilai sebesar faktor "
        f"{B.n_dec((r.med('C2_single', 'W2.1 non-SARG month') or 0) / max(r.med('C2_single', 'W2.2 SARG month') or 1e-9, 1e-9), 0)} "
        f"di tempat ada index dengan kolom leading yang benar, dan hampir nihil di "
        f"tempat tidak ada, dan besar untungnya sendiri dimoderasi oleh "
        f"selektivitas: rentang yang mencakup "
        f"{B.n_dec(100.0 * B.SELECTIVITY['year'] / B.SELECTIVITY['orders_total'], 0)} persen dari sebuah "
        f"tabel hampir tidak menghemat apa pun. Kedua variabel itu tidak bisa "
        f"dievaluasi sendirian, dan itulah argumen metodologis terkuat untuk "
        f"mengukurnya bersama seperti yang dilakukan di sini."))
    p.append(B.body(
        f"Terakhir, satu hasil yang memperbaiki hasil-hasil sebelumnya. Secara "
        f"keseluruhan keuntungan indeksasi tergolong sedang-sedangnya, sekitar dua kali "
        f"lipat, dan beberapa query sama sekali tidak membaik. Ini sifat rezimnya, "
        f"bukan sifat metodenya: tabel terbesar berisi 99.441 baris dan full scan "
        f"terhadapnya memakan waktu puluhan milidetik, jadi ruang gerak yang bisa "
        f"direbut index sedikit. Besarnya keuntungan seperti ini jangan "
        f"diekstrapolasi ke dataset yang lebih besar, karena di sana full scan jauh "
        f"lebih mahal secara proporsional dan mekanisme di level rencana yang sama "
        f"akan memberi keuntungan absolut yang jauh lebih besar. Kesimpulan di level "
        f"rencana, yang merupakan substansi paper ini, tidak bergantung pada ukuran "
        f"dataset maupun pada perangkat keras."))
    p.append(B.body(
        f"Untuk praktisi, urutan yang menyusul adalah: tuliskan predikat dalam "
        f"bentuk yang bisa dipakai optimizer; periksa selektivitasnya; periksa "
        f"rencana; buat index terkecil yang kolom leading-nya cocok dengan predikat "
        f"atau urutan penggerak; lalu ukur ulang, karena keputusan index dan "
        f"keputusan query tidak bisa dipisah. Untuk peneliti, pertanyaan yang masih "
        f"terbuka adalah biaya tulis yang dihilangkan desain hanya-baca ini, perilaku "
        f"workload yang sama pada engine tambahan dan ukuran dataset yang lain, serta "
        f"apakah pemilihan index bisa dipandu langsung oleh jumlah baris yang "
        f"terukur diperiksa alih-alih oleh estimasi kardinalitas."))
    return "".join(p)


# ==========================================================================
# back matter
# ==========================================================================
def back_matter(r: "B.Results") -> str:
    p = []
    p.append(B.h1("Ucapan Terima Kasih"))
    p.append(B.body(
        "Penulis mengucapkan terima kasih kepada [institusi] atas akses terhadap "
        "sumber daya komputasi yang dipakai dalam studi ini. Penulis menyatakan "
        "tidak ada pendanaan yang diterima untuk penelitian ini."))
    p.append(B.h1("Pernyataan"))
    p.append(B.body(
        "Kontribusi penulis. [Penulis Satu] mencetuskan ide studi, merancang protokol "
        "pengukuran, mengimplementasikan schema dan benchmark harness, serta menyusun "
        "draf naskah. [Penulis Dua] dan [Penulis Tiga] berkontribusi pada tinjauan "
        "literatur, memverifikasi data akreditasi acuan, dan meninjau naskah. Semua "
        "penulis menyetujui versi akhir."))
    p.append(B.body(
        "Konflik kepentingan. Penulis menyatakan tidak ada konflik kepentingan."))
    p.append(B.body(
        "Informasi tambahan. Tidak ada informasi tambahan yang tersedia untuk paper ini."))
    p.append(B.h1("Ketersediaan Data dan Perangkat Lunak"))
    p.append(B.body(
        "Dataset yang dianalisis di paper ini adalah dataset publik Brazilian "
        "E-Commerce yang dirilis oleh Olist dan tersedia secara terbuka di "
        "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce. Paket "
        "reproduksi lengkapnya tersedia atas permintaan dari penulis korespondensi "
        f"dan terdiri atas definisi schema, loader CSV-ke-database, definisi "
        f"{B.n_int(B.NQ)} query, benchmark harness yang menghasilkan setiap pengukuran yang "
        "dilaporkan di sini, serta waktu mentah per eksekusi termasuk simpangan bakunya."))
    p.append(B.h1("Lampiran A. Definisi Query"))
    p.append(B.body(
        f"{B.n_int(B.NQ)} query yang dijalankan dalam studi ini dicantumkan "
        f"di bawah ini sesuai urutan kemunculannya di Tabel 2. Setiap pernyataan "
        f"ditampilkan apa adanya seperti yang dieksekusi; lima konfigurasi index "
        f"yang diukur mengubah rencana, bukan pernyataan itu sendiri."))
    for label in B.QUERY_ORDER:
        sql = r.sql.get(label, "").strip()
        if not sql:
            continue
        p.append(B.dx.para(B.dx.run(f"{label}  —  {B.ID_QUERY_DESC[label]}", b=True, sz=8),
                           align="left", before=140, after=40, left=0, hanging=0,
                           keep_next=True))
        p.append(B.mono_block(sql))
    return "".join(p)