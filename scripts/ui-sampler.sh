#!/bin/sh
# Read-only: log per-second frame/GPU/touch interrupts and compositor CPU for N seconds.
N=${1:-240}; L=/var/tmp/ui-sample.log; : > $L
irq() { grep -E " $1\$" /proc/interrupts | head -1 | awk '{s=0; for(i=2;i<=5;i++) s+=$i; print s}'; }
cpu() { p=$(pgrep -x "$1" | head -1); [ -n "$p" ] && awk '{print $14+$15}' /proc/$p/stat || echo 0; }
pm=$(irq msm); pg=$(irq gpu-irq); pt=$(irq ekth3500); pc=$(cpu phoc); ps=$(cpu phosh)
i=0
while [ $i -lt $N ]; do
    sleep 1
    m=$(irq msm); g=$(irq gpu-irq); t=$(irq ekth3500); c=$(cpu phoc); s=$(cpu phosh)
    echo "$i frames=$((m-pm)) gpuirq=$((g-pg)) touch=$((t-pt)) phoc=$((c-pc))% phosh=$((s-ps))% temp=$(cat /sys/class/thermal/thermal_zone2/temp) cap=$(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq)" >> $L
    pm=$m; pg=$g; pt=$t; pc=$c; ps=$s; i=$((i+1))
done
