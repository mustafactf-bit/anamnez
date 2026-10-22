# V2 Alpha1.3 — Yerel anamnez ayıklama ve logo

Sağlanan logo uygulama başlığına, pencere simgesine ve Windows kurulumuna eklendi.
Dikte artık varsayılan olarak yerel GGUF modeliyle hasta bilgilerini anamnez
alanlarına ayırır. Model serbest klinik metin üretmez: yalnızca kaynakta birebir
bulunan alıntılar kabul edilir. İlgisiz sohbet son nota eklenmez. Belirsiz kişi,
soru, eksik kaynak kapsamı veya mevcut manuel alanla çelişki hekim incelemesine
ayrılır; inceleme bitmeden onay ve aktarım açılamaz. Yapılandırma başarısızsa
tüm konuşma son nota sessizce aktarılmaz.

Normal akış başlat, bitir, onayla/kopyala şeklinde üç adımdır. Belirsizliklerde
ek inceleme gerekir. Whisper konuşmacı kimliğini belirlemez; etiketsiz üçüncü
kişilerin tıbbi konuşmalarını kusursuz ayırma garantisi yoktur. Son sorumluluk
hekim kontrolündedir. Miamed'e doğrudan yazma bu sürümde yoktur; tarihli onaylı
metin panoya kopyalanır.

İlk kurulumda ayrı, yaklaşık 1.28 GB Qwen3-1.7B Q4_K_M modeli indirilir.
Model sürümü ve SHA-256 sabitlenmiştir; model kurulumu dışında hasta metni
harici AI servisine gönderilmez. Elle seçilen GGUF ayarı korunur. Model kurulu
değilken kayıt öncesi kurulum sunulur; kurulumdan sonra kayıt kendiliğinden başlamaz.
Üretimde onay sonrasında geçici kaynak ve inceleme ayrıntıları temizlenir.
Ham metin yalnızca açık test modunda kalıcı kayda alınabilir.

V1 manuel giriş, kayıt/yükleme, ayarlar, faster-whisper ve PubMed korunur.
Mevcut elle girilen alanlar otomatik üzerine yazılmaz. AI bilinçli kapatılırsa
önceki dikte akışı görünür uyarıyla kullanılabilir. Kullanıcı kayıtları silinmez.

Gerçek yerel modelle sentetik hasta/öğrenci sohbeti, üçüncü kişi aile bilgisi,
yalnız ilgisiz sohbet ve belirsiz tansiyon örnekleri denendi. Hasta dozu,
olumsuzluk ve tansiyon korundu; belirsizlik incelemeye ayrıldı. Konuşmacı
etiketsiz örnek de geçti. Bu dar doğrulama genel klinik doğruluk ölçümü değildir.
Yerel CPU denemeleri yaklaşık 7–36 saniye sürdü; cihaz performansı değişebilir.
