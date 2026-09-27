#!/usr/bin/env python3
"""Start the same app locally on its canonical HTTPS domain with isolated state."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description='CUP-Hochzeitsspiel lokal über HTTPS starten')
    parser.add_argument('--personalize', type=Path, default=ROOT/'secrets/wedding-personalization.json')
    parser.add_argument('--env-file', type=Path, default=ROOT/'.env.local.example', help='Lokale Domainwerte (Standard: .env.local.example)')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--native', action='store_true', help='Direkter lokaler HTTPS-Testserver ohne Docker-Netzwerk')
    parser.add_argument('--port', type=int, default=8443, help='Port für --native (Standard: 8443, ohne Administratorrechte)')
    args = parser.parse_args()
    env = dict(os.environ, WEDDING_LOCAL_UID=str(os.getuid()), WEDDING_LOCAL_GID=str(os.getgid()))
    command = ['docker', 'compose', '--env-file', str(args.env_file.resolve()), '-f', str(ROOT/'compose.wedding-local.yaml'), '--profile', 'wedding']
    if args.stop:
        subprocess.run(command+['stop'], cwd=ROOT, env=env, check=True)
        return
    import json
    effective = json.loads(subprocess.check_output(command+['config', '--format', 'json'], cwd=ROOT, env=env))
    domains = effective['services']['wedding-local-https']['environment']
    hosts = [domains['WEDDING_HOST'], domains['WEDDING_EXTERNAL_HOST']]
    os.umask(0o077)
    for folder in ['wedding-local-v2','wedding-local-tls','wedding-local-caddy']:
        (ROOT/'data'/folder).mkdir(parents=True, exist_ok=True, mode=0o700)
    config_dir = ROOT/'secrets/wedding-local-v2'
    if not config_dir.exists():
        setup = [sys.executable,str(Path(__file__).with_name('setup.py')),'--directory',str(config_dir),'--generate-password', '--origin', 'https://'+hosts[1]]
        if args.personalize.exists():
            setup += ['--personalize',str(args.personalize)]
        subprocess.run(setup,cwd=ROOT,check=True)
    config = json.loads((config_dir/'config.json').read_text())
    old_origin = config['origin']
    links = (config_dir/'links.txt').read_text()
    config['origin'] = 'https://'+hosts[1]
    (config_dir/'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    (config_dir/'links.txt').write_text(links.replace(old_origin, config['origin']))
    (config_dir/'internal-links.txt').write_text(links.replace(old_origin, 'https://'+hosts[0]))
    if args.native:
        serve_native(config_dir, args.port, hosts)
        return
    subprocess.run(command+['up','-d','--build','wedding','wedding-local-https'],cwd=ROOT,env=env,check=True)
    print('Lokale Instanz gestartet. Persönliche Links und Passwort: secrets/wedding-local-v2/')
    print('Lokale Testdomains: ' + ', '.join(hosts))
    print('Lokales Stammzertifikat: data/wedding-local-tls/caddy/pki/authorities/local/root.crt')
    print('.localhost wird lokal aufgelöst. Zertifikatsvertrauen einrichten; siehe README.')


def serve_native(config_dir, port, hosts):
    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server
    import ssl
    import json
    from server import App
    config = json.loads((config_dir/'config.json').read_text())
    host = hosts[1]
    tls = ROOT/'data/wedding-local-native-tls'
    tls.mkdir(mode=0o700, exist_ok=True)
    def openssl(*args):
        subprocess.run(['openssl', *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not (tls/'root.crt').exists():
        openssl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(tls/'root.key'), '-out', str(tls/'root.crt'), '-days', '365', '-subj', '/CN=CUP local test CA', '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    import re
    cert_names = set()
    if (tls/'server.crt').exists():
        text = subprocess.check_output(['openssl','x509','-in',str(tls/'server.crt'),'-noout','-ext','subjectAltName']).decode()
        cert_names = set(re.findall(r'DNS:([^,\s]+)', text))
    cert_matches = all(name in cert_names for name in hosts)
    if not cert_matches:
        openssl('req', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(tls/'server.key'), '-out', str(tls/'server.csr'), '-subj', f'/CN={host}')
        sans = ','.join('DNS:'+name for name in hosts)
        (tls/'extensions.cnf').write_text(f'subjectAltName={sans}\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n')
        openssl('x509', '-req', '-in', str(tls/'server.csr'), '-CA', str(tls/'root.crt'), '-CAkey', str(tls/'root.key'), '-CAcreateserial', '-out', str(tls/'server.crt'), '-days', '30', '-extfile', str(tls/'extensions.cnf'))
    class Server(ThreadingMixIn, WSGIServer):
        daemon_threads = True
    class Quiet(WSGIRequestHandler):
        def log_message(self, *args):
            pass
    origin = f'https://{host}' + (f':{port}' if port != 443 else '')
    os.environ['WEDDING_ORIGIN'] = origin
    os.environ['WEDDING_ORIGINS'] = ' '.join('https://'+name+(f':{port}' if port != 443 else '') for name in hosts)
    app = App(config_dir/'config.json', ROOT/'data/wedding-local-v2/game-v2.sqlite3')
    native_links = (config_dir/'links.txt').read_text().replace(config['origin'], origin)
    (config_dir/'native-links.txt').write_text(native_links)
    internal_origin = 'https://'+hosts[0]+(f':{port}' if port != 443 else '')
    (config_dir/'native-internal-links.txt').write_text((config_dir/'links.txt').read_text().replace(config['origin'], internal_origin))
    server = make_server('127.0.0.1', port, app, server_class=Server, handler_class=Quiet)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(tls/'server.crt', tls/'server.key')
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(f'Lokaler HTTPS-Testserver läuft auf {origin}.', flush=True)
    print('Intern gespiegelt: '+internal_origin, flush=True)
    print('Nur lokal erreichbar. .localhost braucht keinen Hosts-Eintrag; lokales Zertifikat vertrauen.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    main()
