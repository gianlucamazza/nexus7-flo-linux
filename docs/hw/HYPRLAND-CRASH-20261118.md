# Historical Hyprland crash during flo power/display testing

The tablet retained `/home/tablet/.cache/hyprland/hyprlandCrashReport1735.txt`
from 16 November at 16:47 CET. The process was `Hyprland 0.54.3`, running
`/usr/share/flo-shell/session/hyprland.conf` on kernel `#22`.

The crash report says Hyprland originally received **signal 11**. The
systemd-coredump record for the same PID is **SIGABRT**; it captured the
crash handler's termination, so SIGABRT is not the original fault. This
Alpine armv7 build has no `execinfo.h` backtrace in the Hyprland report.
Loading the tablet's exact musl loader and Hyprland executable into GDB
allowed unwinding across the crash handler's signal frame. The original
faulting stack is:

```
CWLSurfaceResource::client()              # original SIGSEGV, r0 = 0
CSeatManager::sendTouchDown(...)
CInputManager::onTouchDown(...)
```

On ARM, `r0` carries the `this` pointer for this member call. Here it is
zero. The exact [v0.54.3 source][v0543-seat] dereferences `surf` at
`auto client = surf->client()` without checking it. Its [touch-down
caller][v0543-touch] passes `m_touchData.touchFocusSurface.lock()` even
when a window or layer focus was selected but the weak surface reference
has expired or is empty. This establishes a null surface dereference in
the touch delivery path. It does not establish why the surface became
empty in this particular event. As of upstream commit
`4d9a4720d24da84b540fdf8a6aa917abe564d0a2` (17 November 2026),
the same unchecked call remains in [SeatManager][upstream-seat] and
[Touch.cpp][upstream-touch].

At 16:46:51, `systemd-logind` logged a short power-key press. The Hyprland
report's log tail includes repeated removal/readdition of the test-only
`nexus7-uibench-touch` input device, a libseat `Device not taken` error for
`/dev/input/event3`, DSI-1 disable and enable modesets, and repeated CTM
commit failures because the DRM CRTC does not advertise CTM. The process
crashed at 16:47:02. These events are correlated in time; the recovered
stack identifies touch delivery as the faulting operation, but does not
prove whether hotplug, modesetting, or another focus transition made the
surface reference empty. CTM errors are present around normal modesets
and do not by themselves identify the SIGSEGV.

The current r29 session has since passed ten native lock/wake cycles and
user-confirmed login/touch. Those tests reduce the likelihood of an
unconditional power-key failure, but they did not repeat the same virtual
touch hotplug load or establish the cause of the historical crash.

Next: design a compositor fix that rejects an absent surface before
touch-down delivery and leaves touch focus/lock state consistent. Exercise
an expired surface with a still-present window/layer focus in a focused
test, then build/test the exact package and repeat native hotplug and
power-key/DPMS cycles when charging and recovery are stable. Capture
Hyprland/aquamarine logs and kernel DRM/input events with monotonic
timestamps. Do not conflate this event with the separate 32-bit
toplevel-address defect or GTK4 Settings crash.

Host implementation progress on 18 November: the exact v0.54.3 source
was built in an isolated Alpine edge x86 container with Aquamarine 0.12.0
and Hyprutils 0.13.1, matching the tablet packages. A new GTest invokes
the real `CSeatManager::sendTouchDown()` with a null surface while two
touches are recorded. It exited with SIGSEGV (139) before the change.
An entry guard before any listener/focus/count mutation made the test
pass, and the complete available GTest suite passed 2/2 after clearing
stale coverage data. Source branch `flo/touch-null` is at `58a41a8` in
`build/hyprland-touch-src`; pmaports branch `flo/hyprland-touch` is at
`0c060a8` in `build/pmaports-hyprland-touch`. The armv7 package build is
in progress. This is a host regression and compile result, not a native
touch/hotplug validation. The separate question of why the focus surface
became null in the historical sequence remains open.

Rollback prepared before native installation: the official Alpine edge
armv7 `hyprland-0.54.3-r0.apk` is stored privately at
`reports/rollback/hyprland-0.54.3-r0-armv7.apk`. `apk.static verify` with
the cached Alpine public keys reports `OK`. Its SHA-256 is
`cc8139dac97679dd04762893ddb9e30730a376885856bb35f1c27d327a5d0a4b`;
the package's `/usr/bin/Hyprland` SHA-256 is
`a6336feff09c8767fc1d05edadd3dfbeb38f078b4b25bdef0306e73560f26ee6`,
identical to the running tablet's installed binary at the time of this
check. Keep the diagnostic SSH path until explicitly instructed to remove
it. The rollback APK was copied to
`/var/tmp/hyprland-0.54.3-r0-rollback.apk` on the tablet; its SHA-256
there matches the host copy. It has not been installed.

The core was copied temporarily to a private host directory for analysis
and deleted. This document contains no core memory or private firmware.

[v0543-seat]: https://github.com/hyprwm/Hyprland/blob/v0.54.3/src/managers/SeatManager.cpp#L375-L381
[v0543-touch]: https://github.com/hyprwm/Hyprland/blob/v0.54.3/src/managers/input/Touch.cpp#L68-L110
[upstream-seat]: https://github.com/hyprwm/Hyprland/blob/4d9a4720d24da84b540fdf8a6aa917abe564d0a2/src/managers/SeatManager.cpp#L508-L514
[upstream-touch]: https://github.com/hyprwm/Hyprland/blob/4d9a4720d24da84b540fdf8a6aa917abe564d0a2/src/managers/input/Touch.cpp#L149-L152
