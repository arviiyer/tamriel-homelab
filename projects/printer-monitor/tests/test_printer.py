import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location("printer", Path(__file__).parents[1] / "printer_monitor.py")
printer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(printer)


class PrinterTests(unittest.TestCase):
    def test_unknown_levels_are_not_empty_cartridges(self):
        result = printer.supplies({"marker-names": ["Black", "Color", "Toner"],
                                   "marker-levels": [-1, "unknown"], "marker-low-levels": [10]})
        self.assertEqual([x["level"] for x in result], [None, None, None])
        self.assertEqual(printer.supplies({"marker-names": "Black", "marker-levels": 45})[0]["level"], 45)

    def test_offline_device_still_shows_only_selected_queue(self):
        class Queue:
            def getPrinterAttributes(self, name):
                return {}

            def getJobs(self, **kwargs):
                return {1: {"job-printer-uri": "ipp://localhost/printers/printer", "job-name": "Example document"},
                        2: {"job-printer-uri": "ipp://localhost/printers/other", "job-name": "Other document"},
                        3: {"job-name": "Unknown queue"}}

        def connect(**kwargs):
            if kwargs:
                raise RuntimeError("Printer disconnected")
            return Queue()

        result = printer.snapshot({"queue": "printer", "device_uri": "ipp://localhost:60000/ipp/print"},
                                  SimpleNamespace(Connection=connect, IPPError=OSError))
        self.assertFalse(result["online"])
        self.assertTrue(result["queue_available"])
        self.assertEqual([j["id"] for j in result["jobs"]], [1])

    def test_config_rejects_secret_bearing_uri(self):
        from tempfile import TemporaryDirectory
        import json
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"queue": "printer", "device_uri": "ipp://user:password@localhost/ipp/print"}))
            with self.assertRaises(ValueError):
                printer.settings(path)


if __name__ == "__main__":
    unittest.main()
