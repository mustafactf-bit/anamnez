"""Safe model-stage failures; never display raw exception or clinical content."""
class SpeechModelError(RuntimeError):
    def __init__(self,stage,error):
        self.stage=stage
        self.code=f'MODEL-{stage.upper()}-{type(error).__name__.upper()}'
        if stage=='download':
            self.message='Whisper modeli indirilemedi. İnternet bağlantısını ve kullanılabilir disk alanını kontrol edip yeniden deneyin.'
        else:
            self.message='Whisper model dosyası açılamadı. Uygulamayı kapatıp yeniden deneyin. Sorun sürerse aşağıdaki hata kodunu paylaşın.'
        if isinstance(error,ImportError):
            self.message='Paket içindeki bir model bileşeni yüklenemedi. Uygulamanın düzeltilmiş sürümüne güncelleyin.'
        super().__init__(self.code)
