#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TypeVar


BASELINE_MANIFEST = "_baseline.json"
BASELINE_SCHEMA_VERSION = 1
TRIVY_SCHEMA_VERSION = 2
ALLOWED_ARTIFACT_TYPES = {"filesystem", "repository", "container_image"}
SEVERITY_RANK = {
    "UNKNOWN": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


class ScanDataError(ValueError):
    pass


@dataclass(frozen=True)
class VulnerabilityIdentity:
    repository: str
    image: str
    target: str
    package: str
    package_path: str
    vulnerability_id: str


@dataclass(frozen=True)
class VulnerabilityFinding:
    identity: VulnerabilityIdentity
    severity: str
    installed_version: str
    fixed_version: str


@dataclass(frozen=True)
class MisconfigurationIdentity:
    repository: str
    path: str
    check_id: str
    resource: str


@dataclass(frozen=True)
class MisconfigurationFinding:
    identity: MisconfigurationIdentity
    title: str
    severity: str
    start_line: int


@dataclass(frozen=True)
class SecretIdentity:
    repository: str
    path: str
    rule_id: str
    start_line: int


@dataclass(frozen=True)
class SecretFinding:
    identity: SecretIdentity
    title: str
    severity: str


@dataclass(frozen=True)
class ScanResults:
    vulnerabilities: dict[VulnerabilityIdentity, VulnerabilityFinding]
    misconfigurations: dict[MisconfigurationIdentity, MisconfigurationFinding]
    secrets: dict[SecretIdentity, SecretFinding]


@dataclass(frozen=True)
class VulnerabilityChange:
    finding: VulnerabilityFinding
    change: str


Identity = TypeVar(
    "Identity", VulnerabilityIdentity, MisconfigurationIdentity, SecretIdentity
)
Finding = TypeVar(
    "Finding", VulnerabilityFinding, MisconfigurationFinding, SecretFinding
)


def read_trivy_json(path: Path) -> dict[str, object]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ScanDataError(f"cannot read Trivy JSON {path}: {error}") from error
    if not isinstance(document, dict):
        raise ScanDataError(f"Trivy JSON must be an object: {path}")
    if document.get("SchemaVersion") != TRIVY_SCHEMA_VERSION:
        raise ScanDataError(
            f"unsupported Trivy SchemaVersion in {path}; expected {TRIVY_SCHEMA_VERSION}"
        )
    if normalized_text(document.get("ArtifactName")) == "":
        raise ScanDataError(f"Trivy JSON has no ArtifactName: {path}")
    if document.get("ArtifactType") not in ALLOWED_ARTIFACT_TYPES:
        raise ScanDataError(f"Trivy JSON has an unsupported ArtifactType: {path}")
    if normalized_text(document.get("ReportID")) == "":
        raise ScanDataError(f"Trivy JSON has no ReportID: {path}")
    if "Results" in document and not isinstance(document["Results"], list):
        raise ScanDataError(f"Trivy JSON Results must be a list when present: {path}")
    return document


def result_items(document: dict[str, object], path: Path) -> list[dict[str, object]]:
    results = document.get("Results", [])
    if not isinstance(results, list) or not all(isinstance(item, dict) for item in results):
        raise ScanDataError(f"Results must be a list of objects: {path}")
    return results


def normalized_text(value: object, default: str = "") -> str:
    return value.strip() if isinstance(value, str) else default


def normalized_severity(value: object) -> str:
    severity = normalized_text(value, "UNKNOWN").upper()
    return severity or "UNKNOWN"


def repository_from_filename(path: Path, suffix: str) -> str:
    if not path.name.endswith(suffix):
        raise ScanDataError(f"unexpected scan filename: {path.name}")
    repository = path.name.removesuffix(suffix).split("--", maxsplit=1)[0]
    if not repository:
        raise ScanDataError(f"scan filename has no repository alias: {path.name}")
    return repository


def add_unique(
    findings: dict[Identity, Finding], identity: Identity, finding: Finding, path: Path
) -> None:
    existing = findings.get(identity)
    if existing is not None and existing != finding:
        raise ScanDataError(f"conflicting duplicate finding in {path}: {identity}")
    findings[identity] = finding


def parse_vulnerability_file(
    path: Path,
) -> dict[VulnerabilityIdentity, VulnerabilityFinding]:
    document = read_trivy_json(path)
    if document["ArtifactType"] != "container_image":
        raise ScanDataError(f"vulnerability report must target a container image: {path}")
    repository = repository_from_filename(path, "-vuln.json")
    image = normalized_text(document.get("ArtifactName"))
    if not image:
        raise ScanDataError(f"vulnerability scan has no ArtifactName: {path}")

    findings: dict[VulnerabilityIdentity, VulnerabilityFinding] = {}
    for result in result_items(document, path):
        target = normalized_text(result.get("Target"), "unknown") or "unknown"
        vulnerabilities = result.get("Vulnerabilities", [])
        if vulnerabilities is None:
            continue
        if not isinstance(vulnerabilities, list) or not all(
            isinstance(item, dict) for item in vulnerabilities
        ):
            raise ScanDataError(f"Vulnerabilities must be a list of objects: {path}")

        for vulnerability in vulnerabilities:
            identity = VulnerabilityIdentity(
                repository=repository,
                image=image,
                target=target,
                package=normalized_text(vulnerability.get("PkgName"), "unknown")
                or "unknown",
                package_path=normalized_text(vulnerability.get("PkgPath")),
                vulnerability_id=normalized_text(
                    vulnerability.get("VulnerabilityID"), "unknown"
                )
                or "unknown",
            )
            finding = VulnerabilityFinding(
                identity=identity,
                severity=normalized_severity(vulnerability.get("Severity")),
                installed_version=normalized_text(
                    vulnerability.get("InstalledVersion"), "unknown"
                )
                or "unknown",
                fixed_version=normalized_text(vulnerability.get("FixedVersion")),
            )
            add_unique(findings, identity, finding, path)
    return findings


def parse_misconfiguration_file(
    path: Path,
) -> dict[MisconfigurationIdentity, MisconfigurationFinding]:
    document = read_trivy_json(path)
    if document["ArtifactType"] != "filesystem":
        raise ScanDataError(f"misconfiguration report must target a filesystem: {path}")
    repository = repository_from_filename(path, "-misconfig.json")
    findings: dict[MisconfigurationIdentity, MisconfigurationFinding] = {}

    for result in result_items(document, path):
        target = normalized_text(result.get("Target"), "unknown") or "unknown"
        misconfigurations = result.get("Misconfigurations", [])
        if misconfigurations is None:
            continue
        if not isinstance(misconfigurations, list) or not all(
            isinstance(item, dict) for item in misconfigurations
        ):
            raise ScanDataError(f"Misconfigurations must be a list of objects: {path}")

        for misconfiguration in misconfigurations:
            cause_metadata = misconfiguration.get("CauseMetadata", {})
            if cause_metadata is None:
                cause_metadata = {}
            if not isinstance(cause_metadata, dict):
                raise ScanDataError(f"CauseMetadata must be an object: {path}")
            start_line = cause_metadata.get("StartLine", 0)
            if not isinstance(start_line, int):
                raise ScanDataError(f"CauseMetadata.StartLine must be an integer: {path}")
            check_id = normalized_text(
                misconfiguration.get("ID") or misconfiguration.get("AVDID"), "unknown"
            ) or "unknown"
            identity = MisconfigurationIdentity(
                repository=repository,
                path=target,
                check_id=check_id,
                resource=normalized_text(cause_metadata.get("Resource")),
            )
            finding = MisconfigurationFinding(
                identity=identity,
                title=normalized_text(misconfiguration.get("Title"), "Untitled finding")
                or "Untitled finding",
                severity=normalized_severity(misconfiguration.get("Severity")),
                start_line=start_line,
            )
            add_unique(findings, identity, finding, path)
    return findings


def parse_secret_file(path: Path) -> dict[SecretIdentity, SecretFinding]:
    document = read_trivy_json(path)
    if document["ArtifactType"] != "repository":
        raise ScanDataError(f"secret report must target a repository: {path}")
    repository = repository_from_filename(path, "-secret.json")
    findings: dict[SecretIdentity, SecretFinding] = {}

    for result in result_items(document, path):
        target = normalized_text(result.get("Target"), "unknown") or "unknown"
        secrets = result.get("Secrets", [])
        if secrets is None:
            continue
        if not isinstance(secrets, list) or not all(isinstance(item, dict) for item in secrets):
            raise ScanDataError(f"Secrets must be a list of objects: {path}")

        for secret in secrets:
            start_line = secret.get("StartLine", 0)
            if not isinstance(start_line, int):
                raise ScanDataError(f"secret StartLine must be an integer: {path}")
            identity = SecretIdentity(
                repository=repository,
                path=target,
                rule_id=normalized_text(secret.get("RuleID"), "unknown") or "unknown",
                start_line=start_line,
            )
            finding = SecretFinding(
                identity=identity,
                title=normalized_text(secret.get("Title"), "Untitled finding")
                or "Untitled finding",
                severity=normalized_severity(secret.get("Severity")),
            )
            add_unique(findings, identity, finding, path)
    return findings


def merge_findings(target: dict[Identity, Finding], additions: dict[Identity, Finding]) -> None:
    for identity, finding in additions.items():
        existing = target.get(identity)
        if existing is not None and existing != finding:
            raise ScanDataError(f"conflicting finding across scan files: {identity}")
        target[identity] = finding


def load_scan_directory(scan_dir: Path, repositories: list[str]) -> ScanResults:
    if not scan_dir.is_dir():
        raise ScanDataError(f"scan directory does not exist: {scan_dir}")

    vulnerabilities: dict[VulnerabilityIdentity, VulnerabilityFinding] = {}
    misconfigurations: dict[MisconfigurationIdentity, MisconfigurationFinding] = {}
    secrets: dict[SecretIdentity, SecretFinding] = {}

    for repository in repositories:
        misconfiguration_path = scan_dir / f"{repository}-misconfig.json"
        secret_path = scan_dir / f"{repository}-secret.json"
        if not misconfiguration_path.is_file():
            raise ScanDataError(f"missing misconfiguration result: {misconfiguration_path}")
        if not secret_path.is_file():
            raise ScanDataError(f"missing secret result: {secret_path}")

        merge_findings(
            misconfigurations, parse_misconfiguration_file(misconfiguration_path)
        )
        merge_findings(secrets, parse_secret_file(secret_path))

        for path in sorted(scan_dir.glob(f"{repository}--*-vuln.json")):
            merge_findings(vulnerabilities, parse_vulnerability_file(path))

    return ScanResults(vulnerabilities, misconfigurations, secrets)


def empty_results() -> ScanResults:
    return ScanResults({}, {}, {})


def load_baseline(scan_dir: Path, repositories: list[str]) -> ScanResults:
    manifest_path = scan_dir / BASELINE_MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ScanDataError(f"cannot read baseline manifest {manifest_path}: {error}") from error
    if not isinstance(manifest, dict):
        raise ScanDataError(f"baseline manifest must be an object: {manifest_path}")
    if manifest.get("schema_version") != BASELINE_SCHEMA_VERSION:
        raise ScanDataError(f"unsupported baseline schema in {manifest_path}")
    if manifest.get("repositories") != repositories:
        raise ScanDataError(
            "baseline repository set does not match the current configuration; "
            "archive the old baseline and initialize a new series"
        )
    if not isinstance(manifest.get("completed_at"), int):
        raise ScanDataError(f"baseline manifest has no valid completed_at: {manifest_path}")
    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, dict) or not manifest_files:
        raise ScanDataError(f"baseline manifest has no result-file inventory: {manifest_path}")
    actual_files = sorted(
        path.name
        for path in scan_dir.glob("*.json")
        if path.name != BASELINE_MANIFEST
    )
    if sorted(manifest_files) != actual_files:
        raise ScanDataError(f"baseline result-file inventory mismatch: {scan_dir}")
    for filename, expected_digest in manifest_files.items():
        if not isinstance(filename, str) or not isinstance(expected_digest, str):
            raise ScanDataError(f"baseline manifest file inventory is invalid: {manifest_path}")
        digest = hashlib.sha256((scan_dir / filename).read_bytes()).hexdigest()
        if digest != expected_digest:
            raise ScanDataError(f"baseline result digest mismatch: {scan_dir / filename}")
    return load_scan_directory(scan_dir, repositories)


def write_baseline_manifest(
    path: Path, scan_dir: Path, repositories: list[str], completed_at: int
) -> None:
    result_files = sorted(
        result_path
        for result_path in scan_dir.glob("*.json")
        if result_path.name != BASELINE_MANIFEST
    )
    manifest = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "repositories": repositories,
        "completed_at": completed_at,
        "files": {
            result_path.name: hashlib.sha256(result_path.read_bytes()).hexdigest()
            for result_path in result_files
        },
    }
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def compute_delta(
    current: dict[Identity, Finding], previous: dict[Identity, Finding]
) -> tuple[list[Finding], list[Finding]]:
    new = [current[identity] for identity in current.keys() - previous.keys()]
    fixed = [previous[identity] for identity in previous.keys() - current.keys()]
    return new, fixed


def compute_vulnerability_changes(
    current: dict[VulnerabilityIdentity, VulnerabilityFinding],
    previous: dict[VulnerabilityIdentity, VulnerabilityFinding],
) -> list[VulnerabilityChange]:
    changes: list[VulnerabilityChange] = []
    for identity in current.keys() & previous.keys():
        current_finding = current[identity]
        previous_finding = previous[identity]
        if SEVERITY_RANK.get(current_finding.severity, 0) > SEVERITY_RANK.get(
            previous_finding.severity, 0
        ):
            changes.append(VulnerabilityChange(current_finding, "severity_increased"))
        if current_finding.fixed_version and not previous_finding.fixed_version:
            changes.append(VulnerabilityChange(current_finding, "fix_available"))
    return changes


def escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def append_metric(
    lines: list[str], name: str, labels: dict[str, str], value: int | float
) -> None:
    rendered_labels = ",".join(
        f'{key}="{escape_label(label)}"' for key, label in sorted(labels.items())
    )
    suffix = f"{{{rendered_labels}}}" if rendered_labels else ""
    lines.append(f"{name}{suffix} {value}")


def append_family(lines: list[str], name: str, help_text: str) -> None:
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} gauge")


def count_by(findings: Iterable[Finding], key) -> dict[tuple[str, ...], int]:
    counts: dict[tuple[str, ...], int] = defaultdict(int)
    for finding in findings:
        counts[key(finding)] += 1
    return counts


def build_findings_metrics(
    current: ScanResults,
    previous: ScanResults,
    repositories: list[str],
    scan_time: int,
    has_previous: bool,
    first_run_as_new: bool = False,
) -> str:
    if not has_previous and not first_run_as_new:
        new_vulnerabilities: list[VulnerabilityFinding] = []
        fixed_vulnerabilities: list[VulnerabilityFinding] = []
        new_misconfigurations: list[MisconfigurationFinding] = []
        vulnerability_changes: list[VulnerabilityChange] = []
    else:
        new_vulnerabilities, fixed_vulnerabilities = compute_delta(
            current.vulnerabilities, previous.vulnerabilities
        )
        new_misconfigurations, _ = compute_delta(
            current.misconfigurations, previous.misconfigurations
        )
        vulnerability_changes = compute_vulnerability_changes(
            current.vulnerabilities, previous.vulnerabilities
        )

    lines: list[str] = []

    append_family(
        lines,
        "trivy_vulnerabilities",
        "Current vulnerability findings by repository, image, and severity",
    )
    vulnerability_counts = count_by(
        current.vulnerabilities.values(),
        lambda finding: (
            finding.identity.repository,
            finding.identity.image,
            finding.severity,
        ),
    )
    for (repository, image, severity), count in sorted(vulnerability_counts.items()):
        append_metric(
            lines,
            "trivy_vulnerabilities",
            {"repository": repository, "image": image, "severity": severity},
            count,
        )

    append_family(
        lines,
        "trivy_new_vulnerabilities",
        "New vulnerability findings since the last complete scan",
    )
    new_vulnerability_counts = count_by(
        new_vulnerabilities,
        lambda finding: (
            finding.identity.repository,
            finding.identity.image,
            finding.severity,
            "true" if finding.fixed_version else "false",
        ),
    )
    for (repository, image, severity, has_fix), count in sorted(
        new_vulnerability_counts.items()
    ):
        append_metric(
            lines,
            "trivy_new_vulnerabilities",
            {
                "repository": repository,
                "image": image,
                "severity": severity,
                "has_fix": has_fix,
            },
            count,
        )

    append_family(
        lines,
        "trivy_vulnerability_changes",
        "Security-relevant metadata changes on existing vulnerability findings",
    )
    vulnerability_change_counts = count_by(
        vulnerability_changes,
        lambda change: (
            change.finding.identity.repository,
            change.finding.identity.image,
            change.finding.severity,
            change.change,
        ),
    )
    for (repository, image, severity, change), count in sorted(
        vulnerability_change_counts.items()
    ):
        append_metric(
            lines,
            "trivy_vulnerability_changes",
            {
                "repository": repository,
                "image": image,
                "severity": severity,
                "change": change,
            },
            count,
        )

    append_family(
        lines,
        "trivy_fixed_vulnerabilities",
        "Vulnerability findings absent from the latest complete scan",
    )
    fixed_vulnerability_counts = count_by(
        fixed_vulnerabilities,
        lambda finding: (
            finding.identity.repository,
            finding.identity.image,
            finding.severity,
        ),
    )
    for (repository, image, severity), count in sorted(
        fixed_vulnerability_counts.items()
    ):
        append_metric(
            lines,
            "trivy_fixed_vulnerabilities",
            {"repository": repository, "image": image, "severity": severity},
            count,
        )

    append_family(
        lines,
        "trivy_misconfigurations",
        "Current configuration findings by repository and severity",
    )
    misconfiguration_counts = count_by(
        current.misconfigurations.values(),
        lambda finding: (finding.identity.repository, finding.severity),
    )
    for (repository, severity), count in sorted(misconfiguration_counts.items()):
        append_metric(
            lines,
            "trivy_misconfigurations",
            {"repository": repository, "severity": severity},
            count,
        )

    append_family(
        lines,
        "trivy_new_misconfigurations",
        "New configuration findings since the last complete scan",
    )
    new_misconfiguration_counts = count_by(
        new_misconfigurations,
        lambda finding: (finding.identity.repository, finding.severity),
    )
    for (repository, severity), count in sorted(new_misconfiguration_counts.items()):
        append_metric(
            lines,
            "trivy_new_misconfigurations",
            {"repository": repository, "severity": severity},
            count,
        )

    append_family(
        lines,
        "trivy_secrets",
        "Current secret findings in the checked-out repository tree",
    )
    secret_counts = count_by(
        current.secrets.values(),
        lambda finding: (finding.identity.repository, finding.severity),
    )
    for repository in repositories:
        if not any(key[0] == repository for key in secret_counts):
            append_metric(
                lines,
                "trivy_secrets",
                {"repository": repository, "severity": "NONE"},
                0,
            )
    for (repository, severity), count in sorted(secret_counts.items()):
        append_metric(
            lines,
            "trivy_secrets",
            {"repository": repository, "severity": severity},
            count,
        )

    append_family(
        lines,
        "trivy_scan_last_success_timestamp_seconds",
        "Unix timestamp of the last complete scan published as the baseline",
    )
    append_metric(lines, "trivy_scan_last_success_timestamp_seconds", {}, scan_time)

    return "\n".join(lines) + "\n"


def vulnerability_record(finding: VulnerabilityFinding) -> dict[str, object]:
    return {
        "repository": finding.identity.repository,
        "image": finding.identity.image,
        "target": finding.identity.target,
        "package": finding.identity.package,
        "package_path": finding.identity.package_path,
        "vulnerability_id": finding.identity.vulnerability_id,
        "installed_version": finding.installed_version,
        "fixed_version": finding.fixed_version,
        "severity": finding.severity,
    }


def misconfiguration_record(
    finding: MisconfigurationFinding,
) -> dict[str, object]:
    return {
        "repository": finding.identity.repository,
        "path": finding.identity.path,
        "check_id": finding.identity.check_id,
        "resource": finding.identity.resource,
        "start_line": finding.start_line,
        "title": finding.title,
        "severity": finding.severity,
    }


def build_delta_report(
    current: ScanResults,
    previous: ScanResults,
    has_previous: bool,
    completed_at: int,
    first_run_as_new: bool = False,
) -> dict[str, object]:
    if not has_previous and not first_run_as_new:
        new_vulnerabilities: list[VulnerabilityFinding] = []
        fixed_vulnerabilities: list[VulnerabilityFinding] = []
        new_misconfigurations: list[MisconfigurationFinding] = []
        vulnerability_changes: list[VulnerabilityChange] = []
    else:
        new_vulnerabilities, fixed_vulnerabilities = compute_delta(
            current.vulnerabilities, previous.vulnerabilities
        )
        new_misconfigurations, _ = compute_delta(
            current.misconfigurations, previous.misconfigurations
        )
        vulnerability_changes = compute_vulnerability_changes(
            current.vulnerabilities, previous.vulnerabilities
        )

    return {
        "completed_at": completed_at,
        "baseline_initialized": not has_previous,
        "new_vulnerabilities": [
            vulnerability_record(finding)
            for finding in sorted(
                new_vulnerabilities,
                key=lambda item: (
                    item.identity.repository,
                    item.identity.image,
                    item.identity.vulnerability_id,
                    item.identity.package,
                ),
            )
        ],
        "fixed_vulnerabilities": [
            vulnerability_record(finding)
            for finding in sorted(
                fixed_vulnerabilities,
                key=lambda item: (
                    item.identity.repository,
                    item.identity.image,
                    item.identity.vulnerability_id,
                    item.identity.package,
                ),
            )
        ],
        "vulnerability_changes": [
            vulnerability_record(change.finding) | {"change": change.change}
            for change in sorted(
                vulnerability_changes,
                key=lambda item: (
                    item.finding.identity.repository,
                    item.finding.identity.image,
                    item.finding.identity.vulnerability_id,
                    item.change,
                ),
            )
        ],
        "new_misconfigurations": [
            misconfiguration_record(finding)
            for finding in sorted(
                new_misconfigurations,
                key=lambda item: (
                    item.identity.repository,
                    item.identity.path,
                    item.identity.check_id,
                    item.identity.resource,
                ),
            )
        ],
        "current_secret_count": len(current.secrets),
    }


def parse_repositories(path: Path) -> list[str]:
    repositories: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ScanDataError(f"cannot read repository configuration {path}: {error}") from error

    for line_number, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 3 or not all(field.strip() for field in fields):
            raise ScanDataError(f"{path}:{line_number}: expected three tab-separated fields")
        repository = fields[0].strip()
        if repository in repositories:
            raise ScanDataError(f"{path}:{line_number}: duplicate alias {repository!r}")
        repositories.append(repository)

    if not repositories:
        raise ScanDataError(f"repository configuration is empty: {path}")
    return repositories


def command_report(args: argparse.Namespace) -> int:
    repositories = parse_repositories(args.repositories)
    current = load_scan_directory(args.current_dir, repositories)

    has_previous = not args.initialize_baseline
    previous = load_baseline(args.last_dir, repositories) if has_previous else empty_results()
    metrics = build_findings_metrics(
        current,
        previous,
        repositories,
        args.scan_time,
        has_previous,
        first_run_as_new=args.first_run_as_new,
    )
    args.output.write_text(metrics, encoding="utf-8")
    report = build_delta_report(
        current,
        previous,
        has_previous,
        args.scan_time,
        first_run_as_new=args.first_run_as_new,
    )
    args.report_output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_baseline_manifest(
        args.manifest_output, args.current_dir, repositories, args.scan_time
    )

    print(
        "delta: "
        f"{len(current.vulnerabilities)} vulnerabilities, "
        f"{len(current.misconfigurations)} misconfigurations, "
        f"{len(current.secrets)} secrets"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Trivy JSON, calculate finding deltas, and emit metrics"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Build findings metrics")
    report.add_argument("--current-dir", required=True, type=Path)
    report.add_argument("--last-dir", required=True, type=Path)
    report.add_argument("--repositories", required=True, type=Path)
    report.add_argument("--output", required=True, type=Path)
    report.add_argument("--report-output", required=True, type=Path)
    report.add_argument("--manifest-output", required=True, type=Path)
    report.add_argument("--scan-time", type=int, default=int(time.time()))
    report.add_argument(
        "--initialize-baseline",
        action="store_true",
        help="Establish the first baseline without reading prior state",
    )
    report.add_argument(
        "--first-run-as-new",
        action="store_true",
        help="Emit every finding as new when no previous baseline exists",
    )
    report.set_defaults(handler=command_report)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except ScanDataError as error:
        print(f"delta: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
