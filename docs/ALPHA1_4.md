# V2 Alpha1.4 — Hekim odaklı arayüz ve kullanım kılavuzu

Ana ekranda lacivert/mavi marka paleti, tutarlı Segoe UI yazı boyutları,
belirgin kayıt/onay düğmeleri ve üç aşamalı yönlendirme uygulanır.
Anamnez düzenleme alanı ana odağı oluşturur; tarihli aktarım önizlemesi
gerektiğinde açılır. Önizleme açılması onay vermez veya metni değiştirmez.
Alt eylemler küçük pencerede öncelikli alanını korur; editör kalan yüksekliğe uyar.
Metin alanlarında kaydırma çubukları, formda genişliğe uyum ve fare tekerleği
desteği bulunur. Ayarlar görevlerine göre dört grupta sunulur.

F1 yerel HTML kılavuzunu açar; F6 ana taslağa gider. Ctrl+N yeni görüşme,
Ctrl+O JSON açma ve Ctrl+Tab sekme değiştirme destekler. Metin alanında Tab
ve Shift+Tab odak değiştirir. Var olan ayrılma/onay/mahremiyet kuralları korunur.
Kılavuz ilk kurulum, normal üç adım, belirsiz konuşmaların incelenmesi,
Miamed'e manuel yapıştırma, kayıt/yükleme, klavye ve sorun gidermeyi kapsar.
HTML dosyası pakete dahildir; ayrıca Türkçe PDF kılavuzu yayımlanır.

115 yerel test başarılı: önceki 112 regresyon ve yerel yardım, önizleme
güvenliği, küçük pencerede eylem erişimi/inceleme engeli için üç gerçek Tk testi.
PDF'nin altı sayfası görüntülenerek karakterler, tablolar ve taşmalar incelendi.
Windows ekran yakalama aracı iki kez zaman aşımı verdiği için canlı görsel
kabul tamamlandı iddiası yoktur. Bu sürüm klinik motor davranışını değiştirmez;
Alpha1.3 konuşmacı belirsizliği ve hekim kontrolü sınırları sürer.
Gerçek hastane cihazı, yüksek DPI ve Miamed kabulü ayrıca doğrulanmalıdır.
