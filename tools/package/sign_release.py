"""Sign a release with an external Ed25519 PEM key; never commit private keys."""
import argparse
import hashlib
import json
from pathlib import Path
from cryptography.hazmat.primitives.serialization import load_pem_private_key

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--key',required=True)
    parser.add_argument('--installer',required=True)
    parser.add_argument('--version',required=True)
    args=parser.parse_args()
    path=Path(args.installer)
    raw=json.dumps({'version':args.version,
        'url':f'https://github.com/mustafactf-bit/anamnez/releases/download/v{args.version}/Anamnez-Asistani-Kurulum.exe',
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':path.stat().st_size},
        separators=(',',':'),sort_keys=True).encode('utf-8')
    key=load_pem_private_key(Path(args.key).read_bytes(),password=None)
    path.with_name('update.json').write_bytes(raw)
    path.with_name('update.sig').write_bytes(key.sign(raw))
