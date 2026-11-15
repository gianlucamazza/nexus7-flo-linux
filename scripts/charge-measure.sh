#!/bin/sh
# Read-only battery and charger snapshot for the Nexus 7 (flo).
echo "kernel: $(uname -v)"
for d in /sys/class/power_supply/*; do
    [ -e "$d/type" ] || continue
    echo "== $(basename "$d") ($(cat "$d/type"))"
    for f in status online present capacity voltage_now current_now charge_type \
             temp health constant_charge_current constant_charge_voltage; do
        [ -r "$d/$f" ] && printf '   %s=%s\n' "$f" "$(cat "$d/$f" 2>/dev/null)"
    done
done
# SMB345 registers, read through i2c-dev only when no kernel driver owns the chip.
if [ ! -e /sys/bus/i2c/devices/0-006a/driver ] && [ -e /dev/i2c-0 ] && command -v python3 >/dev/null; then
python3 - <<'PY'
import fcntl, os
fd = os.open("/dev/i2c-0", os.O_RDWR)
fcntl.ioctl(fd, 0x0703, 0x6a)  # I2C_SLAVE
def rd(r):
    os.write(fd, bytes([r])); return os.read(fd, 1)[0]
names = {0x00:"charge current",0x01:"input current limit",0x02:"functions",0x03:"float voltage",
         0x04:"charge control",0x06:"pin/enable control",0x09:"other control",0x30:"command A",
         0x31:"command B",0x3b:"status A",0x3c:"status B",0x3d:"status C",0x3e:"status D",0x3f:"status E",0x39:"irq status E"}
for r in sorted(names):
    try: print("   smb345 reg 0x%02x = 0x%02x  (%s)" % (r, rd(r), names[r]))
    except OSError as e: print("   smb345 reg 0x%02x: %s" % (r, e))
PY
else
    echo "   smb345: driver bound or i2c-dev unavailable; see power_supply above"
fi
dmesg | grep -iE "smb34|bq27" | tail -5
