# flo kernel package overlay

`device/testing/linux-postmarketos-qcom-apq8064/` is the exact pmaports
package directory used to build the Nexus 7 flo diagnostic kernel
`7.2_p20261118101500-r48`. It was copied from the isolated pmaports branch
`flo/wcnss-pas-r48-package` at `518fd63`, based on postmarketOS pmaports.
The related kernel source is published on the companion
[`linux-flo` diagnostic branch](https://github.com/gianlucamazza/linux-flo/tree/flo/wcnss-pas-diag-r48).

Copy this directory over the matching directory in a compatible pmaports
checkout, then build with pmbootstrap for `armv7`. The APKBUILD pins the
upstream kernel commit and records SHA-512 checksums for its configuration
and every patch. The built APK is not stored here; the locally tested APK
had SHA-256
`8286ca93264a2f6b8c97833a78959e1d1f9b7cea91471a7bfdcb02e41f128e68`.

The r48 change adds error diagnostics at the SCM/PAS start boundary. It is
**not a Wi-Fi fix**. On the wall charger, three consecutive r48 boots brought
WCNSS, Wi-Fi and greetd up. The earlier intermittent failure has not yet
recurred under r48. Tabla 2.x discovery remains default-off; this package
does not provide functional audio. Display brightness still causes a visible
DSI artifact. See the [current investigation record](../../docs/hw/ANALYSIS-20261118.md)
for measured results, limitations and rollback hashes.
