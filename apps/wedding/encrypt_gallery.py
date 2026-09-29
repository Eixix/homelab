#!/usr/bin/env python3
"""Encode a gallery image as a CUPX1 XOR artifact; keep source photos outside this public repo."""
import argparse
from pathlib import Path

KEY = b'CUP-LAB-2026'
TYPES = {'.svg': 1, '.jpg': 2, '.jpeg': 2, '.png': 3, '.webp': 4}
NAMES = {'bibliothek': 'study-library.cup', 'labor': 'study-lab.cup', 'feierabend': 'study-afterhours.cup'}


def encode(source):
    source = Path(source)
    kind = TYPES.get(source.suffix.lower())
    if kind is None:
        raise ValueError('Erlaubt sind SVG, JPEG, PNG und WebP.')
    image = source.read_bytes()
    if not image or len(image) > 8 * 1024 * 1024:
        raise ValueError('Bild muss zwischen 1 Byte und 8 MiB groß sein.')
    return b'CUPX1' + bytes([kind]) + bytes(value ^ KEY[i % len(KEY)] for i, value in enumerate(image))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', choices=sorted(NAMES))
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    target = Path(__file__).parent / 'public' / NAMES[args.name]
    target.write_bytes(encode(args.source))
    print(f'{target.name} geschrieben; Quelldatei bleibt unverändert.')
