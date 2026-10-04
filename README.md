# Anamnez Asistanı

Windows üzerinde Python 3 ile çalışan, Tkinter tabanlı Türkçe masaüstü uygulaması.

## Çalıştırma

1. Python 3.10 veya üzerini yükleyin. Windows kurulumunda **Add Python to PATH** seçeneğini işaretleyin.
2. İlk kullanımda `WhisperKurulum.vbs` dosyasına çift tıklayın. Gerekli paketleri uygulama klasöründeki `.venv` içine sessizce kurar; işlem internet hızınıza göre birkaç dakika sürebilir. Terminal kullanmanız gerekmez.
3. Uygulamayı açmak için `AnamnezAsistani.vbs` dosyasına çift tıklayın. Kurulum yapıldıysa klasördeki sanal ortamı kullanır; konsol penceresi açmaz.
4. İsterseniz `anamnez_asistani.py` dosyasını terminalden de çalıştırabilirsiniz:

   ```powershell
   python anamnez_asistani.py
   ```

Mikrofon diktesi için `requirements.txt` içindeki `faster-whisper` ve `sounddevice` paketleri kurulur. PubMed'den yayın bilgisi getirmek için ayrıca internet bağlantısı gerekir.

## Dikte ve alanlara aktarma

Uygulamadaki **Dikte metni** sekmesinde **Mikrofonla dikte et** düğmesine basıp konuşun, ardından **Kaydı bitir ve yazıya çevir** düğmesine basın. Kayıt en fazla 15 dakika sürer. Ses, seçilen çok dilli Whisper modeliyle bilgisayarda işlenir; ses dosyası oluşturulmaz veya bir sunucuya gönderilmez. Model ilk kullanımda internetten indirilip önbelleğe alınır. Uygulama CPU üzerinde çalıştırır; ilk model indirme ve çözümleme zaman alabilir.

Varsayılan `small` modeli düşük kaynak kullanımı için seçilmiştir. Model listesinden `medium`, `large-v3` veya `turbo` seçilebilir; büyük modeller daha fazla bellek ve işlem gücü ister. OpenAI Whisper Türkçeyi çok dilli modellerinde destekler, ancak dil desteği yüksek doğruluk garantisi değildir: aksan, arka plan gürültüsü, mikrofon ve özellikle tıbbi terimler sonucu etkileyebilir. Whisper'ın resmi model kartı da dil/aksan/diyalekt farkları ve söylenmemiş metin üretebilme olasılığı konusunda uyarır. Klinik kullanımda dökümü daima dinleyip düzeltin; tanı, ilaç, doz, ölçüm ve negasyonları özellikle kontrol edin.

Whisper yerine Gemini web sitesinde dikte ettiğiniz metni kopyalayıp uygulamaya da yapıştırabilirsiniz. Alan etiketleriyle yazılmış satırlar ilgili alanı günceller; örneğin:

```text
Şikâyet: Halsizlik son iki aydır devam ediyor.
Tansiyon: 120/80 mmHg
HbA1c: 7,2
```

Etiketsiz cümleler mevcut şikâyet metninin sonuna eklenir. Dikte içinde açıkça ve değerle belirtilmeyen alanlara dokunulmaz; özellikle fizik muayenedeki `...` gibi eksik bilgiler değiştirilmez. Aktarılan bilgileri anamnez çıktısını kullanmadan önce kontrol edin.

## Öneriler ve kaynaklar

Uygulama beş genel klinik değerlendirme başlığı sunar. **PubMed kaynaklarını getir** düğmesi her başlık için sabit, genel arama terimlerini NCBI PubMed E-utilities ile arar ve bulunan kayıtların bağlantılarını gösterir. Her başlık ayrıca Google Scholar arama bağlantısı içerir. Google Scholar sonuçları uygulama içinde taranmaz.

Hasta adı, kimlik bilgisi, ses, dikte metni ve anamnez alanları Whisper, PubMed veya Google Scholar hizmetlerine gönderilmez. PubMed'e yalnızca uygulamada yazılı genel literatür arama terimleri gönderilir. Hasta verisi yalnızca kullanıcı **JSON kaydet** veya metin kaydet işlemi yaptığında seçilen konuma yazılır.

Whisper kaynakları: [OpenAI Whisper deposu](https://github.com/openai/whisper), [model kartı](https://github.com/openai/whisper/blob/main/model-card.md), [Whisper makalesi](https://arxiv.org/abs/2212.04356). Makaledeki çok dilli değerlendirmeler Türkçe desteğini anlamaya yardımcı olur; gerçek klinik dikte başarısının yerini tutmaz.

Bu uygulama tanı koymaz ve tedavi önerisi yerine geçmez. Kaynaklar ve olası tetkikler, hastayı değerlendiren sağlık profesyoneli tarafından klinik bağlamda doğrulanmalıdır.
