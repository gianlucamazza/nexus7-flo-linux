#!/bin/sh
# Pause heavy boot-file generation when the SoC gets too hot; resume when cooler.
max=0
while [ -e /run/nexus7-install-running ]; do
    t=0
    for z in /sys/class/thermal/thermal_zone[1-4]/temp; do v=$(cat "$z"); [ "$v" -gt "$t" ] && t=$v; done
    [ "$t" -gt "$max" ] && max=$t
    if [ "$t" -ge 95000 ]; then pkill -STOP -f "mkinitfs|boot-deploy|zstd|gzip|xz" && echo "PAUSE at $t"; fi
    if [ "$t" -le 85000 ]; then pkill -CONT -f "mkinitfs|boot-deploy|zstd|gzip|xz"; fi
    sleep 1
done
pkill -CONT -f "mkinitfs|boot-deploy|zstd|gzip|xz"
echo "max temp during install: $max"
