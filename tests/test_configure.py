import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('configure',ROOT/'scripts/configure.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ConfigureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dev-bootstrap-test-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def test_preserves_settings_and_rerun_is_identical(self):
        original = '# own setup\nexport CUSTOM_VALUE=keep\nalias ll="ls -l"\n'
        (self.home/'.bashrc').write_text(original)
        module.configure(self.home)
        first = (self.home/'.bashrc').read_text()
        backups = list((self.home/'.local/state/jayson-dev/backups').glob('*/*'))
        self.assertTrue(first.startswith(original))
        self.assertEqual(first.count(module.START),1)
        self.assertEqual(backups[0].read_text(),original)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode),0o600)
        module.configure(self.home)
        self.assertEqual((self.home/'.bashrc').read_text(),first)
        self.assertEqual(list((self.home/'.local/state/jayson-dev/backups').glob('*/*')),backups)
        self.assertEqual(stat.S_IMODE((self.home/'.local/bin/dev-run').stat().st_mode),0o755)

    def test_existing_login_profile_wins(self):
        (self.home/'.bash_profile').write_text('source ~/.profile\n')
        (self.home/'.profile').write_text('# untouched\n')
        module.configure(self.home)
        self.assertIn(module.START,(self.home/'.bash_profile').read_text())
        self.assertEqual((self.home/'.profile').read_text(),'# untouched\n')

    def test_invalid_markers_change_nothing(self):
        original = module.START+'\n# incomplete\n'
        (self.home/'.bashrc').write_text(original)
        with self.assertRaises(RuntimeError): module.configure(self.home)
        self.assertEqual((self.home/'.bashrc').read_text(),original)
        self.assertFalse((self.home/'.config').exists())

    def test_unknown_config_is_not_overwritten(self):
        p=self.home/'.config/jayson-dev/env.sh'
        p.parent.mkdir(parents=True)
        p.write_text('# user-owned content\n')
        with self.assertRaises(RuntimeError): module.configure(self.home)
        self.assertEqual(p.read_text(),'# user-owned content\n')
        self.assertFalse((self.home/'.bashrc').exists())

    def test_generated_shell_is_valid_and_path_idempotent(self):
        module.configure(self.home)
        for file in ['.config/jayson-dev/env.sh','.config/jayson-dev/bash.sh','.local/bin/dev-run']:
            subprocess.run(['bash','-n',str(self.home/file)],check=True)
        # HOME is kept intact; source the temporary PATH file twice in a child shell.
        pathfile=str(self.home/'.config/jayson-dev/env.sh')
        result=subprocess.run(['bash','-c','. "$1"; first=$PATH; . "$1"; [[ $first == "$PATH" ]]',
                               'test',pathfile],capture_output=True)
        self.assertEqual(result.returncode,0)

    def test_agent_template_does_not_replace_existing(self):
        p=self.home/'.codex/AGENTS.md';p.parent.mkdir();p.write_text('Existing instructions\n')
        subprocess.run(['python3',str(ROOT/'scripts/configure.py'),'--home',str(self.home),
                        '--agents',str(ROOT/'config/AGENTS.md')],check=True,capture_output=True)
        self.assertEqual(p.read_text(),'Existing instructions\n')

    def test_dry_run_cannot_download_or_use_sudo(self):
        fake=self.home/'commands';fake.mkdir()
        for tool in ['curl','sudo','npm']:
            p=fake/tool;p.write_text('#!/bin/sh\nexit 99\n');p.chmod(0o755)
        env=dict(os.environ,PATH=str(fake)+':'+os.environ['PATH'])
        result=subprocess.run(['bash',str(ROOT/'bootstrap.sh'),'--dry-run'],
                              env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('System packages: 1',result.stdout)

    def test_missing_node_version_runs_install_before_configuration(self):
        fake=self.home/'commands';fake.mkdir()
        python=fake/'python3';python.write_text('#!/bin/sh\nexit 99\n');python.chmod(0o755)
        nvm=self.home/'nvm';nvm.mkdir()
        (nvm/'nvm.sh').write_text("""nvm() {
  case "$1" in
    version) echo N/A; return 3;;
    install) printf '%s' "$2" > "$NVM_DIR/installed";;
    alias) mkdir -p "$NVM_DIR/alias"; printf '%s' "$3" > "$NVM_DIR/alias/default";;
    *) return 0;;
  esac
}
""")
        env=dict(os.environ,PATH=str(fake)+':'+os.environ['PATH'],NVM_DIR=str(nvm))
        result=subprocess.run(['bash',str(ROOT/'bootstrap.sh'),'--user-only','--no-uv','--no-blesh','--no-codex'],
                              env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,99,result.stderr)  # Fake python stops before real home edits.
        self.assertEqual((nvm/'installed').read_text(),'24')

    def test_invalid_option_and_no_node(self):
        invalid=subprocess.run(['bash',str(ROOT/'bootstrap.sh'),'--unknown'],capture_output=True)
        self.assertEqual(invalid.returncode,2)
        result=subprocess.run(['bash',str(ROOT/'bootstrap.sh'),'--dry-run','--no-node'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        self.assertIn('Node 24: 0; Codex 0.161.0: 0',result.stdout)

if __name__ == '__main__': unittest.main()
