#!/bin/sh
# Step the CPU frequency up one OPP at a time with the userspace governor.
# Usage: cpufreq-step-test.sh <max_khz>. Logs to /var/tmp so a hang leaves a trace.
max=${1:-918000}
P=/sys/devices/system/cpu/cpufreq/policy0
L=/var/tmp/cpufreq-step.log
[ -d "$P" ] || { echo "no cpufreq policy"; exit 1; }
echo userspace > $P/scaling_governor
volt() { for r in /sys/class/regulator/regulator.[1-4]; do printf '%s ' "$(cat $r/microvolts)"; done; }
temp() { cat /sys/class/thermal/thermal_zone[1-2]/temp | tr '\n' ' '; }
bench() { s=$(cut -d' ' -f1 /proc/uptime | tr -d .); dd if=/dev/zero bs=1M count=16 2>/dev/null | sha256sum >/dev/null; e=$(cut -d' ' -f1 /proc/uptime | tr -d .); echo $(( (e-s)*10 )); }
for f in $(tr ' ' '\n' < $P/scaling_available_frequencies | sort -n); do
    [ "$f" -gt "$max" ] && break
    echo "about to set $f" >> $L; sync
    echo "$f" > $P/scaling_setspeed
    sleep 1
    line="set=$f cur=$(cat $P/scaling_cur_freq) clk=$(grep -m1 krait0_pri_mux /sys/kernel/debug/clk/clk_summary | awk '{print $5}') uV=$(volt) sha16MB=$(bench)ms temp=$(temp)"
    echo "$line" | tee -a $L; sync
done
