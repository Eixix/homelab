#!/usr/bin/env python3
"""Read-only status broker over a private Unix socket; no mutation endpoint."""
import http.client
import json
import os
from pathlib import Path
import socket
import socketserver
import sys
import time

ROOT = Path('/run/ivr-status')
SOCKET = ROOT / 'status.sock'
BACKUP = Path('/status/last-backup-success')
# Container names and Compose labels are fixed in code, never supplied by callers.
SERVICES = {'homeassistant': 'homeassistant', 'traefik': 'reverse-proxy', 'adguardhome': 'adguardhome'}


class DockerConnection(http.client.HTTPConnection):
    def __init__(self):
        super().__init__('localhost', timeout=1)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


def inspect_container(container):
    if container not in SERVICES:
        raise ValueError('Unknown status target')
    connection = DockerConnection()
    try:
        # No generic proxy and no caller-controlled method, URL or Docker request body.
        connection.request('GET', '/containers/' + container + '/json')
        response = connection.getresponse()
        body = response.read(1048577)
        if len(body) > 1048576 or response.status != 200:
            raise OSError('Docker inspect failed')
        return json.loads(body)
    finally:
        connection.close()


def backup_status(path=BACKUP, now=None):
    now = time.time() if now is None else now
    try:
        stamp = int(path.read_text().strip())
        age = now - stamp
        if stamp <= 0 or age < -60:
            return 'unknown'
        return 'recent' if age < 86400 else 'old'
    except (OSError, ValueError):
        return 'unknown'


class Broker:
    def __init__(self, inspect=inspect_container, backup=backup_status):
        self.inspect = inspect
        self.backup = backup

    def status(self, container):
        try:
            body = self.inspect(container)
            labels = body.get('Config', {}).get('Labels', {})
            if (labels.get('com.docker.compose.project') != 'homelab'
                    or labels.get('com.docker.compose.service') != SERVICES[container]):
                return 'unknown'
            state = body.get('State', {})
            if state.get('Restarting') or state.get('Health', {}).get('Status') in ('unhealthy', 'starting'):
                return 'unhealthy'
            if state.get('Running') is True:
                return 'running'
            return 'stopped' if state.get('Running') is False else 'unknown'
        except (OSError, ValueError, AttributeError, TypeError, http.client.HTTPException):
            return 'unknown'

    def dispatch(self, request):
        if not isinstance(request, dict) or set(request) != {'action'}:
            return {'result': 'denied'}
        if request['action'] == 'ping':
            return {'result': 'ok'}
        if request['action'] == 'backup':
            return {'backup': self.backup()}
        if request['action'] == 'status':
            return {**{name: self.status(name) for name in SERVICES}, 'backup': self.backup()}
        return {'result': 'denied'}


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(3)
        try:
            raw = self.rfile.readline(1025)
            if len(raw) > 1024 or not raw.endswith(b'\n'):
                result = {'result': 'denied'}
            else:
                result = self.server.broker.dispatch(json.loads(raw))
        except (OSError, ValueError, TypeError):
            result = {'result': 'failed'}
        try:
            self.wfile.write(json.dumps(result).encode() + b'\n')
        except OSError:
            pass


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        print('IVR status request failed', file=sys.stderr)


def main():
    os.umask(0o077)
    if sys.argv[1:] == ['health']:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(str(SOCKET))
            client.sendall(b'{"action":"ping"}\n')
            assert json.loads(client.recv(1024)) == {'result': 'ok'}
        return
    ROOT.mkdir(exist_ok=True, mode=0o700)
    ROOT.chmod(0o700)
    SOCKET.unlink(missing_ok=True)
    with Server(str(SOCKET), Handler) as server:
        SOCKET.chmod(0o600)
        server.broker = Broker()
        server.serve_forever()


if __name__ == '__main__':
    main()
