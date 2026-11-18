#!/usr/bin/env python3
"""Measure WebKitGTK page loading on Flo without using the personal profile.

Run as the logged-in tablet user, with its Wayland and D-Bus environment:
    epiphany-perf.py --out /var/tmp/epiphany-perf.json

WebKitWebDriver launches its bundled MiniBrowser in an ephemeral automation
session. Epiphany 50.6 aborts in automation mode on Flo; this measures its
WebKitGTK engine, while normal Epiphany must be inspected separately.
"""

import argparse
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import socket
import statistics
import subprocess
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


PUBLIC_URL = "https://github.com/topics/linux"
CONTROL_HTML = b"""<!doctype html><html><head><meta charset=utf-8>
<title>Flo WebKit control</title><style>
body{font:18px sans-serif;max-width:50rem;margin:auto}
article{padding:1rem;border-bottom:1px solid #ccc}
</style></head><body><main><h1>Flo WebKit control</h1>
<button id=ready type=button>Ready</button>
""" + b"<article>Stable local content for page-load timing.</article>" * 100 + b"</main></body></html>"

PERFORMANCE_JS = """const n=performance.getEntriesByType('navigation')[0];
return {
 navigation:n ? {responseStart:n.responseStart,
  domContentLoadedEventEnd:n.domContentLoadedEventEnd,
  loadEventEnd:n.loadEventEnd} : {},
 paint:performance.getEntriesByType('paint').map(p=>({name:p.name,startTime:p.startTime})),
 resources:performance.getEntriesByType('resource').map(r=>({
  startTime:r.startTime,responseEnd:r.responseEnd,duration:r.duration,
  initiatorType:r.initiatorType})),
 ready:!!document.querySelector(arguments[0]),
 title:document.title, url:location.href
};"""
FRAME_JS = """const done=arguments[arguments.length-1]; const start=performance.now();
requestAnimationFrame(()=>requestAnimationFrame(()=>done({elapsed:performance.now()-start})));"""


def extract_metrics(browser, wall_ms, interaction_ms):
    nav = browser.get("navigation") or {}
    paint = next((item.get("startTime") for item in browser.get("paint", [])
                  if item.get("name") == "first-contentful-paint"), None)
    load = nav.get("loadEventEnd") or None
    resources = browser.get("resources") or []
    types = {}
    for entry in resources:
        kind = entry.get("initiatorType") or "other"
        types[kind] = types.get(kind, 0) + 1
    return {
        "response_start_ms": nav.get("responseStart"),
        "dom_content_loaded_ms": nav.get("domContentLoadedEventEnd") or None,
        "load_ms": load,
        "first_contentful_paint_ms": paint,
        "post_paint_load_ms": round(max(0, load - paint), 2) if load is not None and paint is not None else None,
        "resource_count": len(resources),
        "resources_after_paint": sum(1 for entry in resources
                                     if paint is not None and entry.get("responseEnd", 0) > paint),
        "resource_last_end_ms": max((entry.get("responseEnd", 0) for entry in resources), default=None),
        "resource_max_duration_ms": max((entry.get("duration", 0) for entry in resources), default=None),
        "resource_types": types,
        "wall_ms": round(wall_ms, 2),
        "interaction_ms": round(interaction_ms, 2) if interaction_ms is not None else None,
        "title": browser.get("title"),
        "url": browser.get("url"),
    }


def frame_latency(browser_result):
    elapsed = browser_result.get("elapsed") if isinstance(browser_result, dict) else None
    return elapsed if isinstance(elapsed, (int, float)) and elapsed >= 0 else None


def summarize(samples):
    grouped = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        grouped[sample["site"]][sample["phase"]].append(sample)
    result = {}
    for site, phases in grouped.items():
        result[site] = {}
        for phase, rows in phases.items():
            stats = {"count": len(rows)}
            for key in ("wall_ms", "first_contentful_paint_ms", "post_paint_load_ms",
                        "interaction_ms", "cpu_ms", "pss_kb"):
                values = sorted(row[key] for row in rows if row.get(key) is not None)
                if values:
                    stats[key] = {
                        "median": statistics.median(values),
                        "p90": values[math.ceil(.9 * len(values)) - 1],
                    }
            result[site][phase] = stats
    return result


class ControlHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(CONTROL_HTML)))
        self.end_headers()
        self.wfile.write(CONTROL_HTML)

    def log_message(self, *_args):
        pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class WebDriver:
    def __init__(self):
        self.port = free_port()
        self.process = subprocess.Popen(
            ["WebKitWebDriver-6.0", "--host=local", f"--port={self.port}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if self.request("GET", "/status")["ready"]:
                    return
            except (OSError, RuntimeError):
                time.sleep(.1)
        self.close()
        raise RuntimeError("WebKitWebDriver did not become ready")

    def request(self, method, path, data=None, timeout=45):
        body = json.dumps(data).encode() if data is not None else None
        req = Request(f"http://127.0.0.1:{self.port}{path}", data=body,
                      headers={"Content-Type": "application/json"}, method=method)
        try:
            with urlopen(req, timeout=timeout) as response:
                payload = json.load(response)
        except HTTPError as exc:
            payload = json.load(exc)
        value = payload.get("value")
        if isinstance(value, dict) and value.get("error"):
            raise RuntimeError(f"WebDriver {value['error']}: {value.get('message', '')}")
        return value

    def session(self):
        return self.request("POST", "/session", {"capabilities": {
            "alwaysMatch": {"pageLoadStrategy": "eager"}}}, timeout=30)

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)


def process_snapshot(main_pid):
    """Sum CPU jiffies and proportional memory of the browser process tree."""
    processes = {}
    for path in Path("/proc").glob("[0-9]*"):
        try:
            stat = (path / "stat").read_text()
            fields = stat[stat.rfind(")") + 2:].split()
            processes[int(path.name)] = (int(fields[1]), int(fields[11]) + int(fields[12]))
        except (OSError, ValueError, IndexError):
            continue
    family = {main_pid}
    while True:
        children = {pid for pid, (parent, _) in processes.items() if parent in family}
        if children <= family:
            break
        family |= children
    cpu = sum(processes[pid][1] for pid in family if pid in processes)
    pss = 0
    cpu_by_process = {}
    for pid in family:
        try:
            cpu_by_process[pid] = ((Path("/proc") / str(pid) / "comm").read_text().strip(),
                                   processes[pid][1])
            for line in (Path("/proc") / str(pid) / "smaps_rollup").read_text().splitlines():
                if line.startswith("Pss:"):
                    pss += int(line.split()[1])
                    break
        except (OSError, ValueError):
            pass
    return {"cpu_jiffies": cpu, "pss_kb": pss, "processes": len(family),
            "cpu_by_process": cpu_by_process}


def process_cpu_delta(before, after, ticks_per_second):
    totals = defaultdict(float)
    for pid, (name, ticks) in after["cpu_by_process"].items():
        prior = before["cpu_by_process"].get(pid)
        initial = prior[1] if prior and prior[0] == name else 0
        totals[name] += max(0, ticks - initial) * 1000 / ticks_per_second
    return {name: round(value, 2) for name, value in totals.items()}


def curl_timing(url):
    fmt = "dns=%{time_namelookup} tls=%{time_appconnect} first=%{time_starttransfer} total=%{time_total} code=%{http_code}"
    result = subprocess.run(["curl", "--silent", "--show-error", "--location",
                             "--output", "/dev/null", "--max-time", "20",
                             "--write-out", fmt, url],
                            capture_output=True, text=True, timeout=25)
    return {"exit": result.returncode, "timings": result.stdout.strip(),
            "error": result.stderr.strip()[:200]}


def navigate(driver, session_id, url, selector, main_pid, deadline_seconds):
    prefix = f"/session/{session_id}"
    before = process_snapshot(main_pid)
    start = time.monotonic()
    driver.request("POST", prefix + "/url", {"url": url}, timeout=deadline_seconds)
    end = start + deadline_seconds
    browser = {}
    while time.monotonic() < end:
        browser = driver.request("POST", prefix + "/execute/sync",
                                 {"script": PERFORMANCE_JS, "args": [selector]})
        if browser.get("ready") and (browser.get("navigation") or {}).get("loadEventEnd", 0) > 0:
            break
        time.sleep(.1)
    else:
        raise TimeoutError(f"Page did not reach load event and {selector}: {url}")
    wall_ms = (time.monotonic() - start) * 1000
    frame_result = driver.request("POST", prefix + "/execute/async",
                                  {"script": FRAME_JS, "args": []}, timeout=10)
    interaction_ms = frame_latency(frame_result)
    after = process_snapshot(main_pid)
    metrics = extract_metrics(browser, wall_ms, interaction_ms)
    metrics.update({
        "cpu_ms": round(max(0, after["cpu_jiffies"] - before["cpu_jiffies"])
                        * 1000 / os.sysconf("SC_CLK_TCK"), 2),
        "pss_kb": after["pss_kb"],
        "processes": after["processes"],
        "cpu_by_process_ms": process_cpu_delta(before, after, os.sysconf("SC_CLK_TCK")),
        "memory_pressure": Path("/proc/pressure/memory").read_text().splitlines()[0],
    })
    return metrics


def run(args):
    control = ThreadingHTTPServer(("127.0.0.1", 0), ControlHandler)
    thread = threading.Thread(target=control.serve_forever, daemon=True)
    thread.start()
    sites = [("control", f"http://127.0.0.1:{control.server_port}/", "#ready")]
    if not args.control_only:
        sites.append(("public", args.url, "main"))
    report = {"tool": "WebKitWebDriver-6.0/MiniBrowser", "epiphany_automation": "SIGABRT on Flo 50.6",
              "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "network": {name: curl_timing(url) for name, url, _ in sites},
              "samples": []}
    driver = None
    try:
        driver = WebDriver()
        for name, url, selector in sites:
            for iteration in range(args.runs):
                session = driver.session()
                sid = session["sessionId"]
                pid = session["capabilities"]["webkit:processID"]
                try:
                    for phase in ("cold", "warm"):
                        if phase == "warm":
                            driver.request("POST", f"/session/{sid}/url", {"url": "about:blank"})
                        sample = {"site": name, "phase": phase, "iteration": iteration + 1}
                        sample.update(navigate(driver, sid, url, selector, pid, args.timeout))
                        report["samples"].append(sample)
                        print(f"{name} {phase} {iteration + 1}/{args.runs}: "
                              f"wall={sample['wall_ms']} ms post-paint={sample['post_paint_load_ms']} ms",
                              flush=True)
                finally:
                    driver.request("DELETE", f"/session/{sid}", timeout=10)
        report["summary"] = summarize(report["samples"])
    finally:
        if driver is not None:
            driver.close()
        control.shutdown()
        control.server_close()
        if args.out:
            Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--url", default=PUBLIC_URL)
    parser.add_argument("--out", help="JSON report path")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args()
    if args.runs < 1 or args.timeout < 5:
        parser.error("runs must be positive and timeout must be at least 5 seconds")
    report = run(args)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
