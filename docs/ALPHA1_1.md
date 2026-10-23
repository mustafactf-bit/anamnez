# V2-alpha1.1 — üç tıklama ve yalnızca onaylı üretim kaydı

## Kullanıcı kararı ve uygulanan davranış

Normal uygulama akışı: **1. Dikteyi başlat → 2. Dikteyi bitir → 3. Onayla ve aktar.**
Konuşma bitişi sessizlikten tahmin edilmez. Kayıt fiziksel düğmeyle durur;
15 dakikalık V1 güvenlik/bellek sınırı korunur ve sınıra ulaşma açıkça belirtilir.
Transkripsiyon/yazım kontrolü/taslak hazırlama otomatik aynı worker işi içindedir.
Hekimin ayrıca düzeltme kabulü, taslak hazırlama veya kopyalama tıklaması yapması
gerekmez. Üçüncü düğme tam metin hazır ve güncel olduğunda açılır.

Mikrofon/model hatası, işlem sırasında hekim düzenlemesi veya klinik belirsizlik
istisna yoludur; aynı anda yapılan düzenleme otomatik üzerine yazılmaz. Bu gibi
durumlarda ilave düzeltme/yeniden deneme gerekebilir; koşulsuz tüm senaryolarda
üç tıklama garantisi verilmez.

## Yerel düzeltme

`ai/dictation_corrector.py`: gözden geçirilmiş küçük bir yazım çiftleri sözlüğü.
Örnekler: hiper tansiyon → hipertansiyon, halsizlk → halsizlik. Sayı, birim,
negasyon ve kimlik satırları korunur. İlaç adı tahmini ve yeni klinik bilgi yoktur.

Model yolu ayarlıysa mevcut CPU GGUF backend'i aday düzeltmelerden seçim yapar.
Yanıt, kaynak konumu/metni ve izinli hedef kelimeyle doğrulanır. Sözlük dışı
değişiklikler reddedilir. Hata/bozuk şemada uygulama çökmez; güvenli sözlük veya
değişmemiş metinle hekim incelemesine devam eder. Model yokken indirme yapılmaz.
Gerçek bir GGUF modeliyle bu düzeltmenin doğruluk/hız ölçümü henüz yapılmamıştır.
Bu ilk sürüm geniş kapsamlı serbest tıbbi dil düzeltmesi değildir.

`speech/dictation_pipeline.py`: kayıt → yerel Whisper → düzeltme. Düşük RAM
modunda Whisper, LLM işleminden önce bırakılır. Düzeltme sonrası LLM prompt/KV
durumunu tutmamak için model unload edilir. Üretim worker sonucu ham metin alanı
taşımaz; yalnızca düzeltilmiş aday, uyarı ve sınırlı istatistik döner.

## Ham veri ve kayıt politikası

- Varsayılan `test_mode=False`. Ham ses dosyası yazılmaz. Üretim JSON'unda
  `transcript`, `dictation_applied` ve `_test_data` uzantıları tutulmaz.
- Onaylı son metin esas kayıttır. Onay/yeni görüşme/kapatma yollarında geçici
  dikte, iş bağlamı ve kaynak referansları bırakılır; onayda undo geçmişi sıfırlanır.
- JSON/metin kaydetme güncel hekim onayı gerektirir. Dosya seçimi sırasında
  metin değişirse yeniden onay olmadan dosya yazılmaz.
- Açık test modunda sentetik/izinli ham ve düzeltilmiş metin çiftleri kalite
  ölçümü için saklanabilir; ana ekranda test modu uyarısı vardır.
- Eski JSON dosyaları okunur; bilinen eski ham uzantılar üretimde yeniden
  saklanmaz. Orijinal dosya otomatik değiştirilmez ve toplu silme yapılmaz.
  Manuel anamnez alanları ve ilgisiz uzantılar korunur; son onaylı metin `_note_draft`
  içinde yetkili metindir. Yükleme hiçbir zaman otomatik onay veya pano yazımı yapmaz.
- Temizleme uygulama düzeyindedir; OS pagefile, bellek dökümü veya Windows pano
  geçmişi için adli sıfırlama garantisi değildir. Loglar hasta metni içermez.

## Doğrulama

Değişiklik öncesi: `7c71f92c7c49478afbe00e4e92222ff7f2a562fd`.
Geri dönüş etiketi: `backup/before-alpha1-1-20261021`. Bağımsız Git bundle alındı.

Windows/Python 3.14.7'de 71 test geçti. Gerçek Tk düğmelerinin üç invoke komutuyla
çalıştırıldığı testte yalnızca mikrofon/Whisper/model sınırları sentetik doubles
ile değiştirildi; gerçek queue/worker/düzeltme/taslak/onay/pano controller'ı çalıştı.
Üçüncü komut sonrası düzeltilmiş tarihli kopya, geçici kaynakların temizlenmesi
ve JSON'da ham metin bulunmaması kontrol edildi. Bu test fiziksel mikrofon
veya gerçek GGUF kalite testinin yerine geçmez.

Ek kontroller: sessizliğin kaydı bitirmemesi, 15 dakika sınırı, sayı/doz/negasyon
ve ilaç değişikliğinin reddi, Türkçe büyük harfler, hatalı model/offset, açık test
modu, eski JSON ham alan temizliği, güncel olmayan onay, eşzamanlı hekim düzenlemesi,
dosya diyaloğu sırasında düzenleme, mikrofon hatası ve yerel model fallback.
Başlangıç 52 regresyon testi de güncel üretim onayı politikasına uyarlanarak geçti.

## Miamed kabul kapısı — açık

Akdeniz Üniversitesi Hastanesi'ndeki gerçek Windows Miamed istemcisi bu ortamda
bulunmuyor. Beklenen dosya **Miamed-Ekran-Kontrol-Raporu.json**, kullanıcı
tarafından 22 Ekim'de yüklenecek. Kontrol aracı değişmedi; salt okunurdur.

Bugün üçüncü düğme yalnızca onaylı metni **panoya** aktarır. Miamed'de Ctrl+V
gerektiği için hastane kaydı dahil uçtan uca üç tıklama hedefi henüz tamamlanmadı.
Gerçek ekran raporu sonrası doğru hasta/başvuru eşleştirmesi, eski metni koruma,
mükerrer aktarımı önleme, geri okuma ve kalıcı kayıt ayrıca doğrulanmalıdır.
Gerçek mikrofon, GGUF çıkarımı ve 8 GB RAM cihaz benchmark'ı açık kabul kapılarıdır.
Sürüm adı bu kapıların geçtiğini veya klinik kullanıma hazır olduğunu iddia etmez.

## Dil ve paketleme

Bu sürümde geniş kapsamlı C# yeniden yazımı yapılmadı. Çalışan Python GUI ve
native CTranslate2/llama.cpp motorları korunarak akış düzeltildi. Windows salt
okunur tanılama yardımcısı C#/.NET'tir. Dil değişimi gerçek süre/RAM ölçümlerine
göre ayrı aşamada değerlendirilecektir. Eski ürün için ayrı arayüz tutulmaz.
