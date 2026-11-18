# Historical Hyprland crash during flo power/display testing

The tablet retained `/home/tablet/.cache/hyprland/hyprlandCrashReport1735.txt`
from 16 November at 16:47 CET. The process was `Hyprland 0.54.3`, running
`/usr/share/flo-shell/session/hyprland.conf` on kernel `#22`.

The crash report says Hyprland originally received **signal 11**. The
systemd-coredump record for the same PID is **SIGABRT**; it captured the
crash handler's termination, so SIGABRT should not be presented as the
original fault. This Alpine armv7 build has no `execinfo.h` backtrace in
the Hyprland report. GDB on the core has only two unresolved frames in the
crashing thread; the available package has no matching public `-dbg`
subpackage. No faulting function is established.

At 16:46:51, `systemd-logind` logged a short power-key press. The Hyprland
report's log tail includes repeated removal/readdition of the test-only
`nexus7-uibench-touch` input device, a libseat `Device not taken` error for
`/dev/input/event3`, DSI-1 disable and enable modesets, and repeated CTM
commit failures because the DRM CRTC does not advertise CTM. The process
crashed at 16:47:02. These events are correlated in time; none is proven
to be the faulting operation. In particular, CTM errors are present around
normal modesets and do not by themselves identify the SIGSEGV.

The current r29 session has since passed ten native lock/wake cycles and
user-confirmed login/touch. Those tests reduce the likelihood of an
unconditional power-key failure, but they did not repeat the same virtual
touch hotplug load or establish the cause of the historical crash.

Next native test, when power and recovery are stable: keep the virtual
touch device absent and exercise power-key/DPMS cycles; then test hotplug
without DPMS, and only then their combination. Capture Hyprland/aquamarine
logs and kernel DRM/input events with monotonic timestamps. If a crash
recurs, obtain a symbolized build or a minimal reproduction before
claiming a compositor, input, or DRM fix. Do not conflate this event with
the separate 32-bit toplevel-address defect or GTK4 Settings crash.

The core was copied temporarily to a private host directory for analysis
and deleted. This document contains no core memory or private firmware.
