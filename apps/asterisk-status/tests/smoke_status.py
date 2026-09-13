"""Inside network-none/read-only status image; Docker API is a synthetic Unix server."""
import http.server
import importlib.util
import json
from pathlib import Path
import socketserver
import subprocess
import threading
import time

spec = importlib.util.spec_from_file_location('menu', '/tmp/menu.py')
menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menu)
calls = []


class DockerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        calls.append((self.command, self.path))
        name = self.path.split('/')[2]
        service = {'homeassistant': 'homeassistant', 'traefik': 'reverse-proxy', 'adguardhome': 'adguardhome'}[name]
        body = json.dumps({'Config': {'Labels': {'com.docker.compose.project': 'homelab',
                                               'com.docker.compose.service': service},
                                     'Env': ['SYNTHETIC_SECRET=do-not-return']},
                           'State': {'Running': True}}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args): pass


Path('/status/last-backup-success').write_text(str(int(time.time())))
with socketserver.UnixStreamServer('/var/run/docker.sock', DockerHandler) as docker:
    threading.Thread(target=docker.serve_forever, daemon=True).start()
    proc = subprocess.Popen(['python3', '/app/status.py'])
    try:
        for _ in range(50):
            if Path('/run/ivr-status/status.sock').exists():
                break
            assert proc.poll() is None
            time.sleep(0.1)
        subprocess.run(['python3', '/app/status.py', 'health'], check=True, timeout=5)
        assert menu.status_request('status') == {'homeassistant': 'running', 'traefik': 'running',
                                                  'adguardhome': 'running', 'backup': 'recent'}
        assert menu.status_request('backup') == {'backup': 'recent'}
        assert menu.status_request('restart-homeassistant') == {'result': 'denied'}
        assert calls == [('GET', '/containers/' + name + '/json')
                         for name in ('homeassistant', 'traefik', 'adguardhome')]
        assert Path('/run/ivr-status').stat().st_mode & 0o777 == 0o700
        assert Path('/run/ivr-status/status.sock').stat().st_mode & 0o777 == 0o600
        print('Read-only broker image, AGI client, Docker GET allowlist and backup status verified')
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        docker.shutdown()
