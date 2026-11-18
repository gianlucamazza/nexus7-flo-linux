# Epiphany performance on Flo, 2026-11-18

## Result

On the public `https://github.com/topics/linux` page, the delay after the
first visible content is chiefly work in WebKit's Web process on Flo. A warm
navigation still spends 3.6 s (median of five) between first contentful paint
and the load event. In a follow-up warm run, the resource timing API reported
no request duration above 1 ms. That supports, but does not prove, that the
network is no longer dominant. One attribution run used
14.8 CPU-seconds in `WebKitWebProcess`, 4.5 in MiniBrowser, and 0.15 in the
network process over a 12.4 s wall-clock navigation. This is cumulative CPU
time across cores. The result does not separate JavaScript, style, layout and
compositing inside the Web process.

The current Alpine armv7 repository has Epiphany 50.6 and WebKitGTK 2.54.2-r2.
WebKitGTK 2.54.3 was [released on 18 November](https://webkitgtk.org/2026/11/18/webkitgtk2.54.3-released.html),
but is not yet packaged there. Its release notes mention a fix for prewarmed
Web processes, without claiming an improvement to this page's post-paint work.
Do not locally rebuild WebKit or change the page, browser security settings,
CPU governor, or GTK renderer on this evidence. The tablet's GTK GL renderer
has a separate unresolved GPU hang; Cairo remains configured.

## Reproduction and measurements

Run `scripts/epiphany-perf.py` as the logged-in tablet user with the normal
Wayland and D-Bus environment. It starts a loopback-only WebKitWebDriver and
MiniBrowser with an ephemeral automation profile, loads a fixed local HTML
control and the public GitHub Topics page, and writes a JSON report outside
Git. The cold phase creates a new browser session; the warm phase returns to
`about:blank` and revisits the same page with that session's cache. Each
phase was run five times on WebKitGTK 2.54.2. The normal personal browser
profile, cookies and history were not read.

| Page and phase | First contentful paint, median | Paint to load, median | Two animation frames after load, median | WebDriver wall time, median |
| --- | ---: | ---: | ---: | ---: |
| Local control, cold | 209 ms | 0 ms | 432 ms | 3,417 ms |
| Local control, warm | 485 ms | 0 ms | 460 ms | 1,526 ms |
| GitHub Topics, cold | 13,187 ms | 8,214 ms | 2,109 ms | 26,727 ms |
| GitHub Topics, warm | 4,397 ms | 3,574 ms | 1,735 ms | 12,160 ms |

The two-frame probe runs *after* load and is a rendering responsiveness
indicator, not a touchscreen input-latency measurement. WebDriver wall time
includes protocol and polling overhead, so it is not an end-user page-ready
time. The local control has no subresources and first paints quickly, which
rules out a general inability to paint a simple page. `curl` on the same
tablet fetched the public page's main document in 1.36 s, with first byte at
1.15 s; this alone does not account for third-party resources.

A separate single cold/warm attribution run recorded 72/70 resource timing
entries. Fourteen/thirteen completed after first paint. The longest cold
resource lasted 1.13 s; on the warm navigation the longest reported duration
was 1 ms, yet paint-to-load still took 3.76 s and the Web process used 14.8
CPU-seconds. The network process used 4.02 CPU-seconds cold and 0.15 warm.
Cross-origin resource timing restrictions and caches can limit interpretation
of those per-resource durations; a third-party network delay is not completely
excluded.
There was no memory pressure or swap use during the baseline. The normal
Epiphany process remained open and healthy after the tests.

Epiphany 50.6 aborts with `ephy_embed_container_get_active_child` when
started in `--automation-mode` on Flo. The core is SIGABRT, not an OOM kill.
Thus WebDriver samples the same WebKitGTK engine through MiniBrowser, not
Epiphany's own chrome. An isolated normal Epiphany instance was also launched
with `--profile=/var/tmp/epiphany-perf-profile`; its temporary profile was
removed afterward. Sysprof's trace from that run contained WebKit marks, but
did not reliably cover the full navigation, so it cannot attribute the hot
Web-process functions. Sysprof was uninstalled after this bounded test.

## Next supported change and acceptance

1. When Alpine packages WebKitGTK 2.54.3 for armv7, take an APK rollback copy,
   upgrade through `apk`, and repeat the same five cold and five warm runs.
   Compare medians and slow runs, the local control, and a physical touch
   check. Do not infer a speedup from the release notes alone.
2. If the delay persists, capture a complete WebKit Web-process trace with
   symbols and an upstream reproducible case before proposing an engine
   change. The [upstream performance draft](../upstream/webkitgtk-armv7-page-load-draft.md)
   records the current case and missing evidence. Keep the Epiphany
   automation-mode SIGABRT as a separate bug.
3. Treat changes to the third-party GitHub page as outside this project.

The [WebKitGTK 2.54 notes](https://webkitgtk.org/2026/09/16/webkitgtk-2.54-highlights.html)
describe the Skia compositor and damage-aware rendering already present in
2.54.2. The [WebKitGTK profiling notes](https://webkitgtk.org/2025/11/26/webkitgtk-2.50.html)
describe Sysprof marks and counters, which require a complete process trace
for useful attribution.
