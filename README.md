# nexus7-flo-linux

Tools, notes and patches for running mainline Linux on the
**ASUS/Google Nexus 7 (2013) Wi-Fi** (`flo`, `asus-flo`, Qualcomm APQ8064, ARMv7),
based on postmarketOS (renamed [Nura](https://nura.eco) in September 2026).

> Personal hardware lab, not an official Nura port. Expect breakage.
> Flashing a device can erase your data: read `docs/FIRST-BOOT.md` first.

## Related repositories

| Repository | What it is |
|---|---|
| `nexus7-flo-linux` (this one) | build wrappers, diagnostics, hardware notes, status |
| [`flo-shell`](https://github.com/gianlucamazza/flo-shell) | touch shell, greeter and session for the tablet (Quickshell + Hyprland) |
| [`linux-flo`](https://github.com/gianlucamazza/linux-flo) | kernel branches on top of [apq8064-mainline/linux](https://github.com/apq8064-mainline/linux) |

## Hardware status and roadmap

- [`docs/HARDWARE.md`](docs/HARDWARE.md): what works, per component, with links
  to the evidence. Anything not tested on the tablet is marked untested.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): ordered milestones from the open issues.
- [`docs/hw/MATRIX.md`](docs/hw/MATRIX.md): vendor-source review per peripheral.

## Quick start (host)

```sh
./scripts/doctor          # check the host
./scripts/pmb --version   # pmbootstrap wrapper using this project's config
./scripts/inspect-device  # read-only info from one ADB/fastboot device
```

Nothing in `scripts/` flashes, wipes or repartitions the tablet automatically.
Third-party sources (pmbootstrap, pmaports, Android platform-tools) are fetched
into `upstream/` and `tools/` and are **not** part of this repository; pinned
revisions are in `config/sources.lock.json`.

## flo-agents (experimental, opt-in)

The tablet is ARMv7 with 2 GB RAM. Official Claude Code, Codex CLI and
Grok Build builds target x86_64/aarch64, so this repo does not install them
locally. `scripts/flo-agents` opens a remote SSH or mosh session to a
64-bit host you own. See [`docs/flo-agents.md`](docs/flo-agents.md).

## Layout

- `scripts/` – host and device helpers (pmbootstrap wrapper, diagnostics, benchmarks, flo-agents)
- `config/` – udev/polkit/journald snippets and the pmbootstrap profile
- `docs/` – architecture, kernel workflow, hardware notes
- `tests/` – unit tests for the Python helpers and the flo-agents CLI

Build output, images, backups, downloads and device reports stay local and are
ignored by Git.

## Licence

- Code (scripts, configuration, tests): MIT, see [`LICENSE`](LICENSE).
- Documentation: CC BY 4.0, see [`docs/LICENSE.md`](docs/LICENSE.md).
- Kernel patch files under `docs/` are GPL-2.0, like the kernel. The maintained
  kernel branches live in [`linux-flo`](https://github.com/gianlucamazza/linux-flo).

Most of the documentation is in Italian; the original Italian README is
[`README.it.md`](README.it.md).

## Scripts that talk to the tablet

`scripts/flo-uibench` and `scripts/flo-diag` connect over SSH and need the
tablet address explicitly, for example `FLO_HOST=root@<address> scripts/flo-diag`.
Private data (SSH key, results) is kept outside the repository, in
`$FLO_PRIV` (default `~/nexus7-recovery-20261114`).
