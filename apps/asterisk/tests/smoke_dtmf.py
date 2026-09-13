"""Run inside the built image with --network none and ASTERISK_MODE=local.

Uses only loopback and synthetic SIP/RTP calls, never provider credentials.
Python 3.12 audioop encodes synthetic in-band tones as G.711 A-law.
A loopback HTTP mock checks the PIN gate without changing any real HA state.
"""
import audioop
import math
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import time
import uuid

LOG = Path('/tmp/asterisk-dtmf-smoke.log')


def cli(command):
    return subprocess.run(['asterisk', '-rx', command], capture_output=True, text=True, timeout=3)


def call(method, delay=1, steps=None, expected="custom/unavailable"):
    steps = [("1", delay)] if steps is None else steps
    sip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sip.bind(('127.0.0.1', 0))
    sip.settimeout(5)
    rtp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtp.bind(('127.0.0.1', 0))
    rtp.setblocking(False)
    sip_port, rtp_port = sip.getsockname()[1], rtp.getsockname()[1]
    call_id = uuid.uuid4().hex
    from_header = f'<sip:test@127.0.0.1>;tag={call_id[:10]}'
    to_header = '<sip:ivr@127.0.0.1>'
    target = 'sip:ivr@127.0.0.1:5060'
    offset = len(LOG.read_text())

    def request(method_name, cseq, body='', content_type=None):
        headers = [f'{method_name} {target} SIP/2.0',
                   f'Via: SIP/2.0/UDP 127.0.0.1:{sip_port};branch=z9hG4bK{uuid.uuid4().hex}',
                   'Max-Forwards: 70', f'From: {from_header}', f'To: {to_header}',
                   f'Call-ID: {call_id}', f'CSeq: {cseq} {method_name}',
                   f'Contact: <sip:test@127.0.0.1:{sip_port}>']
        if content_type:
            headers.append(f'Content-Type: {content_type}')
        headers.append(f'Content-Length: {len(body.encode())}')
        sip.sendto(('\r\n'.join(headers) + '\r\n\r\n' + body).encode(), ('127.0.0.1', 5060))

    try:
        payloads = '8 101' if method == 'rfc4733' else '8'
        sdp = (f'v=0\r\no=test 1 1 IN IP4 127.0.0.1\r\ns=DTMF test\r\n'
               f'c=IN IP4 127.0.0.1\r\nt=0 0\r\nm=audio {rtp_port} RTP/AVP {payloads}\r\n'
               'a=rtpmap:8 PCMA/8000\r\na=sendrecv\r\na=ptime:20\r\n')
        if method == 'rfc4733':
            sdp += 'a=rtpmap:101 telephone-event/8000\r\na=fmtp:101 0-16\r\n'
        request('INVITE', 1, sdp, 'application/sdp')
        while True:
            response = sip.recv(65535).decode()
            code = int(response.split()[1])
            if code >= 200:
                assert code == 200, f'{method}: SIP rejected: {code}'
                break
        to_header = re.search(r'^To:\s*(.+)', response, re.MULTILINE | re.IGNORECASE)[1].strip()
        target = re.search(r'^Contact:\s*<([^>]+)>', response, re.MULTILINE | re.IGNORECASE)[1]
        media_port = int(re.search(r'm=audio (\d+)', response)[1])
        request('ACK', 1)
        seq, timestamp, received = 1, 8000, 0

        def packet(payload, payload_type=8, event_timestamp=None, marker=False):
            nonlocal seq, timestamp, received
            header = struct.pack('!BBHII', 0x80, payload_type | (0x80 if marker else 0),
                                 seq, timestamp if event_timestamp is None else event_timestamp, 12345)
            rtp.sendto(header + payload, ('127.0.0.1', media_port))
            seq += 1
            timestamp += 160
            time.sleep(0.02)
            while True:
                try:
                    data = rtp.recv(2048)
                    if len(data) > 12 and data[1] & 0x7f == 8:
                        received += 1
                except BlockingIOError:
                    break

        cseq = 2
        for digits, pause in steps:
            for _ in range(round(pause * 50)):
                packet(b'\xd5' * 160)
            assert received > 10, f'{method}: no usable outbound audio'
            for digit in digits:
                event = '0123456789*#'.index(digit)
                if method == 'info':
                    request('INFO', cseq, f'Signal={digit}\r\nDuration=160\r\n', 'application/dtmf-relay')
                    cseq += 1
                elif method == 'rfc4733':
                    event_timestamp = timestamp
                    for i in range(1, 9):
                        packet(struct.pack('!BBH', event, 10, i * 160), 101, event_timestamp, i == 1)
                    for _ in range(3):
                        packet(struct.pack('!BBH', event, 0x80 | 10, 1280), 101, event_timestamp)
                else:
                    assert digit in ('1', '2')
                    high = 1209 if digit == '1' else 1336
                    for frame in range(10):
                        pcm = b''.join(struct.pack('<h', int(6000 * (math.sin(2 * math.pi * 697 * n / 8000)
                                                                + math.sin(2 * math.pi * high * n / 8000))))
                                       for n in range(frame * 160, (frame + 1) * 160))
                        packet(audioop.lin2alaw(pcm, 2))
                for _ in range(7):
                    packet(b'\xd5' * 160)
        for _ in range(250):
            packet(b'\xd5' * 160)
            if expected in LOG.read_text()[offset:]:
                print(f'{method}: expected menu branch reached; audio received', flush=True)
                break
        else:
            raise AssertionError(f'{method}: expected menu branch was not reached')
        request('BYE', cseq)
        time.sleep(0.2)
    finally:
        sip.close()
        rtp.close()


class SipBusyPeer:
    """Only a loopback peer: record destination and reject calls as busy."""
    def __init__(self):
        self.numbers = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('127.0.0.1', 0))
        self.socket.settimeout(0.2)
        self.port = self.socket.getsockname()[1]
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while not self.stop.is_set():
            try:
                data, address = self.socket.recvfrom(65535)
            except socket.timeout:
                continue
            message = data.decode()
            if not message.startswith('INVITE '):
                continue
            self.numbers.append(re.search(r'^INVITE sip:([^@]+)@', message)[1])
            headers = []
            for name in ('Via', 'From', 'To', 'Call-ID', 'CSeq'):
                value = re.search(r'^' + name + r':\s*(.+)', message, re.MULTILINE | re.IGNORECASE)[1].strip()
                if name == 'To':
                    value += ';tag=busy-test'
                headers.append(name + ': ' + value)
            response = 'SIP/2.0 486 Busy Here\r\n' + '\r\n'.join(headers) + '\r\nContent-Length: 0\r\n\r\n'
            self.socket.sendto(response.encode(), address)

    def close(self):
        self.stop.set()
        self.thread.join()
        self.socket.close()


def main():
    assert os.environ.get('ASTERISK_MODE', 'local') == 'local'
    config = Path('/etc/asterisk/asterisk.conf')
    config.write_text(config.read_text().replace('verbose = 0', 'verbose = 3'))
    Path('/etc/asterisk/logger.conf').write_text('[logfiles]\nconsole => warning,error,verbose,dtmf\n')
    peer = SipBusyPeer()
    pjsip = Path('/etc/asterisk/pjsip.local.conf')
    pjsip.write_text(pjsip.read_text() + '\n[vodafone]\ntype=endpoint\ntransport=transport-udp\ndisallow=all\nallow=alaw\ndirect_media=no\n')
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append((self.path, self.headers.get('Authorization'),
                             json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'[]')
        def log_message(self, *args): pass
    server = HTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    os.environ.update(ASTERISK_MENU_PIN='012345', ASTERISK_HA_TOKEN='synthetic-test-token',
                      ASTERISK_HA_URL=f'http://127.0.0.1:{server.server_port}',
                      ASTERISK_HA_KITCHEN_ENTITY='light.synthetic_kitchen')
    with LOG.open('w') as log:
        proc = subprocess.Popen(['python3', '/usr/local/bin/asterisk-entrypoint.py'], stdout=log, stderr=log)
        try:
            for _ in range(45):
                if 'Asterisk Ready' in LOG.read_text():
                    break
                if proc.poll() is not None:
                    raise RuntimeError('Asterisk startup failed')
                time.sleep(1)
            else:
                raise RuntimeError('Asterisk startup timed out')
            cli('core set verbose 3')
            runtime = Path('/run/asterisk/menu.json')
            config = json.loads(runtime.read_text())
            config.update(mode='vodafone', domain=f'127.0.0.1:{peer.port}',
                          destinations={'annika': '+4915112345678', 'tobias': '+4915112345679'})
            runtime.write_text(json.dumps(config))
            health = subprocess.run(['python3', '/usr/local/bin/asterisk-healthcheck.py'])
            assert health.returncode == 0, 'IVR healthcheck failed'

            for method in ('rfc4733', 'info', 'inband'):
                call(method)
            call('rfc4733', delay=8)
            call('rfc4733', steps=[('2', 1)])
            assert peer.numbers == ['+4915112345678'] * 4 + ['+4915112345679'], 'Wrong outbound destination'
            print('Both fixed forwarding targets and busy fallback verified', flush=True)
            assert not requests, 'Public menu must never call Home Assistant'
            call('rfc4733', steps=[('9', 1), ('000000#', 0.5)], expected='custom/denied')
            assert not requests, 'Wrong PIN must never call Home Assistant'
            call('rfc4733', steps=[('9', 1), ('012345#', 0.5), ('1', 0.5)], expected='custom/action-ok')
            assert requests == [('/api/services/light/turn_on', 'Bearer synthetic-test-token',
                                 {'entity_id': 'light.synthetic_kitchen'})]
            print('PIN gate and exactly one kitchen turn_on request verified', flush=True)
        except Exception:
            print(LOG.read_text())
            raise
        finally:
            peer.close()
            server.shutdown()
            server.server_close()
            cli('core stop now')
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__ == '__main__':
    main()
