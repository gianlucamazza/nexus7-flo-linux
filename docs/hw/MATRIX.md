# Nexus 7 2013 Wi-Fi (flo) hardware integration matrix, Linux 7.2 apq8064-mainline

This matrix was originally an offline source review; the patches were only
applied and compiled to a dtb. For the current sensor investigation and
read-only tablet evidence, see [SENSORS.md](SENSORS.md).

## Sources

| Tag | What | Where |
|---|---|---|
| V | Vendor kernel, `android.googlesource.com/kernel/msm`, branch `android-msm-flo-3.4-marshmallow-mr2`, commit `ad29d11ee316` | `hw/vendor/msm/` (sparse checkout) |
| D | AOSP `device/asus/flo`, branch `marshmallow-mr2-release`, commit `d46525af1908` | `hw/vendor/device-asus-flo/` |
| M | Mainline fork tree, commit `cc2a6a249989` plus the local patches | `tip/linux-cc2a6a249989…/` |
| C | Current kernel config | pmaports `config-postmarketos-qcom-apq8064.armv7` |

Vendor paths below are relative to `arch/arm/mach-msm/asustek/flo/` unless they
start with another directory.

Feasibility classes: **(a)** config only, **(b)** DT (+config), **(c)** needs
driver work, **(d)** not feasible in mainline today.

## Matrix

| Peripheral | Chip | Bus / address / GPIOs / supplies | Vendor citation | Mainline driver + binding | Configs (now) | Class | Risk |
|---|---|---|---|---|---|---|---|
| Bluetooth | WCN3660 (riva), HCI over SMD | SMD channels; TLMM 16/17 = `riva_bt` function (mainline pinctrl); supplies shared with Wi-Fi | V `arch/arm/configs/flo_defconfig` `CONFIG_BT_HCISMD=y`; D `ueventd.flo.rc` `/dev/smd2`, `/dev/smd3`. GPIO 16/17 are **not** in any flo gpiomux table | `drivers/bluetooth/btqcomsmd.c`, `qcom,wcnss-bt` (node already in `qcom-apq8064.dtsi`) | `BT_QCOMSMD` not set; `BT=m` | (a), plus patch 0003 for the pins | Low |
| PMIC ADC + hwmon | PM8921 XOADC | SSBI 0x197; channels vcoin, vbat, dcin, ichg, vph_pwr, ibat, batt_therm, batt_id, usbin, pmic_therm, 625mv, 125v, chg_temp, xo_therm; reference 1.8 V | V `board-flo-pmic.c` `apq8064_pm8921_adc_channels_data[]`, `apq8064_pm8921_adc_data.adc_vdd_reference = 1800`; `board-flo-regulator.c` `VREG_CONSUMERS(L14)` "vreg_xoadc" | `qcom-pm8xxx-xoadc.c` `qcom,pm8921-adc`; `iio_hwmon.c`; both nodes already in `pm8921.dtsi` | `QCOM_PM8XXX_XOADC`, `SENSORS_IIO_HWMON` not set | (a); optional L14 reference in patch 0008 | Low (config) / High by policy (0008 adds a regulator) |
| EEPROM | 24c128 (per current DT) | GSBI1 I2C 0x52 | **None.** Not present in the vendor board files | `at24`, `atmel,24c128` | `EEPROM_AT24` not set | (a) + patch 0005 (read-only) | Low |
| Hall / lid sensor | GPIO hall switch (no part number in source) | TLMM 36, pull-up, low = closed, wake-up; supply L17 3.0 V on HW rev C/D/E | V `drivers/input/lid.c` (`hall_sensor_gpio = 36`, `input_report_switch(SW_LID, !value)`); `board-flo-gpiomux.c` `asustek_hall_sensor_cfg`; `board-flo.c` `asustek_add_lid()` | `gpio-keys` with `linux,input-type = <EV_SW>` | `KEYBOARD_GPIO=y` | (b) patch 0004 | Low (hardware), medium (a wrong polarity would trigger suspend) |
| Audio codec | Qualcomm WCD9310 "tabla" | SLIMbus (TLMM 40 clk, 41 data), e_addr 2.x `{0,1,0x60,0,0x17,2}` / 1.x `{0,1,0x10,0,0x17,2}`; reset PM8921 GPIO 34; IRQ TLMM 42; MCLK TLMM 39; S4 1.8 V (CP, RX, TX, IO), L25 1.25 V (D, A) | V `board-flo.c` `apq8064_tabla_platform_data`, `apq8064_tabla20_platform_data`, `apq8064_slim_tabla20`; `board-flo-regulator.c` `VREG_CONSUMERS(S4)`, `(L25)`; `board-flo-gpiomux.c` `apq8064_slimbus_config[]`, `apq8064_audio_codec_configs[]`; `board-flo-pmic.c` `pm8921_gpios[]` | `sound/soc/codecs/wcd9310.c` (`slim217,60` only), `sound/soc/qcom/apq8064-tabla.c`, `drivers/slimbus` qcom ctrl; bindings `qcom,wcd9310.yaml`, `qcom,apq8064-tabla.yaml` | `SLIMBUS` not set; `SLIM_QCOM_CTRL`, `SND_SOC_APQ8064_TABLA` hidden | (b) for headphones (patch 0006); (c) for the rest | Medium |
| Speakers + amplifier | Amplifier part not named in source; enable GPIO only | PM8921 GPIO 18 (bottom amp enable); inputs LINEOUT1 + LINEOUT3 | V `sound/soc/msm/apq8064.c` `bottom_spk_pamp_gpio`, `apq8064_common_audio_map[]`; `sound/soc/codecs/wcd9310.c` `tabla_2_x_lineout_2_to_4_map[]`; D `mixer_paths.xml` path "speaker" (RX3, RX4, `RX4 DSM MUX = CIC_OUT`) | Codec driver has no RX3/RX4, LINEOUT1/LINEOUT3; machine driver routes "Speaker" to LINEOUT2/4 | as above | (c): add RX3/RX4 + LINEOUT1/3 to wcd9310, routes to apq8064-tabla | Medium |
| Headphone jack | Codec HPHL/HPHR + GPIO detect | TLMM 45 jack detect (low = inserted), TLMM 62 hook key, TLMM 85 debug-board detect | V `sound/soc/msm/asustek_headset.c` (`JACK_GPIO`, `HS_HOOK_DET`, `DB_DET_GPIO`); `board-flo-gpiomux.c` `apq8064_headphone_configs[]` | `hp-det-gpios` in apq8064-tabla | as above | (b) patch 0006; hook key and headset mic (c) | Low |
| Microphones | Digital mic on DMIC1; headset mic on ADC2 with MICBIAS2 | codec pins; cfilt 1.8/2.7/1.8 V, LDOH 2.85 V | V `board-flo.c` `.micbias`; `asustek_headset.c` `set_hs_micbias()`; D `mixer_paths.xml` "dmic1", "adc2" | No capture path in wcd9310.c ("Capture … not provided by this initial driver") | — | (c) | — |
| Notification LED | PM8921 low-current LED driver 1 | SSBI 0x132; 4 mA max; vendor blinks it via LPG/PWM channel 5 | V `board-flo-pmic.c` `pm8921_led_info[]` ("white"), `pm8921_led_configs[]`; `drivers/leds/leds-pm8xxx.c` `SSBI_REG_ADDR_LED_CTRL_BASE` | `leds-pm8058.c` has the same register layout but only `qcom,pm8058-led` and no current cap; no PM8921 LPG/PWM driver | `LEDS_PM8058=y` | (b) patch 0010 as a stopgap; proper support is (c) | **High** (possible LED overcurrent) |
| USB host / OTG | ChipIdea + SMB345 boost | ID pin TLMM 77 (low = host); VBUS from SMB345 OTG boost, 750 mA; PMIC ID comparator unused | V `drivers/usb/otg/msm_otg.c` `APQ_OTG_ID_PIN`, `id_pin_irq_work_function()`, `msm_otg_start_host()`; `drivers/power/smb345-charger.c` `smb345_configure_otg()`; `board-flo.c` `msm_otg_pdata`; `board-flo-gpiomux.c` `msm8064_sp_gpio_config[]` | `extcon-usb-gpio`, smb347 `usb-vbus` regulator, chipidea `vbus-supply` + `extcon` | `EXTCON_USB_GPIO` not set | (b) patches 0001 + 0009 | **High** (5 V sourced from the battery) |
| GPIO 77 "ext_3p3v" in current DT | — | TLMM 77 | V `board-flo.c` (`apq8064_device_ext_3p3v_vreg` commented out), gpiomux as above | — | — | Bug in the current board file; patch 0001 | Low |
| CPU idle (SPC) | SAW2 v1.1 | — | V `board-flo.c` `msm_spm_data[]`, `spm_power_collapse_without_rpm[]` | `cpuidle-qcom-spm.c`, `drivers/soc/qcom/spm.c` | `ARM_QCOM_SPM_CPUIDLE=y` | Workaround (b) patch 0002; real fix (c) | Low |
| Suspend to RAM | — | — | — | `arch/arm/mach-qcom` holds only `platsmp.c`; nothing registers platform suspend ops | `SUSPEND=y` | (d) today: s2idle only | — |
| IMU / compass / light sensor | **Not named in any vendor source** | Unknown; handled by the DSPS sensor core | V `board-flo.c` `apq8064_init_dsps()`, `devices-8064.c` `msm_dsps_device_8064`; D `init.flo.rc` (`sensors.qcom`, `/persist/lightsensor/AL3010_Config.ini`), `proprietary-blobs.txt` (`dsps.*`) | Drivers exist for likely parts, but there is nothing to bind them to | `INV_MPU6050_*=m`, `AK8975=y`, `AL3010` not set | (c) DSPS driver/transport bring-up; see [SENSORS.md](SENSORS.md). Patch 0007 superseded; do not scan inferred buses | Unresolved ownership/power; not validated |
| NFC | Broadcom BCM2079x | GSBI1 I2C 0x77; IRQ TLMM 32; WAKE PM8921 GPIO 8; VEN PM8921 GPIO 9 | V `board-flo.c` `i2c_bcm2079x[]`, `bcm2079x_pdata`, `config_nfc_gpio()` | None (`drivers/nfc` has no Broadcom I2C NCI driver) | `NFC` not set | (d) / (c) new driver | — |
| SlimPort / HDMI out | Analogix ANX7808 | GSBI1 I2C 0x39 (0x72 >> 1); cable detect TLMM 7; INT TLMM 44; power-down PM8921 GPIO 2; reset PM8921 GPIO 1; 27 MHz clock on TLMM 50 (`gp_clk_1b`); 1.05 V core "slimport_1p0" = L28 | V `board-flo.c` `anx7808_pdata`, `i2c_anx7808_info[]`, `anx7808_switch_onoff()`, `add_i2c_anx7808_device()` (PHY tuning values); `drivers/misc/slimport_anx7808/slimport.c` (`gp_clk_b1` 27 MHz); `board-flo-regulator.c` `VREG_CONSUMERS(L28)` | `analogix-anx78xx.c` has `analogix,anx7808`, but no clock consumer, and it reserves 0x39 itself as a dummy address; no flo PHY tuning | `DRM_ANALOGIX_ANX78XX=m`, `DRM_MSM_HDMI=y` | (c) | Not drafted |
| Rear camera | OmniVision OV5693 (id 0x5690) + VCM actuator | GSBI4 I2C (TLMM 10/11); sensor slave address 0x20 in 8-bit form (7-bit 0x10), actuator 0x11; MCLK TLMM 5; power-down PM8921 GPIO 25; reset PM8921 GPIO 31; 2 data lanes; supplies cam_vdig 1.8 V (L23), cam_vio (LVS5), cam_vana 2.8 V (L8), cam_vaf 2.8 V (L16); mount angle 90 | V `board-flo-camera.c` `ov5693_slave_info`, `apq8064_back_cam_gpio[]`, `CAM1_PWDN`, `CAM1_RSTN`, `ov5693_csi_lane_params`, `apq_8064_back_cam_vreg[]`, `ov5693_init_params`; `board-flo-regulator.c` consumers "4-0040" | `drivers/media/i2c/ov5693.c` exists; **no CSI/VFE host driver for APQ8064** (camss bindings in this tree start at msm8916) | `VIDEO_OV5693` not set | (d) | — |
| Front camera | Aptina MI1040 (id 0x2481) | GSBI4 I2C 0x48 (slave address 0x90 in 8-bit form); MCLK TLMM 4; reset PM8921 GPIO 43; 1 data lane; mount angle 270 | V `board-flo-camera.c` `mi1040_slave_info`, `apq8064_front_cam_gpio[]`, `CAM_RST`, `mi1040_csi_lane_params`, `apq_8064_mi1040_vreg[]`, `mi1040_init_params` | `drivers/media/i2c/mt9m114.c` exists (not checked that it accepts this module); same missing host | — | (d) | — |
| GPS | SoC GSS subsystem (firmware `gss.*`) | internal | V `flo_defconfig` `CONFIG_MSM_PIL_GSS=y`, `board-flo.c` `&msm_gss`; D `proprietary-blobs.txt`, `device-common.mk` (`gps.msm8960`) | No GSS remoteproc or location client | `GNSS` not set | (d) | — |
| Wireless charging | via SMB345 DC input | WPC_POK TLMM 34; enables PM8921 GPIO 28 / 32 | V `board-flo.c` `smb345_pdata_ER`, `GPIO_WPC_POK`; `board-flo-pmic.c` `pm8921_gpios_WPC[]` | smb347 driver has `summit,enable-mains-charging` but no WPC GPIO handling | — | Not analysed further | — |
| Charger interrupt lines | SMB345 | STAT TLMM 22, INOK/ACOK TLMM 23 | V `board-flo-gpiomux.c` `smb345_pin_configs[]`; `drivers/power/smb345-charger.c` `APQ_AP_ACOK 23` | smb347 binding has `interrupts`; current DT gives none | — | (b), not drafted | — |
| Touchscreen reset | Elan eKTF3624 | reset TLMM 31, IRQ TLMM 6 | V `board-flo.c` `TS_RESET_GPIO`, `TS_IRQ_GPIO` | current DT has no reset GPIO; works without | — | (b), not drafted | — |
| Vibrator | none found | — | V `flo_defconfig` has `CONFIG_PMIC8XXX_VIBRATOR=y`, but `board-flo-pmic.c` contains no vibrator platform data | `pm8xxx-vibrator.c` | `INPUT_PM8XXX_VIBRATOR=y` | n/a | — |

## Analyses

### 1. "failed to register cpuidle driver" x4

- The message comes from `cpuidle_register()` (`drivers/cpuidle/cpuidle.c:787`)
  when `cpuidle_register_driver()` fails. `__cpuidle_register_driver()`
  (`drivers/cpuidle/driver.c:225`) returns `-ENODEV` when `cpuidle_disabled()`,
  which is exactly what `cpuidle.off=1` sets. `cpuidle-qcom-spm` registers one
  driver per CPU, hence four lines. `spm_cpuidle_drv_probe()` then swallows
  `-ENODEV` silently.
- So the message is the visible effect of the `cpuidle.off=1` workaround, not
  a separate fault. The underlying problem is the one in the project notes:
  with `CONFIG_ARM_QCOM_SPM_CPUIDLE=y` and no `cpuidle.off=1` the boot hangs,
  i.e. entering `qcom,idle-state-spc` does not come back.
- Patch 0002 removes `cpu-idle-states` from the four flo CPUs. Then
  `dt_init_idle_driver()` finds no state, `spm_cpuidle_register()` returns
  `-ENODEV` before `cpuidle_register()`, nothing is printed, and the CPUs idle
  in WFI. Same runtime state as today, without the command-line parameter.
- Root cause of the SPC hang: **not determined.** Source comparison gives
  these differences between mainline `spm_reg_8064_cpu` (`drivers/soc/qcom/spm.c`)
  and vendor `msm_spm_data[]` (`board-flo.c`), found by reading only:

  | | Mainline, all 4 CPUs | Vendor CPU0 | Vendor CPU1-3 |
  |---|---|---|---|
  | PMIC_DLY | 0x02020004 | 0x03070207 | 0x02070207 |
  | PMIC_DATA_0 | 0x0084009C | 0x0084009C | 0x0060009C |
  | PMIC_DATA_1 | 0x00A4001C | 0x00A4001C | 0x0000001C |
  | Sequence | `03 0f` + `00 24 54 10 09 03 01 10 54 30 0c 24 30 0f` | identical | identical |

  The command sequence and SPC start index (2) match. The PMIC delay value
  and the secondary-CPU PMIC data do not. Also, with the SAW regulators that local patch 0010 enables for
  cpufreq, the SPM driver rewrites the voltage fields of PMIC_DATA at run
  time (`smp_set_vdd_v1_1()`), so the voltage restored on wake depends on the last
  cpufreq transition. Which of these (if any) causes the hang needs a serial
  console on the device; candidates to try in order: vendor PMIC_DLY, vendor
  secondary-CPU PMIC_DATA, SPC with cpufreq pinned to one OPP.

### 2. WCD9310 / SLIMbus audio in this fork

- Provides: Apps-managed SLIMbus controller + BAM (`slimbus`, `slimbam` in the
  dtsi, disabled by default), a `wcd9310` codec driver limited to 48 kHz mono
  playback on RX1/RX2 (earpiece, headphones) and RX5/RX6 (LINEOUT2/LINEOUT4),
  and the `apq8064-tabla` machine driver (one speaker-amp GPIO, optional
  headphone-detect GPIO). The only in-tree user is the Galaxy S4 (jflte).
- flo on top of that:
  1. DT nodes (patch 0006): gives a card and, as far as the sources say, a
     working headphone path and jack detection.
  2. Codec: RX3/RX4 mixers and LINEOUT1/LINEOUT3 DAC + PA, because flo's
     speakers are on those outputs (vendor `apq8064.c` routes, AOSP
     `mixer_paths.xml`). Machine driver: route "Speaker" to LINEOUT1/3, stereo.
  3. Capture: DMIC1 (built-in mic), ADC2 + MICBIAS2 (headset mic); none exists.
  4. Codec ID: the driver only matches product code 0x60 (tabla 2.x). The
     vendor board registers 1.x and 2.x; which one a given flo carries is
     decided at SLIMbus enumeration and is not in the source.

### 3. USB OTG host

- ID detection is a plain GPIO (TLMM 77). The PMIC ID interrupt is commented
  out in `msm_otg_pdata`.
- The current board file drives that same GPIO as a fixed-regulator enable
  ("ext_3p3v"), which the vendor board explicitly does not do on flo. Patch
  0001 removes it; this is needed before any ID-based switching.
- VBUS in host mode comes from the SMB345 boost (`smb345_otg_status(true)`),
  250 mA then 750 mA. Mainline smb347 exposes this as the `usb-vbus` regulator.
- Patch 0009 wires ID extcon + VBUS regulator. It is untested and changes
  device-mode detection as a side effect.

### 4. Wi-Fi `hal_start_scan response failed err=5`

`wcn36xx_smd_start_scan()` (`smd.c`) prints the status byte returned by the
firmware for a START_SCAN request; it is called from `wcn36xx_config()` on each
channel change during a software scan and its return value is ignored
(`main.c`, software-scan branch). So the firmware is refusing individual
channels while the scan as a whole continues, which matches "scan returns
results". Which channels (and why) is not visible in the source; enabling
`WCN36XX_DBG_HAL` would log the channel number before each failure.

### 5. Regulators the vendor keeps always on

`board-flo-regulator.c` `apq8064_rpm_regulator_init_data[]` marks S1, S4, L1,
L4, L25 and LVS4 always-on. The current board file has S1 and S4 always-on,
does not define L1 (so the kernel never touches it), and defines L4, L25 and
LVS4 without `regulator-always-on`. L4 has consumers (USB PHY, iris). L25 and
LVS4 have none, so they are switched off after boot. Patch 0011 restores both.

## Patches

Historical drafts; patch 0007 is superseded and must not be applied.
The remaining patches are ordered numerically; all touch `qcom-apq8064-asus-nexus7-flo.dts` only.

| Patch | Topic | Risk | Standalone? |
|---|---|---|---|
| 0001 | Remove "ext_3p3v" on the USB ID pin | Low | yes |
| 0002 | Drop the SPC idle state (cpuidle workaround) | Low | yes |
| 0003 | Bluetooth pins | Low | yes |
| 0004 | Hall / lid switch | Low-medium | needs 0003 (context) |
| 0005 | EEPROM read-only | Low | yes |
| 0006 | WCD9310 codec + sound card (headphones) | Medium | needs 0004 |
| 0007 | GSBI2 I2C probe — superseded by SENSORS.md | Do not apply | — |
| 0008 | XOADC reference L14 | HIGH RISK (new regulator) | yes |
| 0009 | USB host: ID extcon + SMB345 VBUS | HIGH RISK | needs 0001, 0004 |
| 0010 | Notification LED | HIGH RISK | yes |
| 0011 | LVS4 + L25 always-on as in vendor | HIGH RISK (always-on rails) | yes |

No patch was drafted for HDMI/SlimPort, NFC, cameras or GPS (see matrix).

## Verification performed

- `patch --dry-run -p1` and a real apply of 0001-0011 in sequence on a copy of
  the patched tree (`hw/work/verify/seq`): all clean, no fuzz.
- Standalone `patch --dry-run -p1` of each patch on an unmodified copy: results
  in the table above ("needs" = one hunk fails without the earlier patch).
- dtb build after every patch with `cpp` + `dtc` 1.7.2 (dtc was built from the
  kernel tarball's `scripts/dtc`, no system dtc is installed): no errors, no
  new warnings (one pre-existing `avoid_unnecessary_addr_size` warning on
  `dsi@5800000`).
- Not done: `make dtbs_check` / schema validation, kernel build with the new
  config symbols, any test on hardware.

## Points that are not established

1. **Sensor chips and bus.** No vendor source names the IMU, compass or
   light sensor, their addresses, interrupts or mounting matrices. GSBI2 as
   the sensor bus (patch 0007) is an elimination argument, not a citation.
   "AL3010" appears only as a file name in `init.flo.rc`.
2. **WCD9310 revision.** `slim217,60` assumes tabla 2.x. If the unit
   enumerates as product code 0x10 the codec driver will not bind.
3. **Speaker wiring.** LINEOUT1/LINEOUT3 + PM8921 GPIO 18 is derived from the
   vendor machine driver routes plus the AOSP mixer paths; the vendor code
   also defines a "top" amplifier on PM8921 GPIO 19 (LINEOUT2/4) that the flo
   mixer paths never use. Whether GPIO 19 is connected on flo is unknown.
4. **Bluetooth pins.** GPIO 16/17 as `riva_bt` follows mako/yuga; flo's
   gpiomux tables do not mention them.
5. **MCLK source for the codec.** `CODEC_I2S_SPKR_OSR_CLK` on TLMM 39 is
   copied from jflte; the vendor side only shows "cdc_mclk" on GPIO 39
   function 1 and an "osr_clk" lookup.
6. **SMB345 OTG enable.** Whether the I2C command bit alone starts the boost
   on flo (vendor also flips the OTG control mode) is unknown.
7. **Hardware revision.** Lid supply, volume-key GPIOs and wireless-charging
   GPIOs depend on `asustek_get_hw_rev()`; the patches assume a production
   unit (rev C/D/E), consistent with the volume keys already working on
   PM8921 GPIO 4/38.
8. **EEPROM at 0x52.** Not in vendor sources; origin of the node is the
   existing board file.
9. **SPC hang root cause.** Only differences are listed; none is proven.
10. **Wi-Fi err=5.** Meaning of firmware status 5 not found in the source.
11. **MI1040 vs mt9m114 driver.** Same chip id family is an observation; the
    driver was not read.

## Note on the shared kernel tree

While extracting more files from the tarball into
`tip/linux-cc2a6a249989…/`, the wildcard `arch/arm/boot/dts/qcom/*` and the
explicit path `drivers/gpu/drm/panel/panel-jdi-lt070me05000.c` overwrote three
locally patched files with their pristine versions:
`qcom-apq8064-asus-nexus7-flo.dts`, `qcom-apq8064.dtsi`,
`panel-jdi-lt070me05000.c`. They were rebuilt by re-applying the pmaports
patches (0005, 0008, 0009, 0012, 0014 on the flo dts; 0010, 0011 on the dtsi;
0004 and 0015 on the panel driver) and copied back. The two dts files match
what was read before the overwrite (466 and 2014 lines, same node positions).
The panel driver was never read before it was overwritten, so whether 0015
had been applied there originally is an assumption (0015 is in the pmaports
directory but not in the APKBUILD source list). Copies are in
`hw/work/restore/`.
