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

Five-run A/B measurements with the default Skia compositor and process-local
TextureMapper selection showed only a 1.6% improvement to the public warm
wall median with TextureMapper, while the local warm control became 26%
slower and median browser CPU/PSS rose. CPU frequency stayed near its 1.512
GHz maximum and measured temperatures remained below the 85 °C first trip.
There is no supported basis to change the default compositor.

A complete Sysprof navigation had WebKit style, layout and script marks but
no CPU samples. A separate cold-process `perf` capture yielded 3,297 cycle
samples with no loss and resolved CSS selector-matching functions, including
`ElementRuleCollector::collectMatchingRulesForListSlow` (3.43% of sampled
cycles). The 1,667-sample warm capture had 87.42% unknown symbols after
losing process maps; a parent-process repeat also failed symbolization.
Cold selector cost cannot be attributed to the warm post-paint delay.

## Missing before upstream submission

- Repeat on WebKitGTK 2.54.3, when packaged for Alpine armv7.
- Capture a complete *warm* Web-process CPU trace with working symbols,
  separating JavaScript, style/layout, paint and composition. The available
  warm traces cannot support function-level attribution.
- Determine whether the page's own scripts account for the cost or WebKit has
  a fixable regression; attach the raw timing report if appropriate.

Epiphany `--automation-mode` separately aborts with a
`ephy_embed_container_get_active_child` assertion on this device; that crash
needs a distinct report. MiniBrowser itself completes the benchmark.
