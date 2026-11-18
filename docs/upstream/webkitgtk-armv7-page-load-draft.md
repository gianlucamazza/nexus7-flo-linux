# Draft: WebKitGTK 2.54.2, costly page load on ARMv7 Flo

**Status:** Reproduction draft only. Retest with Alpine's WebKitGTK 2.54.3
package and obtain a complete Web-process profile before filing a performance
bug. The current data do not establish a WebKit regression.

## Environment

- ASUS Nexus 7 2013 (Flo), ARMv7, 4 CPU cores, 2 GB RAM.
- Alpine edge/postmarketOS, Epiphany 50.6, WebKitGTK 2.54.2-r2.
- Wayland/Hyprland. `GSK_RENDERER=cairo` for GTK; WebKitGTK 2.54 uses Skia.
- Public URL: `https://github.com/topics/linux`. No account required.

## Reproduce

Run `scripts/epiphany-perf.py --runs 5 --timeout 60 --out /var/tmp/epiphany-perf.json`
as the logged-in tablet user in its Wayland session. The script uses a fresh
WebKitWebDriver MiniBrowser session for each cold sample and revisits the page
in the same session for each warm sample. It also loads a fixed loopback page
to distinguish generic display latency. No personal browser profile is used.

## Observed

On the GitHub page, median first contentful paint is 13.19 s cold and 4.40 s
warm. Median paint-to-load is 8.21 s cold and 3.57 s warm. The loopback page
paints in 0.21 s cold and has no post-paint load wait. In a warm attribution
run the WebKit Web process used 14.78 CPU-seconds, compared with 0.15 in the
network process, while WebDriver wall time was 12.43 s. This is cumulative
CPU time across cores. Resource timing reported no warm request above 1 ms,
but cross-origin timing restrictions limit that observation.

## Missing before upstream submission

- Repeat on WebKitGTK 2.54.3, when packaged for Alpine armv7.
- Capture a complete Web-process Sysprof trace with symbols, separating
  JavaScript, style/layout, paint and compositing. The available trace did not
  reliably cover the entire navigation.
- Determine whether the page's own scripts account for the cost or WebKit has
  a fixable regression; attach the raw timing report if appropriate.

Epiphany `--automation-mode` separately aborts with a
`ephy_embed_container_get_active_child` assertion on this device; that crash
needs a distinct report. MiniBrowser itself completes the benchmark.
