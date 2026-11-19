# Epiphany compositor A/B and Web-process profiling implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Identify whether Flo's slow post-paint loading in WebKitGTK 2.54.2 is caused by the Skia compositor, Web-process computation, or thermal throttling, then apply only a supported measured improvement.

**Architecture:** Reuse the existing `scripts/epiphany-perf.py` and public/local fixtures. Launch each run with a process-local environment, preserve raw reports outside Git, and record graphics and CPU evidence independently. Keep the installed browser profile and system renderer untouched.

**Tech Stack:** Alpine armv7, WebKitGTK 6.0, Epiphany 50.6, WebKitWebDriver/MiniBrowser, Sysprof 51, `/proc` and `/sys` telemetry.

**Spec:** `docs/hw/EPIPHANY-PERF-20261118.md`, especially “Online research, 2026-11-19”.

## Global constraints

- Only run intensive tests when the tablet is reachable and charging or has enough battery for safe completion.
- `WEBKIT_USE_SKIA_FOR_COMPOSITION=0` is scoped to an isolated test process, never installed as a persistent setting.
- Compare the same public URL, local control, session conditions, and five cold/warm samples against the established Skia baseline.
- Do not change GTK `GSK_RENDERER`, CPU governor, site content, browser security settings, or the personal Epiphany profile.
- Keep raw traces and browser reports outside Git; publish aggregate data, versions, exact procedure, and limitations.

## Review focus

- A crashed or stuck test browser must not leave MiniBrowser, WebDriver, or a private profile running.
- A failed network request or missing paint entry must not be counted as a successful fast run.
- An incomplete Sysprof trace must not support an attribution claim.
- Temperature and frequency sensors must be named and timestamped; unknown values must stay unknown.
- A faster TextureMapper result does not by itself justify a permanent switch to a retired compositor.

---

### Task 1: Environment and graphics state

**Files:** Update `docs/hw/EPIPHANY-PERF-20261118.md` with observed versions, renderer, charge state, and the test's device availability.

- [ ] Check Wi-Fi/USB reachability, power status and charge current. Do not run a long test when neither connection nor stable power is present.
- [ ] Refresh `apk` indexes and record the available WebKitGTK and Epiphany package versions. Upgrade WebKitGTK 2.54.3 only if Alpine armv7 packages it, after recording rollback package availability.
- [ ] From an isolated browser process, capture `webkit://gpu/stdout` and identify WebKit renderer, DMA-BUF, GPU/CPU threaded painting, and active compositor. If the page is unsupported by that process, record the failure.
- [ ] Record CPU frequency policy paths and thermal zone names before interpreting their values.

### Task 2: Default Skia versus TextureMapper

**Files:** Update `docs/hw/EPIPHANY-PERF-20261118.md` with aggregate A/B results and exact command environments.

- [ ] Run the existing benchmark first with default Skia and then with `WEBKIT_USE_SKIA_FOR_COMPOSITION=0` in only the test process; use five cold/warm iterations each, identical URL and stable power.
- [ ] During each run, sample CPU current frequency and named thermal zones at fixed intervals, preserving timestamps outside Git.
- [ ] Confirm both runs loaded the expected public page and local control, with no missing FCP/load metrics, no browser crash, and no remaining test process.
- [ ] Compare medians, p90, Web-process CPU and PSS, local control, temperature and frequency. If the difference is within run-to-run variation, record “inconclusive”.

### Task 3: Web-process attribution

**Files:** Update `docs/hw/EPIPHANY-PERF-20261118.md` and the upstream draft if a specific regression is demonstrated.

- [ ] Install Sysprof and matching WebKitGTK debug symbols temporarily if tablet storage and battery allow, without changing WebKit binaries.
- [ ] Attach to the actual Web process during one public navigation. Verify that samples or WebKit marks cover the full navigation interval; discard incomplete captures from conclusions.
- [ ] Attribute CPU to JavaScript/JSC, style/layout, raster/Skia composition, or another named area only if symbols and complete sampling support it.
- [ ] Remove temporary profiling tools/profile after collecting aggregate results; keep the normal Epiphany instance alive.

### Task 4: Decision and publication

**Files:** Update `docs/hw/EPIPHANY-PERF-20261118.md`, `docs/STATUS.md`, and `docs/upstream/webkitgtk-armv7-page-load-draft.md` as evidence warrants.

- [ ] Apply a maintained package update only if available and verify the same benchmark and normal browser interaction. Otherwise preserve the working configuration and state the measured limiting component.
- [ ] Run relevant repository tests only if code changed; always check `git diff --check`, installed package state, browser process state and charge state.
- [ ] Commit findings and push the existing `feat/epiphany-performance` branch to update PR #4. State any device-dependent step that remains unverified.
