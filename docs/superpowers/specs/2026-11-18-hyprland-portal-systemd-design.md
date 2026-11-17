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

Build the revised package for armv7. Check the main package keeps the
binary and D-Bus service and the subpackage owns exactly the user unit.
Simulate and then install the two packages on the tablet. Confirm the
portal backend starts through D-Bus, its interfaces are exposed, and
the user journal no longer reports a missing unit. Test a screenshot
request while the session is unlocked; avoid waking the tablet during
charging until the owner is available. Keep the local package changes
reviewable for an Alpine upstream submission.
