# flo-agents

Experimental, opt-in helper. The Nexus 7 (`flo`, ARMv7, 2 GB RAM) is the
screen and keyboard. Agent CLIs run on a 64-bit host you own, over SSH or
mosh. Userland on the tablet is based on [Nura](https://nura.eco) (formerly
postmarketOS); this is not our own distro.

Official builds of Claude Code, Codex CLI and Grok Build target x86_64 and
aarch64 only. This repository never bundles, downloads or runs those
binaries or their installers on the tablet.

## Setup

On the tablet (or any machine that should act as the client):

```sh
./scripts/flo-agents setup --host user@host.example --transport mosh \
    --agents 'claude codex grok' --default claude
```

Without flags, `setup` prompts on a tty. It writes
`${XDG_CONFIG_HOME:-~/.config}/flo-agents/config` with mode `600` and
installs a wrapper symlink at `~/.local/bin/flo-agents`. Existing config is
not overwritten unless you confirm or pass `--force`.

POSIX `key=value` config, no secrets:

```sh
FLO_AGENT_HOST=user@host.example
FLO_AGENT_TRANSPORT=mosh   # mosh|ssh; falls back to ssh if mosh is missing
FLO_AGENTS="claude codex grok"   # any non-empty subset
FLO_AGENT_DEFAULT=claude
FLO_AGENT_CMD_claude=claude
FLO_AGENT_CMD_codex=codex
FLO_AGENT_CMD_grok=grok
FLO_AGENT_TMUX=1   # attach or create tmux session flo-<tool> on the host
```

Remote launch commands (`FLO_AGENT_CMD_*`) are overridable. Authentication
stays on the host; this file must not contain passwords, tokens or keys.

Then:

```sh
flo-agents list              # tool ids, one per line
flo-agents check             # reachability + command -v on the host
flo-agents launch            # default tool
flo-agents launch claude     # named tool
flo-agents host-help         # official host install/login commands
flo-agents uninstall         # config and wrapper only
```

`launch` execs in the current terminal:

- mosh: `mosh host -- tmux new -A -s flo-<tool> <cmd>`
- ssh: `ssh -t host tmux new -A -s flo-<tool> <cmd>`

If `FLO_AGENT_TMUX` is not `1`, the tmux session is skipped. Exit status is
0 on a normal end, or the transport's error (ssh `255` when the connection
drops).

`install` is refused. On anything other than x86_64/aarch64 it prints why
and points at remote mode. It never runs an installer on any architecture.

## Remote-host prerequisites

The host is a machine **you** own and can SSH into. Suggested baseline:

- Architecture `x86_64` or `aarch64` (`uname -m`)
- Enough RAM to run the chosen CLI (Claude Code documents 4 GB+; the
  tablet's 2 GB is not enough)
- `sshd` reachable with your own keys (`BatchMode` must work for `check`)
- `tmux` on the host if you keep `FLO_AGENT_TMUX=1`
- `mosh` on both ends if you set `FLO_AGENT_TRANSPORT=mosh` (otherwise
  `flo-agents` falls back to ssh)

Install the vendor CLI on that host yourself, then log in with the vendor
command. `flo-agents` does not read or proxy credentials.

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
  placeholders such as `user@host.example`.
- SSH/mosh use **your** existing keys and agent. This tool does not store,
  read or forward passwords or API keys.
- `check` uses `ssh -o BatchMode=yes -o ConnectTimeout=5` and `command -v`
  only. It never installs anything.
- `uninstall` removes our config directory and the `~/.local/bin/flo-agents`
  symlink. Agent CLIs on the host are left untouched.
- Treat vendor installers as untrusted input: review them on the host
  before piping to a shell. This project will not run them for you.

## 2 GB RAM

The Nexus 7 (2013) Wi-Fi has 2 GB of RAM and an ARMv7 (Krait) CPU. The
vendor CLIs above ship official builds for x86_64/aarch64 and expect a
64-bit machine with more memory (Claude Code: 4 GB+). Local install on the
tablet is refused; remote mode is the supported path.

## Uninstall

```sh
flo-agents uninstall
```

Removes `${XDG_CONFIG_HOME:-~/.config}/flo-agents/` and the wrapper
symlink. Does not uninstall Claude Code, Codex CLI or Grok Build on the
host, and does not delete this repository's `scripts/flo-agents`.
