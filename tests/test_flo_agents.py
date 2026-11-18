"""CLI contract tests for scripts/flo-agents (no network)."""
import hashlib
import io
import json
import os
import stat
import subprocess
import tarfile
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'flo-agents'
PLACEHOLDER_HOST = 'user@host.example'
PLACEHOLDER_HOSTNAME = 'host.example'
PLACEHOLDER_USER = 'user'
FAKE_PRIVATE = 'FAKE-PRIVATE-KEY-PLACEHOLDER'
FAKE_PUBLIC = 'ssh-ed25519 AAAACLITESTPLACEHOLDER flo-agents'


class FloAgentsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home'
        self.config_home = Path(self.temp.name) / 'xdg'
        self.bin_dir = Path(self.temp.name) / 'bin'
        self.log_dir = Path(self.temp.name) / 'log'
        self.home.mkdir()
        self.config_home.mkdir()
        self.bin_dir.mkdir()
        self.log_dir.mkdir()
        self.argv_log = self.log_dir / 'argv.jsonl'
        self.curl_mark = self.log_dir / 'curl-called'
        self._write_fakes()

    def _write_fakes(self):
        ssh = self.bin_dir / 'ssh'
        mosh = self.bin_dir / 'mosh'
        curl = self.bin_dir / 'curl'
        uname = self.bin_dir / 'uname'
        recorder = textwrap.dedent('''\
            #!/usr/bin/python3
            import json, os, sys
            log = os.environ["FLO_AGENTS_ARGV_FILE"]
            with open(log, "a", encoding="utf-8") as fh:
                json.dump([os.path.basename(sys.argv[0]), *sys.argv[1:]], fh)
                fh.write("\\n")
            hk = os.environ.get("FLO_AGENTS_HOST_KEY", "known")
            if hk == "changed":
                print("WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!", file=sys.stderr)
                print("Host key verification failed.", file=sys.stderr)
                raise SystemExit(255)
            if hk == "unknown":
                print("ssh: connect to host host.example port 22: Connection timed out", file=sys.stderr)
                raise SystemExit(255)
            if hk == "new":
                print("Warning: Permanently added 'host.example' (ED25519) to the list of known hosts.", file=sys.stderr)
            args = sys.argv[1:]
            i = 0
            while i < len(args):
                a = args[i]
                if a == "--":
                    i += 1
                    break
                if a in ("-t", "-n", "-q", "-T"):
                    i += 1
                    continue
                if a == "-o":
                    i += 2
                    continue
                if a.startswith("-o") or a.startswith("-i") or a.startswith("-p"):
                    if a in ("-i", "-p") or (len(a) == 2 and a[1].isalpha()):
                        i += 2
                    else:
                        i += 1
                    continue
                if a.startswith("-"):
                    i += 1
                    continue
                break
            remote = args[i + 1:] if i < len(args) else []
            joined = " ".join(remote)
            if joined == "true":
                raise SystemExit(0)
            if remote[:2] == ["command", "-v"] or (len(remote) >= 3 and remote[0] == "command" and remote[1] == "-v"):
                name = remote[-1]
                found = os.environ.get("FLO_AGENTS_REMOTE_CMDS", "").split()
                if name in found:
                    print("/usr/bin/" + name)
                    raise SystemExit(0)
                raise SystemExit(1)
            raise SystemExit(int(os.environ.get("FLO_AGENTS_SSH_EXIT", "0")))
            ''')
        ssh.write_text(recorder)
        mosh.write_text(recorder)
        ssh.chmod(0o755)
        mosh.chmod(0o755)
        curl.write_text(textwrap.dedent(f'''\
            #!/usr/bin/python3
            import os, shutil, sys
            mark = "{self.curl_mark}"
            with open(mark, "w", encoding="utf-8") as fh:
                fh.write("called\\n")
            out = None
            url = None
            args = sys.argv[1:]
            i = 0
            while i < len(args):
                a = args[i]
                if a == "-o" and i + 1 < len(args):
                    out = args[i + 1]
                    i += 2
                    continue
                if a.startswith("-"):
                    i += 1
                    continue
                url = a
                i += 1
            tarball = os.environ.get("FLO_AGENTS_FAKE_TARBALL", "")
            if not tarball or not out or not url:
                sys.stderr.write("curl must not run\\n")
                raise SystemExit(1)
            if url.rstrip("/").endswith("checksums.txt"):
                sha = os.environ.get("FLO_AGENTS_TEST_CRUSH_SHA256", "")
                asset = os.path.basename(url.replace("checksums.txt", "").rstrip("/"))
                asset = os.environ.get("FLO_AGENTS_FAKE_ASSET", "crush_0.101.0_Linux_armv7.tar.gz")
                with open(out, "w", encoding="utf-8") as fh:
                    fh.write(f"{{sha}}  {{asset}}\\n")
            else:
                shutil.copy(tarball, out)
            '''))
        curl.chmod(0o755)
        uname.write_text(textwrap.dedent('''\
            #!/bin/sh
            if [ "$1" = -m ]; then
                printf '%s\\n' "${FLO_AGENTS_FAKE_UNAME_M:-armv7l}"
                exit 0
            fi
            exec /usr/bin/uname "$@"
            '''))
        uname.chmod(0o755)
        keygen = self.bin_dir / 'ssh-keygen'
        keygen.write_text(textwrap.dedent(f'''\
            #!/usr/bin/python3
            import json, os, sys
            log = os.environ["FLO_AGENTS_ARGV_FILE"]
            with open(log, "a", encoding="utf-8") as fh:
                json.dump(["ssh-keygen", *sys.argv[1:]], fh)
                fh.write("\\n")
            path = None
            args = sys.argv[1:]
            i = 0
            while i < len(args):
                a = args[i]
                if a == "-f" and i + 1 < len(args):
                    path = args[i + 1]
                    i += 2
                    continue
                if a.startswith("-f") and len(a) > 2:
                    path = a[2:]
                    i += 1
                    continue
                i += 1
            if not path:
                sys.stderr.write("ssh-keygen: missing -f\\n")
                raise SystemExit(1)
            if os.path.exists(path):
                sys.stderr.write("ssh-keygen: key already exists\\n")
                raise SystemExit(1)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{FAKE_PRIVATE}\\n")
            os.chmod(path, 0o600)
            with open(path + ".pub", "w", encoding="utf-8") as fh:
                fh.write("{FAKE_PUBLIC}\\n")
            '''))
        keygen.chmod(0o755)
        qrencode = self.bin_dir / 'qrencode'
        qrencode.write_text(textwrap.dedent('''\
            #!/usr/bin/python3
            import json, os, sys
            log = os.environ["FLO_AGENTS_ARGV_FILE"]
            with open(log, "a", encoding="utf-8") as fh:
                json.dump(["qrencode", *sys.argv[1:]], fh)
                fh.write("\\n")
            out = None
            payload = []
            args = sys.argv[1:]
            i = 0
            while i < len(args):
                a = args[i]
                if a == "-o" and i + 1 < len(args):
                    out = args[i + 1]
                    i += 2
                    continue
                payload.append(a)
                i += 1
            if not out:
                sys.stderr.write("qrencode: missing -o\\n")
                raise SystemExit(1)
            with open(out, "w", encoding="utf-8") as fh:
                fh.write("QR:" + " ".join(payload))
            '''))
        qrencode.chmod(0o755)

    def env(self, extra=None, path_mode='fakes'):
        env = os.environ.copy()
        env['HOME'] = str(self.home)
        env['XDG_CONFIG_HOME'] = str(self.config_home)
        env['FLO_AGENTS_ARGV_FILE'] = str(self.argv_log)
        env['FLO_AGENTS_REMOTE_CMDS'] = 'claude grok'
        env.pop('FLO_AGENT_HOST', None)
        env.pop('FLO_AGENTS_TEST_CRUSH_SHA256', None)
        env.pop('FLO_AGENTS_FAKE_TARBALL', None)
        # Fakes take precedence; keep coreutils on PATH so check/key/local
        # can call mkdir, chmod, tar, sha256sum, rm.
        fake_path = str(self.bin_dir) + os.pathsep + os.environ.get('PATH', '/usr/bin:/bin')
        if path_mode == 'fakes':
            env['PATH'] = fake_path
        elif path_mode == 'ssh_only':
            mosh = self.bin_dir / 'mosh'
            if mosh.exists():
                mosh.unlink()
            env['PATH'] = fake_path
        elif path_mode == 'no_qrencode':
            qrencode = self.bin_dir / 'qrencode'
            if qrencode.exists():
                qrencode.unlink()
            env['PATH'] = fake_path
        elif path_mode == 'system':
            env['PATH'] = os.environ['PATH']
        if extra:
            env.update(extra)
        return env

    def run_cli(self, args, extra=None, path_mode='fakes', input_text=None):
        return subprocess.run(
            [str(SCRIPT), *args],
            env=self.env(extra, path_mode=path_mode),
            capture_output=True,
            text=True,
            input=input_text,
            check=False,
        )

    def config_path(self):
        return self.config_home / 'flo-agents' / 'config'

    def key_path(self):
        return self.home / '.ssh' / 'flo_agents_ed25519'

    def write_config(self, **fields):
        data = {
            'FLO_AGENT_HOST': PLACEHOLDER_HOST,
            'FLO_AGENT_TRANSPORT': 'mosh',
            'FLO_AGENTS': 'claude codex grok',
            'FLO_AGENT_DEFAULT': 'claude',
            'FLO_AGENT_CMD_claude': 'claude',
            'FLO_AGENT_CMD_codex': 'codex',
            'FLO_AGENT_CMD_grok': 'grok',
            'FLO_AGENT_TMUX': '1',
        }
        data.update(fields)
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ['# test config']
        for key, value in data.items():
            lines.append(f"{key}='{value}'")
        path.write_text('\n'.join(lines) + '\n')
        path.chmod(0o600)
        return path

    def write_key(self, private=FAKE_PRIVATE, public=FAKE_PUBLIC):
        path = self.key_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(private + '\n')
        path.chmod(0o600)
        pub = Path(str(path) + '.pub')
        pub.write_text(public + '\n')
        return path, pub

    def recorded_argv(self):
        if not self.argv_log.exists():
            return []
        return [json.loads(line) for line in self.argv_log.read_text().splitlines() if line.strip()]

    def test_unknown_command_is_error(self):
        proc = self.run_cli(['nope'], path_mode='system')
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, '')
        self.assertIn('unknown', proc.stderr.lower())

    def test_no_args_prints_usage(self):
        proc = self.run_cli([], path_mode='system')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('usage:', proc.stderr.lower() + proc.stdout.lower())

    def test_setup_rejects_bad_transport(self):
        proc = self.run_cli(
            ['setup', '--host', PLACEHOLDER_HOST, '--transport', 'telnet', '--agents', 'claude'],
            path_mode='system',
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('transport', proc.stderr.lower())
        self.assertFalse(self.config_path().exists())

    def test_setup_rejects_unknown_agent(self):
        proc = self.run_cli(
            ['setup', '--host', PLACEHOLDER_HOST, '--agents', 'notatool'],
            path_mode='system',
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(self.config_path().exists())

    def test_setup_rejects_default_outside_agents(self):
        proc = self.run_cli(
            ['setup', '--host', PLACEHOLDER_HOST, '--agents', 'claude', '--default', 'grok'],
            path_mode='system',
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(self.config_path().exists())

    def test_setup_rejects_host_starting_with_dash(self):
        proc = self.run_cli(
            ['setup', '--host', '-oProxyCommand=true', '--agents', 'claude'],
            path_mode='system',
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('must not start with -', proc.stderr)
        self.assertFalse(self.config_path().exists())
        self.assertFalse(self.argv_log.exists())

    def test_load_config_rejects_host_starting_with_dash(self):
        self.write_config(FLO_AGENT_HOST='-oProxyCommand=true')
        for cmd in (['list'], ['launch', 'claude'], ['check']):
            with self.subTest(cmd=cmd):
                if self.argv_log.exists():
                    self.argv_log.unlink()
                proc = self.run_cli(cmd)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn('must not start with -', proc.stderr)
                self.assertEqual(self.recorded_argv(), [])

    def test_setup_requires_host_without_tty(self):
        proc = self.run_cli(['setup', '--agents', 'claude'], path_mode='system')
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(self.config_path().exists())

    def test_setup_writes_mode_600_and_expected_keys(self):
        proc = self.run_cli(
            ['setup', '--host', PLACEHOLDER_HOST, '--transport', 'ssh',
             '--agents', 'claude,codex', '--default', 'codex', '--force'],
            path_mode='system',
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        path = self.config_path()
        self.assertTrue(path.is_file())
        mode = stat.S_IMODE(path.stat().st_mode)
        self.assertEqual(mode, 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        text = path.read_text()
        self.assertIn(f"FLO_AGENT_HOST='{PLACEHOLDER_HOSTNAME}'", text)
        self.assertIn(f"FLO_AGENT_USER='{PLACEHOLDER_USER}'", text)
        self.assertIn('FLO_AGENT_PORT=22', text.replace("'", ''))
        self.assertIn("FLO_AGENT_TRANSPORT='ssh'", text)
        self.assertIn("FLO_AGENTS='claude codex'", text)
        self.assertIn("FLO_AGENT_DEFAULT='codex'", text)
        self.assertIn("FLO_AGENT_CMD_claude='claude'", text)
        self.assertIn("FLO_AGENT_CMD_codex='codex'", text)
        self.assertNotIn('FLO_AGENT_CMD_grok', text)
        self.assertIn('FLO_AGENT_TMUX=1', text.replace("'", ''))
        self.assertIn("FLO_AGENT_TMUX_PREFIX='flo'", text)
        self.assertNotRegex(text, r'(?i)(password|token|secret|api[_-]?key)=')

    def test_setup_does_not_overwrite_without_force(self):
        first = self.run_cli(
            ['setup', '--host', PLACEHOLDER_HOST, '--agents', 'claude', '--force'],
            path_mode='system',
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        original = self.config_path().read_text()
        second = self.run_cli(
            ['setup', '--host', 'other@host.example', '--agents', 'grok'],
            path_mode='system',
        )
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(self.config_path().read_text(), original)
        forced = self.run_cli(
            ['setup', '--host', 'other@host.example', '--agents', 'grok', '--force'],
            path_mode='system',
        )
        self.assertEqual(forced.returncode, 0, forced.stderr)
        text = self.config_path().read_text()
        self.assertIn("FLO_AGENT_HOST='host.example'", text)
        self.assertIn("FLO_AGENT_USER='other'", text)
        self.assertIn("FLO_AGENTS='grok'", text)

    def test_list_prints_ids_only(self):
        self.write_config(FLO_AGENTS='claude grok', FLO_AGENT_DEFAULT='grok')
        proc = self.run_cli(['list'], path_mode='system')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, 'claude\ngrok\n')
        self.assertEqual(proc.stderr, '')

    def test_list_without_config_is_error_with_empty_stdout(self):
        proc = self.run_cli(['list'], path_mode='system')
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, '')

    def test_armv7_install_is_refused_and_points_to_remote(self):
        proc = self.run_cli(['install'], extra={'FLO_AGENTS_FAKE_UNAME_M': 'armv7l'})
        self.assertNotEqual(proc.returncode, 0)
        err = proc.stderr.lower() + proc.stdout.lower()
        self.assertIn('armv7', err)
        self.assertIn('remote', err)
        self.assertRegex(err, r'x86_64|aarch64')
        self.assertFalse(self.curl_mark.exists())
        self.assertFalse(self.argv_log.exists() and 'install.sh' in self.argv_log.read_text())

    def test_x86_64_install_still_does_not_download(self):
        proc = self.run_cli(['install'], extra={'FLO_AGENTS_FAKE_UNAME_M': 'x86_64'})
        self.assertNotEqual(proc.returncode, 0)
        err = proc.stderr.lower() + proc.stdout.lower()
        self.assertIn('host-help', err)
        self.assertFalse(self.curl_mark.exists())

    def test_launch_mosh_tmux_command(self):
        self.write_config()
        proc = self.run_cli(['launch', 'claude'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv(), [[
            'mosh', '--ssh=ssh -p 22', '--', PLACEHOLDER_HOST,
            'tmux', 'new', '-A', '-s', 'flo-claude', 'claude',
        ]])

    def test_launch_ssh_tmux_command(self):
        self.write_config(FLO_AGENT_TRANSPORT='ssh')
        proc = self.run_cli(['launch', 'codex'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv(), [[
            'ssh', '-t', '-p', '22', '--', PLACEHOLDER_HOST,
            'tmux', 'new', '-A', '-s', 'flo-codex', 'codex',
        ]])

    def test_launch_without_tmux(self):
        self.write_config(FLO_AGENT_TMUX='0', FLO_AGENT_TRANSPORT='ssh')
        proc = self.run_cli(['launch', 'grok'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv(), [[
            'ssh', '-t', '-p', '22', '--', PLACEHOLDER_HOST, 'grok',
        ]])

    def test_launch_falls_back_to_ssh_when_mosh_missing(self):
        self.write_config(FLO_AGENT_TRANSPORT='mosh')
        proc = self.run_cli(['launch'], path_mode='ssh_only')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        argv = self.recorded_argv()[0]
        self.assertEqual(argv[0], 'ssh')
        self.assertEqual(argv[1:6], ['-t', '-p', '22', '--', PLACEHOLDER_HOST])
        self.assertIn('flo-claude', argv)

    def test_launch_uses_default_and_custom_remote_command(self):
        self.write_config(
            FLO_AGENT_DEFAULT='claude',
            FLO_AGENT_CMD_claude='claude --debug',
            FLO_AGENT_TRANSPORT='mosh',
        )
        proc = self.run_cli(['launch'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv(), [[
            'mosh', '--ssh=ssh -p 22', '--', PLACEHOLDER_HOST,
            'tmux', 'new', '-A', '-s', 'flo-claude', 'claude', '--debug',
        ]])

    def test_launch_unknown_tool_fails(self):
        self.write_config(FLO_AGENTS='claude')
        proc = self.run_cli(['launch', 'grok'], path_mode='system')
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.recorded_argv(), [])

    def test_launch_passes_through_ssh_255(self):
        self.write_config(FLO_AGENT_TRANSPORT='ssh')
        proc = self.run_cli(['launch', 'claude'], extra={'FLO_AGENTS_SSH_EXIT': '255'})
        self.assertEqual(proc.returncode, 255)

    def test_launch_uses_port_key_and_tmux_prefix(self):
        self.write_config(
            FLO_AGENT_HOST=PLACEHOLDER_HOSTNAME,
            FLO_AGENT_USER='alice',
            FLO_AGENT_PORT='2222',
            FLO_AGENT_TRANSPORT='ssh',
            FLO_AGENT_TMUX_PREFIX='dev',
        )
        key, _pub = self.write_key()
        proc = self.run_cli(['launch', 'claude'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv(), [[
            'ssh', '-t', '-p', '2222', '-i', str(key), '-o', 'IdentitiesOnly=yes',
            '--', 'alice@host.example',
            'tmux', 'new', '-A', '-s', 'dev-claude', 'claude',
        ]])

    def test_launch_mosh_passes_ssh_bootstrap_with_port_and_key(self):
        self.write_config(
            FLO_AGENT_HOST=PLACEHOLDER_HOSTNAME,
            FLO_AGENT_USER='alice',
            FLO_AGENT_PORT='2222',
            FLO_AGENT_TRANSPORT='mosh',
            FLO_AGENT_TMUX_PREFIX='lab',
        )
        key, _pub = self.write_key()
        proc = self.run_cli(['launch', 'grok'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv(), [[
            'mosh',
            f'--ssh=ssh -p 2222 -i {key} -o IdentitiesOnly=yes',
            '--', 'alice@host.example',
            'tmux', 'new', '-A', '-s', 'lab-grok', 'grok',
        ]])

    def test_check_reports_reachability_and_remote_commands(self):
        self.write_config(FLO_AGENTS='claude codex grok')
        proc = self.run_cli(['check'])
        self.assertNotEqual(proc.returncode, 0)
        out = proc.stdout
        self.assertIn(PLACEHOLDER_HOST, out)
        self.assertRegex(out, r'reachable.*yes')
        self.assertIn('/usr/bin/claude', out)
        self.assertRegex(out, r'codex.*missing')
        self.assertIn('/usr/bin/grok', out)
        calls = self.recorded_argv()
        self.assertEqual(calls[0][:1], ['ssh'])
        joined = ' '.join(calls[0])
        self.assertIn('BatchMode=yes', joined)
        self.assertIn('ConnectTimeout=5', joined)
        self.assertIn('StrictHostKeyChecking=accept-new', joined)
        self.assertIn('--', calls[0])
        self.assertEqual(calls[0][calls[0].index('--') + 1], PLACEHOLDER_HOST)
        self.assertEqual(calls[0][-1], 'true')
        self.assertIn('-p', calls[0])
        self.assertIn('22', calls[0])
        self.assertFalse(self.curl_mark.exists())

    def test_host_help_prints_official_commands_only(self):
        proc = self.run_cli(['host-help'], path_mode='system')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = proc.stdout
        self.assertIn('curl -fsSL https://claude.ai/install.sh | bash', text)
        self.assertIn('code.claude.com/docs/en/setup', text)
        self.assertIn('curl -fsSL https://chatgpt.com/codex/install.sh | sh', text)
        self.assertIn('codex login --device-auth', text)
        self.assertIn('github.com/openai/codex', text)
        self.assertIn('curl -fsSL https://x.ai/cli/install.sh | bash', text)
        self.assertIn('XAI_API_KEY', text)
        self.assertIn('docs.x.ai/build/overview', text)
        self.assertIn('4 GB', text)
        claude_only = self.run_cli(['host-help', 'claude'], path_mode='system')
        self.assertEqual(claude_only.returncode, 0)
        self.assertIn('claude.ai/install.sh', claude_only.stdout)
        self.assertNotIn('chatgpt.com', claude_only.stdout)
        self.assertFalse(self.curl_mark.exists())

    def test_uninstall_removes_config_and_wrapper_only(self):
        proc = self.run_cli(
            ['setup', '--host', PLACEHOLDER_HOST, '--agents', 'claude', '--force'],
            path_mode='system',
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        wrapper = self.home / '.local' / 'bin' / 'flo-agents'
        self.assertTrue(self.config_path().exists())
        self.assertTrue(wrapper.is_symlink())
        self.assertEqual(wrapper.resolve(), SCRIPT.resolve())
        leftover = self.config_path().parent / 'keep-me'
        leftover.write_text('user file\n')
        tmp = self.config_path().parent / 'config.tmp.12345'
        tmp.write_text('stale\n')
        gone = self.run_cli(['uninstall'], path_mode='system')
        self.assertEqual(gone.returncode, 0, gone.stderr)
        self.assertFalse(self.config_path().exists())
        self.assertFalse(tmp.exists())
        self.assertTrue(leftover.is_file())
        self.assertTrue(leftover.parent.is_dir())
        self.assertFalse(wrapper.exists())
        self.assertFalse(wrapper.is_symlink())
        self.assertTrue(SCRIPT.is_file())

    def test_uninstall_leaves_regular_file_wrapper(self):
        wrap = self.home / '.local' / 'bin'
        wrap.mkdir(parents=True)
        foreign = wrap / 'flo-agents'
        foreign.write_text('#!/bin/sh\n# not ours\n')
        self.write_config()
        gone = self.run_cli(['uninstall'], path_mode='system')
        self.assertEqual(gone.returncode, 0, gone.stderr)
        self.assertTrue(foreign.is_file())
        self.assertFalse(foreign.is_symlink())
        self.assertEqual(foreign.read_text(), '#!/bin/sh\n# not ours\n')
        self.assertFalse(self.config_path().exists())

    def test_uninstall_leaves_symlink_to_other_script(self):
        wrap = self.home / '.local' / 'bin'
        wrap.mkdir(parents=True)
        other = self.home / 'other-tool'
        other.write_text('#!/bin/sh\n')
        foreign = wrap / 'flo-agents'
        foreign.symlink_to(other)
        self.write_config()
        gone = self.run_cli(['uninstall'], path_mode='system')
        self.assertEqual(gone.returncode, 0, gone.stderr)
        self.assertTrue(foreign.is_symlink())
        self.assertEqual(foreign.resolve(), other.resolve())
        self.assertFalse(self.config_path().exists())

    def test_config_get_json_unconfigured_defaults(self):
        proc = self.run_cli(['config', 'get', '--json'], path_mode='system')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data, {
            'configured': False,
            'host': '',
            'user': '',
            'port': 22,
            'transport': 'mosh',
            'agents': ['claude', 'codex', 'grok'],
            'default': 'claude',
            'cmd': {'claude': 'claude', 'codex': 'codex', 'grok': 'grok'},
            'tmux': True,
            'tmux_prefix': 'flo',
            'key': {'present': False, 'public': ''},
            'local': {
                'provider': '',
                'base_url': '',
                'model': '',
                'key_set': False,
                'installed': False,
                'version': '',
                'mode': 'local',
            },
        })
        self.assertIsInstance(data['port'], int)
        self.assertIsInstance(data['tmux'], bool)
        self.assertIsInstance(data['configured'], bool)

    def test_config_get_json_escapes_tricky_strings(self):
        self.write_config()
        tricky = r'claude --foo "bar\baz" and "quotes"'
        proc = self.run_cli(['config', 'set', 'cmd.claude', tricky], path_mode='system')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        dumped = self.run_cli(['config', 'get', '--json'], path_mode='system')
        self.assertEqual(dumped.returncode, 0, dumped.stderr)
        data = json.loads(dumped.stdout)
        self.assertEqual(data['cmd']['claude'], tricky)
        self.assertEqual(data['configured'], True)
        self.assertEqual(data['host'], PLACEHOLDER_HOSTNAME)
        self.assertEqual(data['user'], PLACEHOLDER_USER)

    def test_config_get_plain_keys(self):
        self.write_config(
            FLO_AGENT_HOST=PLACEHOLDER_HOSTNAME,
            FLO_AGENT_USER='alice',
            FLO_AGENT_PORT='2222',
            FLO_AGENT_TMUX='0',
            FLO_AGENT_TMUX_PREFIX='lab',
        )
        cases = {
            'host': 'host.example',
            'user': 'alice',
            'port': '2222',
            'transport': 'mosh',
            'agents': 'claude codex grok',
            'default': 'claude',
            'cmd.claude': 'claude',
            'tmux': '0',
            'tmux_prefix': 'lab',
        }
        for key, expected in cases.items():
            with self.subTest(key=key):
                proc = self.run_cli(['config', 'get', key], path_mode='system')
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout, expected + '\n')

    def test_legacy_user_at_host_splits_on_read(self):
        self.write_config(FLO_AGENT_HOST=PLACEHOLDER_HOST)
        host = self.run_cli(['config', 'get', 'host'], path_mode='system')
        user = self.run_cli(['config', 'get', 'user'], path_mode='system')
        self.assertEqual(host.returncode, 0, host.stderr)
        self.assertEqual(user.returncode, 0, user.stderr)
        self.assertEqual(host.stdout, PLACEHOLDER_HOSTNAME + '\n')
        self.assertEqual(user.stdout, PLACEHOLDER_USER + '\n')
        dumped = self.run_cli(['config', 'get', '--json'], path_mode='system')
        data = json.loads(dumped.stdout)
        self.assertEqual(data['host'], PLACEHOLDER_HOSTNAME)
        self.assertEqual(data['user'], PLACEHOLDER_USER)
        self.assertEqual(data['port'], 22)

    def test_config_set_valid_keys(self):
        cases = [
            ('host', 'host.example', "FLO_AGENT_HOST='host.example'"),
            ('host', 'localhost', "FLO_AGENT_HOST='localhost'"),
            ('host', '192.0.2.1', "FLO_AGENT_HOST='192.0.2.1'"),
            ('host', '2001:db8::1', "FLO_AGENT_HOST='2001:db8::1'"),
            ('user', 'alice', "FLO_AGENT_USER='alice'"),
            ('user', 'bob.o_neill-1', "FLO_AGENT_USER='bob.o_neill-1'"),
            ('port', '22', 'FLO_AGENT_PORT=22'),
            ('port', '2222', 'FLO_AGENT_PORT=2222'),
            ('port', '65535', 'FLO_AGENT_PORT=65535'),
            ('transport', 'ssh', "FLO_AGENT_TRANSPORT='ssh'"),
            ('transport', 'mosh', "FLO_AGENT_TRANSPORT='mosh'"),
            ('agents', 'claude', "FLO_AGENTS='claude'"),
            ('agents', 'claude,codex', "FLO_AGENTS='claude codex'"),
            ('agents', 'grok claude', "FLO_AGENTS='grok claude'"),
            ('default', 'claude', "FLO_AGENT_DEFAULT='claude'"),
            ('cmd.claude', 'claude --debug', "FLO_AGENT_CMD_claude='claude --debug'"),
            ('cmd.codex', 'codex --foo "bar"', '''FLO_AGENT_CMD_codex='codex --foo "bar"\''''),
            ('cmd.grok', 'grok', "FLO_AGENT_CMD_grok='grok'"),
            ('tmux', 'on', 'FLO_AGENT_TMUX=1'),
            ('tmux', 'off', 'FLO_AGENT_TMUX=0'),
            ('tmux', '1', 'FLO_AGENT_TMUX=1'),
            ('tmux', '0', 'FLO_AGENT_TMUX=0'),
            ('tmux_prefix', 'flo', "FLO_AGENT_TMUX_PREFIX='flo'"),
            ('tmux_prefix', 'Lab_1-x', "FLO_AGENT_TMUX_PREFIX='Lab_1-x'"),
        ]
        for key, value, needle in cases:
            with self.subTest(key=key, value=value):
                if self.config_path().exists():
                    self.config_path().unlink()
                proc = self.run_cli(['config', 'set', key, value], path_mode='system')
                self.assertEqual(proc.returncode, 0, proc.stderr)
                path = self.config_path()
                self.assertTrue(path.is_file())
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
                self.assertIn(needle, path.read_text().replace("FLO_AGENT_PORT='", 'FLO_AGENT_PORT=').replace("FLO_AGENT_TMUX='", 'FLO_AGENT_TMUX='))

    def test_config_set_invalid_keys_leave_file_unchanged(self):
        path = self.write_config()
        original = path.read_text()
        invalid = [
            ('host', ''),
            ('host', '-bad.example'),
            ('host', 'user@host.example'),
            ('host', 'host example'),
            ('host', 'host"quote'),
            ("host", "host'quote"),
            ('host', 'host;id'),
            ('user', ''),
            ('user', '-alice'),
            ('user', 'alice@host'),
            ('user', 'alice bob'),
            ('port', '0'),
            ('port', '65536'),
            ('port', 'abc'),
            ('port', '022'),
            ('port', '-22'),
            ('transport', 'telnet'),
            ('agents', ''),
            ('agents', 'notatool'),
            ('default', 'notatool'),
            ('default', 'grok'),  # write_config agents include grok... wait, default grok IS valid
            ('cmd.claude', ''),
            ('cmd.claude', "claude 'oops'"),
            ('cmd.claude', 'claude\n--debug'),
            ('cmd.claude', '  '),
            ('tmux', 'maybe'),
            ('tmux_prefix', ''),
            ('tmux_prefix', 'flo prefix'),
            ('tmux_prefix', 'flo.1'),
            ('nope', 'x'),
        ]
        # grok is in default agents; replace that case with agents=claude then default=grok below
        invalid = [c for c in invalid if c != ('default', 'grok')]
        for key, value in invalid:
            with self.subTest(key=key, value=repr(value)):
                path.write_text(original)
                path.chmod(0o600)
                proc = self.run_cli(['config', 'set', key, value], path_mode='system')
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(proc.stderr.count('\n'), 1)
                self.assertTrue(proc.stderr.strip())
                self.assertEqual(path.read_text(), original)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

        self.write_config(FLO_AGENTS='claude', FLO_AGENT_DEFAULT='claude')
        original = self.config_path().read_text()
        proc = self.run_cli(['config', 'set', 'default', 'grok'], path_mode='system')
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(self.config_path().read_text(), original)

    def test_config_set_agents_adjusts_invalid_default(self):
        self.write_config(FLO_AGENTS='claude grok', FLO_AGENT_DEFAULT='grok')
        proc = self.run_cli(['config', 'set', 'agents', 'claude'], path_mode='system')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = self.config_path().read_text()
        self.assertIn("FLO_AGENTS='claude'", text)
        self.assertIn("FLO_AGENT_DEFAULT='claude'", text)

    def test_config_set_creates_file_atomically_mode_600(self):
        self.assertFalse(self.config_path().exists())
        proc = self.run_cli(['config', 'set', 'host', 'host.example'], path_mode='system')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        path = self.config_path()
        self.assertTrue(path.is_file())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        leftovers = list(path.parent.glob('config.tmp.*'))
        self.assertEqual(leftovers, [])

    def test_config_unset_resets_to_defaults(self):
        self.write_config(
            FLO_AGENT_HOST=PLACEHOLDER_HOSTNAME,
            FLO_AGENT_USER='alice',
            FLO_AGENT_PORT='2222',
            FLO_AGENT_TRANSPORT='ssh',
            FLO_AGENTS='grok',
            FLO_AGENT_DEFAULT='grok',
            FLO_AGENT_CMD_grok='grok --x',
            FLO_AGENT_TMUX='0',
            FLO_AGENT_TMUX_PREFIX='lab',
        )
        expected = {
            'host': '',
            'user': '',
            'port': '22',
            'transport': 'mosh',
            'agents': 'claude codex grok',
            'default': 'claude',
            'cmd.grok': 'grok',
            'tmux': '1',
            'tmux_prefix': 'flo',
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                proc = self.run_cli(['config', 'unset', key], path_mode='system')
                self.assertEqual(proc.returncode, 0, proc.stderr)
                got = self.run_cli(['config', 'get', key], path_mode='system')
                self.assertEqual(got.stdout, value + '\n', got.stderr)

    def test_key_ensure_creates_and_is_idempotent(self):
        proc = self.run_cli(['key', 'ensure'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, FAKE_PUBLIC + '\n')
        key = self.key_path()
        pub = Path(str(key) + '.pub')
        self.assertTrue(key.is_file())
        self.assertTrue(pub.is_file())
        self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(key.parent.stat().st_mode), 0o700)
        self.assertEqual(key.read_text(), FAKE_PRIVATE + '\n')
        key.write_text('DO-NOT-OVERWRITE\n')
        pub.write_text(FAKE_PUBLIC + '\n')
        again = self.run_cli(['key', 'ensure'])
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(again.stdout, FAKE_PUBLIC + '\n')
        self.assertEqual(key.read_text(), 'DO-NOT-OVERWRITE\n')
        gens = [row for row in self.recorded_argv() if row and row[0] == 'ssh-keygen']
        self.assertEqual(len(gens), 1)
        self.assertIn('-t', gens[0])
        self.assertIn('ed25519', gens[0])
        self.assertIn('-N', gens[0])
        self.assertIn('', gens[0])
        self.assertIn('-C', gens[0])
        self.assertIn('flo-agents', gens[0])
        self.assertNotIn(FAKE_PRIVATE, proc.stdout + proc.stderr + again.stdout + again.stderr)
        self.assertNotIn('DO-NOT-OVERWRITE', again.stdout + again.stderr)

    def test_key_show_prints_public_or_exits_1(self):
        missing = self.run_cli(['key', 'show'], path_mode='system')
        self.assertEqual(missing.returncode, 1)
        self.assertNotIn(FAKE_PRIVATE, missing.stdout + missing.stderr)
        self.write_key()
        shown = self.run_cli(['key', 'show'], path_mode='system')
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertEqual(shown.stdout, FAKE_PUBLIC + '\n')
        self.assertNotIn(FAKE_PRIVATE, shown.stdout + shown.stderr)

    def test_key_qr_writes_png_or_exits_3(self):
        self.write_key()
        out = Path(self.temp.name) / 'key.png'
        proc = self.run_cli(['key', 'qr', str(out)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(out.is_file())
        self.assertEqual(out.read_text(), 'QR:' + FAKE_PUBLIC)
        self.assertNotIn(FAKE_PRIVATE, proc.stdout + proc.stderr + out.read_text())
        qr_calls = [row for row in self.recorded_argv() if row and row[0] == 'qrencode']
        self.assertEqual(len(qr_calls), 1)
        missing = self.run_cli(['key', 'qr', str(out)], path_mode='no_qrencode')
        self.assertEqual(missing.returncode, 3)
        self.assertNotIn(FAKE_PRIVATE, missing.stdout + missing.stderr)

    def test_config_get_json_includes_key_never_private(self):
        self.write_config()
        self.write_key(private='PRIVATE_MARKER_NOT_FOR_OUTPUT')
        proc = self.run_cli(['config', 'get', '--json'], path_mode='system')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data['key'], {'present': True, 'public': FAKE_PUBLIC})
        self.assertNotIn('PRIVATE_MARKER_NOT_FOR_OUTPUT', proc.stdout)
        self.assertNotIn('PRIVATE_MARKER_NOT_FOR_OUTPUT', proc.stderr)

    def test_check_json_reachable_with_missing_agent(self):
        self.write_config(FLO_AGENTS='claude codex grok')
        proc = self.run_cli(['check', '--json'])
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        self.assertEqual(data['reachable'], True)
        self.assertEqual(data['agents'], {
            'claude': 'present',
            'codex': 'missing',
            'grok': 'present',
        })
        self.assertEqual(data['host_key'], 'known')
        self.assertIsInstance(data['error'], str)

    def test_check_json_success_all_present(self):
        self.write_config(FLO_AGENTS='claude grok')
        proc = self.run_cli(['check', '--json'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data['reachable'], True)
        self.assertEqual(data['agents'], {'claude': 'present', 'grok': 'present'})
        self.assertEqual(data['host_key'], 'known')

    def test_check_json_host_key_states(self):
        self.write_config(FLO_AGENTS='claude')
        cases = {
            'new': (0, True, 'new'),
            'known': (0, True, 'known'),
            'changed': (1, False, 'changed'),
            'unknown': (1, False, 'unknown'),
        }
        for hk, (code, reachable, label) in cases.items():
            with self.subTest(host_key=hk):
                if self.argv_log.exists():
                    self.argv_log.unlink()
                proc = self.run_cli(['check', '--json'], extra={'FLO_AGENTS_HOST_KEY': hk})
                self.assertEqual(proc.returncode, code, proc.stderr + proc.stdout)
                data = json.loads(proc.stdout)
                self.assertEqual(data['reachable'], reachable)
                self.assertEqual(data['host_key'], label)
                joined = ' '.join(self.recorded_argv()[0])
                self.assertIn('StrictHostKeyChecking=accept-new', joined)
                self.assertNotIn('StrictHostKeyChecking=no', joined)
                self.assertNotIn('StrictHostKeyChecking=ask', joined)
                if hk == 'changed':
                    self.assertIn('changed', data['error'].lower())
                    self.assertIn('host key', (proc.stdout + proc.stderr).lower())

    def test_check_uses_user_port_and_key(self):
        self.write_config(
            FLO_AGENT_HOST=PLACEHOLDER_HOSTNAME,
            FLO_AGENT_USER='alice',
            FLO_AGENT_PORT='2222',
            FLO_AGENTS='claude',
        )
        key, _pub = self.write_key()
        proc = self.run_cli(['check', '--json'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        call = self.recorded_argv()[0]
        self.assertEqual(call[0], 'ssh')
        self.assertIn('-p', call)
        self.assertIn('2222', call)
        self.assertIn('-i', call)
        self.assertIn(str(key), call)
        self.assertIn('IdentitiesOnly=yes', ' '.join(call))
        self.assertEqual(call[call.index('--') + 1], 'alice@host.example')

    TEST_API_KEY = 'test-api-key-xx99'

    def crush_payload_script(self):
        return textwrap.dedent('''\
            #!/usr/bin/python3
            import json, os, sys
            log = os.environ.get("FLO_AGENTS_ARGV_FILE", "")
            env_info = []
            for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY"):
                if k in os.environ:
                    val = os.environ[k]
                    env_info.append({"name": k, "set": True, "last4": val[-4:]})
            env_info.append({
                "name": "CRUSH_GLOBAL_CONFIG",
                "value": os.environ.get("CRUSH_GLOBAL_CONFIG", ""),
            })
            if log:
                with open(log, "a", encoding="utf-8") as fh:
                    json.dump(["crush", *sys.argv[1:], env_info], fh)
                    fh.write("\\n")
            ''')

    def make_crush_tarball(self):
        tarpath = Path(self.temp.name) / 'crush_0.101.0_Linux_armv7.tar.gz'
        payload = self.crush_payload_script().encode()
        license_text = b'Charm Crush\nFunctional Source License, Version 1.1, MIT Future License\n'
        with tarfile.open(tarpath, 'w:gz') as tf:
            info = tarfile.TarInfo('crush')
            info.size = len(payload)
            info.mode = 0o755
            tf.addfile(info, io.BytesIO(payload))
            lic = tarfile.TarInfo('LICENSE')
            lic.size = len(license_text)
            lic.mode = 0o644
            tf.addfile(lic, io.BytesIO(license_text))
        sha = hashlib.sha256(tarpath.read_bytes()).hexdigest()
        return tarpath, sha

    def local_install_env(self, tarpath, sha):
        return {
            'FLO_AGENTS_FAKE_TARBALL': str(tarpath),
            'FLO_AGENTS_TEST_CRUSH_SHA256': sha,
            'FLO_AGENTS_FAKE_ASSET': 'crush_0.101.0_Linux_armv7.tar.gz',
            'FLO_AGENTS_FAKE_UNAME_M': 'armv7l',
        }

    def test_config_set_local_keys(self):
        proc = self.run_cli(['config', 'set', 'local.provider', 'ollama'], path_mode='system')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.run_cli(['config', 'get', 'local.provider'], path_mode='system').stdout,
            'ollama\n',
        )
        url = self.run_cli(
            ['config', 'set', 'local.base_url', 'http://host.example:11434/v1'],
            path_mode='system',
        )
        self.assertEqual(url.returncode, 0, url.stderr)
        model = self.run_cli(['config', 'set', 'local.model', 'llama3.2'], path_mode='system')
        self.assertEqual(model.returncode, 0, model.stderr)
        dumped = self.run_cli(['config', 'get', '--json'], path_mode='system')
        data = json.loads(dumped.stdout)
        self.assertEqual(data['local']['provider'], 'ollama')
        self.assertEqual(data['local']['base_url'], 'http://host.example:11434/v1')
        self.assertEqual(data['local']['model'], 'llama3.2')
        self.assertEqual(data['local']['mode'], 'local')
        self.assertFalse(data['local']['key_set'])
        self.assertFalse(data['local']['installed'])

    def test_config_set_local_invalid_leaves_file_unchanged(self):
        self.write_config()
        original = self.config_path().read_text()
        invalid = [
            ('local.provider', 'nope'),
            ('local.base_url', 'ftp://host.example'),
            ('local.base_url', 'not-a-url'),
            ('local.base_url', 'http://host.example/x y'),
            ('local.model', ''),
            ('local.model', "bad'quote"),
        ]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                self.config_path().write_text(original)
                self.config_path().chmod(0o600)
                proc = self.run_cli(['config', 'set', key, value], path_mode='system')
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(self.config_path().read_text(), original)

    def test_secret_set_from_stdin_never_argv_or_full_print(self):
        bad = self.run_cli(
            ['secret', 'set', 'api_key', self.TEST_API_KEY],
            path_mode='system',
            input_text=self.TEST_API_KEY + '\n',
        )
        self.assertEqual(bad.returncode, 2, bad.stderr)
        self.assertFalse((self.config_home / 'flo-agents' / 'secrets').exists())
        proc = self.run_cli(
            ['secret', 'set', 'api_key'],
            path_mode='system',
            input_text=self.TEST_API_KEY + '\n',
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        secrets = self.config_home / 'flo-agents' / 'secrets'
        self.assertTrue(secrets.is_file())
        self.assertEqual(stat.S_IMODE(secrets.stat().st_mode), 0o600)
        self.assertIn(self.TEST_API_KEY, secrets.read_text())
        self.assertNotIn(self.TEST_API_KEY, proc.stdout)
        self.assertNotIn(self.TEST_API_KEY, proc.stderr)
        status = self.run_cli(['secret', 'status'], path_mode='system')
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(status.stdout, 'set xx99\n')
        self.assertNotIn(self.TEST_API_KEY, status.stdout)
        dumped = self.run_cli(['config', 'get', '--json'], path_mode='system')
        data = json.loads(dumped.stdout)
        self.assertTrue(data['local']['key_set'])
        self.assertNotIn(self.TEST_API_KEY, dumped.stdout)
        unset = self.run_cli(['secret', 'unset'], path_mode='system')
        self.assertEqual(unset.returncode, 0, unset.stderr)
        self.assertFalse(secrets.exists())
        gone = self.run_cli(['secret', 'status'], path_mode='system')
        self.assertEqual(gone.stdout, 'unset\n')

    def test_local_install_verifies_checksum_and_keeps_license(self):
        tarpath, sha = self.make_crush_tarball()
        extra = self.local_install_env(tarpath, sha)
        proc = self.run_cli(['local', 'install'], extra=extra)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('FSL-1.1-MIT', proc.stdout)
        self.assertIn('personal use', proc.stdout.lower())
        verdir = self.home / '.local' / 'share' / 'flo-agents' / 'crush' / '0.101.0'
        binpath = verdir / 'crush'
        self.assertTrue(binpath.is_file())
        self.assertTrue(os.access(binpath, os.X_OK))
        self.assertTrue((verdir / 'LICENSE').is_file())
        self.assertIn('Functional Source License', (verdir / 'LICENSE').read_text())
        link = self.home / '.local' / 'bin' / 'crush-flo'
        self.assertTrue(link.is_symlink())
        status = self.run_cli(['local', 'status'], extra=extra)
        self.assertEqual(status.returncode, 0, status.stderr)
        data = json.loads(status.stdout)
        self.assertEqual(data, {
            'installed': True,
            'version': '0.101.0',
            'path': str(binpath),
        })
        dumped = self.run_cli(['config', 'get', '--json'], extra=extra)
        self.assertTrue(json.loads(dumped.stdout)['local']['installed'])
        self.assertEqual(json.loads(dumped.stdout)['local']['version'], '0.101.0')

    def test_local_install_checksum_mismatch_does_not_extract(self):
        tarpath, _sha = self.make_crush_tarball()
        extra = self.local_install_env(tarpath, '0' * 64)
        proc = self.run_cli(['local', 'install'], extra=extra)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('checksum', proc.stderr.lower())
        verdir = self.home / '.local' / 'share' / 'flo-agents' / 'crush' / '0.101.0'
        self.assertFalse(verdir.exists())
        self.assertFalse((self.home / '.local' / 'bin' / 'crush-flo').exists())

    def test_local_install_refuses_unknown_arch(self):
        tarpath, sha = self.make_crush_tarball()
        extra = self.local_install_env(tarpath, sha)
        extra['FLO_AGENTS_FAKE_UNAME_M'] = 'riscv64'
        proc = self.run_cli(['local', 'install'], extra=extra)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('unsupported', proc.stderr.lower())

    def test_list_and_json_include_crush_when_local_ready(self):
        tarpath, sha = self.make_crush_tarball()
        extra = self.local_install_env(tarpath, sha)
        self.write_config()
        self.assertEqual(self.run_cli(['local', 'install'], extra=extra).returncode, 0)
        self.assertEqual(
            self.run_cli(['config', 'set', 'local.provider', 'anthropic'], extra=extra).returncode,
            0,
        )
        self.assertEqual(
            self.run_cli(['config', 'set', 'local.model', 'claude-placeholder'], extra=extra).returncode,
            0,
        )
        listed = self.run_cli(['list'], extra=extra)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertNotIn('crush', listed.stdout.splitlines())
        self.assertEqual(
            self.run_cli(
                ['secret', 'set', 'api_key'],
                extra=extra,
                input_text=self.TEST_API_KEY + '\n',
            ).returncode,
            0,
        )
        listed = self.run_cli(['list'], extra=extra)
        self.assertEqual(listed.stdout.splitlines()[-1], 'crush')
        dumped = json.loads(self.run_cli(['config', 'get', '--json'], extra=extra).stdout)
        self.assertIn('crush', dumped['agents'])
        self.assertEqual(dumped['local']['mode'], 'local')
        self.assertTrue(dumped['local']['installed'])
        self.assertTrue(dumped['local']['key_set'])

    def test_launch_crush_is_local_and_does_not_ssh(self):
        tarpath, sha = self.make_crush_tarball()
        extra = self.local_install_env(tarpath, sha)
        self.write_config()
        user_crush = self.config_home / 'crush' / 'crush.json'
        user_crush.parent.mkdir(parents=True)
        user_crush.write_text('{"keep":"me"}\n')
        self.assertEqual(self.run_cli(['local', 'install'], extra=extra).returncode, 0)
        self.assertEqual(
            self.run_cli(['config', 'set', 'local.provider', 'anthropic'], extra=extra).returncode,
            0,
        )
        self.assertEqual(
            self.run_cli(['config', 'set', 'local.model', 'claude-placeholder'], extra=extra).returncode,
            0,
        )
        self.assertEqual(
            self.run_cli(
                ['secret', 'set', 'api_key'],
                extra=extra,
                input_text=self.TEST_API_KEY + '\n',
            ).returncode,
            0,
        )
        if self.argv_log.exists():
            self.argv_log.unlink()
        proc = self.run_cli(['launch', 'crush'], extra=extra)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(self.TEST_API_KEY, proc.stdout)
        self.assertNotIn(self.TEST_API_KEY, proc.stderr)
        calls = self.recorded_argv()
        self.assertTrue(calls)
        self.assertEqual(calls[-1][0], 'crush')
        self.assertNotEqual(calls[-1][0], 'ssh')
        self.assertNotEqual(calls[-1][0], 'mosh')
        env_info = calls[-1][-1]
        names = {row['name']: row for row in env_info if isinstance(row, dict)}
        self.assertEqual(names['ANTHROPIC_API_KEY']['last4'], 'xx99')
        self.assertNotIn('OPENAI_API_KEY', names)
        gdir = names['CRUSH_GLOBAL_CONFIG']['value']
        self.assertEqual(gdir, str(self.config_home / 'flo-agents' / 'crush'))
        generated = Path(gdir) / 'crush.json'
        self.assertTrue(generated.is_file())
        text = generated.read_text()
        self.assertIn('$ANTHROPIC_API_KEY', text)
        self.assertNotIn(self.TEST_API_KEY, text)
        self.assertEqual(user_crush.read_text(), '{"keep":"me"}\n')

    def test_local_uninstall_removes_tree_symlink_and_crush_config(self):
        tarpath, sha = self.make_crush_tarball()
        extra = self.local_install_env(tarpath, sha)
        self.assertEqual(self.run_cli(['local', 'install'], extra=extra).returncode, 0)
        self.assertEqual(
            self.run_cli(['config', 'set', 'local.provider', 'ollama'], extra=extra).returncode,
            0,
        )
        self.assertEqual(
            self.run_cli(
                ['config', 'set', 'local.base_url', 'http://host.example:11434/v1'],
                extra=extra,
            ).returncode,
            0,
        )
        self.assertEqual(
            self.run_cli(['config', 'set', 'local.model', 'llama3.2'], extra=extra).returncode,
            0,
        )
        secrets = self.config_home / 'flo-agents' / 'secrets'
        self.run_cli(
            ['secret', 'set', 'api_key'],
            extra=extra,
            input_text=self.TEST_API_KEY + '\n',
        )
        # generate crush.json via a dry launch? uninstall should remove crush config dir
        self.run_cli(['launch', 'crush'], extra=extra)
        gone = self.run_cli(['local', 'uninstall'], extra=extra)
        self.assertEqual(gone.returncode, 0, gone.stderr)
        self.assertFalse((self.home / '.local' / 'share' / 'flo-agents' / 'crush' / '0.101.0').exists())
        self.assertFalse((self.home / '.local' / 'bin' / 'crush-flo').exists())
        self.assertFalse((self.config_home / 'flo-agents' / 'crush' / 'crush.json').exists())
        self.assertTrue(secrets.is_file())
        status = json.loads(self.run_cli(['local', 'status'], extra=extra).stdout)
        self.assertEqual(status['installed'], False)


if __name__ == '__main__':
    unittest.main()
