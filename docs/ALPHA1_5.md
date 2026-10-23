# V2 Alpha1.5 — Görünür işlem durumu ve ilk kullanım turu

Her sekmeden görülen üst işlem alanı hangi işin sürdüğünü, hareketli bekleme
çubuğunu ve geçen süreyi gösterir. Kayıt gerçekten başladığında KAYIT AÇIK
durumu görünür; bitirildikten sonra transkripsiyon ve yerel AI aşamaları izlenir.
Başarı, hata ve hekim incelemesi ayrı sonuç durumlarıdır. Klinik/ayar işlemlerini
tekrar başlatan düğmeler iş boyunca pasiftir; kaydı bitirme düğmesi çalışır.

Gerçek dosya boyutu bilinen model ve güncelleme indirmeleri bayt/yüzde gösterir.
Model hazırlama, transkripsiyon, AI ve aramada süre tahmini veya uydurma yüzde
yoktur; hareketli gösterge kullanılır. Güncelleme indirmesi bitse bile dosya
özeti doğrulanmadan %100 hazır denmez. İmza, SHA-256, boyut ve eski sürüm
uyumluluk kontrolleri korunur.

İlk normal EXE açılışında beş adımlı, atlanabilir tur gösterilir. Model kurulumu,
kayıt/elle bitirme, hekim incelemesi ve Miamed'e manuel yapıştırmayı anlatır.
F2 veya başlıktaki Kullanım turu düğmesiyle tekrar açılır. Tur hasta kaydı,
mikrofon veya model indirmesi başlatmaz; mevcut taslağı değiştirmez. Otomatik
gösterim tercihi yalnız bir boolean içeren ui-preferences.json dosyasında kalır;
ayarlar/hasta kayıtlarından ayrıdır. Paket testleri ilk kullanım turunu açmaz.

124 yerel test başarılı: önceki 115 regresyona ek olarak hareketli bekleme,
geçen süre/aşama, tekrar başlatmanın engellenmesi, başarı/hata/inceleme ayrımı,
gerçek indirme baytları ve hash engeli, tur atlama/hatırlama/yeniden açma ve
taslak/kayıt güvenliği test edildi. Klinik motor ve üç adımlı normal akış korunur.
Miamed'e doğrudan yazma etkin değildir. Gerçek cihaz/yüksek DPI görsel kabulü
ayrıca doğrulanmalıdır.
