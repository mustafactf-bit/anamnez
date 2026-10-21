"""Queue-based Tk dispatch. Workers never call any Tk method."""
import logging
import queue
import threading

logger=logging.getLogger(__name__)

class WorkerBridge:
    """One heavy job at a time, polled only by the UI thread."""
    def __init__(self,root):
        self.root=root;self.queue=queue.Queue();self.closed=False
        self.busy=False
        self.token=root.after(50,self._poll)

    def post(self,callback):
        """Thread-safe callback submission without Tk access."""
        if not self.closed:self.queue.put(callback)

    def _poll(self):
        if self.closed:return
        for _ in range(100):
            try:callback=self.queue.get_nowait()
            except queue.Empty:break
            callback()
        if not self.closed:self.token=self.root.after(50,self._poll)

    def start(self,work,success,failure) -> bool:
        """Return false while another model/network operation is active."""
        if self.busy or self.closed:return False
        self.busy=True
        def finish(callback,result):
            self.busy=False;callback(result)
        def run():
            try:
                result=work()
            except Exception as error:
                # Never log exception text, request contents or patient data.
                logger.warning('Background job failed (%s)',type(error).__name__)
                self.post(lambda error=error:finish(failure,error))
            else:self.post(lambda:finish(success,result))
        threading.Thread(target=run,daemon=True).start()
        return True

    def close(self):
        """Discard callbacks after close; blocked native jobs remain daemonized."""
        self.closed=True
        self.root.after_cancel(self.token)
