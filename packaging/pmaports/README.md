# flo kernel package overlay

`device/testing/linux-postmarketos-qcom-apq8064/` stages the Nexus 7 flo
diagnostic kernel recipe `7.2_p20261118101500-r50`. It advances the tested
r48 recipe with two A320 suspend diagnostics. The r49 package was built,
installed and booted; it reproduced the GPU suspend failure. The r50
package was also built, installed and booted; its added registers narrowed
the investigation but did not resolve suspend. The r50 APK SHA-256 is
`02987568e899dd7cf77cae59e424f232c9be7b18e6c718242b177013a57a3dc4`.
Its source is on the companion
[`linux-flo` diagnostic branch](https://github.com/gianlucamazza/linux-flo/tree/flo/suspend-diagnostics-r50).

Copy this directory over the matching directory in a compatible pmaports
checkout, then build with pmbootstrap for `armv7`. The APKBUILD pins the
upstream kernel commit and records SHA-512 checksums for its configuration
and every patch. Built APKs are not stored here. The r48 APK had SHA-256
`8286ca93264a2f6b8c97833a78959e1d1f9b7cea91471a7bfdcb02e41f128e68`.
The r49 APK had SHA-256
`194d2ce47afe6164b798ccc95af122597c5b50273427f7faa26ad0d3eb31f968`.

The r48 change adds error diagnostics at the SCM/PAS start boundary. It is
**not a Wi-Fi fix**. On the wall charger, three consecutive r48 boots brought
WCNSS, Wi-Fi and greetd up. The earlier intermittent failure has not yet
recurred under r48. Tabla 2.x discovery remains default-off; this package
does not provide functional audio. Display brightness still causes a visible
DSI artifact. See the [current investigation record](../../docs/hw/ANALYSIS-20261118.md)
and [suspend report](../../docs/hw/SUSPEND-20261118.md) for measured results,
limitations and rollback hashes.

## Touch shell and optional agents

`temp/flo-shell/` contains the exact `0.1_git20261118-r1` package recipe and
source archive for the [integrated flo-shell branch](https://github.com/gianlucamazza/flo-shell/tree/feat/agent-pr-integration).
`temp/flo-agents/` contains the separate `0.1_git20261118-r0` CLI package
recipe and source archive. Both are noarch packages built with pmbootstrap
for armv7. The CLI is opt-in: installation creates no agent configuration,
SSH key, remote session, API secret or Crush binary. Its dependencies are
`openssh-client-default` and `curl`; mosh and QR support are optional.

The tablet has both packages installed. The shell package SHA-256 is
`f8435576c99fb994975d9b0c5ea7ccaeb8f732b9064ff645c253da5b1c8f0a39`;
the CLI package SHA-256 is
`5a8b924f3a5eb949d4f1b71a9f49931f0b099d44c9baf844e669baf87e353233`.
The previous shell APK (`0.1_git20261118-r0`, SHA-256
`dc51ae1811c3d28b248cf42134cfb778f620ff36cfcdec5fda90dba793907d94`)
is retained for rollback. The PR integration and native test limits are
recorded in [the current analysis](../../docs/hw/ANALYSIS-20261118.md).
