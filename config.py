FIELDS = {
    "boy": "Boy (cm)",
    "kilo": "Kilo (kg)",
    "sikayet": "Şikâyeti",
    "ozgecmis": "Özgeçmişi",
    "soygecmis_anne": "Soygeçmişi - Anne",
    "soygecmis_baba": "Soygeçmişi - Baba",
    "soygecmis_kardes": "Soygeçmişi - Kardeş",
    "ilaclar": "Kullandığı ilaçlar",
    "genel_durum": "Genel durumu",
    "tansiyon": "Tansiyon",
    "nabiz": "Nabız",
    "ates": "Ateş",
    "solunum": "Solunum sayısı",
    "bb": "Baş-boyun (BB)",
    "kvs": "KVS",
    "sols": "Solunum sistemi (SOLS)",
    "batin": "Batın",
    "ext": "Ekstremiteler (EXT)",
    "aks": "AKŞ",
    "hba1c": "HbA1c",
    "st4": "Serbest T4 (sT4)",
    "tsh": "TSH",
    "kcft": "KCFT",
    "bft": "BFT",
    "goruntuleme": "Görüntüleme (USG/BT/MR/Sintigrafi)",
    "ontani": "Öntanı",
    "oneri": "Öneri",
}

# New encounters are blank. Findings and completed actions must be explicit.
INITIAL_DATA = {key: '' for key in FIELDS}
VERSION = '2.0.0-alpha.1'


RECOMMENDATIONS = [
    (
        "Diyabet kontrolünü gözden geçirin",
        "HbA1c ve mevcutsa ev glukoz ölçümlerini; ilaç kullanımı, uyum ve hipoglisemi öyküsüyle birlikte değerlendirin. "
        "İlaç değişikliği yalnızca hastayı izleyen hekim tarafından yapılmalıdır.",
        '"Diabetes Mellitus" AND "Standards of Care" AND glycemic assessment',
    ),
    (
        "Tiroid değerlendirmesini klinikle birlikte ele alın",
        "Süren yorgunluk veya kilo değişikliği varsa TSH ve gerektiğinde serbest T4 sonuçlarının klinik bağlamda "
        "yorumlanmasını değerlendirin; tek başına belirtiler tanı koydurmaz.",
        '"fatigue" AND "thyroid function tests" AND adults',
    ),
    (
        "Anemi ve diğer eksiklik olasılıklarını değerlendirin",
        "Öykü ve muayene uygun olduğunda tam kan sayımı; klinik şüpheye göre ferritin, demir veya B12 gibi "
        "tetkikleri hekimle değerlendirin.",
        '"fatigue" AND "iron deficiency" AND "primary care"',
    ),
    (
        "PCOS ile ilişkili metabolik riskleri gözden geçirin",
        "Kişinin mevcut kayıtlarına göre kan basıncı, lipid profili ve glisemik risk izleminin güncel kılavuzlara "
        "uygunluğunu; boy/kilo ve yaşam evresi bilgileri tamamlandıktan sonra değerlendirin.",
        '"polycystic ovary syndrome" AND metabolic screening guideline',
    ),
    (
        "Uyku, ruhsal durum ve ilaç etkilerini sorgulayın",
        "Yorgunluğun süresi ve günlük yaşama etkisiyle birlikte uyku kalitesi, duygu durumu, kullanılan ilaçlar "
        "ve klinik açıdan ilgili diğer etkenleri gözden geçirin.",
        '"fatigue" AND "primary care" AND evaluation',
    ),
]

# Dikte metninde alan adı açıkça yazıyorsa yalnızca o alan güncellenir.
LABELS = {
    "boy": ("boy", "boyu"),
    "kilo": ("kilo", "ağırlık"),
    "sikayet": ("şikayeti", "şikâyeti", "şikayet", "şikâyet", "yakınma", "basvuru nedeni", "başvuru nedeni"),
    "ozgecmis": ("özgeçmişi", "özgeçmiş", "ozgecmisi", "ozgecmis", "geçmiş hastalık"),
    "soygecmis_anne": ("anne", "anne soygeçmişi", "anne hastalıkları"),
    "soygecmis_baba": ("baba", "baba soygeçmişi", "baba hastalıkları"),
    "soygecmis_kardes": ("kardeş", "kardeş soygeçmişi", "kardeş hastalıkları"),
    "ilaclar": ("kullandığı ilaçlar", "ilaçları", "ilaç", "ilaclar", "ilac"),
    "genel_durum": ("genel durumu", "genel durum"),
    "tansiyon": ("tansiyon", "kan basıncı"),
    "nabiz": ("nabız", "nabiz"),
    "ates": ("ateş", "ates"),
    "solunum": ("solunum sayısı", "solunum", "solunum sayisi"),
    "bb": ("bb", "baş-boyun", "bas-boyun"),
    "kvs": ("kvs",),
    "sols": ("sols", "solunum sistemi"),
    "batin": ("batın", "batin"),
    "ext": ("ext", "ekstremite", "ekstremiteler"),
    "aks": ("akş", "aks", "açlık kan şekeri"),
    "hba1c": ("hba1c", "hb a1c"),
    "st4": ("st4", "serbest t4", "serbest t 4"),
    "tsh": ("tsh",),
    "kcft": ("kcft",),
    "bft": ("bft",),
    "goruntuleme": ("görüntüleme", "goruntuleme", "usg", "bt", "mri", "mr"),
    "ontani": ("öntanı", "ontani", "ön tanı"),
    "oneri": ("öneri", "oneri", "plan"),
}


