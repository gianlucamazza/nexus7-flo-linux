# Flo DSI brightness and scanout design

## Intent and evidence

Brightness changes must preserve the displayed frame, the notification
panel, and normal charging and sleep behavior. A static DRM/KMS grid and
the notification panel both deform when brightness changes. An r42 trace
captured 39 successful DCS `0x51` transfers while the user saw the glitch;
no DSI error register fired during that interval. The command DMA trigger
occurred 4.27 ms after the preceding MDP vblank (median), and completion
was reported at the next frame. The nominal vertical blank lasts about
121 µs. Removing the driver's 2–4 ms delay in r30 did not fix the grid.

## Approaches

1. **Continuous DSI clock in the current video pipeline.** The JDI panel
   requests a non-continuous clock despite being driven as continuous
   video. The r45 candidate adds only that change to the r44 kernel,
   whose BC1.2 safety fix passed the USB boot test. This is a
   valid video-mode configuration and gives a clean A/B comparison, but
   may raise display power consumption and may not address command
   insertion timing.
2. **Correct video-mode command insertion.** Measure the DSI v2 hardware
   BLLP/command trigger against MDP scanout and use a supported hardware
   scheduling mechanism if available. This preserves the current video
   rendering path but needs evidence that the v2 controller can insert
   DCS commands without disturbing active pixels.
3. **Full MDP4/DSI command-mode pipeline.** The Android flo driver uses
   command mode, while current DRM MDP4 unconditionally selects DSI video.
   A correct port requires frame kickoff, completion and vblank events,
   TE behavior, damage updates, DPMS and suspend/resume handling. Changing
   a panel flag or encoder selector alone would leave the rendering path
   incomplete.

The first experiment is approach 1 because it changes one hardware mode
bit and can be rolled back to the verified r44 boot image. If it fails the
visual test, proceed with hardware timing evidence before approach 2 or
the complete command-mode implementation. No UI throttling or synthetic
brightness backend is an accepted resolution.

## r45 outcome

r45 did not reach the visual brightness comparison. After a normal boot
with greetd and Wi-Fi active, the user found the display black or stuck
and could not access the session or open the notification panel. Several
Power key presses are visible in the journal; Wi-Fi was unreachable until
a manual reboot. The tablet was downgraded over Wi-Fi to r44, which again
passed the user's greeter, login and touch check. Treat continuous clock
alone as an unsuccessful candidate. The exact failure mechanism is not
established, so the next driver change needs direct trace of display
disable/enable and DSI lane/PHY state across DPMS before another boot.

## Validation

- Compare r44 and r45 with the same 38-write rapid sequence and the
  notification panel visible; also repeat the static grid test if the
  panel appears stable.
- Capture DCS transfer results, DSI raw error registers, MDP vblank,
  command trigger/completion, and user-observed screen behavior.
- Verify greeter, login, touch, DPMS wake, Wi-Fi, eMMC access, charger
  classification/current limit and battery current after reboot.
- Retain r41, r42 and r44 APKs and exact boot archives until the candidate
  passes the native matrix. Revert a failed candidate before testing
  another hardware change.
