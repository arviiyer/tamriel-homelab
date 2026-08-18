#!/usr/bin/python3
"""Restricted exact-revision deployment helper for the public example."""

from __future__ import annotations

import copy
import fcntl
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
COMMAND_PATTERN = re.compile(
    r"^(deploy|rollback) (example-api) ([0-9a-f]{40})$"
)
IMAGE_PATTERN = re.compile(
    r"^registry[.]example[.]com/example-api:[A-Za-z0-9._-]+"
    r"@sha256:[0-9a-f]{64}$"
)
COMMAND_ENV = {
    "HOME": "/var/empty",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
}


class DeploymentError(RuntimeError):
    """Raised when a deployment cannot safely continue."""


@dataclass(frozen=True)
class Request:
    operation: str
    service: str
    revision: str


@dataclass(frozen=True)
class State:
    current: str
    previous: str | None


@dataclass(frozen=True)
class PendingTransaction:
    operation: str
    source: str
    target: str


@dataclass(frozen=True)
class Settings:
    service_name: str
    repository_dir: Path
    state_file: Path
    pending_file: Path
    live_compose_file: Path
    repository_compose_path: str
    protected_ref: str
    lock_file: Path
    project_directory: Path
    health_url: str


DEFAULT_SETTINGS = Settings(
    service_name="example-api",
    repository_dir=Path("/var/lib/example-deploy/repositories/apps.git"),
    state_file=Path("/var/lib/example-deploy/state/example-api.json"),
    pending_file=Path("/var/lib/example-deploy/state/example-api.pending.json"),
    live_compose_file=Path("/srv/example-api/compose.yml"),
    repository_compose_path="services/example-api/compose.yml",
    protected_ref="refs/remotes/origin/main",
    lock_file=Path("/run/example-deploy/example-api.lock"),
    project_directory=Path("/srv/example-api"),
    health_url="http://127.0.0.1:8080/health",
)


class Adapter(Protocol):
    def fetch_protected_ref(self) -> None: ...

    def revision_exists(self, revision: str) -> bool: ...

    def is_ancestor(self, ancestor: str, descendant: str) -> bool: ...

    def extract_compose(self, revision: str, destination: Path) -> None: ...

    def render_model(self, compose_file: Path) -> dict[str, object]: ...

    def pull(self, compose_file: Path) -> None: ...

    def apply(self, compose_file: Path) -> None: ...

    def healthy(self) -> bool: ...


def parse_request(command: str) -> Request:
    match = COMMAND_PATTERN.fullmatch(command)
    if match is None:
        raise DeploymentError(
            "allowed commands: deploy|rollback example-api <40-character-main-commit>"
        )
    return Request(*match.groups())


def _validate_revision(value: object, field: str) -> str:
    if not isinstance(value, str) or SHA_PATTERN.fullmatch(value) is None:
        raise DeploymentError(f"invalid {field} revision in deployment state")
    return value


def read_state(path: Path) -> State:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DeploymentError(f"could not read deployment state: {error}") from error
    if not isinstance(payload, dict) or set(payload) != {"current", "previous"}:
        raise DeploymentError("deployment state has an unexpected schema")
    current = _validate_revision(payload["current"], "current")
    previous_value = payload["previous"]
    previous = (
        None
        if previous_value is None
        else _validate_revision(previous_value, "previous")
    )
    if previous == current:
        raise DeploymentError("current and previous revisions must differ")
    return State(current=current, previous=previous)


def read_pending(path: Path) -> PendingTransaction:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DeploymentError(f"could not read pending transaction: {error}") from error
    if not isinstance(payload, dict) or set(payload) != {
        "operation",
        "source",
        "target",
    }:
        raise DeploymentError("pending transaction has an unexpected schema")
    operation = payload["operation"]
    if operation not in {"deploy", "rollback"}:
        raise DeploymentError("invalid pending operation")
    return PendingTransaction(
        operation=operation,
        source=_validate_revision(payload["source"], "pending source"),
        target=_validate_revision(payload["target"], "pending target"),
    )


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def unlink_durable(path: Path) -> None:
    path.unlink(missing_ok=True)
    fsync_directory(path.parent)


def install_file_atomic(source: Path, destination: Path) -> None:
    current = destination.stat()
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        os.chmod(temporary, current.st_mode & 0o777)
        os.chown(temporary, current.st_uid, current.st_gid)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        fsync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)


def validate_candidate_models(
    current: dict[str, object], candidate: dict[str, object], service_name: str
) -> None:
    for name, model in (("current", current), ("candidate", candidate)):
        services = model.get("services")
        if not isinstance(services, dict) or set(services) != {service_name}:
            raise DeploymentError(
                f"{name} model must contain only the allowlisted service"
            )
        service = services[service_name]
        if not isinstance(service, dict):
            raise DeploymentError(f"{name} service model is invalid")
        image = service.get("image")
        if not isinstance(image, str) or IMAGE_PATTERN.fullmatch(image) is None:
            raise DeploymentError(
                f"{name} image must use the allowlisted digest-pinned repository"
            )

    normalized = copy.deepcopy(candidate)
    normalized["services"][service_name]["image"] = current["services"][
        service_name
    ]["image"]
    if normalized != current:
        raise DeploymentError("candidate changes more than the allowlisted image digest")


class SystemAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _git(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/usr/bin/git", f"--git-dir={self.settings.repository_dir}", *arguments],
            check=check,
            capture_output=True,
            text=True,
            timeout=60,
            env=COMMAND_ENV,
        )

    def fetch_protected_ref(self) -> None:
        self._git(
            "fetch",
            "--quiet",
            "--no-tags",
            "--prune",
            "origin",
            f"+refs/heads/main:{self.settings.protected_ref}",
        )

    def revision_exists(self, revision: str) -> bool:
        result = self._git("cat-file", "-e", f"{revision}^{{commit}}", check=False)
        return result.returncode == 0

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        result = self._git(
            "merge-base", "--is-ancestor", ancestor, descendant, check=False
        )
        if result.returncode not in {0, 1}:
            raise DeploymentError("could not evaluate revision ancestry")
        return result.returncode == 0

    def extract_compose(self, revision: str, destination: Path) -> None:
        result = self._git(
            "show", f"{revision}:{self.settings.repository_compose_path}"
        )
        destination.write_text(result.stdout, encoding="utf-8")
        destination.chmod(0o600)

    def _compose(
        self, compose_file: Path, *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "/usr/bin/docker",
                "compose",
                "--project-name",
                self.settings.service_name,
                "--project-directory",
                str(self.settings.project_directory),
                "--file",
                str(compose_file),
                *arguments,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
            env=COMMAND_ENV,
        )

    def render_model(self, compose_file: Path) -> dict[str, object]:
        result = self._compose(compose_file, "config", "--format", "json")
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise DeploymentError("Compose rendered an invalid model")
        return payload

    def pull(self, compose_file: Path) -> None:
        self._compose(compose_file, "pull")

    def apply(self, compose_file: Path) -> None:
        self._compose(compose_file, "up", "--detach", "--pull", "never")

    def healthy(self) -> bool:
        for _ in range(12):
            result = subprocess.run(
                [
                    "/usr/bin/curl",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--max-time",
                    "5",
                    "--output",
                    "/dev/null",
                    self.settings.health_url,
                ],
                check=False,
                timeout=10,
                env=COMMAND_ENV,
            )
            if result.returncode == 0:
                return True
            time.sleep(5)
        return False


class DeploymentController:
    def __init__(self, settings: Settings, adapter: Adapter) -> None:
        self.settings = settings
        self.adapter = adapter

    def _write_state(self, state: State) -> None:
        write_json_atomic(
            self.settings.state_file,
            {"current": state.current, "previous": state.previous},
        )

    def _write_pending(self, transaction: PendingTransaction) -> None:
        write_json_atomic(
            self.settings.pending_file,
            {
                "operation": transaction.operation,
                "source": transaction.source,
                "target": transaction.target,
            },
        )

    def _restore_current(self, current_compose: Path) -> None:
        install_file_atomic(current_compose, self.settings.live_compose_file)
        self.adapter.apply(self.settings.live_compose_file)
        if not self.adapter.healthy():
            raise DeploymentError(
                "automatic recovery failed; pending state retained for operator review"
            )
        unlink_durable(self.settings.pending_file)

    def _recover_interrupted(self, state: State, current_compose: Path) -> None:
        if not self.settings.pending_file.exists():
            return
        pending = read_pending(self.settings.pending_file)
        if state.current == pending.target:
            unlink_durable(self.settings.pending_file)
            return
        if state.current != pending.source:
            raise DeploymentError("pending transaction does not match recorded state")
        self._restore_current(current_compose)

    def _validate_reachable(self, revision: str) -> None:
        if not self.adapter.revision_exists(revision):
            raise DeploymentError("requested revision does not exist")
        if not self.adapter.is_ancestor(revision, self.settings.protected_ref):
            raise DeploymentError("requested revision is not reachable from protected main")

    def run(self, request: Request) -> State:
        if request.service != self.settings.service_name:
            raise DeploymentError("service is not allowlisted")

        state = read_state(self.settings.state_file)
        self.adapter.fetch_protected_ref()
        self._validate_reachable(state.current)

        with tempfile.TemporaryDirectory(prefix="example-deploy-") as temporary_name:
            temporary = Path(temporary_name)
            current_compose = temporary / "current-compose.yml"
            target_compose = temporary / "target-compose.yml"
            self.adapter.extract_compose(state.current, current_compose)
            self._recover_interrupted(state, current_compose)

            if (
                self.settings.live_compose_file.read_bytes()
                != current_compose.read_bytes()
            ):
                raise DeploymentError("live Compose file has drifted from recorded state")

            if request.operation == "deploy":
                target_revision = request.revision
            else:
                if request.revision != state.current:
                    raise DeploymentError(
                        "rollback guard revision does not match current state"
                    )
                if state.previous is None:
                    raise DeploymentError("no previous revision is recorded")
                target_revision = state.previous

            self._validate_reachable(target_revision)
            if request.operation == "deploy" and not self.adapter.is_ancestor(
                state.current, target_revision
            ):
                raise DeploymentError(
                    "deploy target must descend from the recorded current revision"
                )

            self.adapter.extract_compose(target_revision, target_compose)
            validate_candidate_models(
                self.adapter.render_model(current_compose),
                self.adapter.render_model(target_compose),
                self.settings.service_name,
            )

            if target_revision == state.current:
                if not self.adapter.healthy():
                    raise DeploymentError("recorded current revision is unhealthy")
                return state

            self.adapter.pull(target_compose)
            self._write_pending(
                PendingTransaction(
                    operation=request.operation,
                    source=state.current,
                    target=target_revision,
                )
            )

            try:
                install_file_atomic(target_compose, self.settings.live_compose_file)
                self.adapter.apply(self.settings.live_compose_file)
                if not self.adapter.healthy():
                    raise DeploymentError("target revision failed its health check")
            except Exception as error:
                try:
                    self._restore_current(current_compose)
                except Exception as recovery_error:
                    raise DeploymentError(
                        "deployment and automatic recovery both failed; "
                        "operator action is required"
                    ) from recovery_error
                raise DeploymentError(
                    "deployment failed; the recorded current revision was restored"
                ) from error

            new_state = State(current=target_revision, previous=state.current)
            try:
                self._write_state(new_state)
            except Exception as commit_error:
                try:
                    observed_state = read_state(self.settings.state_file)
                except DeploymentError as state_error:
                    raise DeploymentError(
                        "state commit is ambiguous; pending metadata was retained"
                    ) from state_error
                if observed_state == new_state:
                    raise DeploymentError(
                        "state commit durability is ambiguous; pending metadata "
                        "was retained"
                    ) from commit_error
                if observed_state == state:
                    try:
                        self._restore_current(current_compose)
                    except Exception as recovery_error:
                        raise DeploymentError(
                            "state commit and automatic recovery both failed; "
                            "operator action is required"
                        ) from recovery_error
                    raise DeploymentError(
                        "state commit failed; the recorded current revision was restored"
                    ) from commit_error
                raise DeploymentError(
                    "state commit produced unexpected state; pending metadata "
                    "was retained"
                ) from commit_error
            try:
                unlink_durable(self.settings.pending_file)
            except OSError as error:
                print(
                    "restricted-deploy: WARNING: committed state but could not "
                    f"remove pending metadata: {error}",
                    file=sys.stderr,
                )
            return new_state


def assert_root_controlled(path: Path) -> None:
    if path.is_symlink():
        raise DeploymentError(f"required path must not be a symlink: {path}")
    try:
        metadata = path.stat()
    except OSError as error:
        raise DeploymentError(f"required path is unavailable: {path}") from error
    if not (stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode)):
        raise DeploymentError(f"required path has an unsupported type: {path}")
    if metadata.st_uid != 0:
        raise DeploymentError(f"required path is not root-owned: {path}")
    if metadata.st_mode & 0o022:
        raise DeploymentError(f"required path is group- or world-writable: {path}")


def main(arguments: list[str]) -> int:
    if arguments:
        raise DeploymentError("command-line arguments are not accepted")
    if os.geteuid() != 0:
        raise DeploymentError("restricted deployment helper must run as root")

    request = parse_request(os.environ.get("SSH_ORIGINAL_COMMAND", ""))
    for path in (
        Path(__file__).resolve(),
        DEFAULT_SETTINGS.repository_dir,
        DEFAULT_SETTINGS.state_file.parent,
        DEFAULT_SETTINGS.state_file,
        DEFAULT_SETTINGS.live_compose_file,
        DEFAULT_SETTINGS.project_directory,
    ):
        assert_root_controlled(path)
    if DEFAULT_SETTINGS.pending_file.exists():
        assert_root_controlled(DEFAULT_SETTINGS.pending_file)

    DEFAULT_SETTINGS.lock_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert_root_controlled(DEFAULT_SETTINGS.lock_file.parent)
    lock_descriptor = os.open(
        DEFAULT_SETTINGS.lock_file,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_CLOEXEC
        | os.O_NOFOLLOW
        | os.O_NONBLOCK,
        0o600,
    )
    with os.fdopen(lock_descriptor, "w", encoding="utf-8") as lock:
        assert_root_controlled(DEFAULT_SETTINGS.lock_file)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise DeploymentError("another deployment is already running") from error
        state = DeploymentController(
            DEFAULT_SETTINGS,
            SystemAdapter(DEFAULT_SETTINGS),
        ).run(request)
    print(f"{request.operation} succeeded; {state.current} is healthy")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except DeploymentError as error:
        print(f"restricted-deploy: ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except Exception:
        print(
            "restricted-deploy: ERROR: unexpected transaction failure; "
            "inspect pending state",
            file=sys.stderr,
        )
        raise SystemExit(1)
