# Roadmap

Ordered milestones taken from the open issues in
[`docs/hw/ISSUES-20261117.md`](hw/ISSUES-20261117.md) (priority table and
"Ordine di verifica"). No dates: none are documented. Status per component is in
[`HARDWARE.md`](HARDWARE.md).

## 1. Power: charging that keeps up with the display (P0)

- Test the revised BC1.2/charger kernel branch on the tablet: boot without
  gadget, attach/detach, SDP/CDP/DCP, role switching, with r29 as rollback.
- Measure input current and AICL so that the battery charges with the display on.

## 2. Display: brightness changes without glitches or DSI errors (P0)

- Trace MDP DMA_P_DONE, DSI interrupts, error registers and DCS sends in the
  same reproduction; find a safe point for commands while video is streaming.
- Done when both the glitch and the `dsi_err_worker` errors are gone.

## 3. Stability (P1)

- eMMC/DMA: error, removal and shared-request coverage, then a long-run test.
- Lock screen/greeter: surface-failure and restart-during-lock tests.
- Hyprland touch crash: confirm the fixed package; find where the null focus comes from.
- CPU idle: study SPM/PMIC delays so that `cpuidle.off=1` can be dropped.

## 4. Sensors via DSPS (P1, then P2)

- Boot with the DDR reservation for DSPS, then start/stop DSPS manually.
- Validate the `SENSOR` SMD port protocol on the device and expose real IIO samples.
- Then auto-rotation (iio-sensor-proxy), calibration, gyro, compass, light.

## 5. Audio (P2)

- Follow [`hw/AUDIO-DISCOVERY-20261118.md`](hw/AUDIO-DISCOVERY-20261118.md):
  enumerate the WCD9310 with correct power and reset, add the two SLIMbus channels
  and ASoC routing, then test headphones, speakers, microphones and UCM/PipeWire.

## 6. Desktop and apps (P2)

- Validate a newer Hyprland (Lua config already prepared) and drop the local
  Quickshell 32-bit address patch once fixed upstream.
- GTK4/GL crashes, the screenshot portal, and the Wi-Fi scan error (channel-limit
  kernel already built).

## 7. Remaining hardware (P3)

- Hall sensor, PMIC ADC, LED, USB OTG host, wireless charging, NFC, SlimPort,
  cameras and GPS, one device at a time following [`hw/MATRIX.md`](hw/MATRIX.md),
  starting from hardware identification and electrical checks. High-risk drafts
  are not applied in bulk.

## 8. Upstreaming

- Propose the reviewed kernel patches to apq8064-mainline and the subsystem
  lists (not started). Local-only patches are listed in the `linux-flo` README.
- Package fixes (Hyprland touch, portal unit split) to Alpine/postmarketOS aports.

## flo-agents (opt-in, experimental)

Remote agent-CLI sessions from the tablet. The tablet is the screen and
keyboard; the CLI runs on a 64-bit host the user owns. Userland is Nura
(formerly postmarketOS). Details: [`flo-agents.md`](flo-agents.md).

### Milestone 1: remote session

Configure a host, list tools, launch mosh/ssh (optional tmux) to the user's
own Claude Code, Codex CLI or Grok Build install, check reachability, print
official host install/login commands, and uninstall our config/wrapper.
No agent binary is installed on the tablet.

### Milestone 2+: future work

- flo-shell UI to pick a tool and attach to `flo-<tool>`
- Session status and reconnect helpers in the shell
- Optional host-side extras (still no local agent install on the tablet)
