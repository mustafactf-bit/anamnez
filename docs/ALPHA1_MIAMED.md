# V2-alpha1 — Miamed anamnez aktarımı

## Amaç ve sınır

Bu sürümün önceliği, hekimin düzenlediği anamnezi tarih/saatle otomatik panoya
kopyalamak ve Miamed'deki mevcut anamnezin altına elle yapıştırmaya hazırlamaktır.
Uygulama Miamed'in önceki kayıtlarını okumaz, düzenlemez veya silmez. Hekim
doğru hastayı ve ekleme yerini seçer. Gerçek Miamed arayüzüne erişilmedi;
Miamed uçtan uca kabulü tamamlandı iddiası yoktur.

## Davranış

- Yeni görüşmeler boş; V1 örnek hastası, normal muayene ve otomatik
  “hasta bilgilendirildi/poliklinik kontrolü önerildi” ifadeleri kaldırıldı.
- Girilen alanlar ve aktarılmamış ham dikte kayıpsız taslakta korunur;
  hekim metni düzenler. Bu ana iş için LLM veya PubMed gerekmez.
- Hekimin aktardığı yapılandırılmış yaş/cinsiyet/süre/laboratuvar ayrıntıları
  da taslağa alınır. Şema veya model doğruluğu hekim incelemesinin yerine geçmez.
- Onay düğmesi timestamp üretir. İki satır sonu, tarih/saat başlığı ve onaylanan
  gövde eklenir. Önizleme ve pano birebirdir; satır sonu LF/CRLF normalizasyonu
  dışında metin değişmez. Boş anamnez kopyalanamaz.
- Yeniden kopyalama tarihi yenilemez veya ikinci başlık eklemez. Değişiklik
  onayı kaldırır; kaynak değiştiyse taslak yenilenmeden onaylanamaz.
- Windows `CF_UNICODETEXT` native pano kullanılır; ek bağımlılık yoktur.
  Pano yazımı ve geri okuma doğrulanır. Hata başarı sayılmaz, tekrar denenebilir.
- Kayıt/transkripsiyon sürerken onay ve hasta değiştirme engellenir.
  AI/literatür worker'ı ise manuel onay/kopyalamayı engellemez.
- Yeni görüşmede tüm hasta durumu sıfırlanır. Uygulamanın eski pano metni hâlâ
  panodaysa temizlenir. Temizleme hatasında hasta geçişi durdurulur. Başka
  uygulamanın sonradan kopyaladığı içerik silinmez. Disk kayıtları korunur.
- JSON `_note_draft` uzantısıyla düzenlenmiş taslak ve ham dikteyi saklar;
  V1 düz alanlarını ve bilinmeyen ekleri korur. Yükleme onay/pano işlemi yapmaz.
  Güncel olmayan kayıtlı taslak yeniden hazırlanmadan onaylanamaz.

## Kod ve geri dönüş

Başlangıç: `0bcf4671d1dab443d1d84672c79cbb0e6b3a80bb`.
Değişiklik öncesi `backup/v2-alpha-before-alpha1-20261021` etiketi ve bağımsız
`anamnez-before-alpha1.bundle` alındı. Önceki V1 yedeği de korundu.

`note_workflow.py` yalnızca girilen bilgilerle gövde ve tarihli onay üretir.
`ui/note_panel.py` taslak/onay/kaynak değişimi/pano durumunu yönetir.
`ui/clipboard.py` Windows native ve Tk fallback sağlar.
`ui/main_window.py` ana sekme, dosya işlemleri ve görüşme geçişlerini bağlar.
`config.py` boş başlangıç ve sürüm numarasını tanımlar. V1 formatter'ı da artık
varsayılan klinik ifadeler eklemez. Ses, ayarlar, AI ve PubMed korunmuştur.

## Yerel doğrulama

Windows/Python 3.14.7'de 52 test geçti; derleme ve diff kontrolleri temiz.
Gerçek Windows panosu kullanılarak sentetik Türkçe metin yazıldı, geri okundu
ve önceden içerik bulunan gerçek Tk metin alanının sonuna yapıştırıldı. Sonuç:
önceki metin + önizlemedeki tarihli anamnez birebir. Test mevcut metin panosunu
sonunda geri yükler; metin dışı veya erişilemeyen panoda sistem testi atlanır.

Ek testler: boş çıktı, varsayılan bulgu yokluğu, tarih/tekrar kopyalama,
negasyon/Türkçe karakter/ondalık korunması, başarısız pano ve tekrar deneme,
edit sonrası onay iptali, kaynaktan eski kalan taslak, hasta geçişi, kayıt
sırasında engelleme, JSON/metin roundtrip, yinelenen dikte ve PubMed worker'ı
sürerken manuel kopyalama. StringVar değişiklik bildirimi sırasında Entry'nin
henüz güncellenmemiş olabildiği testte bulundu; kaynak karşılaştırması doğrudan
StringVar snapshot'ına taşınarak giderildi.

## Gerçek Miamed kabulü — açık

Kurumun test ortamında veya uygun test kaydında hekim tarafından doğrulanmalı:

1. Anamnez alanında mevcut bir test metni bulunsun.
2. Sentetik dikteyi girin; şikâyet, negasyon, ilaç ve ölçümü kontrol ederek onaylayın.
3. Miamed'de doğru alanın en altına imleci koyun ve Ctrl+V yapıştırın.
4. Eski metnin aynen kaldığını, yeni notun altında doğru tarih/saat, Türkçe
   karakterler, satır düzeni ve eksiksiz içerikle göründüğünü kontrol edin.
5. Miamed kaydını normal iş akışıyla kaydedip yeniden açın; içerik değişmemeli.
6. Alanın karakter sınırı, biçimlendirme veya satır sonu temizliği varsa gerçek
   sonuç kaydedilmeli; kırpılan metin kabul edilmemeli.
7. Yeni görüşmeye geçin; önceki hasta içeriğinin taşınmadığını kontrol edin.

Miamed alan sınırları, uygulamaya özel yapıştırma davranışı ve gerçek kayıt
kalıcılığı bu yerel testlerle doğrulanmış değildir. Gerçek mikrofon/Whisper ve
GGUF kalite/donanım ölçümleri de önceki alpha kabul kapıları olarak açık kalır.
Sürüm kodu alpha1'dir; bu açık kapılar kapanmadan doğrulanmış klinik sürüm
veya Miamed uyum sertifikası anlamına gelmez.
