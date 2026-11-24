import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "deploy_smoke", Path(__file__).resolve().parents[1] / "scripts/deploy-smoke.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def container(service, status="running", health=None, exit_code=0, oneoff=False):
    state = {"Status": status, "ExitCode": exit_code}
    if health:
        state["Health"] = {"Status": health}
    return {
        "Name": f"/{service}-container",
        "Config": {"Labels": {
            "com.docker.compose.service": service,
            "com.docker.compose.oneoff": str(oneoff),
        }},
        "State": state,
    }


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.services = {
            "web": {"depends_on": {"db": {"condition": "service_started"}}},
            "db": {"depends_on": {"init": {"condition": "service_completed_successfully"}}},
            "init": {},
            "optional": {"profiles": ["agent"]},
        }

    def test_selected_dependencies_and_all_profiles(self):
        self.assertEqual(smoke.expected_services(self.services, ["web"]), {"web", "db", "init"})
        self.assertEqual(smoke.expected_services(self.services, ["all"]), set(self.services))
        with self.assertRaises(RuntimeError):
            smoke.expected_services(self.services, ["typo"])

    def test_ready_and_successful_job(self):
        containers = [container("web", health="healthy"), container("db"), container("init", "exited")]
        self.assertEqual(smoke.failures(self.services, {"web", "db", "init"}, containers), [])

    def test_missing_and_existing_unselected_containers(self):
        broken = smoke.failures(self.services, {"web"}, [container("optional", "restarting")])
        self.assertEqual(broken, ["optional-container (optional): restarting", "web: missing container"])

    def test_unhealthy_starting_exited_paused_and_dead(self):
        for status, health in [("running", "unhealthy"), ("running", "starting"), ("exited", None), ("paused", None), ("dead", None)]:
            with self.subTest(status=status, health=health):
                self.assertTrue(smoke.failures(self.services, {"web"}, [container("web", status, health)]))

    def test_failed_or_unfinished_job(self):
        for status, code in [("exited", 1), ("running", 0)]:
            self.assertTrue(smoke.failures(self.services, {"init"}, [container("init", status, exit_code=code)]))

    def test_oneoff_does_not_replace_service(self):
        self.assertEqual(smoke.failures(self.services, {"web"}, [container("web", "exited", oneoff=True)]), ["web: missing container"])

    def run_poll(self, states, timeout):
        snapshots = iter(states)

        def docker(*args):
            if args[0] == "compose":
                return json.dumps({"services": {"web": {}}})
            if args[0] == "ps":
                return "id"
            return json.dumps([next(snapshots)])

        with patch.object(smoke, "docker", side_effect=docker), patch.object(smoke.time, "sleep"), patch.object(smoke.time, "monotonic", side_effect=range(100)), patch("builtins.print"):
            return smoke.main(["web"], timeout=timeout)

    def test_startup_eventually_recovers(self):
        self.assertEqual(self.run_poll([container("web", health="starting")] + [container("web")] * 3, 10), 0)

    def test_persistent_failure_times_out(self):
        self.assertEqual(self.run_poll([container("web", "restarting")] * 3, 3), 1)

    def test_crash_resets_consecutive_passes(self):
        states = [container("web")] * 2 + [container("web", "restarting")] + [container("web")] * 3
        self.assertEqual(self.run_poll(states, 10), 0)


if __name__ == "__main__":
    unittest.main()
