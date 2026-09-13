import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("healthcheck", Path(__file__).parents[1] / "healthcheck.py")
healthcheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(healthcheck)


class HealthTests(unittest.TestCase):
    def responses(self, mode="local", status="Registered"):
        responses = ["chan_pjsip.so  PJSIP Channel Driver  0  Running  core\nres_agi.so AGI 0 Running core\napp_dial.so Dial 0 Running core\nbridge_simple.so Bridge 0 Running core",
                     "1. AGI(/usr/local/bin/menu.py,public)",
                     " Endpoint:  " + ("local-test" if mode == "local" else "vodafone") + "  Unavailable  0 of inf"]
        if mode == "vodafone":
            responses.append(" vodafone-registration/sip:example.invalid  vodafone-auth  " + status)
        return responses

    def test_local_endpoint_needs_no_registration(self):
        with patch.object(healthcheck, "cli", side_effect=self.responses()) as cli:
            self.assertTrue(healthcheck.healthy("local"))
            self.assertEqual(cli.call_count, 3)

    def test_vodafone_requires_registered_status(self):
        for status in ("Registered", "Unregistered", "Rejected", "Request Sent"):
            with patch.object(healthcheck, "cli", side_effect=self.responses("vodafone", status)):
                self.assertEqual(healthcheck.healthy("vodafone"), status == "Registered")

    def test_missing_module_is_unhealthy(self):
        with patch.object(healthcheck, "cli", return_value="0 modules loaded"):
            self.assertFalse(healthcheck.healthy("local"))

    def test_cli_timeout_fails_without_exposing_output(self):
        with patch.object(healthcheck, "cli", side_effect=subprocess.TimeoutExpired("asterisk", 2)), patch("builtins.print") as log:
            self.assertEqual(healthcheck.main(), 1)
            log.assert_called_once_with("Asterisk IVR is not ready")


if __name__ == "__main__":
    unittest.main()
