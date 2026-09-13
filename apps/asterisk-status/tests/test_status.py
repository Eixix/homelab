import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('ivr_status', Path(__file__).parents[1] / 'status.py')
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


def inspection(name, **state):
    return {'Config': {'Labels': {'com.docker.compose.project': 'homelab',
                                  'com.docker.compose.service': status.SERVICES[name]},
                       'Env': ['PRIVATE=must-not-be-returned']},
            'State': {'Running': True, **state}}


class StatusTests(unittest.TestCase):
    def test_only_fixed_read_actions_and_no_sensitive_fields(self):
        calls = []
        broker = status.Broker(inspect=lambda name: calls.append(name) or inspection(name), backup=lambda: 'recent')
        result = broker.dispatch({'action': 'status'})
        self.assertEqual(calls, list(status.SERVICES))
        self.assertEqual(result, {'homeassistant': 'running', 'traefik': 'running',
                                  'adguardhome': 'running', 'backup': 'recent'})
        self.assertNotIn('PRIVATE', json.dumps(result))
        calls.clear()
        for request in ({'action': 'restart-homeassistant'}, {'action': 'restart-service'},
                        {'action': 'exec'}, {'action': 'status', 'container': 'other'}, [],
                        {'action': {'nested': 'status'}}):
            self.assertEqual(broker.dispatch(request), {'result': 'denied'})
        self.assertEqual(calls, [])

    def test_container_states_and_compose_identity(self):
        for state, expected in [({'Running': False}, 'stopped'),
                                ({'Restarting': True}, 'unhealthy'),
                                ({'Health': {'Status': 'unhealthy'}}, 'unhealthy'),
                                ({'Health': {'Status': 'starting'}}, 'unhealthy')]:
            broker = status.Broker(inspect=lambda name: inspection(name, **state))
            self.assertEqual(broker.status('homeassistant'), expected)
        body = inspection('homeassistant')
        body['Config']['Labels']['com.docker.compose.project'] = 'other'
        self.assertEqual(status.Broker(inspect=lambda name: body).status('homeassistant'), 'unknown')
        def failed(name): raise OSError('synthetic daemon failure')
        self.assertEqual(status.Broker(inspect=failed).status('homeassistant'), 'unknown')

    def test_unknown_container_never_reaches_docker(self):
        with patch.object(status, 'DockerConnection') as connection:
            with self.assertRaises(ValueError):
                status.inspect_container('../other')
            connection.assert_not_called()

    def test_backup_missing_recent_old_future_and_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'last-success'
            self.assertEqual(status.backup_status(path, now=100000), 'unknown')
            for value, expected in [('99900', 'recent'), ('100', 'old'), ('200000', 'unknown'),
                                    ('0', 'unknown'), ('invalid', 'unknown')]:
                path.write_text(value)
                self.assertEqual(status.backup_status(path, now=100000), expected)

    def test_private_socket_protocol_bounds_and_no_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'status.sock')
            with status.Server(path, status.Handler) as server:
                server.broker = status.Broker(inspect=inspection, backup=lambda: 'recent')
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    for data, expected in [(b'{"action":"ping"}\n', {'result': 'ok'}),
                                           (b'{"action":"restart-homeassistant"}\n', {'result': 'denied'}),
                                           (b'{"action":"backup"}\n', {'backup': 'recent'}),
                                           (b'x' * 1025 + b'\n', {'result': 'denied'}),
                                           (b'not-json\n', {'result': 'failed'})]:
                        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                            client.settimeout(2)
                            client.connect(path)
                            client.sendall(data)
                            self.assertEqual(json.loads(client.recv(4096)), expected)
                finally:
                    server.shutdown()
                    thread.join()
