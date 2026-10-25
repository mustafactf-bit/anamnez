MİAMED EKRAN KONTROLÜ v1.1 — TEKNİK PİLOT

Teknik geçmiş gerektirmez. Windows 10/11 + .NET Framework 4.x gerektirir.
ÖNEMLİ: Bu paket kaynak koddan Windows üzerinde ilk açılışta EXE üretir;
Windows derlemesi ve hasta içermeyen sentetik WinForms/UIA kabul testi doğrulandı. Gerçek Miamed ve SMTP teslimi henüz doğrulanmadı.
BASLAT.cmd dosyasına çift tıklayın. İlk çalıştırmada kaynak kodu Windows'un
.NET Framework C# derleyicisiyle EXE'ye dönüştürülür; sonraki açılışlar doğrudandır.
İşlem kurum politikaları nedeniyle engellenirse Windows güvenliğini atlatmaya
çalışmayın, bilgi işlem birimine başvurun. Bu paket henüz sertifikalı/imzalı değildir.

KULLANIM
1. Kurumun İZİN VERDİĞİ TEST ORTAMINDA Miamed'i açın; gerçek hasta kullanmayın.
2. Programdan "E-posta ayarları"na basın. Gmail adresinizi girin. Google'ın
   myaccount.google.com/apppasswords sayfasından aldığınız 16 karakterlik UYGULAMA
   ŞİFRESİNİ yazın (Gmail ana hesabınızın parolasını ASLA girmeyin).
   Kurum teknik metaveri gönderimine izin verdiyse ilgili onay kutusunu işaretleyin.
   Bu ayar yalnızca aynı Windows hesabında DPAPI ile şifrelenmiş tutulur.
   Google hesabında iki adımlı doğrulama gerekebilir ve kimi hesaplarda uygulama
   şifreleri kullanılamaz. Gmail SMTP çıkışı ağ politikasına bağlıdır.
3. Miamed'de Anamnez sekmesini ELLE açın, araçtan Anamnez'i seçin ve
   "Rapor al ve otomatik e-postala" düğmesine basın. Şikâyet, Özgeçmiş, Soygeçmiş
   için de ekranı değiştirip aynı adımı tekrarlayabilirsiniz.
4. Kayıtlar Belgeler\Miamed-Teknik-Raporlar klasörüne otomatik kaydedilir.
   Gmail ayarlanmışsa ve ağ izin veriyorsa JSON ek olarak aynı Gmail hesabına
   otomatik gönderilir. Başarı ya da başarısızlık uygulamada açıkça bildirilir.
   E-posta başarısız olsa da yerel dosya korunur. Bir işlem tamamlanmadan yeni
   tarama başlatılmaz. İlgili alanı doğru seçtiğinizi ekrandan kontrol edin.

GİZLİLİK
- Miamed'e YAZMAZ, odağı değiştirmez, tıklama veya tuş basma otomasyonu yapmaz.
- Ham kontrol isimlerini, hasta kimliklerini, alan metnini, AutomationId,
  pencere başlıklarını, şifreleri veya ekran görüntülerini kaydetmez/göndermez.
- Yalnız UI Automation metadata: kontrol türü, sınırlı sabit etiket ipuçları,
  ağaç, pattern desteği, görünürlük, salt-okunur/odaklanabilirlik ve zaman bilgisi.
- E-posta ayarları rapora veya GitHub'a dahil DEĞİLDİR. Gmail SMTP port 587
  üzerinden TLS ile gönderilir. Gmail/kurum güvenlik şartları geçerlidir.
- Hassas bilgi bulunmadığını varsaymayın: arayüz metadatası da kurumun iç
  sistem mimarisine ilişkin olabilir. İzin yoksa e-posta ayarlarını yapmayın.
- Kod daha fazla kontrolü tarar ama değişebilen indeksleri Miamed'in sabit
  alan kimlikleri zannetmeyin. Bu bir entegrasyon kabul testi değildir.

SINIRLAR
- Kurum/PC izinleri, UIA erişimi, SMTP bağlantısı ve Gmail uygulama şifresi
  farklı koşullar gerektirir. Gerçek Miamed ortamında ve Gmail tesliminde henüz test edilmedi.
- Derinlik sınırı 28, öğe sınırı 3500, iç tarama sınırı 20 saniye.
  Partial status varsa sonuç bunu açıkça bildirir.
- Test/araştırma yazılımıdır; doğru hasta/başvuru eşleştirmesi, not ekleme,
  otomatik hasta kaydı veya Miamed bağlantısı sağlamaz.

SON KONTROLLER
Windows_Test.ps1 gerçek Miamed yerine örnek bir Windows penceresi oluşturup gizlilik, UIA düğümleri ve kaynak verinin korunmasını sınar. Gerçek hasta bilgisi veya e-posta göndermez. Paketteki build.ps1 Windows derlemesini ayrı çalıştırır.

GitHub: v1.1 kaynakları codex/miamed-screencheck-v1-1-20261024 geliştirme dalında, tools/screencheck/v1.1 klasöründe tutulur. Ana dal değiştirilmemiştir; bu yalnızca teknik pilot sürümdür.

NOT: Bölüm seçimi rapora etiket koyar; teknik tarama o an açık Miamed penceresinin TAMAMINI inceler. Seçilen sekmeye özel bir API erişimi doğrulanmış değildir. Öncelikle kurumun uygun test ekranını açın.
E-POSTA DURDURMA: Araç içindeki 'E-postayı kapat' düğmesi DPAPI ile tutulan Gmail uygulama şifresi kaydını siler, rapor dosyalarını silmez.

GITHUB'A YUKLEME (KİŞİSEL PC)
GITHUBA_YUKLE.cmd: Bilgisayarinizda Git for Windows kuruluysa, komutla ayrı `codex/miamed-screencheck-v1-1-20261024` geliştirme dalı açıp dosyaları oraya gönderir. GitHub oturum izni sorabilir. main dalını değiştirmez. Yetki veya kimlik doğrulama hatasında kod yüklenmiş sayılmaz. Bunu hastane bilgisayarında çalıştırmayın. GitHub Actions iş akışı yeni dalda Windows üzerinde derleme ve sentetik kabul testini yapar; başarılı olursa imzasız EXE artifact'i üretilir.
