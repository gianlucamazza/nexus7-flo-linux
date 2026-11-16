# Flo accelerometer: implementation status and verified bring-up inputs

The accelerometer is **not functional** on the running r23 kernel. The completed
implementation here is a read-only firmware/memory audit, not a sensor driver.
No kernel, regulator, firmware, calibration or tablet configuration was changed.

## Reproduce the audit

Run as root on the tablet, using Python 3 (standard library only):

```
python3 flo-sensor-audit.py
```

Or run locally on copied firmware and a matching `/proc/iomem` snapshot:

```
python3 scripts/flo-sensor-audit.py --firmware-dir /path/to/firmware --iomem /path/to/iomem
python3 -m unittest discover -s tests -v
```

Exit 0 means the supported split ELF structure and blob lengths validate;
exit 1 means invalid or unreadable firmware. **Exit 0 does not authorize boot.**
Inspect `ddr_memory_check` separately. Even `no-overlap-reservation-unverified`
does not prove a DT carveout exists. Missing/redacted iomem produces `unknown`.
Hashes identify inputs; this tool does not authenticate Qualcomm signatures or
compare payloads against an independently trusted manifest. No network access,
I2C probes, mounts or hardware writes are performed by the tool.

The real-device result is saved in
[evidence/flo-dsps-audit-2026-11-16.json](evidence/flo-dsps-audit-2026-11-16.json).
It reports `overlaps-system-ram`. It was obtained by running the script through
SSH standard input over Wi-Fi, without installing a daemon or changing boot.
The tablet reported `7.2.0-postmarketos-qcom-apq8064 #24`, and its only listed
remoteproc was `3200800.riva-pil`, running. No IIO device was listed.

## Primary-source baseline

Vendor kernel sources below are pinned to AOSP commit
`75977811169d779c039da38e63a1cac4e0cd1693`
(`android-msm-flo-3.4-lollipop-mr1` at retrieval).

| Source | Relevant facts |
|---|---|
| [pil-dsps.c](https://android.googlesource.com/kernel/msm/+/75977811169d779c039da38e63a1cac4e0cd1693/arch/arm/mach-msm/pil-dsps.c) | Uses secure PAS when supported; otherwise the PPSS reset/clock sequence. These are distinct paths. |
| [scm-pas.h](https://android.googlesource.com/kernel/msm/+/75977811169d779c039da38e63a1cac4e0cd1693/arch/arm/mach-msm/scm-pas.h) | `PAS_DSPS` is enum value **2**, not the WCNSS or ADSP ID. |
| [devices-8064.c](https://android.googlesource.com/kernel/msm/+/75977811169d779c039da38e63a1cac4e0cd1693/arch/arm/mach-msm/devices-8064.c) | PPSS memory windows, watchdog resource, `dsps_pwr_ctl_en = 1`; AP clock/regulator arrays empty. |
| [msm_dsps.c](https://android.googlesource.com/kernel/msm/+/75977811169d779c039da38e63a1cac4e0cd1693/arch/arm/mach-msm/msm_dsps.c) | First open loads firmware; close unloads; watchdog and SMSM reset handling; AP pause/resume only when DSPS power control is disabled. |
| [msm_smd.h](https://android.googlesource.com/kernel/msm/+/75977811169d779c039da38e63a1cac4e0cd1693/arch/arm/mach-msm/include/mach/msm_smd.h) | `SMD_APPS_DSPS` edge ID **3**; processor host ID and edge ID are different enums. |
| [irqs-8064.h](https://android.googlesource.com/kernel/msm/+/75977811169d779c039da38e63a1cac4e0cd1693/arch/arm/mach-msm/include/mach/irqs-8064.h) | DSPS SMD GIC SPI **138**, SMSM SPI **137**, watchdog SPI **213**. |
| [Kconfig](https://android.googlesource.com/kernel/msm/+/75977811169d779c039da38e63a1cac4e0cd1693/arch/arm/mach-msm/Kconfig) | Describes DSPS as **ARM7**. Live firmware confirms ELF32 LE, `e_machine = 40` (ARM). |

The current fork already describes DSPS SMSM host 4 and IPC at
`sps_sic_non_secure + 0x4094`, bit 0. This does not instantiate DSPS remoteproc
or its SMD edge. **Do not confuse SMSM IPC with SMD IPC**; the latter must be
verified from matching interrupt configuration before adding the edge.

## Firmware memory map

All ranges below are half-open. Physical and virtual addresses differ in TCM;
a loader must use the correct mapping rather than assume identity.

| Window | Physical range | Firmware segment | Virtual start | File bytes | Memory bytes |
|---|---|---|---|---:|---:|
| TCM code | `0x12000000–0x12028000` | b02 | `0x0` | 116200 | 157644 |
| TCM buffer | `0x12040000–0x12044000` | b04 | `0x28000` | 6720 | 15476 |
| PIPE | `0x12800000–0x12804000` | b05 | `0x12800000` | 13996 | 15792 |
| DDR | `0x8fe00000–0x8ff00000` | b03 | `0x8fe00000` | 62020 | 64916 |

b00 is ELF metadata; b01 is the hash/authentication segment, not an ordinary
load segment. The full 1 MiB DDR window comes from vendor platform data;
reserve it explicitly before any DSPS test, not just b03's initialized bytes.
The live kernel exposes System RAM from `0x8f700000` through `0xfffffffe`,
including this DDR window. Starting DSPS now risks corrupting Linux memory.

The existing `qcom_mdt_load()` assumes a single linear backing region; this
image needs scatter mappings for TCM/PIPE/DDR. Mapping the entire address span
or importing a Q6 reset driver would be an incorrect implementation.

## Chip, bus, registry and transport evidence

Firmware strings include `sns_dd_mpu6050.c`, MPU6050/6500/6515 driver names,
AK8963 and AL3320. This is a **driver capability inventory**, not confirmation
of the populated accelerometer. `cc_gsbi2_qup_apps_clk` provides evidence that
GSBI2 occurs in the firmware; it does not prove rail names, physical addresses,
IRQs or safe simultaneous AP access. The old experimental patch
`0007-flo-sensors-gsbi2-bus-probe.patch` is not a validated bring-up procedure.
Do not scan an inferred bus or force regulators always-on.

The firmware contains `SENSOR`, `sns_smr_dsps.c`, SMD/SMEM support and
`sns_pm_send_qmi_msg` strings. A QMI-related string alone does not prove QRTR
framing, service IDs or compatibility with modern SMGR drivers. Firmware boot
and discovery of a channel will not by themselves establish working IIO.

`persist` was inspected using **debugfs without `-w`**, not mounted or replayed.
Only the sensor registry payload was copied for analysis:

- `/sensors/sns.reg`: 5125 bytes; SHA256
  `ec4e14d35a75f6f5f36224d771c51aa5e39ca0a8e85d8d5c8fe867ba1aa8532e`.
- `/sensors/settings`: present, one byte; unchanged.
- Registry and firmware payloads are not committed or published.

A private research copy is retained under
`~/nexus7-recovery-20261114/sensors-research-20261116/`.
The open [sns-reg project](https://gitlab.com/msm8996-mainline/sns-reg)
was inspected at `4d238e5f0baba3fb77456fe2bffbf8e8f18a71a0`.
Its generator's mapping is documented as derived from `sensors.qti` and extends
past this registry's end (e.g. offset `0x1500`). Its group map therefore cannot
be assumed to describe flo; no generated mapping was installed or used to
infer calibration or sensor identity.

## Remaining implementation gates

1. Verify SMD IPC and the actual SENSOR packet format, service discovery and
   registry transactions from matching sources or captured stock traffic.
   Resolve ownership of bus, clocks, resets and sensor power.
2. Add a native ARM7 DSPS remoteproc driver, DT binding and reserved-memory
   region. Validate every segment before writes; use secure/nonsecure paths
   only when their lifecycle is implemented. Handle boot failure, watchdog,
   reset, shutdown, reload and suspend without corrupting shared memory.
3. Expose actual measurements through IIO. Retain valid per-device calibration;
   verify scale, axes, mount matrix, timestamps and six static poses. Never
   register a synthetic accelerometer merely to make a proxy detect one.
4. Integrate iio-sensor-proxy events and automatic rotation with the existing
   manual lock. Test four orientations, flat stability, greeter and session,
   suspend/resume, idle power and three boots per project kernel policy.

These gates are not completed by the audit. There is no installed sensor
workaround, background polling loop or claim of accelerometer support.
