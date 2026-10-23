# Miamed Ekran Kontrolü — pilot araç

Bu, otomatik anamnez aktarımından önce hastanedeki Windows programının teknik
yapısını incelemek için hazırlanmış **salt okunur** bir araçtır. Python veya
ayrı kurulum gerektirmez; Windows 10/11'de .NET Framework 4.x gerekir.
Normal kullanıcı yetkisiyle çalışır. Dijital imzası olmayan pilot bir uygulamadır;
kurumun çalıştırma kuralları geçerlidir. Engellenirse bilgi işlemle değerlendirin.

## Hastanedeki bilgisayarda kullanım

1. ZIP'i bir klasöre çıkarın.
2. Miamed'i kendi normal oturumunuzda açın. Kurumun uygun test hastası/test
   ekranında anamnez bölümünü gösterin. Oturum şifrenizi paylaşmanız gerekmez.
3. `Miamed-Ekran-Kontrol.exe` dosyasını açın.
4. Listeden Miamed'e ait programı seçin. Listede hasta içerebilecek pencere
   başlıkları yerine program adı ve işlem numarası (PID) görünür. Program adı
   belirsizse bilgi işlemden öğrenin. Birden fazla pencere varsa doğru pencereyi
   tek başına açık bırakmak seçimi kolaylaştırır.
5. **Yapıyı kontrol et** düğmesine basın. Kontrol en fazla yaklaşık 20 saniye sürer.
6. **Raporu kaydet** ile `Miamed-Ekran-Kontrol-Raporu.json` dosyasını kaydedin.
7. Teknik raporu bu sohbete ekleyin. Hasta ekran görüntüsü veya şifre göndermeyin.

## Neye dokunmaz, ne raporlar?

- Miamed'in anamnezini, hasta kaydını, panoyu veya klavyeyi değiştirmez.
- Kaydet, yapıştır, onay veya odak değiştirme işlemi yapmaz.
- Ekran görüntüsü, metin alanı içeriği, hasta kimliği, ham pencere başlığı,
  ham kontrol adı veya AutomationId rapora alınmaz.
- Metin/giriş alanlarının Name/Value/Text içerikleri okunmaz. Diğer arayüz
  etiketleri yalnızca sabit klinik başlık listesiyle bellekte karşılaştırılır;
  eşleşmeyen adlar raporda `other` olur, ham metin saklanmaz.
- Rapor: kontrol türü, ağaç sırası, görünür/etkin durumu, Text/Value desteği ve
  biliniyorsa salt okunur durumu. `read_only: null` destek bilgisi alınamadı
  demektir; alanın yazılabilir olduğu anlamına gelmez.
- Araç ağ bağlantısı kurmaz; raporu yalnızca siz kaydetmeyi seçtiğinizde dışarı
  verirsiniz. İşlem sırasında üretilen metadata geçici dosyası sonunda silinir.

## Sonucu nasıl yorumlarız?

`metadata_only`: sınırlı inceleme tamamlandı. `partial_metadata_only`: bazı
kontroller atlandı veya süre/derinlik/sayı sınırına ulaşıldı. `target_changed`:
seçilen pencere kapanmış/değişmiş olabilir. Kısmi veya boş sonuç, Miamed'in
hiçbir şekilde entegre edilemeyeceğini kanıtlamaz.

Anamnez etiketi veya Text/Value desteği görülmesi, **doğru hasta eşleştirmesi,
otomatik yazma ve kalıcı kayıt uyumluluğunun doğrulandığı anlamına gelmez**.
Raporun ardından Miamed'e özel eşleştirme ve test ortamında aktarım geliştirilir.
Yüksek yetkili, özel çizilmiş veya uzak masaüstü içindeki ekranlar ek inceleme
gerektirebilir. Bu araç erişim engellerini aşmayı denemez.

## Geliştirici doğrulaması

`build.ps1 -OutputPath <tam-exe-yolu>` ve `test.ps1 -HelperPath <tam-exe-yolu>`.
Windows'ta sentetik WinForms ekranıyla kontrol ağacı, sabit etiket eşleştirmesi,
kişisel veri örneklerinin rapora girmemesi, bulunamayan hedef ve kaynak metnin
değişmemesi testleri geçti. Ana anamnez uygulamasının 52 testi de geçti.
Gerçek Akdeniz Miamed ekranı bu bilgisayarda bulunmadığı için henüz denenmedi.

Teknik temel: Microsoft Windows UI Automation.
https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-overview
