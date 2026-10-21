# V2-alpha geçiş raporu — 21 Ekim 2026

## Başlangıç incelemesi ve geri dönüş

`mustafactf-bit/anamnez`, başlangıç SHA:
`35e8c66af748fcf08a44871f9a9eed1347e1f22e`.
Python kaynağı, README, requirements, LICENSE, iki VBS başlatıcı ve yüklenen
`Yapıştırılan metin.txt` şartnamesinin tamamı incelendi. Grafik araçları oturumda
sunulmadığı için kaynak dosyaları okundu. Başlangıç tek dosyalı dört sekmeli
Tk uygulamasıydı; kalıcı ayar veya LLM katmanı yoktu.

İlk kod değişikliğinden önce `backup/v1-before-v2-20261021` etiketi ve depo
dışında `anamnez-v1-backup.bundle` oluşturuldu. Değişiklik dalı:
`codex/unified-v2-alpha`. `main` üzerinde çalışılmadı; kullanıcı kayıtları
aranmadı, taşınmadı, silinmedi. Depoda hasta kayıt dosyası bulunmuyordu.

Yedeği ayrı klasörde açma:

```powershell
git clone anamnez-v1-backup.bundle anamnez-recovery
git -C anamnez-recovery switch --detach backup/v1-before-v2-20261021
```

## Mimari ve riskler

V1 alanları/parser/not çıktısı `config.py` ve `clinical_notes.py` içinde;
GUI `ui/`, ses `speech/`, yerel model ve klinik servisler `ai/`, PubMed ve
sıralama `literature/`, mahremiyet/şema/kaynak kontrolü `safety/`, JSON
`storage/` içindedir. Kalıcı ayarlar hasta dosyalarından ayrıdır.
Mevcut VBS ve `anamnez_asistani.py` aynı birleşik V2'yi açar.

Öncelikli riskler: etiket parser regresyonu, kayıt şeması kaybı, worker'dan
Tk erişimi, pencere kapanış yarışları, aynı anda iki modelin RAM tüketimi,
malformed JSON, kişisel veri sızıntısı ve sahte kaynak. Testler bunları
hedefler; modelin bilimsel doğruluğu test double ile kanıtlanamaz.

## Fazlar ve kontroller

| Faz | Değişiklik / neden | Kontrol |
| --- | --- | --- |
| 1 | GUI/not/storage/genel PubMed ayrıldı, mevcut launcher korundu | 4 V1 uyumluluk testi ve derleme geçti |
| 2 | Protocol + lazy GGUF CPU adapter + test CLI | Eksik model, lifecycle ve JSON sözleşmesi geçti |
| 3 | Türkçe dikte için sıkı anamnez şeması | Sentetik model sözleşmesi ve geçersiz türler geçti |
| 4 | 2–5 soru, isteğe bağlı PICO ve kavramlar | Şema ve soru sayısı geçti |
| 5 | Query builder, esearch/esummary/efetch, privacy boundary | İsim/telefon/TC, XML/JSON, timeout/retry ve boş sonuç testleri geçti |
| 6 | Alaka öncelikli deterministik sıralama | İlgili eski yayın, alakasız yeni guideline'ın önünde |
| 7 | Seçilen abstractlarla sınırlı sentez | Abstract yokluğu ve uydurma kaynak reddi geçti |
| 8 | Zorunlu PMID/DOI retrieval üyeliği | Geçersiz kaynak tüm sentezi engelliyor |
| 9 | Klinik/Ayarlar sekmeleri, seçme/düzenleme ve onaylı aktarım | Gizli gerçek Tk pencereleriyle doğrulandı |
| 10 | Queue bridge, tek worker, model lifecycle ve bounded cache | Ana-thread callback, kapanış ve tek-worker testleri geçti |
| 11 | Sentetik benchmark, CI matrisi ve belgeler | Yerelde 27 test geçti; eksik model benchmark'ı başarısız döndü |

İlk test çağrısı yanlış çalışma dizininden import hatası verdi; repo kökünden
düzeltildi. Tk testinde worker'daki genel `gc.collect()` eski Tk nesnelerini
yanlış thread'de temizliyordu; bu çağrı kaldırıldı. Model referansları unload
ile bırakılır. Düzeltmelerden sonra 27 test geçti.

## Doğrulananlar ve doğrulanmayanlar

Windows/Python 3.14.7 üzerinde unit testler ve gerçek Tk açılması doğrulandı.
21 Ekim 2026'da yalnızca `hypertension` + `hypokalemia` klinik kavramlarıyla
gerçek PubMed esearch/efetch denendi: istenen 30 adaydan 29 Article ayrıştırıldı.
Bazı abstract/DOI alanlarının eksik olması ele alındı. Hasta verisi kullanılmadı.

Gerçek GGUF dosyası sağlanmadı. Model kurulumu, gerçek inference kalitesi,
Whisper mikrofon regresyonu ve 8 GB cihaz performansı doğrulanmadı. Mock parser
testi gerçek Türkçe dil anlama başarısı sayılmaz. CI tanımı eklenmesi CI'ın
geçtiği anlamına gelmez; uzaktaki durum ayrıca kontrol edilmelidir.

## Alpha sınırı ve sonraki kabul kapıları

Sorgular küçük, gözden geçirilmiş klinik sözlükten `Title/Abstract` ile üretilir.
Otomatik MeSH/sinonim/tarih/tür genişletmesi henüz yoktur. Bilinmeyen doğru
terimler de güvenlik gereği engellenir. Soru seçimi tek soruluktur. BitNet
adapter'ı ve ağır reranker eklenmedi; değiştirilebilir interface bırakıldı.

Kaynak kontrolü yayın üyeliğini kanıtlar; iddianın abstract tarafından gerçekten
desteklendiğini kanıtlamaz. Şema kontrolü hallucination'ı tamamen önleyemez.
Kesin tanı/tedavi diline karşı prompt ve sınırlı dil kontrolü var; klinik doğruluk
ve dil güvenliği için hekim değerlendirmesi gerekir.

Klinik ürün kabulü öncesi lisansı uygun gerçek GGUF ile benchmark, hekimce
negasyon/eksik bilgi/iddia desteği kontrolü, mikrofon testi, 8 GB CPU cihazında
RAM/süre ve temiz Windows kurulum testi gereklidir. Ana dala otomatik birleştirme
yapılmaz. V2 ek alanları eski V1 ile yeniden kaydedilirse V1 bunları atabilir;
orijinal JSON yedeklerini ayrı tutun. V2 kendi yükle/kaydet döngüsünde bilinmeyen
ek alanları korur.
