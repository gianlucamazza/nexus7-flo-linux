#!/usr/bin/env python3
"""Summarise a nexus7-perfprobe capture.

usage: perf-analyze.py capture.txt [--top N] [--marks phases.marks]

Prints, for the whole capture and for the samples with touch activity:
frames per second (display interrupt rate), GPU interrupt rate, total CPU
use, and the processes with the most CPU time (percent of one core).
"""
import re
import sys
from collections import Counter

HZ = 100  # USER_HZ for /proc/<pid>/stat utime/stime


def parse(path):
    samples, cur = [], None
    for line in open(path, errors="replace"):
        if line.startswith("@T"):
            parts = line.split()
            cur = {"up": float(parts[1]), "P": {}}
            for kv in parts[2:]:
                k, _, v = kv.partition("=")
                cur[k] = v
            samples.append(cur)
        elif cur is None:
            continue
        elif line.startswith("@C"):
            _, busy, idle = line.split()
            cur["busy"], cur["idle"] = int(busy), int(idle)
        elif line.startswith("@P"):
            m = re.match(r"@P (\d+) \((.*)\) \S+ (.*)", line)
            if not m:
                continue
            f = m.group(3).split()
            # fields after state: ppid pgrp ... utime is field 14 overall -> index 10 here
            cur["P"][(m.group(1), m.group(2))] = int(f[10]) + int(f[11])
    return [s for s in samples if "busy" in s]


def summary(pairs, label, top):
    if not pairs:
        print(f"{label}: no samples")
        return
    dt = sum(b["up"] - a["up"] for a, b in pairs)
    d = lambda k: sum(int(b.get(k, 0) or 0) - int(a.get(k, 0) or 0) for a, b in pairs)
    busy = sum(b["busy"] - a["busy"] for a, b in pairs)
    tot = busy + sum(b["idle"] - a["idle"] for a, b in pairs)
    procs = Counter()
    for a, b in pairs:
        for k, v in b["P"].items():
            if k in a["P"] and v > a["P"][k]:
                procs[k[1]] += v - a["P"][k]
    print(f"{label}: {dt:.1f} s  fps={d('msm')/dt:.1f}  gpu-irq/s={d('gpu')/dt:.1f}  "
          f"touch-irq/s={d('touch')/dt:.1f}  cpu={100*busy/max(tot,1):.0f}% of 4 cores")
    for name, ticks in procs.most_common(top):
        print(f"    {name:<24} {100*ticks/HZ/dt:6.1f} %")


def main():
    args = sys.argv[1:]
    top = 12
    if "--top" in args:
        i = args.index("--top")
        top = int(args[i + 1])
        del args[i:i + 2]
    marks = None
    if "--marks" in args:
        i = args.index("--marks")
        marks = args[i + 1]
        del args[i:i + 2]
    s = parse(args[0])
    pairs = list(zip(s, s[1:]))
    if marks:
        # one summary per phase written by nexus7-uibench ("name uptime" lines)
        m = [(l.split()[0], float(l.split()[1])) for l in open(marks) if l.strip()]
        for (name, start), (_, stop) in zip(m, m[1:]):
            summary([(a, b) for a, b in pairs if a["up"] >= start and b["up"] <= stop], name, top)
        return
    summary(pairs, "all", top)
    active = [(a, b) for a, b in pairs if int(b.get("touch", 0)) - int(a.get("touch", 0)) > 3]
    summary(active, "touching", top)


if __name__ == "__main__":
    main()
