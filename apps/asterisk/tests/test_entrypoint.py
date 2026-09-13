import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("entrypoint", Path(__file__).parents[1] / "entrypoint.py")
entrypoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entrypoint)


class ConfigTests(unittest.TestCase):
    def environment(self):
        return dict(ASTERISK_MODE="vodafone", ASTERISK_BIND="192.0.2.10:5060",
                    ASTERISK_REGISTRAR="sip.example.invalid", ASTERISK_SIP_USER="test-user",
                    ASTERISK_SIP_DOMAIN="example.invalid", ASTERISK_AUTH_USERNAME="test-auth",
                    ASTERISK_SIP_PASSWORD="dummy$pass;word", ASTERISK_INBOUND_SBC="192.0.2.20/32")

    def test_vodafone_and_optional_settings(self):
        env = self.environment()
        env.update(ASTERISK_OUTBOUND_PROXY="proxy.example.invalid:5060",
                   ASTERISK_PUBLIC_IP="198.51.100.10", ASTERISK_LOCAL_NET="192.0.2.0/24",
                   ASTERISK_REGISTRATION_EXPIRATION="600")
        with patch.dict(os.environ, env, clear=True):
            config = entrypoint.render()
        self.assertIn("password = dummy$pass\\;word\n", config)
        self.assertEqual(config.count("outbound_proxy = sip:proxy.example.invalid:5060\\;lr"), 2)
        self.assertIn("external_media_address = 198.51.100.10", config)
        self.assertIn("contact_user = ivr", config)
        self.assertIn("expiration = 600\n", config)
        self.assertIn("dtmf_mode = auto\n", config)

    def test_dtmf_modes(self):
        for mode in ("auto", "auto_info", "rfc4733", "inband", "info"):
            with patch.dict(os.environ, self.environment() | {"ASTERISK_DTMF_MODE": mode}, clear=True):
                self.assertIn("dtmf_mode = " + mode + "\n", entrypoint.render())
        with patch.dict(os.environ, self.environment() | {"ASTERISK_DTMF_MODE": "invalid"}, clear=True):
            with self.assertRaises(ValueError):
                entrypoint.render()

    def test_invalid_registration_expiration_rejected(self):
        for value in ("0", "86401", "invalid"):
            env = self.environment() | {"ASTERISK_REGISTRATION_EXPIRATION": value}
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError):
                    entrypoint.render()

    def test_missing_secret_does_not_leak_values(self):
        env = self.environment()
        del env["ASTERISK_SIP_PASSWORD"]
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ValueError, "^ASTERISK_SIP_PASSWORD must be configured$"):
                entrypoint.render()

    def test_config_injection_and_ambiguous_escapes_rejected(self):
        for value in ("dummy\n[evil]", "dummy\rtest", "dummy\\test"):
            env = self.environment()
            env["ASTERISK_SIP_PASSWORD"] = value
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError) as error:
                    entrypoint.render()
                self.assertNotIn(value, str(error.exception))

    def test_local_mode_does_not_register(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "read_text", return_value="local-only"):
            self.assertEqual(entrypoint.render(), "local-only")

    def test_catchall_and_unknown_mode_rejected(self):
        for override in ({"ASTERISK_INBOUND_SBC": "0.0.0.0/0"}, {"ASTERISK_MODE": "typo"}):
            env = self.environment() | override
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError):
                    entrypoint.render()


if __name__ == "__main__":
    unittest.main()
