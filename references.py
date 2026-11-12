"""
Reference list for the paper.

Every entry below was retrieved and checked during the literature review: the
bibliographic fields come from Crossref or the publisher record, and each SINTA
rank was read from the journal's own accreditation profile on the SINTA portal
(sinta.kemdiktisaintek.go.id). Entries are ordered by first citation in the
text.

`sinta` is recorded for transparency and for the authors' own checking; it is
not printed in the paper.
"""

# (key, sinta_or_venue_note, formatted IEEE-style entry)
REFERENCES: list[tuple[str, str, str]] = [
    ("olist",
     "dataset",
     "Olist, “Brazilian E-Commerce Public Dataset by Olist,” Kaggle, 2018. "
     "[Online]. Available: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"),

    ("andra2022",
     "SINTA 2",
     "D. Andra and A. B. Baizal, “E-commerce recommender system using PCA and "
     "K-Means clustering,” J. RESTI (Rekayasa Sist. dan Teknol. Inform.), vol. 6, "
     "no. 1, pp. 57–63, 2022, doi: 10.29207/resti.v6i1.3782."),

    ("haqqani2026",
     "SINTA 3",
     "Haqqani Septian Raya, A. Saputra, and F. D. Wicaksono, “Segmentasi pelanggan "
     "menggunakan metode K-Means dengan pendekatan RFM pada dataset Olist "
     "Brazilian E-Commerce,” J. Akuntansi dan Sist. Inf. (J-AKSI), vol. 1, no. 3, 2026, "
     "doi: 10.29210/jaksi.v1i3."),

    ("zaghloul2025",
     "Scopus Q1",
     "M. Zaghloul, S. Barakat, and A. Rezk, “Enhancing customer retention in online "
     "retail through churn prediction: A hybrid RFM, K-means, and deep neural network "
     "approach,” Expert Syst. Appl., vol. 290, p. 128465, 2025, "
     "doi: 10.1016/j.eswa.2025.128465."),

    ("jafri2022",
     "Scopus Q1/Q2",
     "S. I. H. Jafri, R. Ghazali, I. Javid, Z. H. Mahmood, and A. A. A. Hassan, "
     "“Deep transfer learning with multimodal embedding to tackle cold-start and "
     "sparsity issues in recommendation system,” PLOS ONE, vol. 17, no. 8, "
     "p. e0273486, 2022, doi: 10.1371/journal.pone.0273486."),

    ("asfe2025",
     "Scopus Q2",
     "A. M. Asfe, M. R. Rahman, and M. S. Hossain, “MNeuralTab: Integrating "
     "meta-modeling and neural networks for customer churn prediction in e-commerce,” "
     "Discover Appl. Sci., vol. 7, no. 6, 2025, doi: 10.1007/s42452-025-07157-0."),

    ("xu2022",
     "conference",
     "Z. Xu, Y. Tan, X. Wang, and X. Li, “Data-driven analysis for the operation "
     "status of the e-commerce platform based on Olist,” in Proc. 1st Int. Conf. "
     "Public Manag., Digital Econ. and Internet Technol. (ICITE 2022), 2022, "
     "pp. 859–867, doi: 10.5220/0011836600003607."),

    ("gogineni2025",
     "conference",
     "S. Gogineni, Y. Chinnam, K. D. Returi, V. M. Mohan, and G. Suryanarayana, "
     "“End-to-end data analysis of Brazilian e-commerce transactions,” in Proc. "
     "Int. Conf. Adv. Intell. Syst., 2025, pp. 82–100, "
     "doi: 10.2991/978-94-6463-976-6_6."),

    ("prorenca2023",
     "conference",
     "M. G. Proença, L. N. Moretti, and L. S. Coelho, “E-commerce customer "
     "satisfaction scores: Prediction with automatic machine learning,” in Proc. 11th "
     "Int. Conf. Prod. Res. – Americas, 2023, pp. 59–65, "
     "doi: 10.1007/978-3-031-36121-0_7."),

    ("gretscher2025",
     "Scopus Q1",
     "L. Gretscher and J. Dittrich, “How to optimize SQL queries? A comparison "
     "between split, holistic, and hybrid approaches,” Proc. VLDB Endow., vol. 18, "
     "no. 11, pp. 3910–3922, 2025, doi: 10.14778/3749646.3749663."),

    ("zhao2023",
     "Scopus Q1",
     "J. Zhao, H. Zhang, and Y. Gao, “Efficient query re-optimization with "
     "judicious subquery selections,” Proc. ACM Manag. Data, vol. 1, no. 2, pp. 1–26, "
     "2023, doi: 10.1145/3589330."),

    ("chen2026",
     "Scopus Q1",
     "S. Chen, C. Wu, Y. Jing, Z. Wu, W. He, Z. Zhang, and X. S. Wang, “RIB: Robust "
     "learning-based index benefit estimation,” Proc. ACM Manag. Data, vol. 4, "
     "no. 1, pp. 1–26, 2026, doi: 10.1145/3786691."),

    ("liang2024",
     "Scopus Q1",
     "F. Liang, F. C. M. Lau, H. Cui, Y. Li, B. Lin, C. Li, and X. Hu, “RelJoin: "
     "Relative-cost-based selection of distributed join methods for query plan "
     "optimization,” Inf. Sci., vol. 658, p. 120022, 2024, "
     "doi: 10.1016/j.ins.2023.120022."),

    ("shin2022",
     "Scopus Q1",
     "Y. Shin, J. Ahn, and D.-H. Im, “Join optimization for inverted index technique "
     "on relational database management systems,” Expert Syst. Appl., vol. 198, "
     "p. 116956, 2022, doi: 10.1016/j.eswa.2022.116956."),

    ("ji2023",
     "Scopus Q2",
     "L. Ji, R. Zhao, Y. Dang, J. Liu, and H. Zhang, “Query join order optimization "
     "method based on dynamic double deep Q-network,” Electronics, vol. 12, no. 6, "
     "p. 1504, 2023, doi: 10.3390/electronics12061504."),

    ("du2024",
     "Scopus Q2",
     "Y. Du, Z. Cai, and Z. Ding, “Query optimization in distributed database based "
     "on improved artificial bee colony algorithm,” Appl. Sci., vol. 14, no. 2, "
     "p. 846, 2024, doi: 10.3390/app14020846."),

    ("xiong2024",
     "Scopus Q1",
     "X. Xiong, J. Yu, and Z. He, “AutoQuo: An adaptive plan optimizer with "
     "reinforcement learning for query plan selection,” Knowl.-Based Syst., vol. 306, "
     "p. 112664, 2024, doi: 10.1016/j.knosys.2024.112664."),

    ("mohsin2021",
     "Scopus Q2",
     "S. A. Mohsin, S. M. Darwish, and A. Younes, “QIACO: A quantum dynamic cost ant "
     "system for query optimization in distributed database,” IEEE Access, vol. 9, "
     "pp. 15833–15846, 2021, doi: 10.1109/ACCESS.2021.3049544."),

    ("zheng2022",
     "Scopus Q2",
     "B. Zheng, X. Li, Z. Tian, and L. Meng, “Optimization method for distributed "
     "database query based on an adaptive double entropy genetic algorithm,” "
     "IEEE Access, vol. 10, pp. 4640–4648, 2022, "
     "doi: 10.1109/ACCESS.2022.3141589."),

    ("chandrashekariah2024",
     "SINTA 1",
     "Y. A. B. Chandrashekariah and H. A. Dinesha, “Structured Query Language query "
     "join optimization by using Rademacher averages and MapReduce algorithms,” "
     "Bull. Electr. Eng. Inform., vol. 13, no. 3, pp. 1730–1740, 2024, "
     "doi: 10.11591/eei.v13i3.6837."),

    ("mokodaser2022",
     "SINTA 2",
     "W. G. Mokodaser, M. Dwijayanti, and S. Samidi, “Implementasi metode indexing "
     "dan penggunaan subquery untuk optimalisasi database rawat jalan rumah sakit "
     "menggunakan MySQL,” CogITo Smart J., vol. 8, no. 2, pp. 335–345, 2022, "
     "doi: 10.31154/cogito.v8i2.415.335-345."),

    ("firmansyah2025",
     "SINTA 3",
     "E. Firmansyah, H. Firdaus, and S. Samidi, “Optimasi performa query subsidi "
     "debitur dengan index and table partition, subquery and indexing, dan parallel "
     "query execution,” J. Pendid. Teknol. Indonesia, vol. 5, no. 6, pp. 1769–1785, "
     "2025, doi: 10.52436/1.jpti.824."),

    ("ikhwan2026",
     "SINTA 3",
     "Ikhwan and A. Pramadjaya, “Penerapan database tuning melalui indexing dan "
     "optimasi query pada sistem kuesioner akademik,” MALCOM: Indonesian J. Mach. "
     "Learn. Comput. Sci., vol. 6, no. 2, 2026, doi: 10.57152/malcom.v6i2.2610."),

    ("naufal2022",
     "SINTA 4",
     "N. Naufal, S. Nurkhodijah, G. B. Anugrah, et al., “Comparasional analysis of "
     "MySQL and MongoDB response time query performance,” J. Inform. Teknol. Komputer "
     "(JITEK), vol. 2, no. 2, pp. 158–166, 2022, doi: 10.55606/jitek.v2i2.245."),

    ("witono2022",
     "SINTA 4",
     "E. Witono and P. Parno, “Perbandingan response time penggunaan index, views, "
     "dan materialized views database MySQL,” J-SAKTI (Jurnal Sains Komputer dan "
     "Informatika), vol. 6, no. 1, 2022, doi: 10.30645/j-sakti.v6i1.463."),

    ("uddin2023",
     "conference",
     "M. S. Farid Uddin, M. Tanziar Rahman, and M. A. Sikder, “Analysis of SARGable "
     "queries for query optimization in relational database,” in Proc. 26th Int. "
     "Conf. Comput. Inf. Technol. (ICCIT), 2023, pp. 1–4, "
     "doi: 10.1109/ICCIT60459.2023.10441199."),

    ("do2022",
     "conference",
     "T.-T.-T. Do, T.-B. Mai-Hoang, V.-Q. Nguyen, and Q.-T. Huynh, “Query-based "
     "performance comparison of graph database and relational database,” in Proc. 11th "
     "Int. Symp. Inf. Commun. Technol. (ISICT), 2022, pp. 375–381, "
     "doi: 10.1145/3568562.3568648."),

    ("fugkeaw2024",
     "Scopus Q1/Q2",
     "S. Fugkeaw, P. Suksai, and L. Hak, “SSF-CDW: Achieving scalable, secure, and "
     "fast OLAP query for encrypted cloud data warehouse,” J. Cloud Comput., vol. 13, "
     "no. 1, 2024, doi: 10.1186/s13677-024-00692-y."),

    ("fritchey2022",
     "book",
     "G. Fritchey, SQL Server 2022 Query Performance Tuning: A Detailed Approach to "
     "Query Optimization. New York, NY, USA: Apress, 2022, "
     "doi: 10.1007/978-1-4842-8891-7."),

    ("pollack2021",
     "book",
     "E. Pollack, Performance Optimization for OLAP Workloads in SQL Server. "
     "New York, NY, USA: Apress, 2021, doi: 10.1007/978-1-4842-7000-4."),
]