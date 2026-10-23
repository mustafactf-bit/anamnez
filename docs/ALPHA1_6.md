# V2 Alpha1.6 — Soru-cevap ayıklaması düzeltmesi

Yerel modelin bir kaynak cümleyi yeniden yazması, önceki sürümde kaynak doğrulamasını
bozup görüşmenin tamamının aktarımını durdurabiliyordu. Model artık yalnız kaynak
numarası, eylem, kişi ve alan seçer. Dört cümlelik gruplar kullanılır. JSON şeması üretim sırasında uygulanır; alan
metni uygulama tarafından orijinal cümleden alınır. Negasyon, süre, sıklık, sayı
ve dozlar bu adımda yeniden yazılmaz. Kaynak kapsamı, tekillik, kişi, alan ve soru
kontrolleri ayrıca uygulanır. Çok parçalı işlem başarısız olursa kısmi sonucu tam
başarı gibi döndürmez; mevcut taslak korunur.

Hasta yanıtları alanlara yerleştirilir. Hekim soruları doğrulanmış bulgu sayılmaz;
belirsiz/yanıtlanmamış ifadeler incelemeye ayrılabilir. Özetleme, tanı üretme veya
konuşmacıları kusursuz ayırma garantisi yoktur; son metni hekim kontrol eder.

Başarısız ayıklama artık alanlara yerleştirildi mesajı göstermez. Yeni bilgi
bulunmaması ve mevcut alanla çelişki ayrı bildirilir. İnceleme beklerken onay
çağrısı kayıt sürüyor şeklinde yanlış açıklanmaz. Güvenli model/şema/yanıt sınırı
hataları kullanıcıya gösterilir; bilinmeyen hata ayrıntıları hasta metniyle birlikte
loglanmaz. Kesilmiş model yanıtı geçerli sonuç olarak kullanılmaz. Başarısız ayıklama
inceleme onaylanmadan Taslağı yeniden hazırla ile tekrar denenebilir.

Verilen soru-cevap örneği cihazdaki Qwen3-1.7B Q4_K_M ile yerelde yeniden denendi:
hastanın dört kaynak cümlesi şikâyet alanına alındı, hekim soruları son nota
alınmadı ve tanı/plan eklenmedi. Kullanıcının metni test dosyalarına veya CI'ya
konulmadı. Kamuya açık testler benzer sentetik bir soru-cevap örneği kullanır.
Gerçek model EXE testi de soru-cevap senaryosunu içerir. Bu dar regresyon kontrolü
genel klinik doğruluk veya hastane cihazında kabul testi değildir.

Alpha1.5 işlem göstergeleri ve ilk açılış turu; logo, V1 manuel alanlar, kayıt/yükleme,
ayarlar, faster-whisper ve PubMed korunur. Üretimde yalnız onaylı son metin kalıcı
kaydedilir. Miamed aktarımı tarihli metni panoya kopyalar; yapıştırma hekimdedir.
Kullanıcı kayıtları silinmez. Geri dönüş etiketi: backup/before-extraction-fix-20261023.

Yerel test paketi: 131 test çalıştı; 130 başarılı, 1 platform koşuluyla atlandı.
Kaynak seçimi, sonraki grup hatasında kısmi başarıyı reddetme, soru/kısa yanıt
koruması, şemanın yerel çözücüye iletilmesi, yanıt kesilmesi, başarısızlık
bildirimi ve onaysız yeniden deneme regresyonları içerilir.
