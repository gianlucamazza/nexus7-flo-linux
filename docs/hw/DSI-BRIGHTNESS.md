# Flo brightness regression: shell permissions and panel protocol

## Panel operating mode: corrected source comparison (2026-11-19)

The 2016 [mainline JDI panel submission](https://lkml.iu.edu/hypermail/linux/kernel/1606.3/02884.html)
describes a video-mode panel and cites a different vendor video-mode DTS.
However, the [Android flo panel configuration](https://android.googlesource.com/kernel/msm/+/android-msm-flo-3.4-marshmallow/drivers/video/msm/mipi_JDI_1080P_pt.c)
explicitly sets `MIPI_CMD_PANEL` and `DSI_CMD_MODE`, enables hardware VSYNC,
selects the TE GPIO and software DSI DMA trigger. Its PHY table comment says
"video mode", but the executable mode settings are command mode. The current
mainline panel driver sets `MIPI_DSI_MODE_VIDEO`, and the MDP4 encoder routes
the CRTC unconditionally to `INTF_DSI_VIDEO`. Our previous claim that the
Android flo driver used video mode was therefore wrong.

This mismatch is a credible explanation for the physical brightness artifact,
not yet a demonstrated cause. A correct command-mode port requires MDP4 frame
kickoff and completion, TE/vblank and atomic flip handling, panel state and
DPMS/resume validation. The DSI host already has some command-mode register
setup; the MDP4 encoder and CRTC are incomplete for command mode. Changing
only the panel flag or encoder selector would break scanout.

On the booted r50 tablet, read-only MMIO confirmed the current mode:
`DSI_CTRL=0x1f3` (video enabled, command disabled),
`MDP4_DISP_INTF_SEL=0x49` (primary DSI video selected), and
`DSI_TRIG_CTRL=0x80000004` (TE select bit and software DMA trigger).
The GPIO debug view shows GPIO0 input low with pull-up, but this is a single
sample, not proof that a TE pulse arrives or has the correct polarity. Stock
flo board code identifies GPIO0 as the JDI TE pin. These observations do not
yet establish that the mode mismatch alone causes the glitch.

The bootable r50 APK and a host archive of both matching boot copies are
retained for recovery; archive SHA-256
`d4b1633bf3cd43ec3892afe2a71d9ec76cb149ae85be1f6583cf2043f3372f95`.

### r51 command-mode candidate (failed boot)

The first full MDP4 command-mode candidate compiled as an armv7 APK and
passed nine KUnit tests. It did not reach Wi-Fi or journald after reboot;
there was no opportunity for the planned physical brightness comparison.
TWRP recovery restored the verified r50 APK and both boot copies, and r50
returned on Wi-Fi with greetd active. The cause of the r51 boot failure is
unknown. The code review also identified an unsafe timeout design: a late
DMA completion could be misattributed to the next frame. The candidate
now waits for the real completion, but a missing TE/IRQ can block the boot
commit indefinitely. A bounded and hardware-backed recovery path and a
diagnostic boot are required before another normal install. r51 must not be
published or described as a brightness fix.

### r52 diagnostic and TE command gap

A diagnostic r52 build retained the r51 command-mode setup but skipped every
MDP4 command-frame DMA kickoff. It reached Wi-Fi and `greetd`; the kernel log
records `MDP4 diagnostic: frame DMA disabled`. This narrows the r51 boot
failure to the kickoff/completion path, without proving which register or
signal is responsible. The display did not receive frames, and fbdev logged
repeated vblank wait timeouts, as expected for this diagnostic. The MDP IRQ
count remained zero. GPIO0 was configured as `mdp_vsync`, input with a 2 mA
pull-down; 200 samples at approximately 5 ms intervals were low. This sampling
cannot rule out short TE pulses. The r52 kernel journal is saved as
`build/flo-r52-kernel-journal-20261119.log`. r50 was reinstalled after the
probe and returned on Wi-Fi with `greetd` active.

The [stock flo DSI host](https://android.googlesource.com/kernel/msm/+/android-msm-flo-3.4-marshmallow/drivers/video/msm/mipi_dsi.c)
sends DCS `SET_TEAR_ON` (`0x35, 0x00`) after enabling a command-mode panel;
r51 did not send it. The stock pull-down setting also
matches the r51 pinctrl state, so pull-down alone is not evidence of a wiring
error. The missing DCS command is a concrete candidate cause of the absent
frame completion. It needs a focused test and native frame/TE verification;
do not treat it as a confirmed fix.

An r53 panel patch sends `SET_TEAR_ON` after display-on and `SET_TEAR_OFF`
before display-off only in command mode. Its KUnit test failed before the
command was added, then all ten MDP4/JDI tests passed. The armv7 APK built,
the simulated upgrade passed, and both boot copies matched. Native r53 again
failed to return on Wi-Fi after reboot, so the TE command alone did not solve
the kickoff/boot failure. Recovery and log capture are pending. A diagnostic
r54 candidate keeps TE enabled, boots with frame DMA skipped, and permits one
post-boot DMA probe while Wi-Fi is available to read MDP registers on timeout.
The r54 APK built successfully (SHA-256
`032c4b0d23c1abdb95f5fc490899aedecef2dfff86308abecccfb463d2ac48ff`)
and was later installed for the post-boot DMA probe. After r53 failed, TWRP recovery mounted the inner
root and boot partitions. The active system journal had a timestamp before
the r53 reboot; no r53 boot log or pstore record was available. The verified
r50 APK was installed without package scripts, then `depmod`, `mkinitfs` and
`nexus7-sync-boot` ran explicitly. The r50 kernel, initramfs and DTB hashes
matched on both `/boot` and p22. After reboot, Wi-Fi and `greetd` returned,
the installed package was r50, and the battery read 97%. The user then
confirmed login and touch work.

### r54 post-boot DMA probe

r54 booted with its diagnostic frame-DMA gate enabled. With the command-mode
panel initialized and `SET_TEAR_ON` sent, GPIO0 sampled high 3 of 400 times
at approximately 2.5 ms intervals; it had stayed low for all 200 r52 samples.
This is evidence that TE pulses are present, though software polling does not
measure their exact shape or period. DSI control was `0x1f5` (command mode),
and the MDP interrupt count was zero before kickoff.

After disabling the gate and restarting greetd, the first MDP4 command frame
completed and raised one MDP IRQ. The second frame timed out at 100 ms and
remained inflight. At timeout: `INTR_ENABLE=0x0d10`, `INTR_STATUS=0`,
`DISP_STATUS=5`, `TEAR_CHECK_EN=1`, `OVERLAY_FLUSH=0x11`. GPIO0 still showed
high samples (4/400) after the stall, so loss of panel TE output alone does
not explain this frame. Wi-Fi later stopped responding; the user was asked to
enter TWRP for r50 rollback. Before repair, e2fsck `-fn` reported an invalid
extent header on inode 132763. Because that prevented `e2image` from saving
metadata, a complete compressed image of the unmounted 12,601,736,704-byte
root partition was saved as `build/r54-root-before-fsck.img.gz` (SHA-256
`1cedfffaa5b7b0e4d09c059900780d6d38b37d08b7804a29fd5a10bdfad75030`).
The gzip stream decompressed without error to exactly the source size. Modern
e2fsck 1.47.4 then replayed the root and inner boot journals with `-p`; a
subsequent full root check with `-fn` returned 0. The earlier extent error was
not present after journal replay. TWRP installed the verified r50 APK offline,
then ran `depmod`, `mkinitfs` and `nexus7-sync-boot`. Kernel, initramfs and DTB
on `/boot` and p22 exactly matched their archived r50 hashes. All mounts and
loops were detached before reboot. r50 booted on Wi-Fi with greetd active and
the installed package at r50; battery read 90% and discharging on computer
USB. The user confirmed PIN login and touch. The exact MDP4 cause
remains unproven.

The stock driver also programs the MDP sync counter (`0x100`), initial line
(`0x128`), output control (`0x118`) and threshold (`0x200`), and enables
`mdp_vsync_clk`. The r51–r54 path programs only tear-check start/read-pointer
registers. This is a concrete integration gap to test next, including clock
lifetime and IRQ behaviour. Do not ship r54 or describe the glitch as fixed.

### r55 VSYNC counter probe

r55 adds the MDP VSYNC clock to the APQ8064 Device Tree and binding, obtains
and enables it in the MDP4 command encoder, and programs the stock sync
counter, initial line, output control and threshold registers. The counter is
derived from the actual clock rate and DRM mode. Twelve KUnit tests passed,
including new counter/configuration cases; the armv7 package built, and the
offline upgrade simulation passed. On the tablet, the clock ran at 27 MHz and
had enable count 1. r55 booted with frame DMA skipped and Wi-Fi/greetd active.
After enabling frame DMA and restarting greetd, the first command frame
completed, but the second stalled again at 100 ms with
`INTR_ENABLE=0x0d10`, `INTR_STATUS=0`, `DISP_STATUS=5`, `TEAR_CHECK_EN=1`,
`OVERLAY_FLUSH=0x11`. The VSYNC clock gap is real but insufficient to fix
this second-frame failure. While Wi-Fi still worked, the verified r50 APK
was installed and the kernel, initramfs and DTB on `/boot` and p22 matched
their r50 hashes. A normal reboot request timed out while the old r55 kernel
was blocked. After a physical power cycle, r50 returned on Wi-Fi with a new
uptime, greetd, NetworkManager and flo-sessiond active. The installed package
and `/boot` hashes match r50; the new kernel journal has no ext4, MMC or MDP
timeout errors. The user confirmed successful PIN login after this boot.

### r56 first-frame transition trace

r56 keeps r55's VSYNC setup and diagnostic DMA gate, adding MDP register
snapshots around the first four command kickoffs. The trace-only patch passed
checkpatch and 12 KUnit tests; the armv7 APK built and the offline upgrade
simulation passed. On the tablet r56 booted with the gate active, Wi-Fi and
greetd running, and the VSYNC clock enabled at 27 MHz. With the gate lifted:

| Time since boot | Event | `DISP_STATUS` | `OVERLAY_FLUSH` | `INTR_STATUS` |
| --- | --- | --- | --- | --- |
| 55.509717 s | Frame 1 before kick | `0` | `0x11` | `0x800` |
| 55.509814 s | Frame 1 completion callback | `5` | `0x10` | `0` |
| 55.524190 s | Frame 2 before kick | `5` | `0x11` | `0` |
| 55.646737 s | Frame 2 timeout | `5` | `0x11` | `0` |

The first callback followed kickoff by only 97 microseconds, far too short
for a 1200×1920 RGB frame to cross DSI. The second kick occurred 14.4 ms later
while `DISP_STATUS` was still `5`. The raw register has no decoded bitfields
in the current MDP4 register definitions, so `5` is not yet labelled as a
specific busy condition. The evidence supports a false or premature first
completion, or an uncompleted first transfer; it does not yet distinguish
these causes. The full kernel log is in
`build/r56-kernel-trace-20261119.log`.

The stock Flo command path writes the primary DMA source address and stride
from the framebuffer; the current DRM command path leaves both zero because
the video path takes pixels from an overlay pipe. This is a concrete
configuration difference to validate before changing it. r50 was restored
over Wi-Fi, and kernel, initramfs and DTB on both boot copies matched the
archived hashes. An emergency sync/remount/reboot returned the tablet to r50;
Wi-Fi, greetd, NetworkManager and flo-sessiond are active, with no new ext4,
MMC or MDP timeout in the boot journal. The user confirmed PIN login and
working touch after this boot.

### r57 framebuffer DMA source probe (prepared)

r57 writes the primary framebuffer IOVA and pitch into the MDP4 DMA source
registers on active command-mode commits, matching the stock driver's
configuration step. The r56 trace also records those registers before each
kickoff. This tests whether zero DMA source/stride caused the 97-microsecond
completion. It remains an unproven hypothesis; the resulting pixels and
multi-plane composition must be checked on hardware before considering it a
fix. The source commit is `0df5f7334`, package commit `fc1c81f`, and the
armv7 APK SHA-256 is
`e9490a4ec958c216515977e33e304c0a0e5e11fdc3f844778a9d7163c89a0b27`.
Checkpatch and 12 KUnit tests passed, the armv7 package built, and the offline
upgrade simulation passed. The APK is copied to the tablet but is **not
installed**; r50 still runs. The wall charger now reports positive current.
A recovery-capable operator confirmation is pending before deployment.

## Confirmed shell fault

On r23 with flo-shell r8, the UI selected brightnessctl because the executable
existed. On this Alpine installation it is not setuid and the tablet user is
not in group video. A write to the current value returned Permission denied.
The UI nevertheless retained its optimistic value (56%, versus sysfs 40/255).

flo-shell commit `b4c6cce`, installed package r9, prefers logind when its service
is available. It confirms the final queued write by reloading sysfs, including
failure, and ignores old read events while a newer write is pending. No group
membership or sysfs permission was broadened. The active shell runs in logind
session c3 on seat0, so its `/session/auto` resolves correctly. An SSH runuser
process has no seat; explicit c3 was used only to verify the API separately.

`make check` includes `dev/test-brightness.py`. The real QML service is exercised
with a temporary backlight file, a private D-Bus and a controlled writer. The
rollback test failed before the fix; denied writes, queue coalescing and backend
selection pass after it. Independent review found no important remaining issue.
Actual discovery and logind writes were verified on the tablet.

## Confirmed panel protocol mismatch

The original [AOSP JDI driver](https://android.googlesource.com/kernel/msm/+/75977811169d779c039da38e63a1cac4e0cd1693/drivers/video/msm/mipi_JDI.c)
uses command 0x51 plus one brightness byte with DCS_WRITE1 (short write with
one parameter). The panel range is 0–255. Our current driver used the generic
16-bit brightness helper, which produces a three-byte DCS long write. The
brightness read also requested two bytes. This is a wire-format discrepancy,
not evidence by itself that every observed visual artifact has the same cause.

Kernel commit `51ad273c2`, branch `flo/dsi-brightness-r24`, corrects initialization
and runtime updates to one-byte levels, requests a one-byte read, and restores
the original DSI mode flags after success and failure.

Reproduce the kernel callback tests using a recording MIPI host:

```
python tools/testing/kunit/kunit.py run \
  --kunitconfig=tools/testing/kunit/configs/jdi_lt070me05000.config \
  --build_dir=.kunit-jdi --jobs=12
```

All four cases failed against the old callbacks and pass with the fix: startup
and runtime short writes, one-byte reads, and flag restoration after transport
errors. The test uses real MIPI helpers to capture the generated packet type
and bytes. Test configuration requires built-in KUnit and backlight support;
modular KUnit cannot enable the bool test. ARM build and checkpatch pass for the
modified panel. Existing kernel link warnings about init_8960 and BPF arena
BTF symbols remain unrelated to this patch.

## Hardware validation status

The user reports full-screen flicker/lines while dragging brightness. r23 logs
still contain `dsi_err_worker: status=5` (timeout and FIFO). Earlier analysis also
found VIDEO_DONE wait timeouts in the host. The 8-bit fix does not change host
synchronization; its effect on errors and visible flicker must be measured.
Do not suppress logs or replace driver synchronization with a UI delay.

Candidate package:
`linux-postmarketos-qcom-apq8064-7.2_p20261116235753-r0.apk`, SHA256
`3e6a77708664207cd869041d036f0332ad720ab0a9dfc2f3ddf2683a87290ae7`.
The APK was checked to contain no DSPS module. DSPS WIP remains on its separate
branch and is not part of this display test. Installation retains the previous
kernel through nexus7-sync-boot and backs up boot/modules/APK DB under
`/var/tmp/nexus7-before-r24-brightness`.

At this document's initial write, installation/reboot and visual testing are
pending. See the follow-up verification record below before claiming resolution.

### r24 hardware result (2026-11-17)

Booted #25 successfully; greetd and SSH active, no failed systemd units. User
unlocked the session and confirms brightness changes, but full-screen flicker
still occurs. During dragging, the sampled kernel log contains zero
`dsi_err_worker`, zero invalid responses and zero underflows, but 22 VIDEO_DONE
wait timeouts. The protocol correction is retained; it does not resolve the
remaining synchronization fault.

Next candidate r25 uses DRM's MDP vblank event for the DSI v2 video-transfer
wait, rather than the DSI VIDEO_DONE completion that does not fire here.
Missing CRTC or failed wait aborts the transfer before DMA. 6G retains its
completion mechanism, with completion reset before interrupt unmask and error
propagation. Hardware validation is still pending.

Further source comparison found an ordering mismatch: the stock
`mipi_dsi_cmdlist_commit()` waits for video completion before
`mipi_dsi_cmds_tx()` enables command mode. Mainline enabled command mode first,
then waited inside DMA submission. The MDP-vblank experiment was therefore
preserved on `flo/dsi-vblank-candidate` (`90da6d0c8`) and **not installed**.
The active r25 candidate instead restores the stock V2 handover order, keeps
DSI VIDEO_DONE, resets completion before unmasking, and aborts on timeout.
Clock/runtime-PM failures unwind correctly, including the 6G performance vote.
Its native build and hardware tests remain pending.

### r25 ordering-only result and r26 candidate

r25 (`ff85fc434`) booted #26, but VIDEO_DONE still timed out before command
mode; systemd-backlight restore failed with -110. This establishes that moving
the wait alone is insufficient here. The failed operation no longer submits
unsynchronized DCS data.

A direct DRM WAIT_VBLANK check on card0 returned sequences 2666, 2667, 2668
with waits 16.86, 12.85, 16.30 ms. r26 (`af242cea4`) therefore combines the
reviewed pre-command handover and cleanup with the DRM/MDP frame completion
source. It is not the old post-command MDP experiment. ARM build and checkpatch
pass. Package `7.2_p20261117002551-r0.apk`, SHA256
`2f70b12680c405f19555e9d416013183cb0469c9eddeaf50e78532349e4dbccd`.
Installation stopped before `apk add`, while copying the APK database into
`/var/tmp/nexus7-before-r26-brightness/apk-db`. r26 is **not installed**;
the last booted kernel remains r25 (#26). The backup process is blocked on
filesystem I/O. The installer parent (PID 1149) was killed and confirmed absent;
the copy child (PID 1153) remains in uninterruptible disk sleep, reparented to
PID 1, with SIGKILL requested. No subsequent installation step can proceed.

The eMMC request counters remain unchanged with 11 requests in flight.
SysRq-w shows the MMC dispatch worker in `mmc_blk_rw_wait`, the timeout worker
waiting in `synchronize_srcu`, and ext4 journal threads waiting for I/O. The
kernel is still reachable over Wi-Fi, but the filesystem cannot be assumed to
sync. The captured blocked-task dump is saved on the host in the private
recovery directory. A forced reboot requires the pending user decision because
unsynced writes can be lost. No forced reboot has been performed.

A separate clock defect is visible in debugfs: requested 52 MHz, actual 64 MHz.
In this tree, GCC MSM8960 SDCC sources use legacy `clk_rcg_ops`, whose rate
selection rounds upward. The table selects 64 MHz for a 52 MHz request.
Existing `clk_rcg_floor_ops` also uses the upward `determine_rate` callback,
so switching the SDCC ops alone would be insufficient. A future correction
must make determination and programming consistently round downward, while
preserving the minimum table rate for the MMCI probe's 100 kHz rounding
request (the SDCC table begins at 144 kHz). Expected 52 MHz result: 48 MHz.
This is not yet implemented or established as the cause of the I/O hang.
No live clock/reset/register changes were attempted on the mounted root disk.

Hardware validation of r26 remains pending storage recovery. The user's last
visual result belongs to r24: brightness varies, but whole-screen glitches
remain. Neither r25 nor r26 has a successful visual validation.

### Recovery after failed boot, 2026-11-17

The user rebooted and then entered recovery because normal boot did not finish.
ADB recovery access works. Saved `/proc/last_kmsg` on the host before any writes.
It identifies r25 (#26), not r26. At 20.389 s a synchronous `mmc_get_ext_csd`
inside `mmc_run_bkops` hits the warning in `mmci_dmae_get_next_data`: no host
cookie but a pending pre-mapped descriptor. The function nevertheless takes
that descriptor. `mmci_dmae_prep_data` then sees an existing current descriptor
and skips preparing the synchronous request's own scatterlist. A DMA error
follows; the fallback releases BAM DMA from hard IRQ and BUGs in `vunmap`.
The reserved-RAM log reports unrecoverable blocks, so individual corrupted
bytes are not treated as reliable, but the stack and source agree.

Plan for recovery:
1. Check unmounted filesystems read-only with a compatible e2fsck; preserve
   original journal/metadata before any necessary repair.
2. Add KUnit coverage of the actual MMCI descriptor handover for synchronous,
   pre-mapped and DMA-disabled requests. Confirm the synchronous case fails
   against the current code, then prevent it from consuming `next_data`.
3. Independently review the descriptor lifecycle and error path, compile ARM,
   and prepare a recovery-installable kernel retaining r26 display changes.
4. Recover storage and verify the boot and disk I/O before brightness tests.

The separate 52-to-64 MHz rounding issue is retained as an open driver defect;
it is not substituted for the directly observed descriptor-ownership failure.

Recovery verification: modern e2fsck 1.47.4 ran from recovery RAM against the
unmounted root loop device. `-fn` found no structural damage; journal replay
with `-p` returned 0 and reported a clean filesystem. Before replay, e2image
saved a 101949440-byte metadata QCOW2 on the host, SHA256
`15114d1e072393cfc057a79a9012e6683f71185747bb5530857aaa68b00041e7`.
Both boot filesystems also pass read-only checks. p22's vmlinuz matches the
original r25 APK SHA256 `235c76542081c31bc95353c774d8c7127e08ec92ac0b17b1a04d51a5d0f34455`.
The inner `/boot` copy differs in a 1024-byte span (1023 differing bytes),
8395776–8396799, which is zeroed. Both copies were saved before replacement.
The booted kernel is read from p22, whose kernel file is intact. Do not infer
that a structurally clean filesystem guarantees every file's content.
Read-only `apk audit --system --recursive /usr /opt` reports seven content
changes, all regenerated modules.{dep,alias,symbols} and modules.builtin.bin;
its many `x` records require separate interpretation under the old recovery.

Regression test of the real `mmci_dmae_get_next_data` callback: old code failed
all four ownership assertions for the synchronous case; prepared and PIO cases
passed. With the cookie guard, 3/3 pass. Independent review finds no blocker
for this narrow fix. Commit `45f75744c`, branch `flo/mmci-bkops-r27`, retains
r26 display changes and does not include DSPS. ARM build in progress.
The separate release-from-hardIRQ and dangling-prepared-descriptor-on-error
paths remain open; these tests do not cover real DMA/unmapping/error recovery.

r27 recovery installation completed. APK `7.2_p20261117101447-r0`, SHA256
`9e409f4cad9faf6f50006c530fac896a88bd130636be2f1672a071fde5960477`;
package verified to contain no DSPS module. Kernel SHA256
`b8a8e17804ba07569f400f6a625cf5672ec3ed28fad52c97bab218243b789358`.
Inner boot's orphan-present feature prevented the old recovery kernel from
mounting it writable until modern e2fsck journal replay; replay returned0.
No filesystem feature was disabled or reformatted. Installed with package
scripts disabled, then depmod/mkinitfs and nexus7-sync-boot explicitly run.
Backup of boot/APK database/cmdline at `/var/tmp/nexus7-before-r27-recovery`.
Both boot sets compared identical, filesystems cleanly unmounted and loop
devices detached, eMMC in-flight0. Normal reboot/hardware validation follows.
