# Anamnez Asistanı V2-alpha1.1

Windows için tek birleşik Tkinter uygulaması. V1'in manuel giriş, etiketli
dikte, CPU/INT8 faster-whisper, JSON/metin kaydı ve beş genel PubMed başlığı
korunur. Ana öncelik tarihli anamnezi Miamed'e yapıştırmaya hazırlamaktır.
**Klinik Asistan** ve **Ayarlar** aynı uygulamadadır. Ayrı V1 ürünü yoktur.
Mevcut VBS başlatıcıları ve `anamnez_asistani.py` aynı V2 uygulamasını açar.

## Ana akış: anamnez → tarihli pano → Miamed

Yeni görüşme boş açılır. Ana sekmede normal dikte akışı **üç tıklamadır**:

1. **Dikteyi başlat.** Hazırlık bitip kayıt durumu göründüğünde konuşun.
2. **Dikteyi bitir.** Kayıt sessizlikten dolayı bitmez. Transkripsiyon, yerel
   yazım kontrolü ve taslak hazırlama otomatik yapılır; ayrı sekme/aktarma/kabul
   tıklaması gerekmez. Son metni okuyup gerekiyorsa aynı alanda düzenleyin.
3. **Onayla ve aktar (şimdilik panoya).** Tam metin hazır olduğunda düğme açılır;
   onay anında tarih/saat eklenir, önizlemenin aynısı panoya yazılıp geri okunur.

**Doğrudan Miamed bağlantısı henüz etkin değildir.** Mevcut sürümde hekim
Miamed'in doğru hasta/başvuru ekranında anamnezin en altına `Ctrl+V` ile yapıştırır.
Bu ek işlem nedeniyle hastane kaydı dahil uçtan uca üç tıklama hedefi henüz
tamamlanmış sayılmaz. İki baştaki satır sonu önceki kaydı koruyarak ayırır.
Miamed teknik JSON raporu geldikten sonra doğrudan aktarım ayrıca doğrulanacaktır.

Miamed'e uygulama tarafından otomatik giriş/yazma yapılmaz; yer ve hasta seçimi
hekimdedir. Gerçek Miamed ekranında kabul testi henüz yapılmadı. Ayrıntılar:
[V2-alpha1.1 sürüm ve kabul raporu](docs/ALPHA1_1.md).

Hastanedeki Windows Miamed ekranının salt okunur teknik ön incelemesi için
[Miamed Ekran Kontrolü](tools/screencheck/README.md) pilot aracı eklendi.
Hasta içeriğini raporlamaz ve hiçbir alana yazmaz; otomatik aktarım adapter'ı değildir.

**Yeniden kopyala** aynı onaylı metni aynı tarih/saatle kopyalar. Metin, dikte
veya alanlar değişince onay kalkar; uygulamanın eski pano metni hâlâ panodaysa
temizlenir. Dikte/alan değişikliğinde taslağı yeniden hazırlamak gerekir.
Kopyalama başarısızsa tamamlandı mesajı gösterilmez, aynı onaylı metinle tekrar
denenebilir. Kayıt/transkripsiyon bitmeden tamamlama yapılamaz. PubMed veya
LLM çalışırken manuel hazırlama/onay/kopyalama kullanılabilir.

**Yeni görüşme** hasta alanlarını, dikteyi, taslağı, AI sonuçlarını ve uygulamanın
panodaki önceki kopyasını temizler; diskteki kayıtları silmez. Pano temizlenemezse
geçiş durur. Başka uygulamanın sonradan koyduğu pano içeriğine dokunulmaz.
Windows pano geçmişi ve sistemin cihazlar arası pano eşitlemesi uygulama
tarafından yönetilmez. Windows'ta standart Unicode pano içeriği uygulama kapansa
da sistemde kalır; yeni hasta öncesi **Yeni görüşme** kullanılmalıdır.

**Üretim modu:** metin/JSON kaydı yalnızca güncel hekim onayından sonra yapılır.
`_note_draft` yalnızca son onaylı metin/tarih bilgisini taşır; ham transkript ve
eski `dictation_applied` metni yazılmaz. Onayda geçici dikte, kaynak snapshot'ı
ve editör undo geçmişi bırakılır. Bu, işletim sistemi belleği/pagefile üzerinde
adli düzeyde sıfırlama garantisi değildir. Eski dosyaların ham uzantıları üretim
modunda geri yüklenmez; orijinal dosyalar otomatik değiştirilmez/silinmez.

**Test modu:** Ayarlar'dan açıkça etkinleştirilir; ana ekranda belirgin uyarı
görünür. Sentetik/izinli veride ham-düzeltilmiş eşler kalite testi için JSON'a
yazılabilir. Gerçek kullanımda kapalı tutun. Yüklenen kayıt her modda yeniden
incelenip onaylanır; otomatik kopyalanmaz. Boş başlıklar/`...` çıktıya girmez.

## Hafif yerel yazım kontrolü

Varsayılan olarak gözden geçirilmiş küçük yazım sözlüğü kullanılır. Örneğin
`hiper tansiyon` → `hipertansiyon`. GGUF ayarlıysa yerel model, bu sözlüğün
metindeki aday düzeltmelerinden uygun olanları otomatik seçer. Kaynak konumu ve
kelime eşleşmesi doğrulanır; modelin serbest yeniden yazımı kabul edilmez.
İlaç isimleri tahmin edilmez; doz/sayı/birim/negasyon değiştiren öneriler reddedilir.
Sözlük dışı kelimeleri kapsayan genel bir Türkçe/tıbbi düzeltme başarısı iddia
edilmez. Hekim son metni inceler. Model yoksa veya hata verirse güvenli sözlükle
akış devam eder; ek onay penceresi açılmaz. Ayarlar'dan yazım kontrolü kapatılabilir.

## Kurulum

Hedef Windows 10/11 x86-64, dört çekirdek ve 8 GB RAM; önerilen 16 GB RAM.
GPU/CUDA gerekmez. Gerçek 8 GB donanım performansı henüz ölçülmedi; RAM ihtiyacı
model ve bağlam boyutuna bağlıdır. Python 3.10+ ve Tkinter gerekir.
Windows paket uyumluluğu için Python 3.12 x64 kullanılabilir.

1. Python'u PATH'e ekleyerek kurun.
2. `WhisperKurulum.vbs` ile ses bileşenlerini `.venv` içine kurun.
3. `AnamnezAsistani.vbs` ile açın. Alternatif: `python app.py`.

Manuel işlevler, ses ve LLM paketleri kurulmadan da açılır. Yerel LLM için
uygulama klasöründe isteğe bağlı CPU backend'ini kurun:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-llm.txt --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

Wheel bulunamazsa kaynak derlemesi C/C++ derleyicisi gerektirebilir.
[Resmî llama-cpp-python belgeleri](https://llama-cpp-python.readthedocs.io/en/latest/)
CPU wheel ve Windows derleme seçeneklerini açıklar.

Türkçe instruction/chat ve JSON çıktısını destekleyen, lisansı kullanımınıza
uygun bir GGUF dosyasını temin edin. **Ayarlar** sekmesinde dosyayı seçip kaydedin.
Model adı sabit değildir; otomatik GGUF indirmesi yoktur. `llama_cpp.Llama`
yerel olarak `n_gpu_layers=0` ile çalışır. BitNet adapter'ı henüz eklenmedi;
değiştirilebilir backend interface'i hazırdır.

Bağımsız yerel model kontrolü:

```powershell
.venv\Scripts\python.exe -m ai.test_model --model "C:\modeller\model.gguf"
```

## Kullanım

- **Hasta bilgileri:** mevcut alanları elle düzenleyin.
- **Dikte metni:** `small`, `medium`, `large-v3`, `turbo` seçenekleri korunur.
  Türkçe, CPU INT8, VAD ve 15 dakika sınırı kullanılır. Ses dosyası yazılmaz.
  İlk Whisper model indirmesi internet gerektirir; transkripsiyon yereldir.
- **Dikteyi alanlara aktar:** V1 etiket parser'ı; etiketsiz metin şikâyete eklenir,
  açıkça belirtilmeyen muayene ve diğer alanlar korunur.
- **Klinik Asistan:** dikteden yerel modelle yapılandırılmış anamnez ve 2–5
  literatür sorusu çıkarın. Bilgileri gözden geçirin. **Onaylanan anamnezi
  alanlara aktar** yalnızca dolu şikâyet/özgeçmiş/ilaç bilgilerini aktarır.
  Yaş/cinsiyet/laboratuvar ayrıntıları yapılandırılmış görünümde ve kayıt
  sırasında `_v2` JSON uzantısında tutulur. Eksik alanlar değiştirilmez.
- Soruyu seçin, soru ve İngilizce kavramları düzenleyin, **PubMed’de Ara**'ya
  basın. PICO yalnızca uygun sorularda önerilir. Tek soru seçilir; birden fazla
  soru ayrı aramalarla araştırılır. Otomatik araştırma başlatılmaz.
- Önce 30 aday (ayarlanabilir 20–50), sonra alaka/tür/güncellik sıralaması,
  ardından en fazla 5 yayınla sentez yapılır. Top-k değerleri ayarlanabilir.
- **5 değerlendirme önerisi:** V1 genel başlıkları/sabit sorgularıdır; bunlar
  hastaya özel AI değerlendirmesi değildir.
- **Anamnez • Miamed:** düzenleme, tarihli otomatik pano, metin/JSON kaydı ve V1 JSON yüklemesi.
- **Ayarlar:** GGUF yolu, thread/bağlam/çıktı boyutları, Whisper modeli, düşük
  RAM, retmax/top-k, timeout/retry/cache, yazım kontrolü ve açık test modu seçenekleri.

## Mahremiyet ve kaynaklar

Ses, dikte, anamnez ve model istemleri yerel kalır; bulut LLM yoktur. PubMed'e
yalnızca `safety/privacy.py` içindeki gözden geçirilmiş İngilizce klinik
sözlükten türetilen sorgu ve sayısal PMID'ler gönderilir. İsim, TC, telefon,
adres, dosya numarası veya serbest hasta metni kabul edilmez. Bilinmeyen doğru
klinik kavramlar da engellenebilir; sözlük genişletmesi geliştirici incelemesi
gerektirir. İlk alpha yalnızca kontrollü `Title/Abstract` sorguları üretir;
MeSH/sinonim/tarih/tür filtrelerini otomatik genişletmez.

PubMed istemcisi timeout, sınırlı retry/backoff ve istek aralığı kullanır.
Önbellek yalnızca güvenli sorgu ve yayınları süreli/sınırlı olarak bellekte tutar.
V1 Google Scholar bağlantıları yalnızca sabit genel klinik sorguları içerir.

Sentez yalnızca getirilen, abstractı bulunan ve bağlama sığan yayınları kullanır.
Yeterli abstract yoksa yayın listesi ve açıklama gösterilir. Her iddianın PMID'si
ve varsa DOI'si senteze verilen retrieval kümesiyle doğrulanır. Geçersiz kaynak
tüm sentezi engeller. Başlık/dergi/yıl ve tıklanabilir PubMed bağlantıları
modelden değil gerçek PubMed metadata'sından alınır. Bu kontrol iddianın yayın
tarafından bilimsel olarak desteklendiğini kanıtlamaz; hekim kaynağı incelemelidir.

Hasta verileri yalnızca kaydetmeyi seçtiğiniz dosyalara yazılır; şifrelenmez.
Kayıt konumunun erişim ve yedeklemesini kurum politikanıza göre yönetin.
Ayarlar `%LOCALAPPDATA%\AnamnezAsistani\settings.json` içindedir; hasta verisi
içermez. Varsayılan logging hasta içeriği, exception metni veya istek gövdesi
yazmaz. Hasta içeriği debug logu eklenmemiştir.

## Bellek, hatalar ve test

Tek ağır worker çalışır. Tk widget'ları yalnızca ana thread'den kuyruk üzerinden
güncellenir. Düşük RAM modunda Whisper/LLM sırayla yüklenir ve işlem sonunda
bırakılır. Hızlı modda modeller yeniden kullanılabilir, RAM tüketimi artabilir.
Kapanışta mikrofon durdurulur ve geç callback'ler atılır. Native inference
için işlem ortası iptal düğmesi yoktur. Eksik model/mikrofon, hatalı JSON,
timeout, boş PubMed ve geçersiz kaynaklar kullanıcı mesajlarıyla ele alınır.

```powershell
python -m unittest discover -s tests -v
python -m compileall -q ai literature safety speech storage ui app.py settings.py
python -m benchmarks.run_benchmark --model "C:\modeller\model.gguf" --output benchmark-results.json
```

Unit testler sentetik veri ve model test double'ları kullanır. Gerçek Tk testleri
gizli pencereler açar; ekran yoksa atlanır. CI: Windows ve Linux/Xvfb, Python
3.10/3.12. Yerel son kontrol: 71 test geçti; gerçek Windows panosu, kayıt altına ekleme,
üç düğme komutuyla worker akışı ve üretimde ham metin yazılmaması dahil.

Benchmark gerçek modelle alan bazlı exact-match, soru şema geçerliliği, güvenli
sorgu oranı, citation membership, süre, process peak RAM ve çıktı tokenı ölçer.
Retrieval fixture'ı açıkça sentetiktir; gerçek yayın değildir. Soru ve sorgunun
klinik kalitesi için hekim değerlendirmesi gerekir; şema puanı kalite puanı
değildir. Eksik model başarı sayılmaz, çıkış kodu 1 döner.

## Geçiş ve sınırlar

Eski kod ve kullanıcı kayıtları veri kaybına yol açacak biçimde silinmez. V1 düz
JSON'ları okunur; bilinmeyen uzantılar korunur. JSON yazımı atomik replace kullanır.
Geri dönüş etiketi, bağımsız yedek, mimari, faz sonuçları ve açık kabul kapıları
[geçiş raporundadır](docs/V2_MIGRATION.md).

Bu bir **V2-alpha** uygulamasıdır. Gerçek GGUF çıkarım kalitesi, mikrofon/Whisper
regresyonu ve 8 GB RAM performansı henüz doğrulanmamıştır. Şema kontrolü eksik
bilgi uydurulmasını tamamen önleyemez; her çıkarım hekimce gözden geçirilmelidir.
Yeni görüşme boş başlar. Eski JSON dosyalarından yüklenen örnek/şablon metinler
hekim tarafından kontrol edilmelidir. Sistem kesin tanı, reçete, doz veya
hekim onaysız klinik karar üretmek için değildir.
