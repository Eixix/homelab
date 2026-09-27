#!/usr/bin/env python3
"""Generate private invitation QR files from the existing role links and password."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,urlencode
import qrcode
from qrcode.image.svg import SvgPathImage


def generate(directory,internal_origin):
    os.umask(0o077)
    directory=Path(directory)
    config=json.loads((directory/'config.json').read_text())
    password=(directory/'password.txt').read_text().strip()
    parsed=urlsplit(internal_origin)
    if parsed.scheme!='https' or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        raise ValueError('Internal origin must be an HTTPS origin without a path.')
    output=directory/'qr'
    output.mkdir(mode=0o700,exist_ok=True)
    links={}
    for line in (directory/'links.txt').read_text().splitlines():
        name,url=line.split(': ',1)
        source=urlsplit(url);role=source.path.split('/')[1]
        if role not in ('a','b'):raise ValueError('Unknown invitation role')
        links[role]=(name,source.path)
    manifest={}
    for scope,origin in [('external',config['origin']),('internal',internal_origin)]:
        host=urlsplit(origin)
        for role,(name,path) in links.items():
            url=urlunsplit((host.scheme,host.netloc,path,'',urlencode({'password':password})))
            stem=f'{scope}-{role}'
            qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=14,border=4)
            qr.add_data(url);qr.make(fit=True)
            qr.make_image(fill_color='black',back_color='white').save(output/(stem+'.png'))
            qr.make_image(image_factory=SvgPathImage).save(output/(stem+'.svg'))
            manifest[stem]=dict(name=name,url=url,png=stem+'.png',svg=stem+'.svg')
    (output/'links.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    for file in output.iterdir():file.chmod(0o600)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--internal-origin',required=True)
    args=parser.parse_args()
    print('Private QR codes saved to '+str(generate(args.directory,args.internal_origin)))
