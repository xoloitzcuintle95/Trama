import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import json

spec = importlib.util.spec_from_file_location("measure", Path(__file__).resolve().parents[1] / "scripts/measure.py")
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


class MeasurementTests(unittest.TestCase):
    def test_long_recording_only_reads_metadata(self):
        metadata = {"streams": [{"codec_name": "h264"}], "format": {"duration": "600"}}
        with patch.object(measure.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, json.dumps(metadata), "")) as run:
            result = measure.probe_video("long.mkv")
        self.assertEqual(result["video"], metadata)
        self.assertEqual(result["frame_count_status"], "skipped_long_recording")
        self.assertEqual(run.call_count, 1)

    def test_frame_count_timeout_keeps_metadata(self):
        metadata = {"streams": [{"codec_name": "h264"}], "format": {"duration": "35"}}
        with patch.object(measure.subprocess, "run", side_effect=[
            subprocess.CompletedProcess([], 0, json.dumps(metadata), ""),
            subprocess.TimeoutExpired("ffprobe", 60)]):
            result = measure.probe_video("short.mkv")
        self.assertEqual(result["video"], metadata)
        self.assertEqual(result["frame_count_status"], "failed")

    def test_stat_names_with_spaces_and_parentheses(self):
        fields = ["S", "9", "10", "11"] + ["0"] * 20
        fields[11], fields[12], fields[19], fields[21] = "40", "20", "1234", "15"
        p = measure.process_stat("123 (worker (demo)) " + " ".join(fields))
        self.assertEqual((p["pid"], p["ppid"], p["session"], p["ticks"], p["start"]),
                         (123, 9, 11, 60, 1234))

    def test_cpu_reused_pid_and_gpu_counter_regression(self):
        def process(start, ticks):
            return {"start": start, "ticks": ticks, "rss_bytes": 1000,
                    "pss_bytes": None, "fdinfo_errors": 1}
        old, current = {3: process(1, 10000)}, {3: process(2, measure.TICKS)}
        counters = {"i915/0000:00:02.0/4/render": 200}
        row = measure.sample(old, current, counters, {"i915/0000:00:02.0/4": {"render": 100}}, 1)
        self.assertEqual(row["cpu_percent_one_core"], 100)
        self.assertIsNone(row["pss_bytes_sum"])
        self.assertEqual(counters["i915/0000:00:02.0/4/render"], 200)
        row = measure.sample(current, current, counters, {"i915/0000:00:02.0/4": {"render": 300}}, 1)
        self.assertAlmostEqual(row["gpu_engine_core_percent"]["i915/0000:00:02.0/render"], 100 / 1e7)

    def test_drm_descriptor_identity(self):
        value = measure.drm_client("pos: 0\ndrm-driver: i915\ndrm-pdev: 0000:00:02.0\n"
                                   "drm-client-id: 4\ndrm-engine-render: 100 ns\n"
                                   "drm-engine-capacity-render: 2\n")
        self.assertEqual(value, ("i915/0000:00:02.0/4", {"render": 100}))
        self.assertIsNone(measure.drm_client("pos: 0\nflags: 0100000\n"))

    def test_missing_pss_does_not_become_zero(self):
        result = measure.summarize([
            {"interval_seconds": 1, "cpu_percent_one_core": 10, "rss_bytes_sum": 100,
             "pss_bytes_sum": None, "gpu_engine_core_percent": None},
            {"interval_seconds": 2, "cpu_percent_one_core": 40, "rss_bytes_sum": 400,
             "pss_bytes_sum": 200, "gpu_engine_core_percent": None}])
        self.assertEqual(result["cpu_percent_one_core_mean"], 30)
        self.assertIsNone(result["pss_bytes_sum_mean"])
        self.assertEqual(result["gpu"], {})

    def test_real_process_tree_and_graceful_shutdown(self):
        # Controlled CPU worker, not GSR: exercises sampling descendants and SIGINT.
        program = """
import os, signal, sys, time
child = os.fork()
if child == 0:
    while True:
        sum(range(10000))
def stop(*args):
    os.kill(child, signal.SIGTERM)
    os.waitpid(child, 0)
    sys.exit(0)
signal.signal(signal.SIGINT, stop)
while True:
    time.sleep(0.05)
"""
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            video = folder / "fixture.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                            "color=size=32x32:rate=5", "-t", "0.4", str(video)], check=True)
            result = measure.trial("test", [sys.executable, "-c", program, str(video)],
                                   None, folder, 0, 2)
            self.assertTrue(result["completed"], result)
            self.assertEqual(len(result["observed_processes"]), 2)
            self.assertGreater(result["cpu_percent_one_core_mean"], 1)
            self.assertGreater(result["rss_bytes_sum_peak"], 0)
            self.assertIsNotNone(result["video"])
            self.assertTrue((folder / "test.csv").is_file())


if __name__ == "__main__":
    unittest.main()
