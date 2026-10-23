# V2-alpha1.2 — Windows kurulumu ve imzalı güncelleme

## Kapsam

Alpha1.1'in üç tıklamalı dikte, sınırlı yerel düzeltme ve onaylı kayıt
politikası aynı birleşik üründe korunur. Alpha1.2, bağımsız Python kurulumu
gerektirmeyen Windows x64 paketini ve uygulama içinden güncellemeyi ekler.
Miamed'e doğrudan yazma bu sürüme dahil değildir; teknik JSON raporu beklenir.

## Güncelleme güven sınırı

Uygulama açılışta yalnızca mustafactf-bit/anamnez GitHub yayın listesini
kontrol eder. Henüz geliştirme aşaması olduğundan alpha yayınları da kanaldadır.
Listeleme ilk 20 yayına bakar. Sürümler sayısal karşılaştırılır; eski sürüm
otomatik önerilmez. Kontrol/indirme istekleri hasta metni içermez.

Yayıncı tarafından dışarıda saklanan Ed25519 özel anahtarıyla imzalanmış
`update.json` ve ham 64 bayt `update.sig` kullanılır. Sabit açık anahtar EXE'dedir.
Manifest yalnızca sürüm, bu deponun sürüm varlığı URL'si, SHA-256 ve boyut içerir.
İmza ve alanlar doğrulanmadan indirme seçeneği oluşmaz. İndirme `.partial`
dosyasına akar; boyut ve özet tutmazsa tamamlanmış dosya oluşturulmaz. Kurulum
başlatılmadan hemen önce özet yeniden okunur. Ağ hatası uygulamayı kapatmaz.

Bu, Windows yayıncı sertifikası değildir; Authenticode imzası yoktur.
Özel anahtar kaybolursa mevcut kurulumların güveneceği güncellemeler imzalanamaz;
anahtar devri güvenilir bir mevcut sürüm güncellemesiyle planlanmalıdır.
Özel anahtar kaynak koduna, EXE'ye, kuruluma veya GitHub varlıklarına konmaz.
Yeni yayın için imza adımı zorunludur; yalnızca EXE yüklemek güncelleme kanalını
tamamlamaz. Henüz CI içine özel anahtar/secrets tanımlanmadı; imza yerelde atılır.

## Kurulum ve geri dönüş

Inno Setup kullanıcı hesabına, yönetici istemeden kurar. Her sürüm ayrı
`versions/<version>` dizinine yerleşir. Önceki sürüm dosyaları güncellemede
silinmez; önceki sürümün Başlat menüsü kısayolu oluşturulur. Kurulum açık
uygulamaları zorla kapatmaz. Kullanıcı güncelleme başlatmadan önce mevcut
görüşmeden ayrılmayı onaylar. Başarısız kurulum eski sürüm dosyalarını üzerine
yazmaz. Otomatik çökme tespiti veya tam işletim sistemi işlemsel rollback yoktur.

Ayarlar `%LOCALAPPDATA%/AnamnezAsistani/settings.json` konumunda, model
önbellekleri kullanıcı profilinde; GGUF dosyası hekimin seçtiği yerdedir.
Hasta dosyaları kaydet iletişim kutusunda seçilen konumda kalır. Kurulum
betiğinde bu veri konumlarına silme/yazma kuralı yoktur. Önceki VBS/Python
kurulumlarından kullanıcı dosyaları otomatik taşınmaz/silinmez.

## Üretim

Windows Python 3.12 üzerinde izole ortam oluşturun. `requirements-windows.lock`
tam bağımlılık sürümlerini kaydeder; llama-cpp-python CPU wheel kaynağı
`https://abetlen.github.io/llama-cpp-python/whl/cpu` adresidir.

```powershell
python -m venv .venv-build
.venv-build/Scripts/python.exe -m pip install -r requirements-windows.lock --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --only-binary=llama-cpp-python
./tools/package/build.ps1 -Compiler 'C:/Program Files (x86)/Inno Setup 6/ISCC.exe'
.venv-build/Scripts/python.exe tools/package/sign_release.py --key <harici-ozel-anahtar.pem> --installer dist/Anamnez-Asistani-Kurulum.exe --version 2.0.0-alpha.1.2
```

PyInstaller onedir paketini Inno Setup tek indirilebilir kurulum EXE'sine
dönüştürür. Tek başına onedir içindeki EXE'yi başka klasöre kopyalamayın;
`_internal` yan dosyaları gerekir. Kurulum bunları yerleştirir. Whisper/GGUF
ağırlıkları pakette yoktur. Paket içinde motorlar vardır; gerçek Türkçe model
doğruluğu/hızı için ayrıca donanım kabul testi gerekir.

## Doğrulama

82 birim/arayüz testi: önceki 71 regresyon ve 11 güncelleme testi. İmza değiştirme,
güvensiz URL, sürüm sırası, ağ hatası, bozuk/yarım/aşırı büyük indirme, çalıştırma
öncesi dosya değişimi ve zorla/sessiz kurulum yapılmaması kapsanır.

Paket smoke testi gerçek EXE'den Tk, faster-whisper/CTranslate2, ONNX VAD,
sounddevice ve llama.cpp yükler; mikrofon kaydı/model çıkarımı yapmaz.
CI'deki sentetik kurulum testi aynı binary ile eski/yeni dizin düzenini
oluşturur, yükseltir, iki sürümü açar, önceki sürüm kısayolunu ve kaldırma
sonrası sentetik kullanıcı dosyasının korunmasını sınar. Bu eski bir yayınla
gerçek sürümler arası model/ayar uyumluluğu kanıtı değildir.

Geri dönüş noktası: `backup/before-alpha1-2-20261021` etiketi ve bağımsız bundle.
Ana dal otomatik değiştirilmez. Gerçek hastane/Miamed testi açık.

Resmi paketleme belgeleri:
[PyInstaller](https://www.pyinstaller.org/en/stable/operating-mode.html),
[Inno kullanıcı kurulumu](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm),
[uygulama kapatma davranışı](https://jrsoftware.org/ishelp/topic_setup_closeapplications.htm).
