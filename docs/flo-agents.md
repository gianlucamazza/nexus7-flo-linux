# flo-agents

Experimental, opt-in helper. The Nexus 7 (`flo`, ARMv7, 2 GB RAM) is the
screen and keyboard. Remote agent CLIs run on a 64-bit host you own, over
SSH or mosh. Optional local mode can install Charm Crush from its official
release (checksummed). Userland on the tablet is based on
[Nura](https://nura.eco) (formerly postmarketOS). This is experimental and
not an official Nura port.

Official builds of Claude Code, Codex CLI and Grok Build target x86_64 and
aarch64 only. This repository never bundles, downloads or runs those
binaries or their installers on the tablet. `flo-agents install` is always
refused. Charm Crush is a separate, opt-in path (`flo-agents local install`).

A touch UI (flo-shell) configures this tool through the CLI and does not
edit the config file itself.

## Setup

On the tablet (or any machine that should act as the client):

```sh
./scripts/flo-agents setup --host user@host.example --transport mosh \
    --agents 'claude codex grok' --default claude
```

`--host user@host.example` is still accepted; setup splits it into hostname
and user. Without flags, `setup` prompts on a tty. It writes
`${XDG_CONFIG_HOME:-~/.config}/flo-agents/config` with mode `600` (directory
`700`) and installs a wrapper symlink at `~/.local/bin/flo-agents`. Existing
config is not overwritten unless you confirm or pass `--force`. `setup` is
implemented on top of `config set`.

POSIX `key=value` config, no secrets:

```sh
FLO_AGENT_HOST=host.example          # hostname only; legacy user@host is split on read
FLO_AGENT_USER=user
FLO_AGENT_PORT=22
FLO_AGENT_TRANSPORT=mosh             # mosh|ssh; falls back to ssh if mosh is missing
FLO_AGENTS="claude codex grok"       # any non-empty subset
FLO_AGENT_DEFAULT=claude
FLO_AGENT_CMD_claude=claude
FLO_AGENT_CMD_codex=codex
FLO_AGENT_CMD_grok=grok
FLO_AGENT_TMUX=1                     # attach or create tmux session <prefix>-<tool>
FLO_AGENT_TMUX_PREFIX=flo
FLO_AGENT_LOCAL_PROVIDER=            # optional local Crush provider
FLO_AGENT_LOCAL_BASE_URL=
FLO_AGENT_LOCAL_MODEL=
```

Remote launch commands (`FLO_AGENT_CMD_*`) are overridable. Authentication
stays on the host; this file must not contain passwords, tokens or keys.
API keys for local Crush go in a separate secrets file (see below).

Then:

```sh
flo-agents config get --json   # one JSON object for the touch UI; always exits 0
flo-agents config set host host.example
flo-agents config set user user
flo-agents list                # tool ids, one per line (plus crush when local is ready)
flo-agents check               # reachability + command -v on the host
flo-agents check --json
flo-agents launch              # default tool
flo-agents launch claude       # named remote tool
flo-agents launch crush        # local Crush, when installed and configured
flo-agents host-help           # official host install/login commands
flo-agents uninstall           # config and wrapper only
```

### config get / set / unset

`flo-agents config get --json` prints one JSON object and always exits 0,
filling defaults when there is no config file:

```json
{
  "configured": false,
  "host": "",
  "user": "",
  "port": 22,
  "transport": "mosh",
  "agents": ["claude", "codex", "grok"],
  "default": "claude",
  "cmd": {"claude": "claude", "codex": "codex", "grok": "grok"},
  "tmux": true,
  "tmux_prefix": "flo",
  "key": {"present": false, "public": ""},
  "local": {
    "provider": "",
    "base_url": "",
    "model": "",
    "key_set": false,
    "installed": false,
    "version": "",
    "mode": "local"
  }
}
```

`config get <key>` prints the plain value. Keys: `host`, `user`, `port`,
`transport`, `agents`, `default`, `cmd.claude`, `cmd.codex`, `cmd.grok`,
`tmux`, `tmux_prefix`, `local.provider`, `local.base_url`, `local.model`.

`config set <key> <value>` creates the file if missing, writes atomically,
and keeps mode `600`. Invalid input exits `2` with a one-line reason on
stderr and leaves the file unchanged. `config unset <key>` resets to the
default. Setting `agents` moves an invalid `default` to the first listed
tool.

### SSH key

```sh
flo-agents key ensure          # create ~/.ssh/flo_agents_ed25519 if missing
flo-agents key show            # print the public key, or exit 1
flo-agents key qr out.png      # needs qrencode on PATH; else exit 3
```

The key is ed25519 with an empty passphrase (`ssh-keygen -N ''`) because the
touch UI does not take passwords. Protect the tablet with disk encryption
or a screen lock. The private key is never printed, copied or sent.

To revoke access on the host, delete the matching line from
`~/.ssh/authorized_keys`.

`launch` and `check` pass `-p PORT` and, when the key exists,
`-i KEY -o IdentitiesOnly=yes`. Destination is `user@host`.

`check` uses `BatchMode=yes`, `ConnectTimeout=5` and
`StrictHostKeyChecking=accept-new` (trust on first use). A changed host key
is reported and not bypassed.

`launch` execs in the current terminal:

- mosh: `mosh --ssh="ssh -p PORT [-i KEY -o IdentitiesOnly=yes]" -- user@host tmux new -A -s <prefix>-<tool> <cmd>`
- ssh: `ssh -t -p PORT [-i KEY -o IdentitiesOnly=yes] -- user@host tmux new -A -s <prefix>-<tool> <cmd>`

If `FLO_AGENT_TMUX` is not `1`, the tmux session is skipped. Exit status is
0 on a normal end, or the transport's error (ssh `255` when the connection
drops).

`install` is refused for Claude Code, Codex CLI and Grok Build. On anything
other than x86_64/aarch64 it prints why and points at remote mode. It never
runs those vendor installers on any architecture.

## Local mode (Charm Crush)

Opt-in. Charm Crush (`https://github.com/charmbracelet/crush`) ships an
official CGO-free Go binary for Linux armv7 under FSL-1.1-MIT. RAM use on
this tablet is unmeasured; there are no numbers here.

```sh
flo-agents local install       # download + checksum + extract
flo-agents local status        # {"installed":bool,"version":str,"path":str}
flo-agents local uninstall     # tree, crush-flo symlink, our crush config
```

`local install` downloads the pinned release (`v0.101.0`) asset
`crush_<ver>_Linux_armv7.tar.gz` on `armv7l`, plus the release
`checksums.txt`, over HTTPS. The expected SHA-256 is pinned in the script
from that official checksums file and is checked before extract. `arm64` /
`aarch64` and `x86_64` / `amd64` assets are also allowed; any other
architecture is refused. Nothing is committed to this repository: no
binaries, no tarballs.

Install layout: `~/.local/share/flo-agents/crush/<ver>/` with `LICENSE`
kept next to the binary, and `~/.local/bin/crush-flo`. The command prints a
one-line licence note (FSL-1.1-MIT, personal use).

`FLO_AGENTS_TEST_CRUSH_SHA256` overrides the pinned hash. That variable is
a test-only interface; do not set it on a device.

Configure the provider through the CLI:

```sh
flo-agents config set local.provider anthropic    # or openai, xai,
                                                  # openai-compat, ollama, llamacpp
flo-agents config set local.model some-model-id
flo-agents config set local.base_url 'http://host.example:11434/v1'
# base_url is required for openai-compat, ollama and llamacpp
```

Example: point Crush at Ollama or llama.cpp on a machine you own (placeholder
URL only):

```sh
flo-agents config set local.provider ollama
flo-agents config set local.base_url 'http://host.example:11434/v1'
flo-agents config set local.model llama3.2
flo-agents launch crush
```

The same pattern works with `llamacpp` and an `http://host.example:8080/v1`
style URL.

### API key (secrets file)

```sh
printf '%s\n' "$KEY" | flo-agents secret set api_key   # STDIN only, never argv
flo-agents secret status     # set/unset and last 4 characters
flo-agents secret unset
```

The value is stored in `${XDG_CONFIG_HOME:-~/.config}/flo-agents/secrets`
with mode `600`, separate from `config`. No command prints the full key.
`config get --json` only reports `local.key_set`.

### launch crush

Runs locally (no ssh). It exports `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` or
`XAI_API_KEY` only into the child process, and sets `CRUSH_GLOBAL_CONFIG` to
`${XDG_CONFIG_HOME:-~/.config}/flo-agents/crush` so Crush reads a
flo-agents-generated `crush.json` instead of the user's
`~/.config/crush/crush.json`. That generated file holds no key in plain
text; it uses Crush's `$ENV` reference syntax (`$ANTHROPIC_API_KEY` and
friends). `list` prints `crush` when local is installed and configured;
`config get --json` lists it under `agents` and sets `local.mode` to
`local`.

## Remote-host prerequisites

The host is a machine **you** own and can SSH into. Suggested baseline:

- Architecture `x86_64` or `aarch64` (`uname -m`)
- Enough RAM to run the chosen CLI (Claude Code documents 4 GB+; the
  tablet's 2 GB is not enough for those vendor CLIs)
- `sshd` reachable with your own keys (`BatchMode` must work for `check`)
- `tmux` on the host if you keep `FLO_AGENT_TMUX=1`
- `mosh` on both ends if you set `FLO_AGENT_TRANSPORT=mosh` (otherwise
  `flo-agents` falls back to ssh)

Install the vendor CLI on that host yourself, then log in with the vendor
command. `flo-agents` does not read or proxy those credentials.

## Official install and login commands

Documentation only. Run these on the 64-bit host, never on the tablet.
Copied from `flo-agents host-help`:

**Claude Code** (64-bit host, 4 GB+ RAM):

```sh
curl -fsSL https://claude.ai/install.sh | bash
claude
```

Docs: <https://code.claude.com/docs/en/setup>

**Codex CLI:**

```sh
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex login
# or: codex login --device-auth
```

Docs: <https://github.com/openai/codex>

**Grok Build:**

```sh
curl -fsSL https://x.ai/cli/install.sh | bash
```

Then first-run browser login, or set `XAI_API_KEY` from
<https://console.x.ai>. Docs: <https://docs.x.ai/build/overview>

## Security notes

- No secrets in the config, this repository, tests or examples. Use
  placeholders such as `user@host.example` and `http://host.example:11434/v1`.
- `FLO_AGENT_HOST` must not start with `-` (setup and load reject it) so it
  cannot be passed as an ssh/mosh option. ssh is invoked with `--` before
  the host.
- The dedicated `flo_agents_ed25519` key has no passphrase. Use device
  encryption or a screen lock. Revoke it by removing the line from
  `authorized_keys` on the host.
- `check` uses `ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new`.
  A changed host key is reported; this tool never sets
  `StrictHostKeyChecking=no`.
- `secret set api_key` reads STDIN only. The full key is never printed.
- Crush is launched with `CRUSH_GLOBAL_CONFIG` pointing at our generated
  config directory so `~/.config/crush/crush.json` is left alone. The
  generated JSON references `$ANTHROPIC_API_KEY` / `$OPENAI_API_KEY` /
  `$XAI_API_KEY` rather than storing the key.
- `local install` verifies the pinned SHA-256 before extract.
- `uninstall` deletes `config` and leftover `config.tmp.*`, then `rmdir`s
  the directory if it is empty. It does not `rm -rf`. The
  `~/.local/bin/flo-agents` path is removed only when it is a symlink that
  resolves to this script. `local uninstall` removes only the Crush tree,
  `crush-flo`, and our generated crush config. Agent CLIs on the host are
  left untouched.
- Treat vendor installers as untrusted input: review them on the host
  before piping to a shell. This project will not run Claude/Codex/Grok
  installers for you.

## 2 GB RAM

The Nexus 7 (2013) Wi-Fi has 2 GB of RAM and an ARMv7 (Krait) CPU. The
vendor CLIs above ship official builds for x86_64/aarch64 and expect a
64-bit machine with more memory (Claude Code: 4 GB+). Local install of
those CLIs on the tablet is refused; remote mode is the supported path.

Charm Crush publishes an official Linux armv7 binary. How much RAM it uses
on this tablet is unmeasured.

## Uninstall

```sh
flo-agents uninstall
flo-agents local uninstall
flo-agents secret unset
```

`uninstall` deletes `${XDG_CONFIG_HOME:-~/.config}/flo-agents/config` and any
leftover `config.tmp.*` in that directory, then removes the directory with
`rmdir` if it is empty. Other files in the directory (including `secrets`
and generated crush config) are left in place. The `~/.local/bin/flo-agents`
wrapper is removed only if it is a symlink that resolves to this script.
Does not uninstall Claude Code, Codex CLI or Grok Build on the host, and
does not delete this repository's `scripts/flo-agents`.
