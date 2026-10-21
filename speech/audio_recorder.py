"""Memory-only, bounded mono microphone recording."""
import time

def record_audio(stop_event, on_started, max_seconds=900):
    """Capture audio without writing files; report overflow and time limit."""
    import numpy as np
    import sounddevice as sd
    chunks=[];overflow=[False];limit=False
    def receive(indata,_frames,_time_info,status):
        if status:overflow[0]=True
        chunks.append(indata.copy())
    with sd.InputStream(samplerate=16000,channels=1,dtype='float32',callback=receive):
        on_started();start=time.monotonic()
        while not stop_event.wait(.1):
            if time.monotonic()-start>=max_seconds:
                limit=True;break
    if not chunks:raise ValueError('Mikrofondan ses alınamadı.')
    return np.concatenate(chunks,axis=0).reshape(-1),overflow[0],limit
