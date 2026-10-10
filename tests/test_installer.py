import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build',ROOT/'scripts/build_installer.py')
build=importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

class InstallerTests(unittest.TestCase):
    def test_generated_file_matches_source(self):
        self.assertEqual((ROOT/'install.sh').read_text(),build.build())

    def test_stdin_execution_forwards_options_and_cleans_up(self):
        with tempfile.TemporaryDirectory(prefix='installer-tests-') as directory:
            env=dict(os.environ,TMPDIR=directory)
            result=subprocess.run(['bash','-s','--','--dry-run','--no-node'],
                                  input=(ROOT/'install.sh').read_text(),capture_output=True,text=True,env=env)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('System packages: 1',result.stdout)
            self.assertIn('Node 24: 0; Codex 0.161.0: 0',result.stdout)
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_user_only_disables_system_packages(self):
        result=subprocess.run(['bash',str(ROOT/'install.sh'),'--dry-run','--user-only'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('System packages: 0',result.stdout)

    def test_failure_propagates_and_cleans_up(self):
        with tempfile.TemporaryDirectory(prefix='installer-tests-') as directory:
            result=subprocess.run(['bash',str(ROOT/'install.sh'),'--unknown'],
                                  env=dict(os.environ,TMPDIR=directory),capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(list(Path(directory).iterdir()),[])

if __name__=='__main__':unittest.main()
