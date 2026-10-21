# V2 Alpha1.2.2 — İlk model indirme ve hata ayrımı

Kullanıcı Alpha1.2.1'de “Dikte başarısız” ve dolu yeşil çubukla model
indirme/yükleme hatası bildirdi. Eski ileti gerçek istisnayı göstermediği için
o denemenin kesin hata nedeni geriye dönük kanıtlanamadı. Kurulu sürümün
özgün modülleri ve native dosyalarıyla ayrı bir tanılama kopyasında mevcut
small önbelleği başarıyla açıldı; sıfır ses transkripsiyonu geçti. Kullanıcının
kurulu EXE'si/model önbelleği değiştirilmedi, gerçek mikrofon kaydı yapılmadı.

Boş önbellekten yapılan ayrı denemede büyük dosya aktarımında bekleme görüldü;
eski Hub HTTP taşıma yığını SSL gövde okumasında bekliyordu. Bu gözlem önceki
ekrandaki hatayla kesin olarak eşitlenmez.

## Değişiklik

- Model dosyaları doğrudan HTTPS üzerinden 4 MiB aralık istekleriyle alınır;
  yüzde 128 KiB okumalarından hesaplanır. Soket bekleme sınırı 20 saniyedir.
- Kısmi dosya `.partial` olarak kalır; sonraki deneme doğru `Content-Range`
  kontrolüyle devam eder. Sunucu Range'i yok sayarsa dosya baştan güvenli yazılır.
- Boyut ve varsa yayıncı LFS SHA-256 özeti tutmadan dosya tamamlandı sayılmaz.
  Bozuk hashli uygulama geçici dosyası bırakılmaz; eski kullanıcı dosyaları silinmez.
- Dosya listesi ve model ağırlığı aynı değişmez Hub commit'ine sabitlenir.
  Yalnızca dosya boyutları ve model dosyaları indirilir; hasta metni gönderilmez.
- Yeni doğrulanan model önbelleği `%LOCALAPPDATA%/AnamnezAsistani/models`
  altında tutulur. Eski tam Hugging Face önbelleği çevrimdışı olarak kullanılmaya
  devam eder. Mevcut model dosyaları taşınmaz veya silinmez.
- İndirme/model açma hatası `MODEL-DOWNLOAD-...` veya `MODEL-LOAD-...`
  koduyla gösterilir. Ham istisna metni normal hekim ekranına taşınmaz.
- Başarısız işlem yeşil dolu çubuk bırakmaz; gösterge sıfırlanır ve hata rengi alır.

## Test sınırı

97 otomatik test: devam/Ranges/bozuk hash, hata kodu ve gizlilik, gerçek Tk
gösterge durumu ve önceki işlevlerin regresyonları. Yerel panoda metin dışı
içerik varsa mevcut pano testi onu değiştirmeden atlanır.

Önceki paket smoke testi modülleri ve VAD dosyasını yüklemekle sınırlıydı;
tam Whisper model yüklemesini sınamıyordu. Yeni `--model-smoke <rapor>` modu
gerçek small modelini yükler ve yapay sessizlik üzerinden transkripsiyon/VAD
yürütür. Bu yol mikrofon açmaz; normal üretim akışında ham hasta verisi kaydetmez.
Tanılama raporu yalnızca bu model testi için model/istisna bilgisi içerir.

Windows CI artık boş önbellekten EXE ile gerçek small modelini indirip açar;
ardından sessiz ses testi yapar. Kurulum/yükseltme/önceki sürüm ve veri koruma
testleri devam eder. Gerçek mikrofon/hastane/Miamed kabulü ayrı kalır.

Ürün adı **V2 Alpha1.2.2**, eski güncelleme okuyucusuyla uyumlu makine sürümü
**2.0.2-alpha.1.2**. AppId ve Ed25519 güncelleme anahtarı değişmedi.
Geri dönüş etiketi: `backup/before-alpha1-2-2-20261022`.
