#!/usr/bin/env python3
"""Pack local photos into one authenticated, AES-CTR-XORed gallery file."""
import argparse
import base64
import hashlib
import hmac
import json
from pathlib import Path
import secrets

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from game import gallery_key

MEDIA = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
SIGNATURES = {'image/jpeg': b'\xff\xd8\xff', 'image/png': b'\x89PNG\r\n\x1a\n', 'image/webp': b'RIFF'}
MARKER = b'CUPX2'


def encode_bundle(directory, key):
    if len(key) != 32:
        raise ValueError('Der private Galerieschlüssel muss 32 Byte lang sein.')
    photos = sorted(path for path in Path(directory).iterdir() if path.is_file())
    if not photos:
        raise ValueError('Der Bilderordner ist leer.')
    images = []
    for number, path in enumerate(photos, 1):
        mime = MEDIA.get(path.suffix.lower())
        if not mime:
            raise ValueError(f'Nicht unterstütztes Bildformat: {path.suffix}')
        data = path.read_bytes()
        if not data.startswith(SIGNATURES[mime]) or len(data) > 8 * 1024 * 1024:
            raise ValueError(f'Bild ist beschädigt oder zu groß: {path.name}')
        images.append({'id': f'{number:02d}', 'mime': mime, 'data': base64.b64encode(data).decode('ascii')})
    plain = json.dumps({'version': 2, 'images': images}, separators=(',', ':')).encode()
    nonce = secrets.token_bytes(16)
    enc_key = hmac.digest(key, b'cup-gallery/enc', hashlib.sha256)
    mac_key = hmac.digest(key, b'cup-gallery/mac', hashlib.sha256)
    encryptor = Cipher(algorithms.AES(enc_key), modes.CTR(nonce)).encryptor()
    ciphertext = encryptor.update(plain) + encryptor.finalize()
    header = MARKER + nonce
    tag = hmac.digest(mac_key, header + ciphertext, hashlib.sha256)
    return header + tag + ciphertext, len(images)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_dir', type=Path, help='Lokaler, nicht versionierter Bilderordner')
    parser.add_argument('--config', type=Path, required=True, help='Bestehende private Wedding-Konfiguration')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'public/study-gallery.cup')
    args = parser.parse_args()
    bundle, count = encode_bundle(args.source_dir, gallery_key(json.loads(args.config.read_text())))
    args.output.write_bytes(bundle)
    print(f'{count} Bilder als {args.output.name} kodiert. Originale bleiben unverändert.')
