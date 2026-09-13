#!/usr/bin/env python3
"""Fixed phone destinations and PIN-gated local Home Assistant action via AGI."""
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import signal
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


def kitchen_on(config):
    """One fixed action, no caller-provided URL/entity/data and no automatic retry."""
    if not config.get('ha_token') or not config.get('ha_entity'):
        return False
    domain = config['ha_entity'].split('.')[0]
    request = urllib.request.Request(
        config['ha_url'] + '/api/services/' + domain + '/turn_on',
        data=json.dumps({'entity_id': config['ha_entity']}).encode(),
        headers={'Authorization': 'Bearer ' + config['ha_token'], 'Content-Type': 'application/json'},
        method='POST')
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=3) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as error:
        error.close()
        return False
    except (urllib.error.URLError, OSError, ValueError):
        return False


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

    def option(self):
        result = self.command('GET OPTION custom/home-menu "0123456789*#" 7000')[0]
        return chr(int(result)) if result and int(result) > 0 else ''

    def variable(self, name):
        result, rest = self.command('GET VARIABLE ' + name)
        return rest.strip()[1:-1] if result == '1' else ''


def forward(agi, config, who):
    number = config['destinations'].get(who)
    if config['mode'] != 'vodafone' or not number or not config['domain']:
        agi.play('unavailable')
        return
    agi.play('forward-' + who)
    agi.execute('Set', 'TIMEOUT(absolute)=1835')
    # URI, endpoint and target are fixed by operator configuration, never by DTMF.
    agi.execute('Dial', f"PJSIP/vodafone/sip:{number}@{config['domain']},35,L(1800000)")
    if agi.variable('DIALSTATUS') != 'ANSWER':
        agi.play('unavailable')


def home_menu(agi, config, attempt=reserve_pin_attempt, action=kitchen_on):
    if not all(config.get(k) for k in ('pin_hash', 'ha_token', 'ha_entity')):
        agi.play('unavailable')
        return
    authenticated = False
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
    if not authenticated:
        return
    # Authentication is only held in this AGI process, never inherited by other calls.
    for _ in range(5):
        choice = agi.option()
        if choice in ('', '0'):
            return
        if choice == '1':
            agi.play('action-ok' if action(config) else 'action-failed')
        else:
            agi.play('invalid-action')


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
