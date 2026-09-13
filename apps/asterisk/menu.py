#!/usr/bin/env python3
"""Bounded public phone tree and PIN-gated home automation and read-only status."""
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG = Path('/run/asterisk/menu.json')
RATE_LIMIT = Path('/run/asterisk/menu-attempts.json')
PIN_ROUNDS = 200_000


def build_config():
    def value(name):
        result = os.environ.get('ASTERISK_' + name, '')
        if any(ord(c) < 32 for c in result):
            raise ValueError('ASTERISK_' + name + ' contains control characters')
        return result

    destinations = {}
    for who in ('ANNIKA', 'TOBIAS'):
        number = value(who + '_NUMBER')
        if number and not re.fullmatch(r'\+[1-9][0-9]{6,14}', number):
            raise ValueError('ASTERISK_' + who + '_NUMBER must be an international number starting with +')
        destinations[who.lower()] = number
    domain = value('SIP_DOMAIN')
    if domain and not re.fullmatch(r'[a-zA-Z0-9.-]+(?::[0-9]{1,5})?', domain):
        raise ValueError('ASTERISK_SIP_DOMAIN must be a SIP hostname with optional port')
    pin = value('MENU_PIN')
    if pin and not re.fullmatch(r'[0-9]{6,12}', pin):
        raise ValueError('ASTERISK_MENU_PIN must contain 6 to 12 digits')
    salt = secrets.token_hex(16)
    pin_hash = hashlib.pbkdf2_hmac('sha256', pin.encode(), bytes.fromhex(salt), PIN_ROUNDS).hex() if pin else ''
    ha_url = value('HA_URL') or 'http://127.0.0.1:8123'
    url = urllib.parse.urlsplit(ha_url)
    if (url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.path not in ('', '/')):
        raise ValueError('ASTERISK_HA_URL must be an HTTP(S) origin without credentials or path')
    entity = value('HA_KITCHEN_ENTITY')
    if entity and not re.fullmatch(r'(light|switch)\.[a-z0-9_]+', entity):
        raise ValueError('ASTERISK_HA_KITCHEN_ENTITY must be one light or switch entity')
    return dict(mode=value('MODE') or 'local', domain=domain, destinations=destinations,
                pin_salt=salt, pin_hash=pin_hash, ha_url=ha_url.rstrip('/'),
                ha_token=value('HA_TOKEN'), ha_entity=entity)


def verify_pin(config, entered):
    if not config.get('pin_hash') or not re.fullmatch(r'[0-9]{6,12}', entered):
        return False
    candidate = hashlib.pbkdf2_hmac('sha256', entered.encode(), bytes.fromhex(config['pin_salt']), PIN_ROUNDS).hex()
    return hmac.compare_digest(candidate, config['pin_hash'])


def reserve_pin_attempt(path=RATE_LIMIT, now=None):
    """Global, concurrent-call-safe limit: ten attempts per five minutes."""
    now = time.time() if now is None else now
    with path.open('a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        raw = f.read()
        attempts = json.loads(raw) if raw else []
        attempts = [stamp for stamp in attempts if stamp > now - 300]
        allowed = len(attempts) < 10
        if allowed:
            attempts.append(now)
        f.seek(0)
        f.truncate()
        json.dump(attempts, f)
        f.flush()
        return allowed


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def ha_request(config, path, data=None):
    """Fixed local API, bounded response, no redirects/proxies or mutation retries."""
    if not config.get('ha_token'):
        return False, None
    request = urllib.request.Request(
        config['ha_url'] + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={'Authorization': 'Bearer ' + config['ha_token'], 'Content-Type': 'application/json'},
        method='GET' if data is None else 'POST')
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=3) as response:
            body = response.read(262145)
            if len(body) > 262144:
                return False, None
            return 200 <= response.status < 300, json.loads(body)
    except urllib.error.HTTPError as error:
        error.close()
    except (urllib.error.URLError, OSError, ValueError):
        pass
    return False, None


def entity_state(config, entity):
    if not entity:
        return None
    ok, body = ha_request(config, '/api/states/' + entity)
    return body.get('state') if ok and isinstance(body, dict) else None


def ha_action(config, action):
    if not config.get('ha_token'):
        return 'not-configured'
    if action in ('kitchen-on', 'kitchen-off'):
        entity = config.get('ha_entity')
        if not entity:
            return 'not-configured'
        state = 'on' if action == 'kitchen-on' else 'off'
        ok, _ = ha_request(config, '/api/services/' + entity.split('.')[0] + '/turn_' + state,
                           {'entity_id': entity})
        if not ok:
            return 'action-failed'
        # A service response alone is not evidence that the device changed state.
        return 'kitchen-' + state if entity_state(config, entity) == state else 'action-ok'
    return 'invalid-action'


def status_request(action, path='/run/ivr-status/status.sock'):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(4)
            client.connect(path)
            client.sendall(json.dumps({'action': action}).encode() + b'\n')
            with client.makefile('rb') as stream:
                body = stream.readline(4097)
            if len(body) > 4096:
                return {}
            result = json.loads(body)
            return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def status_action(agi, config, choice, control):
    if choice == '1':
        if not config.get('ha_token'):
            agi.play('not-configured')
        else:
            agi.play('ha-online' if ha_request(config, '/api/')[0] else 'ha-offline')
    elif choice == '2':
        if not config.get('ha_token') or not config.get('ha_entity'):
            agi.play('not-configured')
        else:
            state = entity_state(config, config['ha_entity'])
            agi.play('kitchen-' + state if state in ('on', 'off') else 'state-unknown')
    elif choice == '3':
        homelab_status(agi, control, 'summary')
    else:
        agi.play('invalid-action')


def homelab_status(agi, control, detail):
    result = control('backup' if detail == 'backup' else 'status')
    if not result:
        agi.play('unavailable')
        return
    if detail == 'services':
        for service in ('homeassistant', 'traefik', 'adguardhome'):
            state = result.get(service)
            suffix = state if state in ('running', 'stopped', 'unhealthy') else 'unknown'
            agi.play(service + '-' + suffix)
    elif detail == 'summary':
        states = [result.get(service) for service in ('homeassistant', 'traefik', 'adguardhome')]
        agi.play('services-running' if all(state == 'running' for state in states) else 'services-attention')
    if detail in ('summary', 'backup'):
        agi.play({'recent': 'backup-recent', 'old': 'backup-old'}.get(result.get('backup'), 'backup-unknown'))


class Hangup(Exception):
    pass


class AGI:
    def __init__(self):
        for line in sys.stdin:
            if not line.strip():
                break

    def command(self, command):
        print(command, flush=True)
        response = sys.stdin.readline()
        if not response or response.startswith('HANGUP'):
            raise Hangup()
        match = re.match(r'200 result=([^\s]*)(.*)', response)
        if not match or match[1] == '-1':
            raise Hangup()
        return match[1], match[2]

    def execute(self, application, args):
        return self.command('EXEC ' + application + ' ' + json.dumps(args))[0]

    def play(self, prompt):
        self.execute('Playback', 'custom/' + prompt)

    def read_pin(self):
        # GET DATA returns a digit string (keep leading zeroes), terminated by #.
        return self.command('GET DATA custom/pin 7000 13')[0]

    def option(self, prompt="home-menu"):
        result = self.command('GET OPTION custom/' + prompt + ' "0123456789*#" 7000')[0]
        return chr(int(result)) if result and int(result) > 0 else ''

    def variable(self, name):
        result, rest = self.command('GET VARIABLE ' + name)
        return rest.strip()[1:-1] if result == '1' else ''


def forward(agi, config, who):
    number = config['destinations'].get(who)
    if config['mode'] != 'vodafone' or not number or not config['domain']:
        agi.play('unavailable')
        return False
    agi.play('forward-' + who)
    agi.execute('Set', 'TIMEOUT(absolute)=1835')
    # URI, endpoint and target are fixed by operator configuration, never by DTMF.
    agi.execute('Dial', f"PJSIP/vodafone/sip:{number}@{config['domain']},25,L(1800000)")
    return agi.variable('DIALSTATUS') == 'ANSWER'


def home_menu(agi, config, attempt=reserve_pin_attempt, action=ha_action, control=status_request):
    if not config.get('pin_hash'):
        agi.play('not-configured')
        return
    for _ in range(3):
        if not attempt():
            agi.play('denied')
            return
        entered = agi.read_pin()
        authenticated = verify_pin(config, entered)
        entered = ''
        if authenticated:
            break
        agi.play('denied')
    else:
        return
    # Authentication belongs only to this invocation; returning to public discards it.
    agi.execute('Set', 'TIMEOUT(absolute)=300')
    level = 'home'
    for _ in range(30):
        choice = agi.option(level + '-menu')
        if not choice:
            return
        if choice == '0':
            if level == 'home':
                return
            level = 'home'
            continue
        if level == 'home':
            target = {'1': 'devices', '2': 'status', '3': 'homelab'}.get(choice)
            if target:
                level = target
            else:
                agi.play('invalid-action')
        elif level == 'devices':
            target = {'1': 'kitchen-on', '2': 'kitchen-off'}.get(choice)
            agi.play(action(config, target) if target else 'invalid-action')
        elif level == 'status':
            status_action(agi, config, choice, control)
        elif level == 'homelab':
            detail = {'1': 'services', '2': 'backup'}.get(choice)
            if detail:
                homelab_status(agi, control, detail)
            else:
                agi.play('invalid-action')


def public_menu(agi, config, forward_action=forward, protected=home_menu, attempt=reserve_pin_attempt):
    remaining = 3

    def pin_attempt():
        nonlocal remaining
        if remaining <= 0:
            return False
        remaining -= 1
        return attempt()

    prompt = 'greeting'
    for _ in range(5):
        choice = agi.option(prompt)
        prompt = 'greeting'
        if choice in ('1', '2'):
            if forward_action(agi, config, 'annika' if choice == '1' else 'tobias'):
                return
            agi.execute('Set', 'TIMEOUT(absolute)=120')
            prompt = 'forward-fallback'
        elif choice == '9':
            protected(agi, config, attempt=pin_attempt)
            agi.execute('Set', 'TIMEOUT(absolute)=120')
        elif choice == '0':
            continue
        elif choice:
            prompt = 'invalid'
        else:
            break
    agi.play('goodbye')


def main():
    os.umask(0o077)
    signal.signal(signal.SIGHUP, lambda *_: sys.exit(0))
    agi = AGI()
    try:
        config = json.loads(CONFIG.read_text())
        if sys.argv[1:] in (['forward', 'annika'], ['forward', 'tobias']):
            forward(agi, config, sys.argv[2])
        elif sys.argv[1:] == ['home']:
            home_menu(agi, config)
        elif sys.argv[1:] == ['public']:
            public_menu(agi, config)
    except (Hangup, BrokenPipeError):
        pass
    except Exception:
        # Never log PINs, phone numbers, token, URLs or exception payloads.
        print('IVR menu failed', file=sys.stderr)
        try:
            agi.play('unavailable')
        except (Hangup, BrokenPipeError):
            pass


if __name__ == '__main__':
    main()
