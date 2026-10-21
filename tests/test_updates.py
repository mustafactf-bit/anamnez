import base64
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from distribution import updater as u

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.key=Ed25519PrivateKey.generate()
        self.public=base64.b64encode(self.key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode()
        self.data={'version':'2.0.0-alpha.1.3',
            'url':'https://github.com/mustafactf-bit/anamnez/releases/download/v2.0.0-alpha.1.3/Anamnez-Asistani-Kurulum.exe',
            'size':4,'sha256':hashlib.sha256(b'EXE!').hexdigest()}

    def signed(self):
        raw=json.dumps(self.data).encode()
        return raw,self.key.sign(raw)

    def test_signature_and_mutation(self):
        raw,sig=self.signed()
        self.assertEqual(u.verify_manifest(raw,sig,self.public).version,self.data['version'])
        for changed,signature in [(raw+b' ',sig),(raw,b'0'*64)]:
            with self.assertRaises(u.UpdateError):u.verify_manifest(changed,signature,self.public)

    def test_signed_but_unsafe_metadata(self):
        for field,value in [('url','https://evil.example/setup.exe'),('size',True),
                ('size',u.MAX_INSTALLER+1),('sha256','invalid'),('version','../../bad')]:
            original=self.data[field];self.data[field]=value
            with self.assertRaises(u.UpdateError):u.verify_manifest(*self.signed(),self.public)
            self.data[field]=original

    def test_order_prevents_downgrades(self):
        versions=['2.0.0-alpha.1.1','2.0.0-alpha.1.2','2.0.0-alpha.1.12','2.0.0']
        self.assertEqual(versions,sorted(versions,key=u.version_key))
        with self.assertRaises(u.UpdateError):u.version_key('2.0.0;calc')

    def test_no_new_release_or_draft(self):
        reader=lambda *_:json.dumps([{'tag_name':'v2.0.0-alpha.1.1'},
            {'tag_name':'v9.0.0','draft':True}]).encode()
        self.assertIsNone(u.check_updates('2.0.0-alpha.1.2',reader))

    def test_network_error_safe(self):
        with self.assertRaises(u.UpdateError):u.check_updates('2.0.0-alpha.1.2',lambda *_:(_ for _ in ()).throw(OSError()))

    def test_verified_download_and_corruption_cleanup(self):
        release=u.Release(**self.data)
        with tempfile.TemporaryDirectory() as directory:
            for payload,success in [(b'EXE!',True),(b'FAIL',False),(b'EXE!extra',False),(b'EX',False)]:
                with patch.object(u.urllib.request,'urlopen',return_value=io.BytesIO(payload)):
                    if success:
                        path=u.download_update(release,directory)
                        self.assertEqual(path.read_bytes(),b'EXE!')
                    else:
                        with self.assertRaises(u.UpdateError):u.download_update(release,directory)
                self.assertFalse(list(Path(directory).glob('*.partial')))
                self.assertEqual(path.read_bytes(),b'EXE!')

    def test_launch_rehash_rejects_tampered_exe(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'setup.exe';path.write_bytes(b'FAIL')
            with patch.object(u.sys,'frozen',True,create=True),patch.object(u.sys,'platform','win32'),patch.object(u.subprocess,'Popen') as launch:
                with self.assertRaises(u.UpdateError):u.launch_installer(path,u.Release(**self.data))
                launch.assert_not_called()

    def test_launch_is_not_silent_or_forced(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'setup.exe';path.write_bytes(b'EXE!')
            with patch.object(u.sys,'frozen',True,create=True),patch.object(u.sys,'platform','win32'),patch.object(u.subprocess,'Popen') as launch:
                u.launch_installer(path,u.Release(**self.data))
                args=launch.call_args.args[0]
                self.assertIn('/NOCLOSEAPPLICATIONS',args)
                self.assertNotIn('/VERYSILENT',args)

    def test_repo_url_boundary(self):
        for url in ['http://github.com/mustafactf-bit/anamnez/releases/download/a/b',
            'https://github.com.evil/mustafactf-bit/anamnez/releases/download/a/b',
            'https://github.com/other/repo/releases/download/a/b']:
            self.assertFalse(u.allowed_url(url))
