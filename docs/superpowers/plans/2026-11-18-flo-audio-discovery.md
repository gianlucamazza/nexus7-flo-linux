# Flo Audio Codec Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Identify the actual tabla SLIMbus product code on this Nexus 7 without enabling an audio route or speaker amplifier.

**Architecture:** An isolated kernel branch from the GPIO77-corrected r29 base enables the APQ8064 SLIMbus controller and a flo-only diagnostic power sequencer. The sequencer is off at boot; a manual sysfs write holds the controller awake, asserts reset, enables the documented rails, releases reset and enables MCLK. The SLIMbus core's `REPORT_PRESENT` path then creates devices with their actual enumeration addresses. This branch is not the final audio driver and will not be merged as the permanent codec solution.

**Tech Stack:** Linux 7.2 ARMv7, device tree, platform driver, regulator, GPIO, common clock, runtime PM, SLIMbus, KUnit, postmarketOS kernel package.

**Spec:** `docs/hw/AUDIO-DISCOVERY-20261118.md`

## Global Constraints

- Do not create an ALSA card, codec device with a guessed product code, or speaker GPIO consumer in this discovery kernel.
- Codec VDDIO/VDDA_RX/VDDA_TX/VDD_CP use PM8921 S4 at 1.8 V; VDDD_CDC_D/VDDA_A_1P2V use PM8921 L25 at 1.25 V.
- Reset is PM8921 GPIO34 active-low; MCLK is TLMM GPIO39 via `CODEC_I2S_SPKR_OSR_CLK` at 12.288 MHz; SLIMbus pins are TLMM GPIO40/41.
- Keep GPIO77 input and the r29 rollback package/boot backup. No native install without physical recovery available.
- Every failure path asserts reset and releases MCLK, rails, and runtime-PM reference. Suspend/removal leaves the codec off.
- A product code is established only by `REPORT_PRESENT`/logical address, not by the DT node name or a registered but unenumerated device.

## Review Focus

- Controller probe has not completed when the discovery device probes: defer without touching supplies.
- A regulator or clock operation fails partway through power-on: unwind all acquired resources in reverse order.
- A second write of `1` or `0` arrives: preserve idempotence and balanced runtime-PM counts.
- Suspend occurs while discovery power is on: assert reset and shut down; do not restart without another explicit write.
- Both tabla product codes or no product code appear: record exact observed addresses, never infer hardware from the expected set.

---

### Task 1: Controlled power sequencer

**Files:**
- Create: `drivers/misc/flo_tabla_discovery.c`
- Modify: `drivers/misc/Kconfig`, `drivers/misc/Makefile`
- Test: `drivers/misc/flo_tabla_discovery_test.c` (KUnit sequence/error-injection tests)

**Interfaces:**
- Consumes DT compatible `asus,flo-tabla-discovery`, phandle `slim-controller`, supplies `vdd-1p8` and `vdd-1p25`, `reset-gpios`, clock `mclk`.
- Produces `/sys/bus/platform/devices/<device>/enabled`: read `0`/`1`, write `0`/`1`; no automatic enable.

- [ ] Write tests for idempotent on/off, controller not bound, each failed enable step, suspend, and remove; assert no active MCLK or rails after failure.
- [ ] Run KUnit and record failing assertions before implementation.
- [ ] Implement `CONFIG_FLO_TABLA_DISCOVERY` as a mutex-protected state machine: obtain and assert reset at probe; on write `1`, resume controller, enable S4 then L25, hold reset for at least 20 ms, deassert, wait 20 ms, set 12.288 MHz and enable MCLK; on `0` or error, assert reset, disable MCLK, disable L25 then S4, release runtime PM. Add a device link to the SLIMbus controller and defer probe until it is bound.
- [ ] Run KUnit, ARM object build, checkpatch and `git diff --check`; commit driver and tests.

### Task 2: Flo device tree and configuration

**Files:**
- Modify: `arch/arm/boot/dts/qcom/qcom-apq8064-asus-nexus7-flo.dts`.

**Interfaces:**
- Produces the DT node and pinctrl/supply phandles consumed by Task 1; enables `&slimbus` but leaves `&slimbam`, codec audio devices, sound card and speaker amplifier disabled.

- [ ] Add DT assertions that the node has exactly the two named rails, active-low reset GPIO34, MCLK GPIO39, SLIMbus GPIO40/41, and no codec or amplifier node; run them RED.
- [ ] Add the discovery node, pinctrl states and `&slimbus` status.
- [ ] Build the flo DTB, inspect the compiled node and run DT tests GREEN; commit DT/config.

### Task 3: Package and native discovery

**Files:**
- Modify: isolated pmaports kernel package recipe/patch series and `config-postmarketos-qcom-apq8064.armv7`; update `docs/hw/AUDIO-DISCOVERY-20261118.md` and `docs/hw/ISSUES-20261117.md` with results.

**Interfaces:**
- Consumes Tasks 1–2; produces a staged APK, then exact observed SLIMbus enumeration addresses when recovery is available.

- [ ] Enable `CONFIG_SLIMBUS=y`, `CONFIG_SLIM_QCOM_CTRL=y` and `CONFIG_FLO_TABLA_DISCOVERY=y` in the packaged config. Build the complete ARM kernel and a clean APK; inspect config, DTB, checksums and `apk add --simulate`; keep r29 rollback verified.
- [ ] With physical recovery available, install only this isolated kernel, reboot, verify Wi-Fi/greeter/touch/charge, and confirm the discovery device starts disabled.
- [ ] Write `1` once, capture supply/reset/clock state, controller IRQs, journal `REPORT_PRESENT`, and `/sys/bus/slimbus/devices/*` logical-address status; write `0` and verify all resources return off.
- [ ] Repeat on/off and suspend/error checks only after the first cycle is safe. Identify 1.x (`0x10`) or 2.x (`0x60`) from the observed product code, or record no enumeration with electrical prerequisites still unverified.
- [ ] Restore r29 if any boot or power regression occurs. Commit only verified source/docs; keep this diagnostic branch separate from the final audio implementation.
