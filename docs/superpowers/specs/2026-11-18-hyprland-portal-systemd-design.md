# Hyprland portal: systemd package integration

## Intent

Restore the Hyprland screenshot, screencast and global-shortcuts portal on
the Nexus 7 systemd image without a user-specific service override.

## Evidence

On the running tablet, `xdg-desktop-portal-hyprland-1.3.12-r0` installs
`org.freedesktop.impl.portal.desktop.hyprland.service` with
`SystemdService=xdg-desktop-portal-hyprland.service`, but no matching
systemd user unit. The user journal says D-Bus activation failed because
that unit could not be found. Alpine's `testing/xdg-desktop-portal-hyprland`
APKBUILD explicitly removes `/usr/lib/systemd` after installation. The
upstream project supplies the unit. PipeWire's Alpine package already
uses a conditional `-systemd` subpackage for its user unit.

## Approaches

1. Add the unit to flo-shell or postmarketOS `systemd-services`: small
   local change, but the service would be owned by the wrong package;
   pmaports explicitly directs new units to upstream packages.
2. Remove `SystemdService` from the D-Bus file: enables direct D-Bus
   activation, but changes the upstream activation model for every init
   system and avoids the existing systemd unit.
3. Keep the upstream unit in Alpine's build and move it into an optional
   `xdg-desktop-portal-hyprland-systemd` subpackage. Its `install_if`
   depends on both the main package and systemd, as with PipeWire.

Use approach 3. The package owns its own unit, the OpenRC installation
does not gain a systemd dependency, and systemd users receive the file
referenced by D-Bus. This is a packaging correction, not a runtime patch.

## Verification

The isolated Alpine aports branch
`fix/xdg-portal-hyprland-systemd` at `2431fca` implements the package
split. An x86_64 Alpine edge `abuild` compiled the source and created
the three APKs. Inspection confirms the main APK keeps the binary,
portal descriptor and D-Bus service, while the `-systemd` APK owns only
`usr/lib/systemd/user/xdg-desktop-portal-hyprland.service` and declares
`install_if = xdg-desktop-portal-hyprland=1.3.12-r1 systemd`. The
temporary container did not trust its freshly generated signing key
when indexing its repository, after package creation. The armv7 build
then completed through pmbootstrap. Both APKs were transferred over
Wi-Fi and passed SHA-256 comparison and `apk add --simulate` before
installation. D-Bus activation now starts the user service successfully;
introspection exposes Screenshot, ScreenCast and GlobalShortcuts. The
service is active with no failed user units, and PipeWire connects.
An end-to-end screenshot with the display on remains to be tested.

Keep the local package changes reviewable for an Alpine upstream
submission. Test an end-to-end screenshot request while the session is
unlocked; avoid waking the tablet during charging until the owner is
available.
