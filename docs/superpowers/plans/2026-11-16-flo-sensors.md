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
