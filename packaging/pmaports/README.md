# flo kernel package overlay

`device/testing/linux-postmarketos-qcom-apq8064/` is the exact pmaports
package directory used to build the experimental Nexus 7 flo kernel
`7.2_p20261118101500-r41`. It comes from the isolated pmaports branch
`flo/charging-extcon-package` at `5fd17cb`, based on postmarketOS pmaports.
The kernel changes are in the companion
[`linux-flo` branch](https://github.com/gianlucamazza/linux-flo/tree/flo/charging-extcon-package).

Copy this directory over the matching directory in a compatible pmaports
checkout, then build with pmbootstrap for `armv7`. The APKBUILD pins the
upstream kernel commit and records SHA-512 checksums for its configuration
and every patch. The built APK is not stored here; the locally tested APK
had SHA-256
`56d3a5f658e5e611af133811ed279c1d30e7b0c208a47134a2cbb1262c4601dc`.

The tablet boots r41, recognizes VBUS from the SMB345 charger and charges
from the tested wall supply. The USB computer-port current limit and
display-on charge balance still require native verification. See
[`docs/hw/ISSUES-20261117.md`](../../docs/hw/ISSUES-20261117.md)
for the measurements and rollback record.
