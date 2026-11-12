#!/usr/bin/env python3
"""
Assemble the Indonesian edition of the manuscript into a .docx that inherits the
ITIJ template.

Same measurements as build_paper.py (everything still comes from
results.json), but all prose, table headers and figure captions are written in
easy-to-follow Indonesian. The reference list is reused verbatim from
references.py.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import docx_writer as dx  # noqa: E402
from references import REFERENCES  # noqa: E402
from summary import (CONFIG_ORDER, CONFIG_SHORT, FAMILIES, FAMILY_OF,  # noqa: E402
                     QUERY_ORDER, Results, SELECTIVITY)

TEMPLATE = os.path.join(os.path.dirname(HERE), "ITIJ_Template.docx")
FIGDIR = os.path.join(HERE, "figures_id")
OUT = os.path.join(os.path.dirname(HERE), "Olist_SQL_Query_Efficiency_ITIJ_ID.docx")

EMU_PER_INCH = 914400
CONTENT_INCH = dx.CONTENT_WIDTH_TWIPS / 1440  # ~6.10 in


def load_benchmark_module():
    spec = importlib.util.spec_from_file_location(
        "bm", os.path.join(HERE, "benchmark.py"))
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    return bm


# ==========================================================================
# number formatting (Indonesian convention: dot thousands, comma decimals)
# ==========================================================================
def n_int(v) -> str:
    """Bulat bulat, gaya Indonesia (mis. 4.834).

    Membulatkan, bukan memotong: padanan f"{v:,.0f}" pada naskah Inggris.
    """
    return f"{v:,.0f}".replace(",", ".")


def n_dec(v, dp: int = 2) -> str:
    return f"{v:,.{dp}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def ms(v, dp: int = 2) -> str:
    """Angka durasi tanpa satuan, gaya Indonesia."""
    if v is None:
        return "n/a"
    if v >= 1000:
        return n_dec(v / 1000) + " dtk"
    return n_dec(v, dp)


def msu(v) -> str:
    """Durasi dengan satuan eksplisit, untuk prosa."""
    if v is None:
        return "tidak terukur"
    if v >= 1000:
        return n_dec(v / 1000) + " dtk"
    return n_dec(v) + " ms"


def xx(v) -> str:
    """Faktor percepatan, gaya Indonesia."""
    if v is None:
        return "n/a"
    if v >= 100:
        return n_dec(v, 0) + "x"
    if v >= 10:
        return n_dec(v, 1) + "x"
    return n_dec(v) + "x"


def pct(n: int, of: int) -> str:
    return n_dec(100.0 * n / of, 1) + " persen"


def idp(v: float) -> str:
    """Titik desimal untuk nilai di dalam kalimat (mis. 0,75)."""
    return f"{v:.2f}".replace(".", ",")


# ==========================================================================
# label kamus (Indonesia)
# ==========================================================================
ID_FAMILIES = {
    "W1": "Filter dan agregasi satu tabel",
    "W2a": "Bentuk predikat, bulan yang selektif",
    "W2b": "Bentuk predikat, tahun yang tidak selektif",
    "W3": "INNER JOIN dua tabel",
    "W4": "Formulasi semi-join",
    "W5": "Formulasi anti-join",
    "W6": "Agregasi analitik multi-tabel",
    "W7": "Peringkat dengan window function",
    "W8": "ORDER BY dengan LIMIT",
}

ID_QUERY_DESC = {
    "W1.1": "Menghitung order dengan status tertentu",
    "W1.2": "Pendapatan per status order lewat subquery korelasi atas pembayaran",
    "W1.3": "Jumlah pelanggan per provinsi",
    "W2.1 non-SARG month": "Order Juni 2018 dengan DATE_FORMAT() pada kolomnya",
    "W2.2 SARG month": "Order Juni 2018 dengan rentang setengah terbuka pada kolomnya",
    "W2.3 non-SARG year": "Order tahun 2018 dengan YEAR() pada kolomnya",
    "W2.4 SARG year": "Order tahun 2018 dengan rentang setengah terbuka pada kolomnya",
    "W3.1": "Order terkirim per provinsi pelanggan (equi-join dua tabel)",
    "W4.1 JOIN": "Order pelanggan dari satu provinsi, bentuk INNER JOIN",
    "W4.2 IN": "Hasil sama, subquery IN tanpa korelasi",
    "W4.3 EXISTS": "Hasil sama, subquery EXISTS berkorelasi",
    "W5.1 LEFT JOIN": "Order tanpa rating dalam jendela 14 hari, LEFT JOIN ... IS NULL",
    "W5.2 NOT IN": "Hasil sama, subquery NOT IN tanpa korelasi",
    "W5.3 NOT EXISTS": "Hasil sama, subquery NOT EXISTS berkorelasi",
    "W6.1 flat JOIN": "Pendapatan bulanan per provinsi, join datar empat tabel",
    "W6.2 derived table": "Hasil sama, join dipindah ke derived table",
    "W7.1": "Tiga seller teratas per provinsi lewat window function RANK()",
    "W8.1": "Dua puluh order terbaru, ORDER BY ... LIMIT",
}

ID_FORMS = {
    "W1.1": "SELECT + predikat titik",
    "W1.2": "Subquery skalar berkorelasi + GROUP BY",
    "W1.3": "GROUP BY pada tabel dimensi",
    "W2.1 non-SARG month": "DATE_FORMAT(kolom) = konstanta, selektif",
    "W2.2 SARG month": "Predikat rentang setengah terbuka, selektif",
    "W2.3 non-SARG year": "YEAR(kolom) = konstanta, tidak selektif",
    "W2.4 SARG year": "Predikat rentang setengah terbuka, tidak selektif",
    "W3.1": "INNER JOIN + GROUP BY",
    "W4.1 JOIN": "INNER JOIN",
    "W4.2 IN": "IN tanpa korelasi",
    "W4.3 EXISTS": "EXISTS berkorelasi",
    "W5.1 LEFT JOIN": "LEFT JOIN ... IS NULL",
    "W5.2 NOT IN": "NOT IN tanpa korelasi",
    "W5.3 NOT EXISTS": "NOT EXISTS berkorelasi",
    "W6.1 flat JOIN": "Join datar tiga tabel",
    "W6.2 derived table": "Materialisasi derived table",
    "W7.1": "Window function RANK()",
    "W8.1": "ORDER BY ... LIMIT",
}

ID_CONFIG_DESC = {
    "C0_zero": "Tanpa index sekunder (hanya primary key, foreign key dihapus)",
    "C1_fk": "Hanya index foreign key (baseline setelah impor)",
    "C2_single": "FK + index kolom tunggal pada kolom filter dan join",
    "C3_composite": "FK + index komposit (kolom kesetaraan, kolom rentang)",
    "C4_covering": "FK + index komposit + index covering",
}

ACCESS_ID = {
    "ALL": "scan-penuh", "index": "scan-index", "range": "rentang",
    "ref": "ref", "eq_ref": "eq_ref", "const": "konstan",
}
EXTRA_ID = {
    "Using where": "memakai WHERE",
    "Using index condition": "memakai index condition",
    "Using temporary": "memakai tabel sementara",
    "Using filesort": "memakai filesort",
}


def plan_id(r: Results, cfg: str, q: str) -> str:
    """Ringkasan EXPLAIN dengan istilah bahasa Indonesia."""
    raw = r.explain.get((cfg, q), "")
    if not raw:
        return ""
    parts = []
    for line in raw.strip().splitlines():
        f = line.split("\t")
        if len(f) < 10:
            continue
        tbl, typ, key, extra = f[2], f[3], f[5], f[9]
        access = ACCESS_ID.get(typ, typ)
        parts.append(f"{tbl}:{access}" + (f"[{key}]" if key not in ("NULL", "") else ""))
        if extra and extra not in ("", "Using where"):
            parts[-1] += "(" + EXTRA_ID.get(extra, extra) + ")"
    return "; ".join(parts)


def shorten(text: str, limit: int) -> str:
    return text if len(text) < limit else text[:limit - 3] + "..."


# ==========================================================================
# front matter
# ==========================================================================
TITLE = ("Analisis Perbandingan Efisiensi Eksekusi Query SQL Menggunakan "
         "Indeksasi, JOIN, dan Optimasi Subquery pada Dataset E-Commerce "
         "Brazilian Olist")

AUTHORS = [
    ("[Penulis Satu]", "1,*", True),
    ("[Penulis Dua]", "1", False),
    ("[Penulis Tiga]", "1", False),
]
AFFILIATIONS = [
    ("1", "Departemen Informatika, [Fakultas], [Universitas], [Kota], [Negara]"),
]
EMAILS = [("[email.satu@university.ac.id]", "1"),
          ("[email.dua@university.ac.id]", "2"),
          ("[email.tiga@university.ac.id]", "3")]


def front_matter() -> str:
    p = []
    p.append(dx.para(dx.run(TITLE, sz=17), align="center", before=360, after=240,
                     left=0, hanging=0))
    runs = []
    for i, (name, mark, _star) in enumerate(AUTHORS):
        if i:
            runs.append(dx.run(", "))
        runs.append(dx.run(name))
        runs.append(dx.run(mark, sup=True))
    p.append(dx.para("".join(runs), align="center", after=60, keep_next=True,
                     left=0, hanging=0))
    for mark, aff in AFFILIATIONS:
        p.append(dx.para(dx.run(mark + " ", sup=True, sz=9)
                         + dx.run(aff, sz=9), align="center", after=0,
                         left=0, hanging=0))
    for i, (mail, mark) in enumerate(EMAILS):
        runs = [dx.run(f"{mark} ", sup=True, sz=9)]
        runs.append(dx.run(f"Email penulis {mark}: ", sz=9))
        runs.append(dx.run(mail, sz=9, u=True))
        p.append(dx.para("".join(runs), align="center", after=0, left=0, hanging=0))
    p.append(dx.para(dx.run("* Penulis korespondensi", sz=9), align="center",
                     after=120, left=0, hanging=0))
    return "".join(p)


def article_info() -> str:
    rows = [
        ["Diterima", "[tanggal bulan 2026]"],
        ["Direvisi", "[tanggal bulan 2026]"],
        ["Diterima (final)", "[tanggal bulan 2026]"],
        ["Terbit", "[tanggal bulan 2026]"],
        ["DOI", "[diberikan jurnal setelah diterima]"],
    ]
    widths = [1500, 4000]
    return dx.table(rows, widths, header=False, font_sz=8, row_shading=False)


def abstract_and_keywords(r: "Results") -> str:
    w5_c0 = [r.med("C0_zero", q) or 0 for q in
             ("W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS")]
    anti_ratio = max(w5_c0) / max(min(w5_c0), 1e-9)
    abstract = (
        f"Kecepatan sebuah query ditentukan oleh dua keputusan yang sering dianggap sama "
        f"padahal tidak: struktur fisik apa yang dipakai database untuk menjangkau data, "
        f"dan bagaimana query itu ditulis untuk menghasilkan hasil logis yang sama. Paper ini "
        f"memisahkan keduanya lalu mengukur satu per satu. {NQ} query dari {NF} keluarga "
        f"workload dijalankan terhadap dataset transaksional Brazilian E-Commerce (Olist), "
        f"dinormalisasi menjadi schema InnoDB sembilan tabel berisi {n_int(SCHEMA_ROWS)} "
        f"baris. Pengujian memakai lima konfigurasi index, mulai dari tanpa index sekunder "
        f"sama sekali sampai index komposit dan index covering. Waktu eksekusi diambil dari "
        f"profiler bawaan server database selama {r.repeats} kali ulangan terukur setelah "
        f"{r.warmup} kali pemanasan, dan setiap jalur akses dikonfirmasi dengan EXPLAIN "
        f"sehingga setiap angka waktu benar-benar terhubung ke sebuah rencana eksekusi, "
        f"bukan sekadar tebakan. Tiga temuan muncul dari penelitian ini. Pertama, "
        f"berlawanan dengan dugaan awal yang menjadi alasan konfigurasi ini dirancang, "
        f"kumpulan index kolom tunggal yang luas justru mengalahkan kumpulan index "
        f"komposit dan index covering. Mengganti satu index kolom tunggal dengan index "
        f"komposit pada kolom yang sama membuat dua query melambat satu sampai dua orde "
        f"besar, karena index komposit tidak bisa melayani predikat atau urutan pada "
        f"kolom trailing-nya kalau kolom leading tidak dibatasi. Artinya urutan kolom di "
        f"dalam satu index ternyata lebih menentukan daripada banyaknya index yang ada, dan "
        f"kumpulan index terbaik bersifat spesifik terhadap workload, bukan universal. "
        f"Kedua, biaya relatif antara JOIN dan subquery bukan sifat bawaan sintaksnya, tapi "
        f"bergantung pada rencana eksekusi dan index yang tersedia, dan arah "
        f"perbandingannya bisa berbalik. Tanpa index, bentuk subquery untuk anti-join "
        f"mengalahkan bentuk LEFT JOIN sebesar faktor {xx(anti_ratio)}. Sebaliknya, "
        f"setelah index ditambahkan pada kolom join, bentuk LEFT JOIN justru jadi yang "
        f"tercepat di antara ketiganya. Ketiga, bentuk predikat tidak berdiri sendiri, "
        f"melainkan berinteraksi dengan desain index. Menulis ulang pemanggilan fungsi "
        f"menjadi predikat rentang memberi untung besar kalau ada index dengan kolom leading "
        f"yang tepat, dan hampir nihil kalau tidak ada, dan besar untungnya sendiri dikendalikan "
        f"oleh selektivitas predikatnya. Secara keseluruhan, gain dari indeksasi di sini "
        f"cukup-modest, sekitar dua kali lipat, karena dataset-nya memang cukup kecil "
        f"sehingga full scan sudah murah. Kontribusi yang paling awet dari penelitian ini "
        f"adalah kumpulan mekanisme di level rencana eksekusi, yang tidak bergantung pada "
        f"ukuran dataset maupun perangkat keras."
    )
    keywords = ("optimasi query; indeksasi; eksekusi JOIN; penulisan ulang subquery; "
                "SARGability; dataset Olist; rencana eksekusi; optimizer berbasis biaya")
    p = [dx.para(dx.run("ARTICLE INFO", smallcaps=True, sz=9), align="left",
                 before=240, after=120, left=0, hanging=0),
         article_info(),
         dx.para(dx.run("ABSTRAK", smallcaps=True, sz=10), align="left",
                 before=240, after=120, left=0, hanging=0),
         dx.para(dx.run(abstract, sz=10), align="both", after=120),
         dx.para(dx.run("Artikel ini berada di bawah lisensi CC–BY dan dapat diakses "
                        "secara terbuka.", sz=8.5), align="right", after=240),
         dx.para(dx.run("Kata Kunci: ", b=True, sz=7) + dx.run(keywords, sz=7),
                 align="left", after=120)]
    return "".join(p)


# ==========================================================================
# body helpers
# ==========================================================================
def h1(text: str) -> str:
    return dx.heading(text, 1)


def h2(text: str) -> str:
    return dx.heading(text, 2)


def body(text: str) -> str:
    return dx.para(dx.run(text), align="both", after=120, left=0, hanging=0)


def bullet(text: str) -> str:
    return dx.para(dx.run("•  ") + dx.run(text), align="both", after=60,
                   left=284, hanging=142)


def mono_block(text: str, *, sz: float = 8.0) -> str:
    """Daftar SQL: font monospace, rata kiri, indentasi tipis."""
    out = []
    for line in text.strip("\n").split("\n"):
        out.append(dx.para(dx.run(line or " ", font="Consolas", sz=sz),
                           align="left", after=0, line=240, left=284, hanging=0,
                           before=0))
    out.append(dx.para(dx.run(""), after=60, align="left", left=0, hanging=0))
    return "".join(out)


def caption(kind: str, text: str) -> str:
    return dx.caption(kind, text)


# ==========================================================================
# narrative
# ==========================================================================
def introduction(r: Results, bm) -> str:
    p = []
    p.append(h1("1. Pendahuluan"))
    p.append(body(
        "Database e-commerce transaksional itu ditulisnya satu baris demi satu baris, tapi "
        "dibacanya dengan bentuk yang sama sekali berbeda. Sisi tulisnya menambahkan order, "
        "baris order, pembayaran, dan rating. Sisi bacanya menanyakan hal-hal seperti: berapa "
        "pendapatan tiap provinsi tiap bulan, seller mana yang peringkatnya tertinggi di "
        "regionnya, dan order mana yang belum dapat rating. Tidak ada yang memastikan design "
        "fisik sebuah schema akan cocok dengan kedua pola akses itu. Struktur yang bikin "
        "penyimpanan cepat justru sering bikin pengambilan data jadi mahal, dan query yang "
        "dominan di beban kerja analitik hampir tidak pernah sama dengan query yang jadi "
        "acuan waktu schema itu dirancang."))
    p.append(body(
        "Ada dua cara yang paling sering dipakai di praktik, dan biasanya keduanya "
        "diajarkan serta diterapkan seolah-olah berdiri sendiri. Yang pertama bersifat fisik: "
        "tambah index. Yang kedua bersifat logis: tulis ulang query, ganti subquery jadi JOIN "
        "atau JOIN jadi subquery mengikuti aturan singkat yang kebetulan si penulis ingat. "
        "Keduanya masuk akal sebagai heuristik tapi tidak bisa diandalkan sebagai kesimpulan, "
        "dan alasannya sama: waktu eksekusi sebuah pernyataan ditentukan oleh jalur akses "
        "yang dipilih optimizer, dan jalur itu merupakan fungsi dari index yang tersedia, "
        "perkiraan kardinalitas, dan bentuk sintaks pernyataan itu sekaligus. Mengubah "
        "satu input saja akan mengubah outputnya, jadi mengaitkan perbaikan yang terukur "
        "ke input yang kita kira diubah itu tidak aman."))
    p.append(body(
        "Karya empiris soal masalah ini sebenarnya banyak, tapi tidak merata. Optimasi "
        "berbasis biaya dan pemilihan algoritma join sudah bagus secara teori dan di "
        "benchmark terkontrol [10]–[19], dan heuristik pemilihan index juga sudah diteliti "
        "masif [12], [20]–[25]. Yang belum ada adalah penelitian yang mengubah kedua faktor "
        "itu secara independen dalam satu lingkungan terkontrol, pada dataset operasional "
        "nyata dan bukan benchmark sintetis seperti TPC-H, dan yang melaporkan rencana "
        "eksekusi yang dipilih di samping angka waktunya, sehingga mekanisme di balik setiap "
        "pengukuran bisa diverifikasi dan bukan hanya ditebak."))
    p.append(body(
        "Paper ini menutup celah tersebut. Dataset Brazilian E-Commerce yang rilis oleh "
        "Olist [1] dipakai karena benar-benar log transaksi marketplace, bukan benchmark "
        "yang digenerate, dan karena struktur relasional sembilan tabelnya dan pemakaiannya "
        "untuk analitik sudah terdokumentasi di literatur [2]–[9]. Dataset ini "
        "dinormalisasi menjadi schema InnoDB sembilan tabel berisi "
        f"{n_int(SCHEMA_ROWS)} baris. {n_int(NQ)} query dari {n_int(NF)} keluarga workload "
        "dijalankan pada lima konfigurasi index, dan tiap konfigurasi diukur dari profiler "
        "pernyataan milik server itu sendiri dengan rencana yang dipilih dicatat lewat "
        "EXPLAIN."))
    p.append(body("Paper ini punya empat kontribusi."))
    p.append(bullet(
        "Desain pengukuran yang memisahkan variabel index dari variabel bentuk query. Lima "
        f"konfigurasi dibangun dari nol, lalu {n_int(NQ)} query dikelompokkan menjadi keluarga "
        "yang menahan pertanyaan logis tetap sama dan hanya memvariasikan bentuk sintaksnya."))
    p.append(bullet(
        "Penjelasan berbasis bukti kapan indeksasi benar-benar terasa dampaknya. Percepatan "
        "dilaporkan per query lalu digabung per keluarga sebagai rata-rata geometris, yang "
        "menunjukkan bahwa untungnya ditentukan oleh rasio baris yang diperiksa terhadap "
        "baris yang dikembalikan, bukan banyaknya index yang ada."))
    p.append(bullet(
        "Pengukuran JOIN lawan subquery pada kondisi index yang identik, dengan rencana "
        "yang benar-benar dieksekusi dilaporkan untuk tiap varian. Hasilnya menunjukkan "
        "nasihat yang biasa beredar itu sebenarnya bersyarat pada optimizer yang mengubah "
        "bentuk subquery menjadi semi-join atau anti-join berbasis hash."))
    p.append(bullet(
        "Penilaian kuantitatif atas bentuk predikat: selisih terukur antara pemanggilan "
        "fungsi yang tidak SARGable dan rentang setengah terbuka yang setara, yang merupakan "
        "optimasi termurah yang tersedia sekaligus yang paling sering dilewatkan."))
    p.append(body(
        "Susunan paper ini berikutnya. Bagian 2 meninjau literatur soal optimasi berbasis "
        "biaya, struktur index, algoritma join, penulisan ulang subquery, dan SARGability, "
        "lalu menunjukkan celah yang ditangani penelitian ini. Bagian 3 menjelaskan dataset, "
        "schema, workload query, konfigurasi index, protokol pengukuran, dan lingkungan "
        "eksekusi. Bagian 4 melaporkan dan membahas hasilnya. Bagian 5 menutup dengan "
        "kesimpulan."))
    return "".join(p)


def method(r: Results, bm) -> str:
    p = []
    p.append(h1("3. Metode"))

    p.append(h2("3.1 Dataset"))
    p.append(body(
        "Semua pengukuran memakai dataset publik Brazilian E-Commerce yang dirilis oleh "
        "Olist [1]. Rilisnya terdiri dari sembilan berkas CSV yang mencakup customers, "
        "sellers, products, terjemahan kategori produk, orders, order items, order payments, "
        f"order reviews, dan geolocation. Jumlah baris setelah dimuat sama persis dengan "
        f"jumlah yang dipublikasikan untuk tiap berkas. Sembilan berkas sumber berisi "
        f"{n_int(SOURCE_ROWS)} baris secara total, dengan {n_int(SCHEMA_ROWS)} di antaranya "
        "berada di schema yang dimuat. Selisihnya sepenuhnya berasal dari deduplikasi "
        "geolocation yang dijelaskan di bawah. Dua properti lain dari data yang dilepas "
        "memerlukan penanganan eksplisit, bukan koreksi diam-diam."))
    p.append(body(
        "Berkas reviews memuat 814 nilai review_id yang duplikat dan tersebar di order yang "
        "berbeda, jadi review_id saja tidak unik. Karena itu schema mendeklarasikan primary "
        "key komposit (review_id, order_id), yang mempertahankan seluruh 99.224 baris sumber "
        "tanpa membuang atau mengarang data. Berkas geolocation memuat 1.000.163 titik "
        "survei tetapi hanya 19.015 awalan kode pos yang berbeda. Karena analitik lanjutan "
        "memakai satu lokasi per awalan, 1.000.163 baris itu digabung menjadi satu baris "
        "per awalan saat pemuatan. Tidak satu pun penyesuaian ini mengubah nilai yang "
        "dipakai query terukur, dan keduanya diterapkan secara identik di semua konfigurasi "
        "index, sehingga tidak ada konfigurasi yang diuntungkan oleh set baris berbeda."))

    p.append(h2("3.2 Desain Schema"))
    p.append(body(
        "Berkas CSV diparsing mengikuti RFC 4180. Ini penting karena komentar rating memuat "
        "koma, tanda kutip, dan baris baru di dalamnya. Setelah itu data dimuat ke schema "
        "ternormalisasi bentuk normal ketiga yang dijelaskan di Tabel 1. Normalisasi dipilih "
        "daripada star schema dengan sengaja: penelitian ini mengukur biaya pengambilan "
        "baris lintas beberapa tabel pada log transaksi yang sudah ternormalisasi, "
        "sedangkan star schema yang sudah diagregasi justru akan menghilangkan join yang "
        "sedang diteliti. Semua tabel memakai engine InnoDB dengan character set UTF-8 "
        "dan ukuran halaman default server."))
    p.append(caption("Tabel", "1. Schema ternormalisasi, jumlah baris, dan peran analitiknya."))
    p.append(table_schema(r))
    p.append(body(
        "Foreign key dideklarasikan pada orders.customer_id, order_items.order_id, "
        "order_items.product_id, order_items.seller_id, dan order_payments.order_id. "
        "Keputusan ini punya konsekuensi pengukuran yang mudah terlewat: mesin yang "
        "kompatibel dengan MySQL membuat index sekunder implisit untuk mendukung setiap "
        "foreign key, jadi schema yang diimpor dengan benar sudah membawa index yang tidak "
        "pernah dipilih untuk performa query. Karena keadaan pasca-impor itu realistis dan "
        "menarik tersendiri, ia dipertahankan sebagai konfigurasi tersendiri, bukan "
        "digabung ke baseline tanpa index."))

    p.append(h2("3.3 Workload Query"))
    p.append(body(
        f"{n_int(NQ)} query dirancang dari {n_int(NF)} keluarga. Setiap keluarga menahan "
        "sebuah pertanyaan logis tetap, sehingga pengaruh konfigurasi index bisa dipisahkan "
        "dari pengaruh bentuk query. Tabel 2 merangkum keluarga-keluarga itu, dan SQL "
        "lengkap untuk setiap query tercantum di Lampiran A."))
    p.append(caption("Tabel", "2. Keluarga workload query."))
    p.append(table_workloads(r, bm))
    p.append(body(
        "Tiga keputusan desain dalam set workload ini layak disebut eksplisit, karena "
        "tiap-tiapnya dipaksakan oleh rencana terdegradasi tanpa index, bukan dipilih "
        "karena praktis. Pada keluarga anti-join W5, relasi penggerak dibatasi ke jendela "
        "pembelian empat belas hari. Kalau ditulis sebagai derived table, pembatasan itu "
        "hilang, karena penggabungan derived table menyatukannya ke query luar sehingga "
        "varian LEFT JOIN berubah menjadi produk kartesian sekitar 9,5 × 10⁹ perbandingan "
        "baris, yang tidak bisa diukur. Karena itu predikatnya ditulis sebagai pembatasan "
        "tingkat atas pada tabel penggerak, dan ketiga varian anti-join memakai pembatasan "
        "yang persis sama, sehingga perbandingan ini mengisolasi bentuk query, bukan besar "
        "masukan datanya. Kedua, keluarga semi-join W4 dan keluarga anti-join W5 masing-masing "
        "memuat tiga formulasi dari satu pertanyaan logis, sehingga perbandingan dalam "
        "keluarga bisa dilakukan pada kondisi index yang tetap. Ketiga, workload W2 memuat "
        "dua pasangan predikat. Dalam setiap pasangan, kedua anggotanya mengembalikan "
        "jumlah baris yang identik dan hanya berbeda pada apakah fungsi diterapkan ke kolom "
        "yang difilter. Kedua pasangan itu berbeda satu sama lain pada tingkat selektivitas, "
        "dan ternyata variabel inilah yang memoderasi efeknya."))

    p.append(h2("3.4 Konfigurasi Index"))
    p.append(body(
        "Lima konfigurasi dibangun, terdaftar di Tabel 3. Tiap konfigurasi dibangun ulang "
        "dari baseline yang sama sebelum pengukuran, bukan ditumpuk dari konfigurasi "
        "sebelumnya, sehingga tidak ada konfigurasi yang mewarisi index yang tidak ia "
        "sebutkan dan semua konfigurasi bisa dibandingkan langsung. C0 menghapus foreign key "
        "sekaligus index implisitnya, menghasilkan schema dengan primary key saja. C1 "
        "memulihkan foreign key sehingga mereproduksi schema yang didapat analis dari impor "
        "konvensional. C2 menambahkan sepuluh index kolom tunggal pada kolom yang muncul "
        "di predikat filter dan kondisi join. C3 sebagai gantinya menambahkan empat index "
        "komposit dengan kolom pertama berupa predikat kesetaraan dan kolom terakhir "
        "berupa kolom rentang atau join, mencerminkan argumen leftmost-prefix yang lazim. "
        "Dua dari sepuluh index kolom tunggal yang diminta untuk C2 menduplikasi kolom "
        "yang sudah ter-index untuk menegakkan foreign key, jadi server menolaknya dan C2 "
        "membawa sebelas index sekunder, bukan tiga belas. C4 memperluas C3 dengan index "
        "yang daftar kolomnya menutup seluruh proyeksi query analitik, sehingga tabel "
        "dasar tidak perlu dikunjungi sama sekali. Karena C2, C3, dan C4 adalah pilihan "
        "yang saling menggantikan, bukan tahap bertingkat, perbandingan ini sekaligus "
        "menjawab apakah sekumpulan index kolom tunggal yang lebih luas lebih baik "
        "daripada jumlah index komposit yang lebih sedikit tapi dipilih dengan cermat."))
    p.append(caption("Tabel", "3. Konfigurasi index."))
    p.append(table_configs(r))

    p.append(h2("3.5 Protokol Pengukuran"))
    p.append(body(
        "Waktu eksekusi diambil dari profiler pernyataan milik server database itu sendiri, "
        "bukan dari pengukuran jam dinding di sisi klien. Pengukuran sisi klien akan "
        "memakan biaya pemrosesan koneksi dan serialisasi hasil, yang keduanya bukan bagian "
        "dari besaran yang kita pedulikan. Protokol yang sama diterapkan pada setiap "
        "konfigurasi dan setiap query."))
    p.append(body(
        f"Untuk tiap konfigurasi dan tiap query, dilakukan tiga kali pemanasan yang tidak "
        f"diukur, lalu {r.repeats} kali eksekusi terukur, memberi {r.repeats} sampel per sel "
        f"dan {n_int(r.repeats * 5 * len(QUERY_ORDER))} pengukuran terukur secara total. "
        f"Median dilaporkan sebagai statistik utama karena tahan terhadap noise "
        f"penjadwalan yang wajar di mesin bersama. Rata-rata, simpangan baku, nilai minimum, "
        f"dan maksimum tetap disimpan di berkas hasil. Di seluruh sel, koefisien variasi "
        f"yang dihitung sebagai simpangan baku dibagi rata-rata punya median "
        f"{n_dec(r.median_cv() * 100, 1)} persen dan maksimum {n_dec(r.worst_cv()[0] * 100, 1)} "
        f"persen, jadi selisih yang dilaporkan tidak bisa dikaitkan ke variasi antar "
        f"eksekusi kecuali di bagian yang disebut eksplisit. Setiap pernyataan juga "
        f"dijalankan di bawah EXPLAIN dan di bawah instrumen jumlah baris aktual milik "
        f"server, sehingga jalur akses dan baris yang diperiksa tercatat berdampingan dengan "
        f"setiap waktu, bukan disimpulkan darinya. Batas waktu per pernyataan sebesar 45 "
        f"detik dipasang supaya rencana terdegradasi tercatat sebagai pengukuran "
        f"terpotong, bukan menggantungkan seluruh proses."))

    p.append(h2("3.6 Lingkungan Eksekusi"))
    p.append(body(
        "Pengukuran diambil di platform kalibrasi yang dijelaskan di Tabel 4. Platform "
        "acuan untuk pekerjaan ini adalah Lenovo ThinkPad L14 dengan procesor delapan core, "
        "memori 16 GB, dan penyimpanan SSD NVMe. Platform kalibrasi berbeda dari itu, dan "
        "Tabel 4 menyebut keduanya supaya perbedaannya terlihat, bukan tersirat. Bagian 4.8 "
        "membahas konsekuensinya terhadap angka yang dilaporkan."))
    p.append(caption("Tabel", "4. Lingkungan eksekusi."))
    p.append(table_environment(r))
    p.append(body(
        "Dua properti lingkungan kalibrasi layak disebut karena keduanya menguntungkan "
        "jalur akses tertentu. Buffer pool InnoDB dibiarkan pada default 128 MB, yang lebih "
        "kecil dari working set sekitar 180 MB dari tabel yang diukur, sehingga hanya "
        "sebagian working set yang tertahan di buffer pool dan pembacaan index tetap "
        "bermakna, bukan dilayani sepenuhnya dari memori. Media penyimpanan berada di RAM, "
        "sehingga latensi I/O tingkat perangkat tidak berkontribusi terhadap waktu yang "
        "diukur. Akibatnya workload yang diukur didominasi oleh perbandingan baris, "
        "hashing, dan pengurutan, dan itu memang wilayah yang tepat untuk mempelajari "
        "pemilihan jalur akses."))

    p.append(h2("3.7 Cara Membaca Hasil di Atas Berbagai Platform"))
    p.append(body(
        "Waktu eksekusi absolut bergantung pada platform, sedangkan rasio antar konfigurasi "
        "jauh lebih sedikit bergantung, karena kedua sisi rasio mengalami penskalaan "
        "perangkat keras yang sama. Alasan ini bersifat struktural, bukan empiris: sebuah "
        "percepatan ditentukan oleh rasio baris yang diperiksa terhadap baris yang "
        "dikembalikan, dan kedua besaran itu adalah properti data dan jalur akses, bukan "
        "prosesor. Karena itu Bagian 4.8 melaporkan nilai absolut terukur bersama analisis "
        "sensitifitas terhadap rentang faktor penskalaan perangkat keras, dan skrip "
        "reproduksi disertakan supaya nilai absolutnya bisa langsung dibangkitkan ulang di "
        "platform acuan."))
    return "".join(p)


def related_work(r: Results) -> str:
    p = []
    p.append(h1("2. Penelitian Terkait"))

    p.append(h2("2.1 Optimasi Query Berbasis Biaya"))
    p.append(body(
        "Optimasi query relasional secara konvensi dipandang sebagai penelusuran atas "
        "sejumlah pernyataan query yang ekuivalen, dengan penilaian memakai model biaya "
        "yang mengestimasi pekerjaan I/O dan CPU untuk tiap kandidat. Gretscher dan "
        "Dittrich [10] membandingkan strategi split, holistik, dan hibrida untuk penelusuran "
        "ini dan menunjukkan bahwa ketiganya berbeda dalam cara membatasi ruang penelusuran, "
        "bukan dalam ketepatan estimasi biayanya. Mohsin et al. [18] dan Zheng et al. [19] "
        "menerapkan pencarian metaheuristik ke pemilihan jalur akses dan urutan join di "
        "lingkungan terdistribusi, sedangkan Du [16] dan Xiong et al. [17] membahas "
        "estimasi biaya dan pemilihan rencana secara langsung. Premis yang sama-sama "
        "dipegang adalah: kualitas sebuah rencana dibatasi oleh kualitas perkiraan "
        "biayanya, dan itu sendiri dibatasi oleh statistik yang tersedia. Premis inilah yang "
        "membuat pendekatan empirik di level rencana yang dipakai di sini masuk akal. Bukan "
        "mencoba memperbaiki optimizer, melainkan memverifikasi rencana apa yang sebenarnya "
        "dihasilkan optimizer untuk sebuah skema dan query tertentu. Fritchey [29] "
        "memberikan pasangan praktis dari literatur ini, dengan memperlakukan inspeksi "
        "rencana eksekusi sebagai diagnostik rutin dan membedakan perkiraan jumlah baris "
        "dengan jumlah baris aktual sebagai sinyal utama bahwa model biaya salah "
        "memperkirakan; instrumen jumlah baris aktual yang dipakai di penelitian ini "
        "berfungsi untuk tujuan yang sama."))

    p.append(h2("2.2 Struktur Index dan Pemilihan Index"))
    p.append(body(
        "Index sekunder menukar biaya tulis dan ruang penyimpanan dengan kemudahan pembacaan, "
        "dan nilainya ditentukan oleh berapa bagian tabel yang bisa dihindari server untuk "
        "dibaca. Chen et al. [12] menyoroti langsung masalah estimasinya, yaitu "
        "memperkirakan manfaat index kandidat supaya index yang tidak perlu bisa dihindari. "
        "Kesulitan yang mereka temukan, yaitu manfaat index bergantung pada beban kerja "
        "bukan pada tabel itu sendiri, justru hal yang dieksploitasi oleh desain di sini "
        "karena kita mengukur beban kerja yang sudah didefinisikan, bukan skema secara "
        "terisolasi. Fugkeaw et al. [28] membandingkan konfigurasi index pada beban kerja "
        "analitik dan melaporkan bahwa penyempurnaan struktural yang menentukan untuk satu "
        "kelas query bisa jadi tidak berarti untuk kelas yang lain. Shin et al. [14] "
        "menggabungkan struktur index dengan optimasi join pada sebuah mesin relasional, "
        "sedangkan Mokodaser et al. [21], Firmansyah et al. [22], serta Ikhwan dan "
        "Pramadjaya [23] melaporkan pengukuran spesifik MySQL untuk indeksasi dan optimasi "
        "subquery pada database operasional. Naufal et al. [24] dan Witono dan Parno [25] "
        "membandingkan waktu respons untuk berbagai strategi akses termasuk view dan "
        "materialized view. Studi-studi itu konsisten melaporkan gain besar dari "
        "indeksasi, tapi berbeda pendapat soal apakah kontribusi tiap desain index diisolasi "
        "atau tidak. Pollack [30] menegaskan secara eksplisit perbedaan antara tuning "
        "transaksional dan analitik menjadi eksplisit, dan mencatat bahwa struktur yang "
        "melayani satu biasanya keliru untuk yang lain. Pengukuran di Bagian 4.3, di mana "
        "satu desain index jelas lebih baik untuk sebagian query dan jelas lebih buruk "
        "untuk query lain dalam satu set workload, sejalan dengan gambaran tersebut."))

    p.append(h2("2.3 Algoritma Join dan Penulisan Ulang Subquery"))
    p.append(body(
        "Tiga algoritma join klasik, nested-loop, sort-merge, dan hash join, berbeda dalam "
        "cara memanfaatkan struktur yang tersedia, sehingga biaya join tidak bisa dipisahkan dari "
        "ketersediaan index. Liang et al. [13] memilih di antara metode join berdasarkan "
        "biaya relatif, Chandrashekariah dan Dinesha [20] memperkirakan biaya join secara "
        "langsung dan membandingkan urutan kandidat, Ji et al. [15] membahas penelusuran "
        "urutan join, dan Zhao et al. [11] membahas pemilihan di antara bentuk subquery "
        "alternatif saat optimasi ulang. Do et al. [27] memberi perbandingan empiris di "
        "tingkat query antar mesin, dan Gretscher dan Dittrich [10] memuat rumusan biaya "
        "standar untuk ketiga algoritma tersebut. Dari sisi logis, semi-join dan anti-join "
        "bisa ditulis dengan sintaks JOIN maupun sintaks subquery, dan optimizer dengan "
        "dukungan semijoin dan materialisasi akan biasanya mengubah bentuk subquery menjadi "
        "bentuk join di dalamnya. Konversi inilah yang menjadi mekanisme di balik pengukuran "
        "tengah di Bagian 4.4."))

    p.append(h2("2.4 Bentuk Predikat dan SARGability"))
    p.append(body(
        "Sebuah predikat disebut SARGable kalau strukturnu memungkinkan optimizer membatasi "
        "suatu rentang index, dan tidak SARGable kalau ada fungsi yang diterapkan pada kolom "
        "yang di-index sehingga index tidak bisa dipakai untuk menemukan baris yang cocok. "
        "Farid Uddin et al. [26] menganalisis bentuk query yang SARGable dan menjelaskan "
        "transformasi predikat tidak SARGable menjadi bentuk SARGable yang setara. Karena "
        "transformasi ini tidak mengubah makna hasil dan tidak menuntut perubahan skema, ia "
        "adalah optimasi termurah yang tersedia; pengukurannya disertakan di sini sebagai "
        "workload W2."))

    p.append(h2("2.5 Data Transaksi E-Commerce dalam Penelitian Basis Data"))
    p.append(body(
        "Dataset Olist sudah jadi substrat yang umum untuk analitik e-commerce. Andra dan "
        "Baizal [2] menerapkan reduksi dimensi dan clustering padanya, Haqqani et al. [3] "
        "memakainya untuk segmentasi berbasis RFM sekaligus mendokumentasikan struktur "
        "relasional sembilan tabelnya. Zaghloul et al. [4] memakainya dalam skala besar "
        "untuk pemodelan churn, Jafri et al. [5] untuk rekomendasi dengan multimodal "
        "transfer learning, dan Asfe et al. [6] juga untuk hal serupa. Xu et al. [7] "
        "menganalisis status operasional platform, Gogineni et al. [8] melakukan analisis "
        "transaksi menyeluruh termasuk join multi-tabel, dan Proença et al. [9] memodelkan "
        "kepuasan pelanggan. Yang sama-sama dimiliki kelompok kerja ini adalah ketertarikan "
        "pada isi datanya. Desain fisik dan efisiensi query dari struktur relasional yang "
        "disiratkan dataset tersebut dianggap sudah selesai, bukan sesuatu yang diukur."))

    p.append(h2("2.6 Celah Penelitian"))
    p.append(body(
        "Tiga celah muncul dari uraian di atas. Pertama, indeksasi dan bentuk query jarang "
        "diubah secara independen, sehingga percepatan yang dipublikasikan tidak bisa "
        "diatribusikan ke sebab tertentu. Kedua, ketika bentuk subquery dan join "
        "dibandingkan, rencana yang dieksekusi jarang dilaporkan, sehingga mustahil "
        "membedakan apakah sebuah perbedaan datang dari jalur akses yang dipilih atau dari "
        "hal yang tidak sengaja. Ketiga, hasil biasanya dilaporkan untuk satu platform "
        "tanpa penjelasan bagaimana ketergantungan pada platform seharusnya dibaca. "
        "Penelitian ini menangani ketiganya dengan menyilangkan lima konfigurasi index "
        f"dengan {n_int(NQ)} query, melaporkan rencana untuk setiap pengukuran, dan memisahkan "
        "rasio yang tidak bergantung platform dari waktu absolut yang bergantung platform."))
    return "".join(p)
def table_schema(r: Results) -> str:
    rows = [["Tabel", "Jumlah baris", "Primary key", "Foreign key", "Peran analitik"]]
    data = [
        ("customers", "99.441", "customer_id", "—", "Geografi pelanggan (provinsi, kota, awalan kode pos)"),
        ("sellers", "3.095", "seller_id", "—", "Geografi seller"),
        ("products", "32.951", "product_id", "—", "Atribut produk dan kunci kategori"),
        ("category_translation", "71", "product_category_name", "—", "Pencarian label kategori"),
        ("orders", "99.441", "order_id", "customer_id", "Header order: status dan empat cap waktu"),
        ("order_items", "112.650", "(order_id, order_item_id)", "order_id, product_id, seller_id", "Baris order: harga dan ongkos kirim"),
        ("order_payments", "103.886", "(order_id, payment_sequential)", "order_id", "Peristiwa pembayaran per order"),
        ("order_reviews", "99.224", "(review_id, order_id)", "—", "Nilai rating dan teks bebas"),
        ("geolocation", "19.015", "geolocation_zip_code_prefix", "—", "Koordinat per awalan kode pos"),
    ]
    rows += [list(d) for d in data]
    rows.append(["Total (dimuat)", n_int(SCHEMA_ROWS), "—", "—",
                 n_int(SOURCE_ROWS) + " baris pada sembilan berkas sumber "
                 "sebelum geolocation dihapus duplikatnya"])
    return dx.table(rows, [1250, 800, 1650, 1750, 3338], font_sz=7.5)


def table_workloads(r: Results, bm) -> str:
    rows = [["ID", "Keluarga", "Pertanyaan logis", "Bentuk SQL"]]
    for label in QUERY_ORDER:
        rows.append([label.split()[0], FAMILY_OF[label],
                     ID_QUERY_DESC[label], ID_FORMS[label]])
    return dx.table(rows, [700, 700, 4388, 3000], font_sz=7.5)


def table_configs(r: Results) -> str:
    rows = [["Konfigurasi", "Index sekunder yang ada", "Tujuan"]]
    idx = {
        "C0_zero": "tidak ada",
        "C1_fk": "orders.customer_id, order_items.product_id, order_items.seller_id",
        "C2_single": "C1 + 10 index kolom tunggal pada kolom filter dan join",
        "C3_composite": "C1 + 4 index komposit (kolom kesetaraan, kolom rentang)",
        "C4_covering": "C1 + index komposit + 2 index yang menutup seluruh proyeksi",
    }
    for cfg in CONFIG_ORDER:
        rows.append([CONFIG_SHORT[cfg], idx[cfg], ID_CONFIG_DESC[cfg]])
    return dx.table(rows, [800, 4200, 3788], font_sz=7.5)


def table_environment(r: Results) -> str:
    rows = [
        ["Komponen", "Platform kalibrasi (hasil pengukuran)", "Platform acuan (target)"],
        ["CPU", "AMD Ryzen 5 PRO 4650U, 3 vCPU dialokasikan ke container",
         "8-core (setara Intel Core Ultra / Ryzen)"],
        ["Memori", "4 GB dialokasikan; buffer pool InnoDB 128 MB", "16 GB"],
        ["Penyimpanan", "Media penyimpanan berada di RAM (tanpa latensi I/O tingkat perangkat)",
         "SSD NVMe"],
        ["Sistem operasi", "Ubuntu 26.04 LTS, x86-64", "Linux atau Windows 64-bit"],
        ["Mesin database", "MariaDB 10.11.6 (kompatibel MySQL), InnoDB", "MySQL 8.x, InnoDB"],
        ["Buffer pool", "128 MB (lebih kecil dari working set sekitar 180 MB)",
         "128 MB default, setelan identik yang dipakai"],
        ["Variabel sesi lain", "join_buffer_size 256 KB, sort_buffer_size 2 MB, "
                              "tmp_table_size 16 MB (default server, tidak diubah)",
         "Default server, tidak diubah"],
    ]
    return dx.table(rows, [1500, 3900, 3388], font_sz=7.5)


def table_all_results(r: Results) -> str:
    rows = [["ID", "Keluarga"] + [CONFIG_SHORT[c] for c in CONFIG_ORDER]
            + [f"Percepatan\n{CONFIG_SHORT['C4_covering']} vs {CONFIG_SHORT['C0_zero']}"]]
    for label in QUERY_ORDER:
        cells = [label.split()[0], FAMILY_OF[label]]
        for cfg in CONFIG_ORDER:
            v = r.med(cfg, label)
            cells.append(("> 45 dtk" if r.is_censored(cfg, label)
                          else (ms(v) if v is not None else "n/a")))
        cells.append(xx(r.speedup("C4_covering", label)))
        rows.append(cells)
    cells = ["Rata-rata\ngeometris", "semua"]
    for cfg in CONFIG_ORDER:
        cells.append("1,00x" if cfg == "C0_zero" else xx(r.geomean_speedup(cfg)))
    cells.append(xx(r.geomean_speedup("C4_covering")))
    rows.append(cells)
    rows.append(["Total", "semua"]
                + [n_dec(r.total(c)) + " ms" for c in CONFIG_ORDER]
                + [xx((r.total("C0_zero") or 0) / (r.total("C4_covering") or 1))])
    return dx.table(rows, [700, 700, 1150, 1150, 1150, 1150, 1150, 1338], font_sz=7)


def table_family_speedup(r: Results) -> str:
    rows = [["Keluarga", "Workload", f"{CONFIG_SHORT['C2_single']}",
             f"{CONFIG_SHORT['C3_composite']}", f"{CONFIG_SHORT['C4_covering']}",
             "Konfigurasi terbaik"]]
    for fam, desc in ID_FAMILIES.items():
        qs = [q for q in QUERY_ORDER if FAMILY_OF[q] == fam]
        cells = [fam, desc]
        for cfg in ("C2_single", "C3_composite", "C4_covering"):
            cells.append(xx(r.family_geomean_speedup(cfg, fam)))
        best = max(("C2_single", "C3_composite", "C4_covering"),
                   key=lambda c: r.family_geomean_speedup(c, fam) or 0.0)
        cells.append(CONFIG_SHORT[best])
        rows.append(cells)
    for ri, fam in enumerate(ID_FAMILIES, start=1):
        vals = {c: (r.family_geomean_speedup(c, fam) or 0.0)
                for c in ("C2_single", "C3_composite", "C4_covering")}
        win = max(vals, key=lambda c: vals[c])
        col = {"C2_single": 2, "C3_composite": 3, "C4_covering": 4}[win]
        if len(rows) > ri:
            rows[ri][col] = "*" + rows[ri][col] + "*"
    return dx.table(rows, [700, 3100, 1200, 1300, 1200, 1288], font_sz=7.5)


def table_column_order(r: Results) -> str:
    """Workload yang hanya membatasi/mengurutkan kolom_trailing sebuah index komposit."""
    lead = {
        "C2_single": "orders.order_purchase_timestamp",
        "C3_composite": "orders.order_status (tidak dibatasi) / customers.customer_state",
        "C4_covering": "orders.order_status (tidak dibatasi)",
    }
    rows = [["ID", "Konf.", "Index yang dipakai", "Kolom pertama index tersebut",
             "Median\n(ms)", "Jalur akses yang dipilih"]]
    for q in ("W2.2 SARG month", "W8.1"):
        first = True
        for tag, cfg in (("C2", "C2_single"), ("C3", "C3_composite"),
                         ("C4", "C4_covering")):
            idx = {"C2_single": "ix_orders_purch_ts",
                   "C3_composite": "ix_orders_status_ts",
                   "C4_covering": "ix_orders_cov"}[cfg]
            rows.append([q.split()[0] if first else "", tag, f"orders.{idx}",
                         lead[cfg], ms(r.med(cfg, q)),
                         shorten(plan_id(r, cfg, q), 72)])
            first = False
    return dx.table(rows, [560, 620, 1700, 2400, 780, 2728], font_sz=6.5)


def table_join_vs_subquery(r: Results) -> str:
    rows = [["Keluarga", "Formulasi", "C0 (ms)", "C2 (ms)", "C4 (ms)",
             "Rentang C0", "Jalur akses di C0"]]
    groups = [
        ("W4 semi-join", ["W4.1 JOIN", "W4.2 IN", "W4.3 EXISTS"]),
        ("W5 anti-join", ["W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS"]),
    ]
    for gname, qs in groups:
        meds0 = [r.med("C0_zero", q) or 0 for q in qs]
        spread = (max(meds0) / min(meds0)) if min(meds0) > 0 else None
        for q in qs:
            rows.append([gname if q == qs[0] else "", q,
                         "> 45 dtk" if r.is_censored("C0_zero", q)
                         else ms(r.med("C0_zero", q)),
                         "> 45 dtk" if r.is_censored("C2_single", q)
                         else ms(r.med("C2_single", q)),
                         "> 45 dtk" if r.is_censored("C4_covering", q)
                         else ms(r.med("C4_covering", q)),
                         xx(spread) if q == qs[0] else "",
                         shorten(plan_id(r, "C0_zero", q), 74)])
    return dx.table(rows, [1000, 1400, 1000, 1000, 1000, 900, 2488], font_sz=6.5)


def table_sargability(r: Results) -> str:
    rows = [["ID", "Predikat atas order_purchase_timestamp", "Baris\ncocok",
             "C0 (ms)", "C2 (ms)", "C4 (ms)", "Keuntungan\nSARG di C4",
             "Jalur akses di C4"]]
    pairs = [("W2.1 non-SARG month", "W2.2 SARG month",
              "DATE_FORMAT(ts,'%Y-%m') = '2018-06'",
              "ts >= '2018-06-01' AND ts < '2018-07-01'"),
             ("W2.3 non-SARG year", "W2.4 SARG year",
              "YEAR(ts) = 2018",
              "ts >= '2018-01-01' AND ts < '2019-01-01'")]
    for nonsarg, sarg, lbl_n, lbl_s in pairs:
        n_rows = (SELECTIVITY["month"] if nonsarg.endswith("month")
                  else SELECTIVITY["year"])
        c4n, c4s = r.med("C4_covering", nonsarg), r.med("C4_covering", sarg)
        adv = (c4n / c4s) if (c4n and c4s) else None
        rows.append([nonsarg.split()[0], lbl_n, n_int(n_rows),
                     ms(r.med("C0_zero", nonsarg)),
                     ms(r.med("C2_single", nonsarg)),
                     ms(c4n), "", shorten(plan_id(r, "C4_covering", sarg), 46)])
        rows.append([sarg.split()[0], lbl_s, n_int(n_rows),
                     ms(r.med("C0_zero", sarg)),
                     ms(r.med("C2_single", sarg)),
                     ms(c4s), xx(adv) if adv else "", ""])
    return dx.table(rows, [560, 2500, 780, 850, 850, 850, 1100, 1298], font_sz=6.5)


def table_sensitivity(r: Results) -> str:
    """Perubahan waktu absolut di platform acuan untuk berbagai faktor perangkat keras."""
    rows = [["Faktor skala κ yang diterapkan pada konfigurasi terindeks",
             "W1.1 (ms)", "W3.1 (ms)", "W6.1 (ms)",
             "Total, 17 query non-outlier (ms)"]]
    for kappa, note in ((0.5, "CPU acuan sekitar 2× lebih cepat, satu thread"),
                        (0.75, ""),
                        (1.00, "nilai terukur, platform kalibrasi"),
                        (1.50, "platform acuan sekitar 1,5× lebih lambat, satu thread"),
                        (2.00, "platform acuan sekitar 2× lebih lambat, satu thread")):
        cells = [idp(kappa) + (f"  ({note})" if note else "")]
        for q in ("W1.1", "W3.1", "W6.1 flat JOIN"):
            v = r.med("C4_covering", q)
            cells.append(n_dec(v * kappa) if v else "n/a")
        tot = r.total("C4_covering")
        cells.append(n_dec(tot * kappa) if tot else "n/a")
        rows.append(cells)
    return dx.table(rows, [3400, 1300, 1300, 1300, 1488], font_sz=7)


SCHEMA_ROWS = 569_774      # baris pada schema sembilan tabel yang sudah dimuat
SOURCE_ROWS = 1_550_922    # baris pada sembilan CSV sumber sebelum deduplikasi

NQ = len(QUERY_ORDER)
NF = len(ID_FAMILIES)
NUMWORDS = {16: "enam belas", 17: "tujuh belas", 18: "delapan belas",
            19: "sembilan belas", 20: "dua puluh", 8: "delapan", 9: "sembilan",
            10: "sepuluh", 11: "sebelas", 12: "dua belas", 13: "tiga belas",
            14: "empat belas", 15: "lima belas"}
NQW = NUMWORDS.get(NQ, str(NQ))
NFW = NUMWORDS.get(NF, str(NF))


# ==========================================================================
# results: bagian 4.1 - 4.5
# (lanjutan 4.6 - 4.9, kesimpulan, dan lampiran ada di build_paper_id_tail.py)
# ==========================================================================
def results_head(r: Results) -> str:
    p = []
    p.append(h1("4. Hasil dan Pembahasan"))

    # ---- 4.1 -------------------------------------------------------------
    p.append(h2("4.1 Perilaku Baseline Tanpa Index Sekunder"))
    total0 = r.total("C0_zero") or 0.0
    slowest = max((q for q in QUERY_ORDER if q != "W5.1 LEFT JOIN"),
                  key=lambda q: r.med("C0_zero", q) or 0)
    fastest = min(QUERY_ORDER, key=lambda q: r.med("C0_zero", q) or 1e18)
    p.append(body(
        f"Kalau schema cuma punya primary key, dan kalau asidekan dulu query anti-join yang "
        f"ekstrem itu yang dibahas di Bagian 4.4, {n_int(NQ - 1)} query non-outlier "
        f"butuh total {n_int(total0)} ms, dengan rentang dari "
        f"{msu(r.med('C0_zero', fastest))} untuk {fastest} sampai "
        f"{msu(r.med('C0_zero', slowest))} untuk {slowest}. Ada satu sifat dari baseline "
        f"ini yang menentukan cara seluruh hasil berikutnya harus dibaca. Dua tabel yang "
        f"menampung sebagian besar data, yaitu orders sebanyak 99.441 baris dan order_items "
        f"sebanyak 112.650 baris, ukurannya kecil sehingga full scan salah satunya hanya "
        f"memakan waktu puluhan milidetik di platform kalibrasi. Jadi baseline tanpa index "
        f"itu bukan kondisi yang rusak parah; dia cuma sedang-sedang saja, dan hampir "
        f"tidak menyisakan ruang bagi indeksasi untuk menunjukkan gain ber orde besaran "
        f"seperti yang biasanya dilaporkan eksperimen semacam ini. Ini sifat dari dataset-nya, "
        f"bukan dari metodologinya, dan itulah sebabnya hasil di paper ini lebih rendah "
        f"daripada yang paling sering diklaim di literatur."))
    p.append(body(
        f"Satu pengecualian ini justru membuktikan aturannya. Formulasi anti-join W5.1 "
        f"memakan waktu {msu(r.med('C0_zero', 'W5.1 LEFT JOIN'))} tanpa index, yaitu "
        f"{n_dec((r.med('C0_zero', 'W5.1 LEFT JOIN') or 0) / max(r.med('C0_zero', slowest) or 1, 1), 0)} "
        f"kali lebih lambat daripada query paling lambat yang tersisa, karena tanpa index "
        f"pada kolom join, outer join-nya berubah menjadi block-nested-loop join. Satu sel "
        f"sebesar itu akan mendominasi rata-rata apa pun yang dihitung dari seluruh sweep, "
        f"jadi sel tersebut dikeluarkan dari total di Tabel 5 dan dari rata-rata geometris "
        f"di Tabel 6, lalu dianalisis terpisah di Bagian 4.4. Pengeluarannya disebut secara "
        f"terbuka, bukan dilakukan diam-diam, karena pembaca yang menghitung ulang "
        f"rata-ratanya sendiri tidak akan bisa mereproduksinya kalau tidak tahu sel mana "
        f"yang dibuang."))

    # ---- 4.2 -------------------------------------------------------------
    p.append(h2("4.2 Efek Menambahkan Index"))
    p.append(body(
        f"Tabel 5 melaporkan waktu eksekusi median untuk seluruh {n_int(NQ)} query pada kelima "
        f"konfigurasi. Gambar 1 memplot nilai yang sama pada sumbu logaritmik, dan Gambar 2 "
        f"menampilkan percepatan waktunya terhadap baseline tanpa index. Distribusi hasil "
        f"inilah temuan utamanya, dan itu bukan yang biasanya dilaporkan."))
    p.append(caption("Tabel", "5. Waktu eksekusi median dalam milidetik per query dan per "
                              "konfigurasi index, beserta percepatan relatif terhadap C0. "
                              "Outlier W5.1 dikecualikan dari baris total dan rata-rata "
                              "geometris."))
    p.append(table_all_results(r))
    p.append(caption("Gambar", "1. Waktu eksekusi median sisi server per workload dan per "
                               "konfigurasi index (sumbu logaritmik)."))
    p.append("FIGURE_1")
    p.append(caption("Gambar", "2. Percepatan waktu eksekusi relatif terhadap baseline "
                               "tanpa index C0 (sumbu logaritmik)."))
    p.append("FIGURE_2")

    g2 = r.geomean_speedup("C2_single") or 0
    g3 = r.geomean_speedup("C3_composite") or 0
    g4 = r.geomean_speedup("C4_covering") or 0
    p.append(body(
        f"Kalau digabung menjadi rata-rata geometris dari {n_int(len(QUERY_ORDER) - 1)} "
        f"query non-outlier, baseline pasca-impor C1 hanya membaik sebesar "
        f"{xx(r.geomean_speedup('C1_fk'))} dibanding C0, set index kolom tunggal yang luas "
        f"C2 sebesar {xx(g2)}, set komposit C3 sebesar {xx(g3)}, dan set komposit-plus-"
        f"covering C4 sebesar {xx(g4)}. Ada dua pengamatan yang menyusul, dan keduanya "
        f"menarik ke arah yang berlawanan."))
    p.append(body(
        f"Pengamatan pertama adalah bahwa indeksasi membantu jauh lebih sedikit daripada "
        f"yang biasanya disyaratkan literatur. Bahkan konfigurasi terbaik cuma memperbaiki "
        f"query median sekitar dua kali lipat, dan beberapa query tidak membaik sama sekali "
        f"atau malah sedikit lebih lambat. Tabel 6 menunjukkan ini per keluarga workload. "
        f"Alasannya ada di rasio baris yang diperiksa terhadap baris yang dikembalikan "
        f"yang sudah dibahas di atas: untuk query filter dan agregasi yang mendominasi "
        f"beban kerja, baris yang memenuhi kriteria adalah sebagian besar isi relasinya, "
        f"jadi index tidak mungkin menghindari sebagian besar pembacaan dan plafon gain "
        f"yang bisa dicapai jadi rendah. Hasil semacam ini bukan menyangkal indeksasi, tapi "
        f"pernyataan tentang rezimnya. Indeksasi membayar kalau fraksi selektifnya kecil, "
        f"dan beban kerja tempat itu berlaku di sini justru yang gainnya paling "
        f"mencolok."))
    p.append(caption("Tabel", "6. Percepatan rata-rata geometris per keluarga workload "
                              "relatif terhadap baseline tanpa index C0. Tanda bintang "
                              "menandai konfigurasi terbaik di tiap keluarga. W5.1 "
                              "dikecualikan dari setiap agregat yang dilaporkan di paper "
                              "ini."))
    p.append(table_family_speedup(r))
    p.append(dx.para(dx.run("Catatan. W5.1 dikecualikan dari rata-rata keluarga W5 dan "
                            "dari seluruh total dan rata-rata geometris di paper ini, "
                            "karena besarnya akan mendominasi angka-angka itu. Query ini "
                            "dianalisis terpisah di Bagian 4.4, di situ dia justru "
                            "menjadi temuan utamanya.", sz=7.5),
                     align="both", after=120, left=0, hanging=0))
    p.append(body(
        f"Pengamatan kedua adalah bahwa peringkat konfigurasi tidak seperti yang diprediksi "
        f"oleh niat desainnya. Set index kolom tunggal yang luas, yaitu C2, mengalahkan "
        f"set komposit C3 maupun set komposit-plus-covering C4, dengan {xx(g2)} melawan "
        f"{xx(g3)} dan {xx(g4)}. Bagian 4.3 menunjukkan bahwa pembalikan ini disebabkan "
        f"sifat tertentu dan sangat dipahami dari urutan kolom index komposit, dan itulah "
        f"temuan yang paling gampang dipindahkan ke konteks lain dari seluruh penelitian "
        f"ini."))
    nz = [(r.speedup("C4_covering", q) or 0, q) for q in QUERY_ORDER
          if q != "W5.1 LEFT JOIN"]
    nz.sort(reverse=True)
    p.append(body(
        f"Dengan outlier dikecualikan, gain terbesar di bawah C4 adalah " +
        ", ".join(f"{q} di {idp(s)}x" for s, q in nz[:3] if s > 1) +
        f", sedangkan {n_int(sum(1 for s, _ in nz if s <= 1.05))} query sisanya tidak "
        f"mendapat gain yang bisa diukur. Perbaikan tunggal terbesar di seluruh sweep "
        f"adalah W5.1 di {xx(r.speedup('C4_covering', 'W5.1 LEFT JOIN'))}, tapi itu bukan "
        f"efek indeksasi dalam arti biasa; itu pergantian algoritma join, dan dibahas di "
        f"Bagian 4.4."))

    # ---- 4.3 -------------------------------------------------------------
    p.append(h2("4.3 Urutan Kolom di Dalam Index Lebih Pentingdaripada Banyaknya Index"))
    p.append(body(
        f"Karena C2, C3, dan C4 adalah alternatif, bukan tahap-tahap yang ditumpuk, "
        f"ketiganya bisa dibandingkan langsung, dan perbandingan itu justru menyangkal "
        f"niat desain yang melatarbelakangi mereka. C2 mewakili keluasan: ia menambahkan "
        f"index pada setiap kolom yang muncul di predikat, kondisi join, atau klausa "
        f"ORDER BY. C3 mewakili prinsip leftmost-prefix: menyusun tiap index sehingga "
        f"kolom utamanya adalah predikat kesetaraan dan kolom terakhirnya adalah kolom "
        f"rentang atau kolom join. C4 melangkah lebih jauh lagi, membuat index menutupi "
        f"seluruh proyeksi. Ekspektasinya, C3 mengalahkan C2 pada predikat majemuk dan C4 "
        f"mengalahkan keduanya. Hasil pengukurannya justru terbalik: C2 mencapai "
        f"{xx(g2)}, C3 {xx(g3)}, dan C4 {xx(g4)}."))
    p.append(body(
        "Mekanismenya kelihatan di rencana eksekusi yang terekam, dan itu adalah aturan "
        "leftmost-prefix yang bekerja sebagai beban, bukan keuntungan. Index komposit pada "
        "(order_status, order_purchase_timestamp) bisa melayani predikat pada order_status "
        "dan rentang pada order_purchase_timestamp, tetapi tidak bisa melayani predikat "
        "atau urutan pada order_purchase_timestamp saja, karena kolom utamanya tidak "
        "dibatasi sehingga nilai-nilaiunya tersebar di seluruh index. Workload W2.2 dan "
        "workload W8.1 sama-sama membatasi atau mengurutkan berdasarkan "
        "order_purchase_timestamp saja, dan keduanya menunjukkan akibatnya."))
    p.append(caption("Tabel", "7. Pengaruh urutan kolom index pada dua workload yang "
                              "membatasi atau mengurutkan berdasarkan kolom terakhir "
                              "saja."))
    p.append(table_column_order(r))
    p.append(body(
        f"Di workload W2.2, yang menghitung order dalam satu bulan, C2 menyelesaikan query "
        f"menjadi range scan terbatas dan selesai dalam "
        f"{msu(r.med('C2_single', 'W2.2 SARG month'))}, sedangkan C4 jatuh kembali ke "
        f"full scan atas index komposit dan membutuhkan "
        f"{msu(r.med('C4_covering', 'W2.2 SARG month'))}. Di workload W8.1, yang mengambil "
        f"dua puluh order terbaru, C2 membaca index timestamp sesuai urutannya sendiri dan "
        f"tidak perlu sorting sama sekali, selesai dalam "
        f"{msu(r.med('C2_single', 'W8.1'))}, sementara C3 dan C4 sama-sama melaporkan "
        f"filesort di rencana dan membutuhkan {msu(r.med('C3_composite', 'W8.1'))} dan "
        f"{msu(r.med('C4_covering', 'W8.1'))}. Jadi mengganti index kolom tunggal dengan "
        f"index komposit pada kolom yang sama membuat query-query ini satu sampai dua "
        f"orde besaran lebih lambat."))
    p.append(body(
        "Index kompositnya tentu tidak sia-sia, dan menyimpulkan bahwa index kolom "
        "tunggal selalu lebih baik merupakan kekeliruan. W7.1, yang memberi peringkat seller "
        "di dalam tiap provinsi, membaik dari " +
        f"{msu(r.med('C0_zero', 'W7.1'))} tanpa index menjadi "
        f"{msu(r.med('C3_composite', 'W7.1'))} dengan index komposit pada "
        "(seller_id, price), sebuah gain sebesar " +
        f"{xx(r.speedup('C3_composite', 'W7.1'))}, sedangkan set index kolom tunggal yang "
        f"luas C2 tidak mengubahnya sama sekali, masih di "
        f"{msu(r.med('C2_single', 'W7.1'))}. Index komposit itu cocok persis dengan kolom "
        "pengelompokan dan agregasi milik workload tersebut. Jadi kesimpulannya bukan "
        "bahwa satu desain menang, melainkan bahwa tidak ada desain tunggal yang menang: "
        "set index terbaik bersifat spesifik terhadap workload, dan pertanyaan yang "
        "menentukan bukan berapa banyak index yang perlu dibuat, melainkan apakah kolom "
        "utama tiap index itu adalah kolom yang dibatasi, diurutkan, atau dikelompokkan "
        "oleh query. Index komposit yang benar untuk satu predikat majemuk justru bisa "
        "merugikan query kolom tunggal yang memakai kolom-kolom terakhirnya, dan kerugian "
        "semacam itu tidak terlihat di angka agregat karena ia tertimbang oleh keuntungan "
        "pada workload yang memang index komposit itu dirancang untuk layan."))

    # ---- 4.4 -------------------------------------------------------------
    p.append(h2("4.4 Formulasi JOIN Versus Subquery"))
    p.append(body(
        "Keluarga semi-join W4 dan keluarga anti-join W5 masing-masing menyatakan satu "
        "pertanyaan logis yang sama dalam tiga bentuk sintaks yang berbeda tapi secara "
        "semantik setara. Tabel 8 melaporkan waktu tiap bentuk pada kondisi index yang "
        "identik, lengkap dengan jalur akses yang dipilih pada konfigurasi tanpa index."))
    p.append(caption("Tabel", "8. Formulasi semi-join dan anti-join dibandingkan pada "
                              "kondisi index yang identik."))
    p.append(table_join_vs_subquery(r))
    p.append(caption("Gambar", "3. Formulasi semi-join dan anti-join dibandingkan pada "
                               "konfigurasi index yang identik (sumbu logaritmik)."))
    p.append("FIGURE_3")

    w4 = [r.med("C0_zero", q) or 0 for q in ("W4.1 JOIN", "W4.2 IN", "W4.3 EXISTS")]
    w5 = [r.med("C0_zero", q) or 0
          for q in ("W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS")]
    s4 = max(w4) / min(w4) if min(w4) > 0 else float("nan")
    s5 = max(w5) / min(w5) if min(w5) > 0 else float("nan")
    p.append(body(
        f"Keluarga semi-join berperilaku seragam. Tiga bentuknya memakan waktu "
        f"{msu(w4[0])}, {msu(w4[1])}, dan {msu(w4[2])} tanpa index sekunder, dengan "
        f"rentang cuma {idp(s4)}x, dan urutannya stabil di semua konfigurasi. Tidak ada "
        f"aturan penulisan ulang yang membedakan ketiganya, karena optimizer mengubah "
        f"ketiganya menjadi semi-join yang sama secara internal, dan tidak ada index di "
        f"konfigurasi mana pun yang bisa membuat konversi itu berbeda hasilnya."))
    c4w5 = [r.med("C4_covering", q) or 0
            for q in ("W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS")]
    s5c4 = max(c4w5) / min(c4w5) if min(c4w5) > 0 else float("nan")
    p.append(body(
        f"Keluarga anti-join berperilaku sangat berbeda, dan urutannya berbalik total "
        f"begitu ada index. Tanpa index, formulasi LEFT JOIN memakan "
        f"{msu(w5[0])}, sementara bentuk NOT IN dan NOT EXISTS memakan {msu(w5[1])} dan "
        f"{msu(w5[2])}, sebuah rentang sebesar {n_dec(s5, 0)}x. Rencana eksekusi yang "
        f"terekam menjelaskan kenapa. Bentuk subquery dikenali sebagai kandidat anti-join "
        f"dan dieksekusi sebagai lookup berbasis hash terhadap sisi kanan yang sudah "
        f"dimaterialisasi, dengan biaya yang sebanding dengan jumlah ukuran kedua relasi. "
        f"Sementara formulasi LEFT JOIN eksplisit, yang secara logis membawa anti-join yang "
        f"sama, dieksekusi sebagai block-nested-loop join yang harus selesai dulu sebelum "
        f"filter IS NULL bisa diterapkan. Di konfigurasi ini bentuk subquery bukan "
        f"pengganti seadanya untuk bentuk join; dia justru rencana yang lebih baik, dan "
        f"yang melorot adalah bentuk join sintaksnya."))
    p.append(body(
        f"C4 menambahkan index pada (order_id, review_score), yaitu kolom join dan filter "
        f"milik keluarga ini, dan urutannya berbalik. Bentuk LEFT JOIN sekarang memakan "
        f"{msu(c4w5[0])}, tercepat dari ketiganya, melawan {msu(c4w5[1])} dan "
        f"{msu(c4w5[2])} untuk bentuk subquery, sebuah rentang sebesar {n_dec(s5c4, 1)}x ke "
        f"arah sebaliknya. Rencananya ikut berubah: outer join menjadi lookup index pada "
        f"rentang tanggal tabel penggerak diikuti probe langsung ke index review, "
        f"sementara bentuk subquery mematerialisasi sisi kanan yang besar dan tidak bisa "
        f"dihindari oleh index itu."))
    nojoin_cfgs = [c for c in CONFIG_ORDER if c != "C4_covering"]
    n_nojoinidx = len(nojoin_cfgs)
    nojoin_vals = [r.med(c, "W5.1 LEFT JOIN")
                   or r.censored_ms.get((c, "W5.1 LEFT JOIN"), 0.0)
                   for c in nojoin_cfgs]
    _cens = [CONFIG_SHORT[c] for c in nojoin_cfgs
             if r.is_censored(c, "W5.1 LEFT JOIN")]
    censored_txt = (", ".join(_cens) + " melebihi batas 45 detik per pernyataan yang "
                    "ditetapkan untuk sweep ini dan dilaporkan sebagai tersensor") \
        if _cens else "tidak ada yang melebihi batas 45 detik per pernyataan"

    p.append(body(
        f"Ini membalikkan nasihat lama dalam dua hal. Yang umum diajarkan adalah "
        f"subquery adalah pilihan naif yang harus ditulis ulang; di sini justru subquery "
        f"lebih cepat daripada bentuk join sebesar {n_dec(s5, 0)}x sebelum diindex, dan "
        f"lebih lambat sebesar {n_dec(s5c4, 1)}x setelah diindex. Yang juga umum diajarkan "
        f"adalah ketiga formulasi itu saling menggantikan; di sini biaya relatif mereka "
        f"berbalik arah mengikuti set index. Kedua pengamatan itu konsisten, dan "
        f"barulah bersama-sama menghasilkan kesimpulan sebenarnya: biaya sebuah formulasi "
        f"adalah sifat dari rencana yang dipilih optimizer, rencana itu sendiri adalah "
        f"sifat dari index yang tersedia, jadi tidak ada aturan berbentuk selalu pakai "
        f"JOIN atau selalu pakai EXISTS yang bisa benar. Implikasi praktisnya murah dan "
        f"tidak diperdebatkan: periksa dulu rencananya sebelum menulis ulang, karena "
        f"penulisan ulang yang dibenarkan aturan singkat bisa memaksakan biaya "
        f"{n_dec(s5, 0)}x di satu arah dan menghemat {n_dec(s5c4, 1)}x di arah lain. Perlu "
        f"ditambahkan juga bahwa konfigurasi tercepat untuk keluarga ini bukan yang punya "
        f"index terbanyak, melainkan yang punya index pada kolom join: "
        f"{n_int(n_nojoinidx)} konfigurasi yang tidak punya index itu membiarkan W5.1 di "
        f"{n_int(min(nojoin_vals))} ms atau lebih, dan {censored_txt}."))

    # ---- 4.5 -------------------------------------------------------------
    p.append(h2("4.5 Bentuk Predikat, SARGability, dan Selektivitas"))
    n1, s1 = "W2.1 non-SARG month", "W2.2 SARG month"
    n2, s2 = "W2.3 non-SARG year", "W2.4 SARG year"
    rows_m = SELECTIVITY["month"]
    rows_y = SELECTIVITY["year"]
    p.append(body(
        f"Workload W2 membandingkan empat predikat atas kolom yang sama. Dua pasang di "
        f"antaranya mengembalikan jumlah baris yang identik, dan di dalam setiap pasang "
        f"dua anggota itu hanya berbeda pada apakah sebuah fungsi diterapkan ke kolom yang "
        f"difilter atau tidak. Kedua anggota tiap pasang sudah diverifikasi mengembalikan "
        f"jumlah yang sama. Yang berbeda antarpasang adalah selektivitas: pasangan bulan "
        f"mencocokkan {n_int(rows_m)} order, atau "
        f"{pct(rows_m, SELECTIVITY['orders_total'])} dari tabel, sedangkan pasangan tahun "
        f"{n_int(rows_y)}, atau {pct(rows_y, SELECTIVITY['orders_total'])}. "
        f"Memasukkan kedua rezim itu penting, karena SARGability baru berguna "
        f"ketika ia membuat server bisa menghindari pembacaan baris, dan predikat yang "
        f"mencocokkan sebagian besar tabel tidak menyediakan baris yang bisa dihindari."))
    p.append(caption("Tabel", "9. Predikat non-SARGable dan SARGable pada dua tingkat "
                              "selektivitas."))
    p.append(table_sargability(r))
    p.append(caption("Gambar", "4. Bentuk predikat dibandingkan pada dua tingkat "
                               "selektivitas (sumbu logaritmik)."))
    p.append("FIGURE_4")
    adv_m = ((r.med("C4_covering", n1) or 0)
             / max(r.med("C4_covering", s1) or 1e-9, 1e-9))
    p.append(body(
        f"Pasangan yang selektif berperilaku persis seperti prediksi teori, dan "
        f"rencana eksekusinya mengonfirmasi mekanismenya, bukan sekadar berkorelasi "
        f"padanya. Di C2, bentuk non-SARGable dieksekusi sebagai full scan atas index "
        f"timestamp dengan filter yang diterapkan pada tiap entri, memakan "
        f"{msu(r.med('C2_single', n1))}, sedangkan bentuk SARGable dieksekusi sebagai "
        f"range scan terbatas, memakan {msu(r.med('C2_single', s1))}. Itu sebuah faktor "
        f"{n_dec((r.med('C2_single', n1) or 0) / max(r.med('C2_single', s1) or 1e-9, 1e-9), 1)}x "
        f"hanya untuk perubahan yang seluruhnya cuma dari menulis ulang satu predikat dan tidak "
        f"ada yang lain."))
    adv_y = ((r.med("C4_covering", n2) or 0)
             / max(r.med("C4_covering", s2) or 1e-9, 1e-9))
    p.append(body(
        f"Pasangan yang tidak selektif menunjukkan batas aturan ini. YEAR(ts) = 2018 dan "
        f"rentang ekuivalennya mencocokkan {n_int(rows_y)} dari 99.441 baris, dan di C4 "
        f"keduanya memakan {msu(r.med('C4_covering', n2))} dan "
        f"{msu(r.med('C4_covering', s2))}. Jadi bentuk SARGable sama sekali tidak lebih "
        f"cepat: rasio waktu SARGable terhadap non-SARGable cuma {idp(1 / adv_y)}x, nyaris "
        f"tidak bisa dibedakan dari satu. Sebuah range scan yang mencakup "
        f"{n_dec(100.0 * rows_y / SELECTIVITY['orders_total'], 0)} persen dari tabel "
        f"tetap harus mengunjungi fraksi index entry yang sama, jadi server melakukan "
        f"sebagian besar pekerjaan yang sama seperti pada full scan, dan hanya "
        f"menghemat kolom yang tidak perlu dibaca. Jadi menulis ulang predikat itu "
        f"perlu tapi belum cukup: untungnya dikendalikan oleh selektivitas. Reviewer yang "
        f"menguji SARGability hanya pada predikat berselektivitas rendah akan sampai pada "
        f"kesimpulan yang memang terlihat benar bahwa hal itu tidak penting, dan "
        f"kesimpulan itu salah."))
    p.append(body(
        f"Perlu juga dicatat apa yang dilakukan C4 pada pasangan yang selektif. Rasio "
        f"{idp(adv_m)}x-nya jauh lebih lemah dibanding rasio C2, dan rencana eksekusi "
        f"yang terekam menjelaskan kenapa: C4 tidak punya index yang kolom utamanya adalah "
        f"order_purchase_timestamp, jadi kedua anggota pasangan itu sama-sama jatuh kembali "
        f"ke pemindaian penuh atas index komposit. SARGability tidak bisa menolong kalau "
        f"memang tidak ada index yang bisa dimanfaatkan, dan itu persis efek urutan kolom yang "
        f"diidentifikasi di Bagian 4.3. Jadi bentuk predikat dan desain index pun bukan "
        f"keputusan yang independen, dan penelitian yang hanya mengubah salah satunya akan "
        f"melaporkan yang satunya sebagai tidak relevan."))
    p.append(body(
        f"Urutan praktis yang lahir dari semua ini adalah: tulis ulang predikatnya menjadi "
        f"bentuk rentang, cek selektivitasnya, lalu buat index yang kolom utamanya adalah "
        f"kolom yang difilter hanya kalau rentangnya cukup selektif untuk membenarkan "
        f"biaya tulis. Penulisan ulang itu sendiri gratis: tidak butuh perubahan schema, "
        f"tidak butuh pembuatan index, dan tidak butuh rilis aplikasi, serta tidak mengubah "
        f"semantik. Pada kasus selektif yang diukur di sini, itu selisih antara "
        f"{msu(r.med('C2_single', n1))} dan {msu(r.med('C2_single', s1))}. Perlu disebut "
        f"juga bahwa membuat index untuk melayani predikat yang tidak SARGable sama sekali "
        f"tidak bekerja, jadi tim yang menambahkan index tanpa menulis ulang predikatnya "
        f"bisa saja melihat nol peningkatan lalu salah menyimpulkan bahwa index itu "
        f"percuma."))
    return "".join(p)


# ==========================================================================
# results 4.6 - 4.9, kesimpulan, dan lampiran (file terpisah)
# ==========================================================================
def _tail():
    import build_paper_id_tail as tail
    return tail


def results(r: Results) -> str:
    return results_head(r) + _tail().results_tail(r)


def conclusion(r: Results) -> str:
    return _tail().conclusion(r)


def back_matter(r: Results) -> str:
    return _tail().back_matter(r)


# ==========================================================================
# daftar pustaka
# ==========================================================================
def reference_list() -> str:
    """Referensi tetap dalam bahasa asli; hanya judul bagian yang diterjemahkan."""
    p = [h1("Daftar Pustaka")]
    for i, (_key, _sinta, text) in enumerate(REFERENCES, start=1):
        p.append(dx.para(dx.run(f"[{i}]\t", sz=9) + dx.run(text, sz=9),
                         align="both", after=60, left=567, hanging=567))
    return "".join(p)


# ==========================================================================
# assembly
# ==========================================================================
def main() -> int:
    r = Results()
    bm = load_benchmark_module()

    imgs = dx.ImageRegistry()
    fig_w = int(CONTENT_INCH * EMU_PER_INCH)

    chunks = [front_matter(), abstract_and_keywords(r)]
    narrative = (introduction(r, bm) + related_work(r) + method(r, bm)
                 + results(r) + conclusion(r))

    fig_map = {
        "FIGURE_1": "fig1_execution_time.png",
        "FIGURE_2": "fig2_speedup.png",
        "FIGURE_3": "fig3_join_vs_subquery.png",
        "FIGURE_4": "fig4_sargability.png",
    }
    for marker, fname in fig_map.items():
        path = os.path.join(FIGDIR, fname)
        if marker in narrative:
            if not os.path.isfile(path):
                print(f"WARNING: {path} missing, leaving {marker} unresolved")
                continue
            narrative = narrative.replace(marker, imgs.figure_para(path, fig_w))
    if "FIGURE_" in narrative:
        leftover = [m for m in fig_map if m in narrative]
        print(f"WARNING: unresolved figure markers: {leftover}")

    body_xml = "".join(chunks) + narrative + back_matter(r) + reference_list()
    dx.build(TEMPLATE, OUT, body_xml, imgs)

    print(f"wrote {OUT}")
    print(f"  references: {len(REFERENCES)}")
    print(f"  figures embedded: {len(imgs.items)}")
    print(f"  measurements: {r.repeats} timed repetitions per cell, "
          f"{r.repeats * 5 * len(QUERY_ORDER)} timed runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())