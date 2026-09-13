import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
import unittest
from unittest.mock import patch
from urllib.parse import urlunsplit

spec = importlib.util.spec_from_file_location('menu', Path(__file__).parents[1] / 'menu.py')
menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menu)


class FakeAGI:
    def __init__(self, pins=(), choices=(), status='ANSWER'):
        self.pins = iter(pins)
        self.choices = iter(choices)
        self.status = status
        self.commands = []

    def play(self, prompt): self.commands.append(('play', prompt))
    def read_pin(self): return next(self.pins)
    def option(self): return next(self.choices)
    def execute(self, app, args): self.commands.append((app, args))
    def variable(self, name): return self.status


class MenuTests(unittest.TestCase):
    def config(self, **overrides):
        env = dict(ASTERISK_MODE='vodafone', ASTERISK_SIP_DOMAIN='example.invalid',
                   ASTERISK_ANNIKA_NUMBER='+4915112345678', ASTERISK_TOBIAS_NUMBER='+4915112345679',
                   ASTERISK_MENU_PIN='012345', ASTERISK_HA_TOKEN='dummy-test-token',
                   ASTERISK_HA_KITCHEN_ENTITY='light.test_kitchen')
        env.update(overrides)
        with patch.dict(os.environ, env, clear=True): return menu.build_config()

    def test_pin_is_hashed_and_leading_zero_preserved(self):
        config = self.config()
        self.assertNotIn('012345', json.dumps(config))
        self.assertTrue(menu.verify_pin(config, '012345'))
        self.assertFalse(menu.verify_pin(config, '12345'))
        self.assertFalse(menu.verify_pin(config, '000000'))

    def test_configuration_rejects_dial_and_http_injection(self):
        # Synthetic userinfo fixture: construct it as URL components so secret
        # scanners do not mistake the rejection test for a live credential URI.
        credential_url = urlunsplit(('http', 'user:password@localhost:8123', '', '', ''))
        for key, value in (('ASTERISK_ANNIKA_NUMBER', '+49123&evil'),
                           ('ASTERISK_SIP_DOMAIN', 'host/evil'),
                           ('ASTERISK_MENU_PIN', 'abcd'),
                           ('ASTERISK_HA_URL', credential_url),
                           ('ASTERISK_HA_KITCHEN_ENTITY', 'light.kitchen,light.other')):
            with self.assertRaises(ValueError): self.config(**{key: value})

    def test_only_fixed_targets_can_be_dialed(self):
        for who, number in (('annika', '+4915112345678'), ('tobias', '+4915112345679')):
            agi = FakeAGI()
            menu.forward(agi, self.config(), who)
            self.assertIn(('Dial', f'PJSIP/vodafone/sip:{number}@example.invalid,35,L(1800000)'), agi.commands)
        agi = FakeAGI()
        menu.forward(agi, self.config(), '0900123456')
        self.assertEqual(agi.commands, [('play', 'unavailable')])

    def test_local_mode_never_dials_provider(self):
        agi = FakeAGI()
        menu.forward(agi, self.config(ASTERISK_MODE='local'), 'annika')
        self.assertEqual(agi.commands, [('play', 'unavailable')])

    def test_failed_forwarding_has_fallback_prompt(self):
        agi = FakeAGI(status='BUSY')
        menu.forward(agi, self.config(), 'annika')
        self.assertEqual(agi.commands[-1], ('play', 'unavailable'))

    def test_wrong_pin_never_calls_home_assistant(self):
        agi = FakeAGI(pins=['000000'] * 3)
        calls = []
        menu.home_menu(agi, self.config(), attempt=lambda: True, action=lambda c: calls.append(c))
        self.assertEqual(calls, [])
        self.assertEqual(agi.commands, [('play', 'denied')] * 3)

    def test_missing_pin_or_rate_limit_denies_access(self):
        for config, attempt in ((self.config(ASTERISK_MENU_PIN=''), lambda: True),
                                (self.config(), lambda: False)):
            agi = FakeAGI()
            menu.home_menu(agi, config, attempt=attempt, action=lambda c: self.fail('Action bypassed PIN'))
            self.assertEqual(len(agi.commands), 1)

    def test_successful_pin_allows_only_action_one(self):
        agi = FakeAGI(pins=['012345'], choices=['8', '1', '0'])
        calls = []
        menu.home_menu(agi, self.config(), attempt=lambda: True, action=lambda c: calls.append(c) or True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(agi.commands, [('play', 'invalid-action'), ('play', 'action-ok')])

    def test_failed_action_not_retried(self):
        agi = FakeAGI(pins=['012345'], choices=['1', '0'])
        calls = []
        menu.home_menu(agi, self.config(), attempt=lambda: True, action=lambda c: calls.append(c) or False)
        self.assertEqual(len(calls), 1)
        self.assertEqual(agi.commands, [('play', 'action-failed')])

    def test_rate_limit_survives_new_call_and_expires(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'attempts.json'
            for _ in range(10): self.assertTrue(menu.reserve_pin_attempt(path, now=1000))
            self.assertFalse(menu.reserve_pin_attempt(path, now=1001))
            self.assertTrue(menu.reserve_pin_attempt(path, now=1301))

    def test_parallel_calls_share_the_rate_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'attempts.json'
            with ThreadPoolExecutor(max_workers=8) as pool:
                allowed = list(pool.map(lambda _: menu.reserve_pin_attempt(path, now=1000), range(20)))
            self.assertEqual(sum(allowed), 10)

    def test_agi_pin_response_keeps_zeroes(self):
        with patch('sys.stdin', io.StringIO('\n200 result=012345\n')), patch('sys.stdout', io.StringIO()) as out:
            self.assertEqual(menu.AGI().read_pin(), '012345')
            self.assertNotIn('012345', out.getvalue())

    def test_http_body_token_and_no_redirect(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            redirect = False
            def do_POST(self):
                requests.append((self.path, self.headers.get('Authorization'),
                                 json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(302 if self.redirect else 200)
                if self.redirect: self.send_header('Location', '/unexpected')
                self.end_headers()
                self.wfile.write(b'[]')
            def log_message(self, *args): pass
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            config = self.config(ASTERISK_HA_URL=f'http://127.0.0.1:{server.server_port}')
            self.assertTrue(menu.kitchen_on(config))
            self.assertEqual(requests, [('/api/services/light/turn_on', 'Bearer dummy-test-token',
                                         {'entity_id': 'light.test_kitchen'})])
            Handler.redirect = True
            self.assertFalse(menu.kitchen_on(config))
            self.assertEqual(len(requests), 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
