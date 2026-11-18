# Flo sensor bring-up implementation plan

> **For agentic workers:** Use superpowers:executing-plans task by task.

**Goal:** Expose real accelerometer samples through IIO and integrate stable automatic orientation.

**Architecture:** Establish firmware/memory/transport facts before hardware writes. Use a native ARM7 DSPS remoteproc driver and the actual SENSOR transport if DSPS ownership is required; use existing IIO drivers only if direct AP ownership is proven. Keep calibration and orientation in standard Linux interfaces.

**Tech Stack:** Linux remoteproc, Qualcomm SCM/SMEM/SMD, IIO, iio-sensor-proxy, Quickshell.

**Spec:** User requirements: complete, correct, modern; no technical debt or workarounds.

## Global constraints

- Preserve Wi-Fi access and diagnostic key.
- No guessed sensor addresses, supplies, mount matrices or protocol compatibility.
- Do not start DSPS while its firmware DDR overlaps Linux RAM.
- Firmware strings are supported driver names, not a physical chip inventory.
- Original firmware may be loaded with standard Linux mechanisms.

## Review focus

Malformed firmware must fail closed; hashes must describe actual files; truncated or mismatched split segments must be rejected; unavailable memory evidence must remain unknown; passing a memory check must never be represented as permission to boot.

### Task 1: Reproducible firmware and memory audit

Files: `scripts/flo-sensor-audit.py`, `tests/test_flo_sensor_audit.py`.
Interface: `audit(firmware_dir: Path, iomem: Path) -> dict`; CLI prints JSON, exits 0 when firmware validates, 1 for invalid/unreadable input. Memory safety is separately reported, never boot authorization.

- [x] Write tests using hand-built ELF32 split images, covering physical versus virtual addresses, hash/non-load segments, bounds/overlap, corrupt blobs and absent/redacted iomem.
- [x] Watch tests fail, implement validation, run the complete unittest suite.
- [x] Run against firmware and iomem collected read-only from the tablet; preserve hashes and output.

### Task 2: Native DSPS remoteproc

Prerequisites: establish ARM7 memory windows, PAS ID, reset/clock ownership, crash and shutdown IRQ semantics. Implement bindings, validated scatter loading, lifecycle and recovery. Reserve DDR in DT before enabling the driver. Build with warnings enabled, validate bindings, install with previous boot image retained. Require three successful boots and verified shutdown/recovery. Do not substitute a Q6 driver.

### Task 3: SENSOR transport, registry and IIO

Prerequisites: document actual packet framing, service discovery and registry requests from matching sources or captured traffic. Implement the native transport and typed IIO channels, timestamps, scales and error handling. Preserve per-device registry calibration. Verify six static poses and dynamic samples on hardware.

### Task 4: Orientation integration

After real IIO samples: integrate iio-sensor-proxy orientation events; maintain manual rotation lock; verify four orientations, flat/hysteresis behavior, greeter/session transitions and suspend/resume. Test idle power and remove experimental probes.

## Execution record

2026-11-16: Tasks 2–4 lack prerequisite protocol/lifecycle evidence. No speculative driver will be installed. Task 1 is independently useful and does not make the accelerometer functional. Continue research from the primary-source findings in `docs/hw/SENSORS.md`.

Task 1 verification: 14 unittest tests pass; independent review findings reproduced
and corrected with regression tests. Final live audit matches saved evidence exactly;
RIVA remains running, no failed systemd units, kernel unchanged, no IIO devices.
Ruling: tasks 2–4 remain unimplemented, not completed by an audit. Protocol capture
or matching source analysis is required before a correct driver can be written.

## Task 2 execution — secure DSPS remoteproc

New evidence: original `last_kmsg-after-test:205` reports
`pil_dsps pil_dsps: using secure boot`. Historical upstream APQ8064 DTS
confirms SMD IPC `sps_sic_non_secure + 0x4080`, bit 0, edge 3, SPI 138.
`SMSM_RESET = 0x40` is bit 6. These resolve the loader/IPC prerequisites;
the higher-level SENSOR protocol remains independent and unknown.

Files in the companion `linux-flo` repository, branch `flo/dsps-r24`:
- `drivers/remoteproc/qcom_dsps_fw.h`: bounded ARM ELF32 split-MDT validation
  against mapped physical regions, metadata/hash, overflow and overlap checks.
- `drivers/remoteproc/qcom_dsps_test.c`: KUnit tests for valid scattered image,
  malformed headers/hash metadata, invalid/overlapping ranges and relocation.
- `drivers/remoteproc/qcom_dsps.c`: secure PAS ID 2 only; reject unsupported PAS;
  preload and validate every blob before PAS initialization and MMIO writes;
  copy into mapped SRAM/DDR, zero BSS; start/stop, fatal/watchdog handling and
  SMD subdevice lifetime managed by remoteproc. No nonsecure fallback guessed.
- `Documentation/devicetree/bindings/remoteproc/qcom,apq8064-dsps-pil.yaml`:
  PPSS control plus TCM/PIPE mappings, reserved DDR, watchdog/SMSM interrupts,
  firmware name and SMD edge.
- SoC/board DT: DSPS disabled at SoC level, reserved DDR and enabled on flo.
  Driver registers with `auto_boot = false` during bring-up. No AP I2C probing.
- Package config/APKBUILD: version r24 plus driver and DT patches.

Verification: KUnit first RED then GREEN; ARM driver compilation; binding and
DT validation; independent review before install; preserve previous boot image;
first reboot verifies carveout with DSPS offline, then manually start and inspect
SMD channels. Stop/restart and three boots are required before calling stable.
Ruling: use the existing incremental source/build location with a dedicated
kernel branch, preserving the clean r23 branch and `.output` cache.

Task 2 intermediate checks: ARM kernel/module build succeeded; checkpatch reports
zero warnings/errors on the three new C files; dt-doc-validate passes and full
kernel schema collection validates flo's new node without diagnostics. KUnit
5/5 GREEN after initial RED (valid image rejected by stub). Nothing installed.

Independent review identified four issues to fix before packaging/install:
1. Recovery-disabled CRASHED teardown: rproc_shutdown rejects CRASHED.
2. PAS shutdown failure followed by retry: common SMD stop is not idempotent;
   first stop already unregisters SMD before the driver's stop callback.
3. Enable SMSM fatal notification before PAS auth/reset, not after it; otherwise
   SMSM unmask snapshots away a fatal edge during boot. Unwind IRQs on failure.
4. Require e_phoff == sizeof(ELF32 header), since common dump helper ignores it.
Additional root finding: generic coredump runs after PAS stop; do not read SRAM
then without proving it remains accessible. DDR-only dump is safe to implement.

User reported broken brightness while this work was being reviewed. Priority
shifted to that regression: tablet brightnessctl denied writes (tablet is not
in video group), but UI kept optimistic values; logind SetBrightness works for
active session c3. DSPS branch remains uninstalled pending the fixes above.

2026-11-17 display regression follow-up: shell r9 fixes permission/backend and
readback; kernel r24 (`51ad273c2`) fixes JDI brightness wire format, but user
still observes glitches and DSI VIDEO_DONE timeout remains. r25 display-only
candidate restores the original V2 wait-before-command-enable order. Alternate
MDP-vblank candidate (`90da6d0c8`) preserved but uninstalled. After display
validation, resume DSPS WIP `e14857e3e` and address the four review issues plus
SRAM coredump accessibility before rebasing onto the validated display branch.
