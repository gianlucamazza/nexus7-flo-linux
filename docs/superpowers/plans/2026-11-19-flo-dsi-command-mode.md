# Flo MDP4/DSI Command Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive flo's JDI panel through a complete DRM command-mode scanout path and remove the physical brightness artifact without regressing display, touch or power behavior.

**Architecture:** The stock flo kernel selects MDP4 command mode, TE and software-triggered DSI DMA. Mainline DRM currently uses MDP4 video mode. Implement a command-mode path in MDP4 and DSI with one owner for frame kickoff, completion and vblank; use TE only when physically verified. Preserve the existing video path for other boards.

**Tech Stack:** Linux DRM/KMS, `drm/msm` MDP4 and DSI v2, MIPI DSI, KUnit, pmbootstrap armv7, tracefs.

**Spec:** [Flo DSI brightness design](../specs/2026-11-18-flo-dsi-brightness-design.md).

## Files and responsibilities

- `drivers/gpu/drm/msm/disp/mdp4/mdp4_dsi_encoder.c`: select and enable the command interface for a command-mode panel, retain video behavior elsewhere.
- `drivers/gpu/drm/msm/disp/mdp4/mdp4_crtc.c` and `mdp4_kms.h`: command frame kickoff, completion, atomic flip events and real vblank accounting.
- `drivers/gpu/drm/msm/disp/mdp4/mdp4_kms.c` and `registers/display/mdp4.xml`: carry the attached panel's mode into the encoder and define any missing MDP4 command/TE registers against stock offsets. MDP5 provides an existing `msm_dsi_is_cmd_mode()` modeset pattern, not a drop-in MDP4 implementation.
- `drivers/gpu/drm/msm/dsi/dsi_host.c` and `dsi_manager.c`: expose mode/trigger state to MDP4 and serialize panel DCS with frame DMA.
- `drivers/gpu/drm/panel/panel-jdi-lt070me05000.c`: select command mode only after the complete transport path exists; preserve one-byte `0x51` and power sequencing.
- `arch/arm/boot/dts/qcom/qcom-apq8064-asus-nexus7-flo.dts`: describe TE pin only if GPIO0 and polarity are validated against stock source and live pin state.
- Focused KUnit tests beside the changed driver code, plus `scripts/nexus7-dsi-trace` and private trace artifacts for native validation.

## Task 1: establish hardware and baseline contract

- [ ] Confirm the exact stock flo JDI mode, TE GPIO/polarity, DSI trigger settings and MDP4 DMA/IRQ sequence from the [stock panel configuration](https://android.googlesource.com/kernel/msm/+/android-msm-flo-3.4-marshmallow/drivers/video/msm/mipi_JDI_1080P_pt.c) and [MDP4 command path](https://android.googlesource.com/kernel/msm/+/android-msm-flo-3.4-marshmallow/drivers/video/msm/mdp4_overlay_dsi_cmd.c); record source hashes and differences from current DRM. In stock direct output, `INTR_DMA_P_DONE` completes a frame and `INTR_PRIMARY_RDPTR` reports VSYNC; queued DCS is committed before mixer/frame kickoff.
- [ ] Read GPIO0 and pinctrl state without reconfiguring it; capture current DSI/MDP mode registers and a 38-write brightness trace on r50. Require user observation of the static KMS grid and keep the original backlight value.
- [ ] Archive both r50 boot copies and verify matching checksums before installing another kernel; prove recovery over USB and retain the r50 APK.

## Task 2: implement and test the MDP4 command frame lifecycle

- [ ] Write a failing KUnit test for one atomic flush producing exactly one command-frame kickoff and one completion event, including a second flush queued before the first completes; verify RED against current MDP4.
- [ ] Implement the command-frame state in MDP4 using the stock primary DMA trigger and `MDP4_IRQ_DMA_P_DONE` completion. Keep `PENDING_FLIP` until that IRQ; complete events and release frame resources once, including timeout/disable paths. Keep `MDP4_IRQ_PRIMARY_RDPTR` distinct as a candidate VSYNC source, subject to the TE measurement in Task 3.
- [ ] Verify GREEN, video-mode tests, ARM object build and `checkpatch`; inspect races between IRQ, disable and atomic commits before continuing.

## Task 3: TE and DSI integration

- [ ] Write failing tests for command mode selecting `INTF_DSI_CMD`, DSI command-mode registers, TE/trigger configuration and error unwind; keep the video-mode branch unchanged.
- [ ] Add the mode negotiation between DSI and MDP4, verified TE setup, and serialized panel DCS/frame DMA. Use the hardware IRQ for vblank only if it is observed; otherwise define and test a correct completion-based DRM vblank policy before hardware deployment.
- [ ] Verify GREEN, all relevant DRM/MSM tests, full ARM kernel build and no new warnings. Ensure panel initialization/brightness commands cannot race with an active frame transaction.

## Task 4: deploy one complete candidate and compare

- [ ] Build a signed armv7 APK with a new revision, verify the exact source and patch hashes, simulate an offline kernel-only upgrade, then install with r50 recovery ready.
- [ ] Confirm boot, PIN, login, touch, KMS grid, ordinary flips, idle, lock/DPMS wake and panel power cycles. Revert immediately if any frame or greeter fails.
- [ ] Repeat the 38-write brightness sequence and static grid with user observation; require no distortion, DSI errors, lost flips or stuck completion. Capture trace and compare to r50.
- [ ] Verify charging classification and limits, Wi-Fi, eMMC I/O and guarded `pm_test=devices`. Keep the independent A320 suspend defect open until its own device test passes.
- [ ] Update the driver branch, package overlay, status, issue and rollback hashes. Do not mark brightness fixed before the physical comparison passes.

## Review focus

- Command DMA IRQ arrives during disable: event and buffer references are released exactly once.
- Missing TE pulse: no permanent blocked atomic commit or false vblank completion.
- Brightness DCS overlaps frame DMA: serialization preserves both transactions.
- DPMS off/on: first frame is visible and command engine clocks are balanced.
- Video-mode boards: encoder selection and timing remain unchanged.
