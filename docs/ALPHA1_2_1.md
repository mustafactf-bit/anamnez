# V2 Alpha 1.2.1 — Whisper indirme ilerlemesi

Small, medium, large-v3 ve turbo ilk kez indirilirken sol altta yeşil bir
çubuk ve yüzde gösterilir. Payda sabit model dosyalarının metadata boyutlarıdır;
ilerleme Hugging Face snapshot indirmesinin bayt/reconstruction olaylarından
alınır. Zamanlayıcıyla sahte ilerleme üretilmez. Birden çok dosya ve önbellekte
tam bulunan dosyalar toplam hesaba dahil edilir. Kısmi dosyanın devam eden
indirmesi indirme motorunun başlangıç/bayt ilerlemesinden alınır.

Metadata alınırken yüzde gösterilmez. İndirme başarılı dönene kadar yüzde
en fazla 99'dur; tamamlandığında 100 ve ardından ayrı “model hazırlanıyor” /
“hazır” bilgisi gelir. İndirme/yükleme hatası açıkça görünür; başarısız dosya
indirmesi tamamlandı sayılmaz. Tam önbellek dosyaları varsa çevrimdışı yol
kullanılır ve indirme yüzdesi gösterilmez. Başka model seçilince gösterge sıfırlanır.

İlerleme olayları worker kuyruğundan Tk ana iş parçacığına taşınır; model
indirme kodu arayüze doğrudan dokunmaz. Olaylar sınırlanır; çok sayıdaki bayt
olayı arayüz kuyruğunu doldurmaz. Yeşil Canvas çubuğu Windows temasının renk
ayarını yok sayma sorununu önler. Global tqdm/Hub davranışı değiştirilmez.

GGUF modeli hâlâ hekim tarafından dosyadan seçilir; uygulamada GGUF indirme
işlemi olmadığı için ona sahte bir indirme göstergesi eklenmez. Dikte,
hekim onayı, kayıt/veri koruma ve Miamed sınırları önceki sürümle aynıdır.

## Sürüm kimliği ve mevcut kurulumlarla uyumluluk

Kullanıcıya görünen sürüm **V2-alpha1.2.1**'dir. Makine kimliği ve GitHub
etiketi **2.0.1-alpha.1.2 / v2.0.1-alpha.1.2** kullanır. Alpha1.2'deki
güncelleme okuyucusu alpha sonrasında iki sayısal parça beklediğinden,
`2.0.0-alpha.1.2.1` biçimini atlar. SemVer patch artırımı mevcut kurulumların
bu gerçek güncellemeyi bulmasını sağlar; yeni kod aynı kimliği kullanarak
kendisine tekrar güncelleme önermez. İmza anahtarı ve AppId korunur.

## Doğrulama

- 93 otomatik test: önceki 82 regresyon ve 11 indirme/arayüz testi.
- Sabit bayt paydası, önbellek ve devam eden byte offset, yüzdelik sınır,
  olay sıklığı, eksik boyut, hata halinde 100 olmaması, yerel model yoluna
  geçiş ve gerçek Tk'de yeşil renk/sol konum/yüzde doğrulaması.
- Gerçek Hugging Face small deposundan config/tokenizer dosyaları indirildi;
  callback ve ikinci çağrıda önbellek yolu doğrulandı. Bu deneme tüm model
  ağırlıklarını indirme veya klinik transkripsiyon kalitesi ölçümü değildir.
- Windows paketi yerel motorları EXE'den yükler; sentetik kurulum/yükseltme,
  önceki sürümü açma ve kaldırma sonrası kullanıcı dosyasının korunması CI'da
  sınanır. Gerçek hastane/Miamed kabulü açık.

Geri dönüş: `backup/before-alpha1-2-1-20261021` ve bağımsız git bundle.

İlerleme API'si: [Hugging Face resmi indirme belgeleri](https://huggingface.co/docs/huggingface_hub/en/package_reference/file_download).
