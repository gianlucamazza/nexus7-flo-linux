# Flo accelerometer: implementation status and verified bring-up inputs

The accelerometer is **not functional** on the running r29 kernel. This
document began as a read-only firmware/memory audit. A separate host branch,
`flo/dsps-lifecycle` (`4e89c8ee3`), now contains an ARM7 remoteproc loader,
SMD edge, and a reserved 1 MiB DDR region. Its ARMv7 package `7.2-r32` was
built and staged, but has not been installed or booted. No IIO sensor exists
on the tablet. The audit below did not change firmware or calibration.

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
Schema 2 also reports `ddr_dt_reservation`: `exact-no-map` requires the live
`dsps@8fe00000` node to contain the exact 1 MiB big-endian `reg` and a
`no-map` property. This is an independent check; it cannot override a
`ddr_memory_check` of `overlaps-system-ram` or `unknown`. Neither field alone
authorizes starting the remote processor.
Hashes identify inputs; this tool does not authenticate Qualcomm signatures or
compare payloads against an independently trusted manifest. No network access,
I2C probes, mounts or hardware writes are performed by the tool.

The real-device result is saved in
[evidence/flo-dsps-audit-2026-11-16.json](evidence/flo-dsps-audit-2026-11-16.json).
It reports `overlaps-system-ram`. It was obtained by running the script through
SSH standard input over Wi-Fi, without installing a daemon or changing boot.
The tablet reported `7.2.0-postmarketos-qcom-apq8064 #24`, and its only listed
remoteproc was `3200800.riva-pil`, running. No IIO device was listed.
Re-running the schema-2 audit on the stable r29 boot after the 18 November
cable reconnect reports `ddr_dt_reservation=missing` and
`ddr_memory_check=overlaps-system-ram`. This is the expected unsafe baseline
against which the r32 boot will be compared; DSPS was not started.

The same read-only schema-2 audit on the current r50 boot (20 November)
still reports `ddr_dt_reservation=missing` and
`ddr_memory_check=overlaps-system-ram`. The live System RAM range intersects
the full 1 MiB DSPS DDR window. No DSPS start or firmware modification was
attempted. This confirms that the r50 baseline still cannot safely launch
DSPS; the isolated carveout/remoteproc branch needs its own boot and memory
validation before any sensor protocol experiment.

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

The r29 fork describes DSPS SMSM host 4 and IPC at
`sps_sic_non_secure + 0x4094`, bit 0. The isolated r32 branch also describes
the SMD edge with GIC SPI 138 and IPC at `sps_sic_non_secure + 0x4080`, bit 0.
**Do not confuse SMSM IPC with SMD IPC**. The SMD edge still needs a native
boot test; source and DT inspection cannot prove that an interrupt arrives.

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

## SENSOR transport and sample format: source reconstruction

The pinned flo [SMD packet driver](https://android.googlesource.com/kernel/msm/+/75977811169d779c039da38e63a1cac4e0cd1693/arch/arm/mach-msm/smd_pkt.c)
maps `/dev/smd_sns_dsps` to channel `SENSOR` on `SMD_APPS_DSPS` edge 3.
This independently matches the `SENSOR` string in the firmware. It is the
SMD packet transport, not a QRTR service name. The r32 DT describes edge 3,
but channel creation and packet exchange have not been observed on flo.
The [AOSP flo proprietary-file manifest](https://android.googlesource.com/device/asus/flo/+/4ffa22bb4af373abff09b8c3423c67235f8e132d/proprietary-blobs.txt)
also lists `sensors.qcom`, `sensors.msm8960.so`, `sns_dsps_tc0001` and
`sns_smr_loopback_test` for this device. That is device-specific evidence
for the original userspace stack and a loopback diagnostic, but the
manifest does not disclose their packet layout or the installed sensor ID.

An open Qualcomm sensor daemon source snapshot at
[`e0666c3`](https://github.com/sethsong90/vendor_qcom/tree/e0666c398903d38e72aeda7042ec2836cd3dba68/sensors/dsps)
shows the candidate application protocol. Its
[`sns_smr_la.c`](https://github.com/sethsong90/vendor_qcom/blob/e0666c398903d38e72aeda7042ec2836cd3dba68/sensors/dsps/sensordaemon/smr/src/sns_smr_la.c)
opens `/dev/smd_sns_dsps` except on MSM8974, reads one SMD packet into an
SMR message, and encodes outgoing bodies with `qmi_idl_message_encode()`.
`SMR_ENCODE_ON` is defined in its
[`sns_smr_priv.h`](https://github.com/sethsong90/vendor_qcom/blob/e0666c398903d38e72aeda7042ec2836cd3dba68/sensors/dsps/sensordaemon/common/smr/src/sns_smr_priv.h).
The packed [`sns_smr_header_s`](https://github.com/sethsong90/vendor_qcom/blob/e0666c398903d38e72aeda7042ec2836cd3dba68/sensors/dsps/sensordaemon/common/smr/inc/sns_smr_util.h)
is 12 bytes: destination, source, priority, transaction, external-client,
message type, alignment and service are eight one-byte fields, followed by
little-endian 16-bit message ID and body length. The body is a QMI IDL
encoded service message, not a second generic QRTR packet header. This
source is close in generation but **not the exact flo build**; packet layout
must be checked against a live capture before Linux sends requests.

In the same snapshot, [`sns_common_v01.h`](https://github.com/sethsong90/vendor_qcom/blob/e0666c398903d38e72aeda7042ec2836cd3dba68/sensors/dsps/api/sns_common_v01.h)
assigns SMGR service 0. Its
[`sns_smgr_api_v01.h`](https://github.com/sethsong90/vendor_qcom/blob/e0666c398903d38e72aeda7042ec2836cd3dba68/sensors/dsps/api/sns_smgr_api_v01.h)
assigns accelerometer sensor ID 0, version request/response message 1,
periodic report request/response message 2 and indication message 3.
Accelerometer primary samples have three signed Q16 fields in m/s², X/Y/Z
order; the report also carries timestamps, flags and calibration selection.
These are protocol candidates, **not yet measurements from flo**. In
particular, an IIO scale or mount matrix cannot be taken from the header
without validating the firmware response and six physical poses.

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

1. Verify SMD IPC and the candidate SENSOR/SMR packet format, service
   discovery and registry transactions against flo firmware or captured
   stock traffic; the Qualcomm source above is not exact-flo provenance.
   Resolve ownership of bus, clocks, resets and sensor power.
2. Boot-test the isolated ARM7 DSPS remoteproc driver, DT binding and
   reserved-memory region with recovery available. Verify the carveout in
   the live memory map and exercise start, stop, failure, watchdog, reset,
   shutdown, reload and suspend without corrupting shared memory. The host
   build and unit tests do not establish these runtime properties.
3. Expose actual measurements through IIO. Retain valid per-device calibration;
   verify scale, axes, mount matrix, timestamps and six static poses. Never
   register a synthetic accelerometer merely to make a proxy detect one.
4. Integrate iio-sensor-proxy events and automatic rotation with the existing
   manual lock. Test four orientations, flat stability, greeter and session,
   suspend/resume, idle power and three boots per project kernel policy.

These gates are not completed by the audit. There is no installed sensor
workaround, background polling loop or claim of accelerometer support.
