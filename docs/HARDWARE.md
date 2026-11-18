# Hardware support matrix

Device: ASUS/Google Nexus 7 (2013) Wi-Fi, `flo` / `asus-flo`, Qualcomm APQ8064.
Reference build: kernel **r29** from [`linux-flo`](https://github.com/gianlucamazza/linux-flo)
(`flo/main`) plus the userland in this repository and
[`flo-shell`](https://github.com/gianlucamazza/flo-shell).

Status values:

- **working**: verified on the tablet, as recorded in the linked notes
- **partial**: works, with documented limitations or open bugs
- **not working**: verified absent or broken on the tablet
- **untested**: no test on the tablet is recorded in this repository

Statuses come only from this repository's notes and commit history (state as of
18 Nov 2026). Most notes are in Italian. Anything not recorded is listed as
untested.

| Component | Status | Notes | Evidence |
|---|---|---|---|
| Display panel (JDI, DSI) | partial | Image and UI work. A physical glitch and `dsi_err_worker` errors appear while the brightness changes; the root cause in the DSI/MDP pipeline is still open | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove), [DSI-BRIGHTNESS](hw/DSI-BRIGHTNESS.md) |
| Backlight / brightness | partial | The slider changes the real brightness (8-bit DCS `0x51`); see the display glitch above | [ISSUES](hw/ISSUES-20261117.md#correzioni-già-comprovate) |
| Touchscreen (elants) | working | Touch, greeter and adaptive UI have positive tests; physical size taken from DT. A Hyprland null dereference on touch-down is fixed in a local package; its trigger is still being investigated | [STATUS](STATUS.md), [HYPRLAND-CRASH](hw/HYPRLAND-CRASH-20261118.md) |
| Wi-Fi (WCN3660, wcn36xx) | partial | Associates and carries traffic. Recurring `hal_start_scan err=5` during software scans; the channel-limit fix is built but not installed yet | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| Bluetooth (WCN3660, btqcomsmd) | working | `hci0` present, BlueZ active, scanning finds devices (kernel r23 and later). Audio profiles untested (no sound card) | [STATUS](STATUS.md), [ISSUES](hw/ISSUES-20261117.md#correzioni-già-comprovate) |
| Audio (WCD9310 codec, speakers, mics, jack) | not working | No ALSA card. SLIMbus/WCD9310 integration and speaker/capture paths are missing; a discovery kernel is staged, not installed | [AUDIO-DISCOVERY](hw/AUDIO-DISCOVERY-20261118.md), [MATRIX](hw/MATRIX.md) |
| eMMC storage (MMCI + DMA) | partial | r28/r29 DMA and clock fixes pass KUnit and repeated native I/O tests; long-run and error-path coverage still pending | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| USB device mode (gadget, USB networking) | partial | Works with the USB ID GPIO fix; earlier sessions recorded USB drops | [USB-DIAGNOSIS](USB-DIAGNOSIS.md), [ISSUES](hw/ISSUES-20261117.md) |
| USB host / OTG | untested | Draft DT patch only (marked high risk: 5 V from the battery) | [MATRIX](hw/MATRIX.md) |
| Charging (SMB345) | partial | Charges with the display off; with the display on the battery still drains. Charger branch in testing | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| Battery fuel gauge (bq27541) | working | Capacity, current and status are reported and used for the charging measurements | [ISSUES](hw/ISSUES-20261117.md) |
| Sensors (accelerometer, gyro, compass, light, via DSPS) | not working | No IIO devices. DSPS firmware loading and memory reservation are identified; the DSPS kernel branch passes KUnit but is not installed | [SENSORS](hw/SENSORS.md), [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| Auto-rotation | not working | Depends on sensors; the UI supports manual rotation | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| GPU (Adreno 320, freedreno/Mesa) | partial | The shell renders on the GPU. GTK4 apps use cairo because of an earlier A320 hang and GL crashes in GTK4 Settings | [STATUS](STATUS.md), [GTK4-GL-CRASH](hw/GTK4-GL-CRASH-20261118.md) |
| CPU frequency scaling / thermal | partial | cpufreq and thermal throttling work in limited tests; `cpuidle.off=1` workaround still active | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| Suspend to RAM | not working | No platform suspend ops in mainline for this SoC; s2idle only | [MATRIX](hw/MATRIX.md) |
| Hall sensor (cover) | untested | Draft DT patch | [MATRIX](hw/MATRIX.md) |
| Notification LED | untested | Draft DT patch, marked high risk | [MATRIX](hw/MATRIX.md) |
| PMIC ADC / hwmon | untested | Config and optional DT patch drafted | [MATRIX](hw/MATRIX.md) |
| Cameras | not working | No APQ8064 CSI/VFE host in the current kernel | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| GPS | untested | Not integrated | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| NFC | untested | Not integrated | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| Wireless charging | untested | Not integrated | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| SlimPort (HDMI over USB) | untested | Not integrated | [ISSUES](hw/ISSUES-20261117.md#problemi-aperti-e-stato-delle-prove) |
| Hardware power / volume keys | untested | No dedicated test recorded (the power-off/reboot buttons confirmed in [STATUS](STATUS.md) are the on-screen ones) | — |
