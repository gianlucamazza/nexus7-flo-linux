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
time across cores. The warm result does not reliably separate JavaScript,
style, layout and compositing inside the Web process. A later cold-only CPU
sample identifies CSS selector matching as one contributor to the initial
load; it cannot be extrapolated to the warm delay.

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
removed afterward. Its first Sysprof trace did not reliably cover the full
navigation. A later complete mark trace and cold CPU sample are described
below; neither supplies reliable warm function attribution. Sysprof was
uninstalled after profiling.

## Next supported change and acceptance

1. When Alpine packages WebKitGTK 2.54.3 for armv7, take an APK rollback copy,
   upgrade through `apk`, and repeat the same five cold and five warm runs.
   Compare medians and slow runs, the local control, and a physical touch
   check. Do not infer a speedup from the release notes alone.
2. If the delay persists, capture a warm WebKit Web-process CPU trace with
   working symbols and an upstream reproducible case before proposing an
   engine change. The [upstream performance draft](../upstream/webkitgtk-armv7-page-load-draft.md)
   records the current case and missing evidence. Keep the Epiphany
   automation-mode SIGABRT as a separate bug.
3. Treat changes to the third-party GitHub page as outside this project.

The [WebKitGTK 2.54 notes](https://webkitgtk.org/2026/09/16/webkitgtk-2.54-highlights.html)
describe the Skia compositor and damage-aware rendering already present in
2.54.2. The [WebKitGTK profiling notes](https://webkitgtk.org/2025/11/26/webkitgtk-2.50.html)
describe Sysprof marks and counters, which require a complete process trace
for useful attribution.

## Online research, 2026-11-19

The current Alpine edge/community armv7 `APKINDEX` still lists
`webkit2gtk-6.0` 2.54.2-r2 and Epiphany 50.6-r0. The tablet was unreachable
over Wi-Fi when this was checked, so installed versions were not refreshed.
The [WebKitGTK 2.54.3 release notes](https://webkitgtk.org/2026/11/18/webkitgtk2.54.3-released.html)
identify a prewarmed Web-process fix, but do not claim a remedy for this
page's post-paint CPU time.

The [2.54 architecture notes](https://webkitgtk.org/2026/09/16/webkitgtk-2.54-highlights.html)
show that Skia composition, damage-aware repainting, and mimalloc on 32-bit
ARM are already in our version. These are not missing switches to enable.
The [compositor author's guidance](https://blogs.igalia.com/carlosgc/2026/09/21/skia-compositor-for-wpe-webkit-and-webkitgtk/)
does provide a useful diagnostic A/B: run one isolated browser instance with
`WEBKIT_USE_SKIA_FOR_COMPOSITION=0` and compare it with the default. This
selects the older TextureMapper compositor in 2.54. Use it only to detect a
Skia regression; TextureMapper is being retired and is not a durable local
performance setting. An [actual Skia backdrop-filter regression](https://bugs.webkit.org/show_bug.cgi?id=327701)
was fixed and backported into 2.54.2, so it does not justify reverting our
installed package or attributing this GitHub page to that bug.

WebKit's [graphics diagnostics](https://blogs.igalia.com/carlosgc/2024/09/27/graphics-improvements-in-webkitgtk-and-wpewebkit-2-46/)
document `webkit://gpu/stdout`, which can report the active renderer and
threaded painting backend. Capture it from an isolated browser process before
considering any graphics change; the tablet's existing GTK GL hang makes an
unmeasured GPU toggle particularly risky. [WebKit's contributor notes](https://docs.webkit.org/Other/Contributor%20Meetings/ContributorMeeting2025.html)
describe ARMv7 Sysprof/samply support and JIT-aware profiling. Alpine armv7
currently packages Sysprof and WebKitGTK debug symbols, but not `samply`.
The next profiling attempt should attach to the actual Web process and verify
that samples or marks span the entire navigation before interpreting a flame
graph. Simultaneously log CPU frequency and temperature to check throttling.

## Live graphics inventory, 2026-11-19

Wi-Fi returned and the tablet was unlocked, at 100% battery with the power
controller reporting `Full` and positive current. After `apk update`, Alpine
armv7 still offered Epiphany 50.6-r0 and WebKitGTK 2.54.2-r2; 2.54.3 was not
available for installation. An isolated MiniBrowser `webkit://gpu/stdout`
probe reported Wayland at 600×960 logical pixels, scale 2, 60 Hz; WebKitGTK
2.54.2; Mesa 26.3.0 freedreno FD320; OpenGL ES 3.0; DMA-BUF XR24; and **GPU
threaded rendering with two threads**. `GSK_RENDERER=cairo` applies to the GTK
shell and does not mean that WebKit's web view is software-only. The GPU page
does not expose the active compositor name; Skia remains the 2.54 default
unless a process-local override is used.

Four CPU frequency policies expose `scaling_cur_freq` and `scaling_max_freq`.
The thermal zones are `bq27541-0` and `cpu0-thermal` through
`cpu3-thermal`. Before the benchmark the CPU policy maximum was 1.512 GHz;
the CPU zones read 40–47 °C. These are starting values, not load results.
The probe browser and its temporary profile were closed and removed.

## Compositor A/B on the tablet, 2026-11-19

With the tablet at 100% and the power controller reporting `Full`, the same
benchmark ran five cold/warm iterations per page first with WebKitGTK's
default Skia compositor, then with process-local
`WEBKIT_USE_SKIA_FOR_COMPOSITION=0` (TextureMapper). Each run used
`/var/tmp/epiphany-ab-run.sh <skia|texturemapper>`, which invoked the
unchanged `scripts/epiphany-perf.py` as user `tablet`, sampled all four CPU
frequency policies and named thermal zones once per second, and restored
`flo-shell`'s idle inhibition on exit. No persistent setting was changed.
All 40 page loads had the expected title, first contentful paint, and load
event; both test browsers exited normally.

| Page and phase | Skia wall median / p90 | TextureMapper wall median / p90 | Skia paint-to-load median | TextureMapper paint-to-load median |
| --- | ---: | ---: | ---: | ---: |
| Local cold | 3,481 / 4,125 ms | 3,858 / 4,034 ms | 0 ms | 0 ms |
| Local warm | 1,530 / 1,686 ms | 1,936 / 2,006 ms | 0 ms | 0 ms |
| GitHub cold | 27,102 / 28,409 ms | 26,512 / 27,589 ms | 8,444 ms | 8,089 ms |
| GitHub warm | 12,451 / 12,949 ms | 12,249 / 12,397 ms | 3,605 ms | 3,468 ms |

On the warm GitHub visit, TextureMapper improved the WebDriver wall median
by 202 ms (1.6%) and paint-to-load by 137 ms (3.8%), while the local warm
control regressed by 405 ms (26%). Median cumulative browser CPU on GitHub
warm rose from 20.44 to 20.98 CPU-seconds and PSS rose from 242,444 to
249,596 kB. Web-process CPU alone was
14.91 versus 14.45 CPU-seconds; the UI process rose from 5.72 to 6.19.
The public page loaded about 70 resources in both warm modes. TextureMapper
also reduced the post-load two-frame probe from 1,707 to 1,364 ms, but that
probe is not a touch-latency measurement and the local navigation regressed.

The Skia run started with CPU zones at 44–48 °C and reached 72 °C; the later
TextureMapper run started at 51–56 °C and reached 79 °C. This test order
confounds the temperature comparison. Both runs had median CPU frequency
1.512 GHz, with 264/297 and 259/300 one-second samples at that frequency;
the first thermal trip point is 85 °C and the CPU policy maximum remained
1.512 GHz. No sustained thermal throttle was observed. The small public-page
difference, higher CPU/PSS and slower local control do not meet the plan's
acceptance criteria. **Keep Skia as the default.** The A/B flag was never
applied to Epiphany's installed configuration. Raw reports and telemetry stay
in the ignored `reports/` directory on the host.

## Web-process profiling, 2026-11-19

Sysprof 51, `perf` 7.3.5 and matching WebKitGTK 2.54.2 debug symbols were
installed temporarily. A complete public-page navigation produced 1,577
WebKit Sysprof marks over 19.7 s, but Sysprof's sampling helper could not
open its per-CPU event stream on this kernel. The marks span both sides of
first contentful paint: one `StyleRecalc` interval ran from 4.38 to 9.99 s,
and subsequent `PerformLayout`, `ExecuteScriptElement` and `StyleRecalc`
intervals reached roughly 16.6 s. Marks can overlap and are **not** CPU-time
totals. They show activity after paint, not which operation dominates the
warm page load.

Direct `perf record` sampling did work on the actual Web process. The
single-process cold navigation yielded 3,297 cycle samples in 32.0 s with
zero lost samples. By DSO, 41.17% of sampled cycles were in WebKitGTK,
12.28% in JavaScriptCore, 22.16% in musl, 12.82% in the kernel, 6.49% in
fontconfig and 0.99% in Mesa. With matching debug symbols, the largest
resolved leaf function was
`WebCore::Style::ElementRuleCollector::collectMatchingRulesForListSlow`
(3.43% of sampled cycles); `WebCore::SelectorChecker::checkOne` accounted
for 1.84%. These data support CSS selector matching as a **cold-load**
contributor, not as the cause of the warm 3.6 s paint-to-load interval.

A separate 14.8 s warm-process capture had 1,667 samples, but 87.42% were
`[unknown]` after `perf` lost the process map during attachment. A final
parent-process capture included both navigation phases and 9,678 samples
with no reported loss. Its warm navigation completed in 12.63 s (FCP 4.59 s,
paint-to-load 3.77 s), but this tablet's `perf` symbolization terminated
while processing the full parent capture, so that trace also cannot support
function-level warm attribution. The repeat run is consistent with the
five-sample baseline; it is not an additional A/B trial. The unresolved
symbols are a measurement limitation, not evidence of an engine fault.

All trace files and private test profiles were removed from the tablet after
the aggregate results were recorded on the host. Sysprof, `perf`, matching
debug symbols and their temporary `/usr/lib/debug/lib` symlink were removed;
Epiphany 50.6 and WebKitGTK 2.54.2 remained installed. The tablet session
was unlocked and responded to `flo-shell`, with idle inhibition off,
and the battery controller reported `Full`, 100%.

On 20 November, `apk update` completed successfully against the configured
postmarketOS and Alpine edge repositories. `apk policy` still offered only
Epiphany `50.6-r0` and `webkit2gtk-6.0` `2.54.2-r2` for this tablet, the same
versions already installed. The planned 2.54.3 comparison therefore has no
packaged candidate yet; no browser package or profile was changed.
