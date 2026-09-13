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
        self.prompts = []

    def play(self, prompt): self.commands.append(('play', prompt))
    def read_pin(self): return next(self.pins)
    def option(self, prompt="home-menu"):
        self.prompts.append(prompt)
        return next(self.choices)
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
            self.assertIn(('Dial', f'PJSIP/vodafone/sip:{number}@example.invalid,25,L(1800000)'), agi.commands)
        agi = FakeAGI()
        menu.forward(agi, self.config(), '0900123456')
        self.assertEqual(agi.commands, [('play', 'unavailable')])

    def test_local_mode_never_dials_provider(self):
        agi = FakeAGI()
        menu.forward(agi, self.config(ASTERISK_MODE='local'), 'annika')
        self.assertEqual(agi.commands, [('play', 'unavailable')])

    def test_failed_forwarding_has_fallback_prompt(self):
        agi = FakeAGI(status='BUSY')
        self.assertFalse(menu.forward(agi, self.config(), 'annika'))

    def test_wrong_pin_never_calls_home_assistant(self):
        agi = FakeAGI(pins=['000000'] * 3)
        calls = []
        menu.home_menu(agi, self.config(), attempt=lambda: True, action=lambda c, a: calls.append(c))
        self.assertEqual(calls, [])
        self.assertEqual(agi.commands, [('play', 'denied')] * 3)

    def test_missing_pin_or_rate_limit_denies_access(self):
        for config, attempt in ((self.config(ASTERISK_MENU_PIN=''), lambda: True),
                                (self.config(), lambda: False)):
            agi = FakeAGI()
            menu.home_menu(agi, config, attempt=attempt, action=lambda c, a: self.fail('Action bypassed PIN'))
            self.assertEqual(len(agi.commands), 1)

    def test_successful_pin_allows_only_action_one(self):
        agi = FakeAGI(pins=['012345'], choices=['8', '1', '1', '0', '0'])
        calls = []
        menu.home_menu(agi, self.config(), attempt=lambda: True, action=lambda c, a: calls.append((c, a)) or 'action-ok')
        self.assertEqual(len(calls), 1)
        self.assertIn(('play', 'invalid-action'), agi.commands)
        self.assertIn(('play', 'action-ok'), agi.commands)

    def test_failed_action_not_retried(self):
        agi = FakeAGI(pins=['012345'], choices=['1', '1', '0', '0'])
        calls = []
        menu.home_menu(agi, self.config(), attempt=lambda: True, action=lambda c, a: calls.append((c, a)) or 'action-failed')
        self.assertEqual(len(calls), 1)
        self.assertIn(('play', 'action-failed'), agi.commands)

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
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"state":"on"}')
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
            self.assertEqual(menu.ha_action(config, 'kitchen-on'), 'kitchen-on')
            self.assertEqual(requests, [('/api/services/light/turn_on', 'Bearer dummy-test-token',
                                         {'entity_id': 'light.test_kitchen'})])
            Handler.redirect = True
            self.assertEqual(menu.ha_action(config, 'kitchen-on'), 'action-failed')
            self.assertEqual(len(requests), 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


    def test_full_devices_tree_and_back_navigation(self):
        agi = FakeAGI(pins=['012345'], choices=['1', '1', '2', '3', '4', '8', '0', '0'])
        calls = []
        menu.home_menu(agi, self.config(), attempt=lambda: True,
                       action=lambda c, a: calls.append(a) or 'action-ok')
        self.assertEqual(calls, ['kitchen-on', 'kitchen-off'])
        self.assertEqual(agi.prompts[-1], 'home-menu')
        self.assertIn(('play', 'invalid-action'), agi.commands)

    def test_status_tree_is_read_only_and_speaks_only_known_results(self):
        agi = FakeAGI(pins=['012345'], choices=['2', '1', '2', '3', '0', '0'])
        calls = []
        with patch.object(menu, 'ha_request', return_value=(True, {'state': 'off'})) as request:
            menu.home_menu(agi, self.config(), attempt=lambda: True,
                           action=lambda c, a: self.fail('Status must not mutate'),
                           control=lambda a: calls.append(a) or
                           {'homeassistant': 'running', 'traefik': 'stopped', 'adguardhome': 'running', 'backup': 'recent'})
        self.assertEqual(calls, ['status'])
        self.assertTrue(all(len(call.args) == 2 for call in request.call_args_list))
        for prompt in ('ha-online', 'kitchen-off', 'services-attention', 'backup-recent'):
            self.assertIn(('play', prompt), agi.commands)

    def test_homelab_information_works_without_ha_token(self):
        agi = FakeAGI(pins=['012345'], choices=['3', '1', '2', '8', '0', '0'])
        calls = []
        menu.home_menu(agi, self.config(ASTERISK_HA_TOKEN='', ASTERISK_HA_KITCHEN_ENTITY=''),
                       attempt=lambda: True, control=lambda a: calls.append(a) or
                       {'homeassistant': 'running', 'traefik': 'stopped', 'adguardhome': 'unknown', 'backup': 'old'})
        self.assertEqual(calls, ['status', 'backup'])
        for prompt in ('homeassistant-running', 'traefik-stopped', 'adguardhome-unknown', 'backup-old', 'invalid-action'):
            self.assertIn(('play', prompt), agi.commands)

    def test_public_repeat_busy_fallback_and_protected_return(self):
        agi = FakeAGI(choices=['0', '1', '2', '9', ''])
        forwards, homes = [], []
        menu.public_menu(agi, self.config(),
                         forward_action=lambda a, c, who: forwards.append(who) or False,
                         protected=lambda a, c, **kwargs: homes.append(True))
        self.assertEqual(forwards, ['annika', 'tobias'])
        self.assertEqual(homes, [True])
        self.assertEqual(agi.prompts, ['greeting', 'greeting', 'forward-fallback', 'forward-fallback', 'greeting'])
        self.assertEqual(agi.commands[-1], ('play', 'goodbye'))

    def test_new_protected_entry_reauthenticates(self):
        agi = FakeAGI(pins=['012345', '000000', '000000', '000000'], choices=['0'])
        menu.home_menu(agi, self.config(), attempt=lambda: True)
        menu.home_menu(agi, self.config(), attempt=lambda: True,
                       control=lambda a: self.fail('Authentication leaked'))
        self.assertEqual(agi.commands.count(('play', 'denied')), 3)

    def test_only_kitchen_can_be_changed(self):
        with patch.object(menu, 'ha_request') as request:
            for action in ('lights-off', 'arrival', 'unlock', 'restart', 'kitchen-toggle'):
                self.assertEqual(menu.ha_action(self.config(), action), 'invalid-action')
            request.assert_not_called()
        with self.assertRaises(ValueError):
            self.config(ASTERISK_HA_KITCHEN_ENTITY='lock.test_door')

    def test_failed_mutation_never_retried(self):
        with patch.object(menu, 'ha_request', return_value=(False, None)) as request:
            self.assertEqual(menu.ha_action(self.config(), 'kitchen-off'), 'action-failed')
            self.assertEqual(request.call_count, 1)

    def test_accepted_command_does_not_claim_device_changed(self):
        with patch.object(menu, 'ha_request', side_effect=[(True, []), (True, {'state': 'off'})]):
            self.assertEqual(menu.ha_action(self.config(), 'kitchen-on'), 'action-ok')


    def test_pin_attempt_budget_survives_return_to_public_menu(self):
        agi = FakeAGI(pins=['000000'] * 3, choices=['9', '9', ''])
        with patch.object(menu, 'ha_request') as request:
            menu.public_menu(agi, self.config(), attempt=lambda: True)
            request.assert_not_called()
        self.assertEqual(agi.commands.count(('play', 'denied')), 4)

    def test_silence_never_triggers_an_action(self):
        for choices in ([''], ['1', ''], ['2', ''], ['3', '']):
            agi = FakeAGI(pins=['012345'], choices=choices)
            menu.home_menu(agi, self.config(), attempt=lambda: True,
                           action=lambda *a: self.fail('Action on silence'),
                           control=lambda *a: self.fail('Status on silence'))
