"""Checks for the browser benchmark's result interpretation."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "epiphany-perf.py"
spec = importlib.util.spec_from_file_location("epiphany_perf", SCRIPT)
perf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(perf)


class PerformanceResultsTest(unittest.TestCase):
    def test_distinguishes_first_paint_from_later_page_load(self):
        browser = {
            "navigation": {
                "responseStart": 120,
                "domContentLoadedEventEnd": 350,
                "loadEventEnd": 500,
            },
            "paint": [{"name": "first-contentful-paint", "startTime": 200}],
            "ready": True,
        }
        result = perf.extract_metrics(browser, wall_ms=620, interaction_ms=40)
        self.assertEqual(result["post_paint_load_ms"], 300)
        self.assertEqual(result["wall_ms"], 620)
        self.assertEqual(result["interaction_ms"], 40)

    def test_missing_paint_stays_unknown(self):
        browser = {"navigation": {"loadEventEnd": 500}, "paint": [], "ready": True}
        result = perf.extract_metrics(browser, wall_ms=700, interaction_ms=None)
        self.assertIsNone(result["first_contentful_paint_ms"])
        self.assertIsNone(result["post_paint_load_ms"])

    def test_load_before_paint_has_no_post_paint_wait(self):
        browser = {
            "navigation": {"loadEventEnd": 200},
            "paint": [{"name": "first-contentful-paint", "startTime": 260}],
        }
        result = perf.extract_metrics(browser, wall_ms=1000, interaction_ms=30)
        self.assertEqual(result["post_paint_load_ms"], 0)

    def test_frame_latency_uses_browser_clock(self):
        self.assertEqual(perf.frame_latency({"elapsed": 32.5}), 32.5)

    def test_cached_response_start_zero_is_preserved(self):
        browser = {"navigation": {"responseStart": 0, "loadEventEnd": 500}, "paint": []}
        result = perf.extract_metrics(browser, wall_ms=600, interaction_ms=30)
        self.assertEqual(result["response_start_ms"], 0)

    def test_resource_summary_separates_late_fetches_without_storing_urls(self):
        browser = {
            "navigation": {"loadEventEnd": 500},
            "paint": [{"name": "first-contentful-paint", "startTime": 200}],
            "resources": [
                {"startTime": 40, "responseEnd": 120, "duration": 80, "initiatorType": "link"},
                {"startTime": 180, "responseEnd": 460, "duration": 280, "initiatorType": "img"},
                {"startTime": 210, "responseEnd": 490, "duration": 280, "initiatorType": "fetch"},
            ],
        }
        result = perf.extract_metrics(browser, wall_ms=600, interaction_ms=30)
        self.assertEqual(result["resource_count"], 3)
        self.assertEqual(result["resources_after_paint"], 2)
        self.assertEqual(result["resource_last_end_ms"], 490)
        self.assertEqual(result["resource_max_duration_ms"], 280)
        self.assertEqual(result["resource_types"], {"link": 1, "img": 1, "fetch": 1})
        self.assertNotIn("resources", result)

    def test_summary_keeps_cold_and_warm_separate(self):
        samples = [
            {"site": "control", "phase": "cold", "wall_ms": n}
            for n in (100, 120, 130, 140, 200)
        ] + [{"site": "control", "phase": "warm", "wall_ms": 50}]
        summary = perf.summarize(samples)
        self.assertEqual(summary["control"]["cold"]["wall_ms"]["median"], 130)
        self.assertEqual(summary["control"]["cold"]["wall_ms"]["p90"], 200)
        self.assertEqual(summary["control"]["warm"]["wall_ms"]["median"], 50)

    def test_process_cpu_deltas_attribute_web_and_network_processes(self):
        before = {"cpu_by_process": {11: ("MiniBrowser", 20),
                                     12: ("WebKitWebProces", 50)}}
        after = {"cpu_by_process": {11: ("MiniBrowser", 25),
                                    12: ("WebKitWebProces", 80),
                                    13: ("WebKitNetworkPr", 10)}}
        self.assertEqual(perf.process_cpu_delta(before, after, ticks_per_second=100),
                         {"MiniBrowser": 50, "WebKitWebProces": 300,
                          "WebKitNetworkPr": 100})


if __name__ == "__main__":
    unittest.main()
