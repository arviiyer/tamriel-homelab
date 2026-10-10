#!/usr/bin/env python3
"""Replay a sandbox run with generated events and an in-memory worker."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


class TransitionError(ValueError):
    pass


@dataclass
class Run:
    name: str = "Example URL analysis"
    state: str = "queued"
    worker: str = "ready"
    evidence: str = "not collected"
    outcome: str = "completed"
    reset_done: bool = False
    events: list = field(default_factory=list)

    def record(self, kind, detail):
        self.events.append({"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "type": kind, "detail": detail})

    def advance(self, action):
        if action == "assign" and self.state == "queued" and self.worker == "ready":
            self.state, self.worker = "preparing", "restoring"
            self.record("run.assigned", "Assigned to worker-01; restoring the sample baseline")
        elif action == "boot" and self.state == "preparing" and self.worker == "restoring":
            self.worker = "booting"
            self.record("worker.restored", "Baseline restore reported complete; waiting for an idle heartbeat")
        elif action == "heartbeat" and self.state == "preparing" and self.worker == "booting":
            self.worker = "assigned"
            self.record("worker.heartbeat", "Fresh idle heartbeat from the restored worker instance")
        elif action == "start" and self.state == "preparing" and self.worker == "assigned":
            self.state, self.worker = "running", "running"
            self.record("run.started", "Generated browser task started; no program is executed by this demo")
            self.record("process.created", "Example browser process, PID 1000")
            self.record("dns.query", "example.com, generated event")
        elif action in {"finish", "stop"} and self.state == "running":
            self.state, self.worker = "collecting", "collecting"
            self.outcome = "stopped" if action == "stop" else "completed"
            self.record("run." + action, "Execution ended; collecting the generated evidence manifest")
        elif action in {"collect", "missing-evidence"} and self.state == "collecting" and self.worker == "collecting":
            self.evidence = "complete" if action == "collect" else "partial"
            self.worker = "reverting"
            self.record("evidence." + self.evidence,
                        "Telemetry and screenshot metadata recorded" if action == "collect" else "Required telemetry export missing")
            self.record("worker.reset.started", "Restoring the baseline after the run")
        elif action == "reset-ok" and self.worker == "reverting" and not self.reset_done:
            self.reset_done = True
            self.record("worker.reset.completed", "Restore finished; a fresh idle heartbeat is still required")
        elif action == "heartbeat" and self.worker == "reverting" and self.reset_done:
            self.state = self.outcome if self.evidence == "complete" else "failed"
            self.worker = "ready" if self.evidence == "complete" else "quarantined"
            self.record("worker.heartbeat", "Fresh idle heartbeat after reset")
            self.record("run.finalized", "Worker ready" if self.worker == "ready" else "Partial evidence retained; worker quarantined for review")
        elif action == "reset-failed" and self.worker == "reverting" and not self.reset_done:
            self.state, self.worker = "failed", "quarantined"
            self.record("worker.reset.failed", "Reset failed; worker cannot receive another run")
        else:
            raise TransitionError(f"Cannot {action} while run={self.state}, worker={self.worker}")

    def snapshot(self):
        return asdict(self)


SCENARIOS = {
    "complete": ["assign", "boot", "heartbeat", "start", "finish", "collect", "reset-ok", "heartbeat"],
    "stop": ["assign", "boot", "heartbeat", "start", "stop", "collect", "reset-ok", "heartbeat"],
    "missing-evidence": ["assign", "boot", "heartbeat", "start", "finish", "missing-evidence", "reset-ok", "heartbeat"],
    "failed-reset": ["assign", "boot", "heartbeat", "start", "finish", "collect", "reset-failed"],
}


def replay(scenario):
    run = Run()
    for action in SCENARIOS[scenario]:
        run.advance(action)
    return run


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=SCENARIOS, default="complete", nargs="?")
    args = parser.parse_args()
    print(json.dumps(replay(args.scenario).snapshot(), indent=2))
