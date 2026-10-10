import importlib.util
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location("sandbox_lifecycle", Path(__file__).parents[1] / "lifecycle.py")
lifecycle = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lifecycle
spec.loader.exec_module(lifecycle)


class LifecycleTests(unittest.TestCase):
    def test_ready_requires_post_reset_heartbeat(self):
        run = lifecycle.Run()
        for action in lifecycle.SCENARIOS["complete"][:-1]:
            run.advance(action)
        self.assertEqual(run.worker, "reverting")
        self.assertEqual(run.state, "collecting")
        with self.assertRaises(lifecycle.TransitionError):
            run.advance("assign")
        run.advance("heartbeat")
        self.assertEqual((run.state, run.worker), ("completed", "ready"))

    def test_execution_does_not_start_before_worker_ready(self):
        run = lifecycle.Run()
        for action in ["assign", "boot"]:
            run.advance(action)
        with self.assertRaises(lifecycle.TransitionError):
            run.advance("start")

    def test_collection_and_reset_failures_retain_quarantine(self):
        for scenario in ["missing-evidence", "failed-reset"]:
            run = lifecycle.replay(scenario)
            self.assertEqual((run.state, run.worker), ("failed", "quarantined"))
            self.assertGreater(len(run.events), 5)
            with self.assertRaises(lifecycle.TransitionError):
                run.advance("assign")

    def test_stop_still_collects_and_resets(self):
        run = lifecycle.replay("stop")
        self.assertEqual((run.state, run.worker, run.evidence), ("stopped", "ready", "complete"))
        kinds = [event["type"] for event in run.events]
        self.assertLess(kinds.index("run.stop"), kinds.index("worker.reset.completed"))


if __name__ == "__main__":
    unittest.main()
