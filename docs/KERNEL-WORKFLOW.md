# Kernel workflow (flo)

## Where things live

- **Source tree:** `../linux-flo`, a git checkout of
  `apq8064-mainline/linux` (shallow).
  - `flo/base`: the fork commit used as `_commit` in the APKBUILD.
  - `flo/rN`: the base plus our patches, one commit per patch, in APKBUILD
    order and with the original author.
- **Package:** `upstream/pmaports/device/testing/linux-postmarketos-qcom-apq8064/`,
  which holds the APKBUILD, the config and the patches. This stays the source
  of truth for what gets installed.

## Rules

- One risky change per kernel. Every new kernel gets 3 boots with an unlocked
  session before it counts as stable (see `docs/STATUS.md`).
- Patch identity: the author is Gianluca Mazza <info@gianlucamazza.it> for our
  patches and the original author otherwise. Use `Assisted-by: Claude:<model>`.
  Never add `Signed-off-by` for the user; the user adds it when sending.
- Changing the config forces a full rebuild (about 2 h with pmbootstrap).
  Group config changes together.

## Fast loop (incremental, envkernel)

```
scripts/flo-kernel build     # make in linux-flo/.output inside the native chroot
scripts/flo-kernel package   # pmbootstrap build --envkernel → apk
```

The objects stay in `linux-flo/.output`, so a DT or driver change rebuilds in
minutes. Use it for experiments; for the kernel that gets installed, put the
change into pmaports as well.

## Clean build (release)

```
scripts/pmb -y checksum linux-postmarketos-qcom-apq8064
scripts/pmb -y build --arch armv7 linux-postmarketos-qcom-apq8064
```

## Patches from git

- Edit or add commits on `flo/rN` (`git commit --fixup`, `git rebase -i` by
  hand).
- `scripts/flo-kernel patches` writes `git format-patch flo/base..HEAD` to
  `reports/kernel-patches/`; copy them into the package directory and update
  `source=`.

## Installing on the tablet

- Use `~/nexus7-recovery-20261114/install-rN-remote.sh`, which:
  - backs up `/boot`, the apk database and the modules;
  - runs `apk add`, `depmod` and `mkinitfs`;
  - checks the command line;
  - syncs the boot partition p22.
- Always keep the previous kernel in p22 (`*.previous`) for TWRP recovery.

## Crash data

- **pstore:** `/var/lib/systemd/pstore`. The lockup detectors panic and the
  tablet reboots after 10 s.
- **GPU crash dumps:** `/var/lib/nexus7-devcoredump/` (udev rule). Decode on
  the laptop with Mesa's `crashdec`; see the session scratchpad
  `crashdec/build`.
- **Journal:** persistent, synced every 2 s. After a hang, copy it from TWRP
  (procedure in the project memory/STATUS).

## Package versions from envkernel

`pmbootstrap build --envkernel` names the package `7.2_p<timestamp>-r0`.
apk treats `7.2_p…` as newer than any `7.2-rN`, so after an envkernel kernel
a clean `7.2-rN` build is a downgrade for apk. Always install kernels with the
`install-rN-remote.sh` script, which passes the file explicitly (`apk add
<file>` accepts downgrades), never with `apk upgrade`.
