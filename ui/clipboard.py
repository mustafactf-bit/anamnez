"""Verified Unicode clipboard writes, persistent on Windows without extra packages."""
import sys
import time


class ClipboardError(RuntimeError):
    """The clipboard could not be written/read reliably."""


def normalize_lines(value: str) -> str:
    """Clipboard text consumers may expose CRLF as LF."""
    return value.replace('\r\n', '\n')


class TkClipboard:
    """Fallback for non-Windows desktop testing."""
    def __init__(self, root):
        self.root = root

    def read(self):
        try:
            return self.root.clipboard_get()
        except Exception as error:
            raise ClipboardError('Pano okunamadı.') from error

    def write(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            if normalize_lines(self.read()) != normalize_lines(text):
                raise ClipboardError('Pano doğrulaması başarısız.')
        except Exception as error:
            raise ClipboardError('Pano yazılamadı.') from error


class WindowsClipboard:
    """CF_UNICODETEXT owned by Windows survives application shutdown."""
    def __init__(self, root):
        import ctypes
        from ctypes import wintypes as w
        self.ctypes = ctypes
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.root = root
        for name,args,result in [
            ('OpenClipboard',[w.HWND],w.BOOL), ('CloseClipboard',[],w.BOOL),
            ('EmptyClipboard',[],w.BOOL), ('GetClipboardData',[w.UINT],w.HANDLE),
            ('SetClipboardData',[w.UINT,w.HANDLE],w.HANDLE),
            ('IsClipboardFormatAvailable',[w.UINT],w.BOOL)]:
            function=getattr(self.user,name);function.argtypes=args;function.restype=result
        for name,args,result in [
            ('GlobalAlloc',[w.UINT,ctypes.c_size_t],w.HANDLE),
            ('GlobalLock',[w.HANDLE],ctypes.c_void_p),
            ('GlobalUnlock',[w.HANDLE],w.BOOL), ('GlobalFree',[w.HANDLE],w.HANDLE)]:
            function=getattr(self.kernel,name);function.argtypes=args;function.restype=result

    def _open(self):
        for _ in range(4):
            if self.user.OpenClipboard(self.root.winfo_id()):return
            time.sleep(.025)
        raise ClipboardError('Pano başka bir uygulama tarafından kullanılıyor; yeniden deneyin.')

    def read(self):
        self._open()
        try:
            if not self.user.IsClipboardFormatAvailable(13):return None
            handle=self.user.GetClipboardData(13)
            pointer=self.kernel.GlobalLock(handle) if handle else None
            if not pointer:raise ClipboardError('Panodaki metin okunamadı.')
            try:return self.ctypes.wstring_at(pointer)
            finally:self.kernel.GlobalUnlock(handle)
        finally:self.user.CloseClipboard()

    def write(self, text):
        payload=text.replace('\r\n','\n').replace('\n','\r\n').encode('utf-16-le')+b'\x00\x00'
        handle=self.kernel.GlobalAlloc(2,len(payload))
        if not handle:raise ClipboardError('Pano için bellek ayrılamadı.')
        transferred=False
        try:
            pointer=self.kernel.GlobalLock(handle)
            if not pointer:raise ClipboardError('Pano belleğine erişilemedi.')
            try:self.ctypes.memmove(pointer,payload,len(payload))
            finally:self.kernel.GlobalUnlock(handle)
            self._open()
            try:
                if not self.user.EmptyClipboard() or not self.user.SetClipboardData(13,handle):
                    raise ClipboardError('Metin panoya yazılamadı.')
                transferred=True
            finally:self.user.CloseClipboard()
        finally:
            if not transferred:self.kernel.GlobalFree(handle)
        if normalize_lines(self.read() or '')!=normalize_lines(text):
            raise ClipboardError('Panodaki metin doğrulanamadı; yeniden kopyalayın.')


def create_clipboard(root):
    """Choose native persistent clipboard on the target Windows platform."""
    return WindowsClipboard(root) if sys.platform=='win32' else TkClipboard(root)
