"""CLI contract tests for scripts/flo-agents (no network)."""
import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'flo-agents'
PLACEHOLDER_HOST = 'user@host.example'


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
            #!/bin/sh
            echo called > "{self.curl_mark}"
            echo "curl must not run" >&2
            exit 1
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

    def env(self, extra=None, path_mode='fakes'):
        env = os.environ.copy()
        env['HOME'] = str(self.home)
        env['XDG_CONFIG_HOME'] = str(self.config_home)
        env['FLO_AGENTS_ARGV_FILE'] = str(self.argv_log)
        env['FLO_AGENTS_REMOTE_CMDS'] = 'claude grok'
        env.pop('FLO_AGENT_HOST', None)
        if path_mode == 'fakes':
            env['PATH'] = str(self.bin_dir)
        elif path_mode == 'ssh_only':
            mosh = self.bin_dir / 'mosh'
            if mosh.exists():
                mosh.unlink()
            env['PATH'] = str(self.bin_dir)
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
            ['setup', '--host', PLACEHOLDER_HOST, '--agents', 'omarchy'],
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
        text = path.read_text()
        self.assertIn(f"FLO_AGENT_HOST='{PLACEHOLDER_HOST}'", text)
        self.assertIn("FLO_AGENT_TRANSPORT='ssh'", text)
        self.assertIn("FLO_AGENTS='claude codex'", text)
        self.assertIn("FLO_AGENT_DEFAULT='codex'", text)
        self.assertIn("FLO_AGENT_CMD_claude='claude'", text)
        self.assertIn("FLO_AGENT_CMD_codex='codex'", text)
        self.assertNotIn('FLO_AGENT_CMD_grok', text)
        self.assertIn('FLO_AGENT_TMUX=1', text.replace("'", ''))
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
        self.assertIn("FLO_AGENT_HOST='other@host.example'", self.config_path().read_text())
        self.assertIn("FLO_AGENTS='grok'", self.config_path().read_text())

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
            'mosh', PLACEHOLDER_HOST, '--',
            'tmux', 'new', '-A', '-s', 'flo-claude', 'claude',
        ]])

    def test_launch_ssh_tmux_command(self):
        self.write_config(FLO_AGENT_TRANSPORT='ssh')
        proc = self.run_cli(['launch', 'codex'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv(), [[
            'ssh', '-t', PLACEHOLDER_HOST,
            'tmux', 'new', '-A', '-s', 'flo-codex', 'codex',
        ]])

    def test_launch_without_tmux(self):
        self.write_config(FLO_AGENT_TMUX='0', FLO_AGENT_TRANSPORT='ssh')
        proc = self.run_cli(['launch', 'grok'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv(), [[
            'ssh', '-t', PLACEHOLDER_HOST, 'grok',
        ]])

    def test_launch_falls_back_to_ssh_when_mosh_missing(self):
        self.write_config(FLO_AGENT_TRANSPORT='mosh')
        proc = self.run_cli(['launch'], path_mode='ssh_only')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv()[0][0], 'ssh')
        self.assertEqual(self.recorded_argv()[0][1:3], ['-t', PLACEHOLDER_HOST])
        self.assertIn('flo-claude', self.recorded_argv()[0])

    def test_launch_uses_default_and_custom_remote_command(self):
        self.write_config(
            FLO_AGENT_DEFAULT='claude',
            FLO_AGENT_CMD_claude='claude --debug',
            FLO_AGENT_TRANSPORT='mosh',
        )
        proc = self.run_cli(['launch'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.recorded_argv(), [[
            'mosh', PLACEHOLDER_HOST, '--',
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
        self.assertIn('BatchMode=yes', ' '.join(calls[0]))
        self.assertIn('ConnectTimeout=5', ' '.join(calls[0]))
        self.assertEqual(calls[0][-1], 'true')
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
        self.assertTrue(wrapper.exists() or wrapper.is_symlink())
        gone = self.run_cli(['uninstall'], path_mode='system')
        self.assertEqual(gone.returncode, 0, gone.stderr)
        self.assertFalse(self.config_path().exists())
        self.assertFalse(wrapper.exists())
        self.assertFalse(wrapper.is_symlink())
        self.assertTrue(SCRIPT.is_file())


if __name__ == '__main__':
    unittest.main()
