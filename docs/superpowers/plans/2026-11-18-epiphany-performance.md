# Epiphany performance implementation plan

**Goal:** Measure and improve the delay between first paint and usable interaction on complex public pages on Flo, without changing the user's browser profile or site behavior.

**Baseline:** Epiphany 50.6, WebKitGTK 2.54.2, armv7, GTK Cairo renderer. Alpine does not yet package WebKitGTK 2.54.3. Use the distribution package when it appears; do not maintain a local WebKit build.

## Task 1: Repeatable measurement

- Add a Python standard-library WebDriver client and local static control fixture under `scripts/`, using WebKitGTK MiniBrowser in its ephemeral automation session and a loopback-only driver. Epiphany 50.6 currently aborts in its own automation mode; sample its normal process separately without touching its profile.
- Record cold and warm navigation timings, first paint when available, page-ready interaction latency, process CPU/PSS, pressure, and matching curl DNS/TLS/TTFB. Never read the user's browser history or cookies.
- Write parser/aggregation tests first and observe them fail, then implement. Run `python3 -m unittest discover -s tests` (all relevant Python tests) and `python3 -m py_compile scripts/epiphany-perf.py`.

## Task 2: Baseline and attribution

- Run five cold and five warm navigations of a local fixed page and `https://github.com/topics/linux`, on the tablet with the user session kept recoverable. Capture a process trace with Sysprof if package and permissions allow; otherwise capture bounded per-process sampling and WebKit inspector timings.
- Determine whether network, WebContent CPU/JS, compositing, or another layer dominates the delay. Keep raw reports out of Git and publish a concise result with commands and version information.
- No renderer, CPU governor, feature-disable, or content-filter changes without A/B evidence. A cause intrinsic to the third-party site is documented, not hidden by altering its behavior.

## Task 3: Supported improvement and verification

- Check Alpine armv7 package availability for WebKitGTK 2.54.3. If available, take an APK/profile rollback copy, upgrade using the distribution package, and repeat the benchmark. If absent, record the pending upgrade and continue the diagnosis on 2.54.2.
- Apply only a demonstrated local fix or supported upstream correction that directly addresses the measured cause; add a regression test first. If no safe local fix exists, prepare a minimal upstream reproduction and state the hardware or site limit.
- Accept an improvement only when the median page-ready time improves beyond run-to-run variation, the slowest runs do not regress materially, and the local control, touch, tabs, graphics, and browser stability remain sound. Request one physical confirmation of perceived responsiveness.

**Assumption:** Public, unauthenticated GitHub Topics is the complex sample; the local fixture is the network-free control. The user's normal browser profile is never used by the automation.
