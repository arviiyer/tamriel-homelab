from __future__ import annotations

import configparser
import re
import shlex
import unittest
from pathlib import Path


UNIT_PATH = (
    Path(__file__).resolve().parents[1]
    / "systemd"
    / "example-storage-dependent.service"
)
MARKER_PATH = UNIT_PATH.parent / "shared-bulk-data.marker"


def load_unit() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    with UNIT_PATH.open(encoding="utf-8") as handle:
        parser.read_file(handle)
    return parser


class StorageDependencyPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit = load_unit()

    def test_requires_network_readiness_and_the_exact_storage_mount(self) -> None:
        unit = self.unit["Unit"]
        self.assertEqual(["network-online.target"], shlex.split(unit["Wants"]))
        self.assertEqual(["network-online.target"], shlex.split(unit["After"]))
        self.assertEqual("/srv/example-data", unit["RequiresMountsFor"])
        self.assertEqual("/srv/example-data", unit["AssertPathIsMountPoint"])
        self.assertEqual("/srv/example-data", unit["AssertPathIsReadWrite"])

    def test_validates_the_shared_bulk_boundary_marker_without_a_shell_or_poll(self) -> None:
        service = self.unit["Service"]
        prestart = shlex.split(service["ExecStartPre"])
        self.assertEqual(
            [
                "/usr/bin/cmp",
                "--silent",
                "/usr/local/share/example-storage-boundary",
                "/srv/example-data/.storage-boundary",
            ],
            prestart,
        )
        self.assertEqual(b"shared-bulk-data\n", MARKER_PATH.read_bytes())
        self.assertEqual(["/usr/bin/true"], shlex.split(service["ExecStart"]))
        self.assertTrue(prestart[0].startswith("/"))
        self.assertTrue(shlex.split(service["ExecStart"])[0].startswith("/"))

        prohibited = re.compile(
            r"(^|/)(ba|da|z)?sh$|(^|/)(mount|umount|curl|wget|nc|ncat|ping|sleep)$"
        )
        self.assertFalse(any(prohibited.search(token) for token in prestart))
        self.assertNotIn("-c", prestart)

    def test_applies_the_required_service_hardening(self) -> None:
        service = self.unit["Service"]
        required = {
            "DynamicUser": "yes",
            "UMask": "0027",
            "NoNewPrivileges": "yes",
            "CapabilityBoundingSet": "",
            "AmbientCapabilities": "",
            "PrivateTmp": "yes",
            "PrivateDevices": "yes",
            "ProtectSystem": "strict",
            "ProtectHome": "yes",
            "ProtectHostname": "yes",
            "ProtectKernelTunables": "yes",
            "ProtectKernelModules": "yes",
            "ProtectKernelLogs": "yes",
            "ProtectControlGroups": "yes",
            "ProtectProc": "invisible",
            "ProcSubset": "pid",
            "RestrictSUIDSGID": "yes",
            "RestrictRealtime": "yes",
            "RestrictNamespaces": "yes",
            "LockPersonality": "yes",
            "MemoryDenyWriteExecute": "yes",
            "RemoveIPC": "yes",
            "SystemCallArchitectures": "native",
            "SystemCallFilter": "@system-service",
            "SystemCallErrorNumber": "EPERM",
            "ReadWritePaths": "/srv/example-data",
        }
        for directive, expected in required.items():
            with self.subTest(directive=directive):
                self.assertIn(directive, service)
                self.assertEqual(expected, service[directive])


if __name__ == "__main__":
    unittest.main()
