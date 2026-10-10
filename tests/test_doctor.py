import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('doctor',ROOT/'scripts/doctor.py')
doctor=importlib.util.module_from_spec(spec);spec.loader.exec_module(doctor)

class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='doctor-test-');self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)

    def test_missing_optional_tools_do_not_fail_cpu_host(self):
        with patch.object(doctor.shutil,'which',return_value=None):
            report=doctor.collect([],self.home)
        self.assertTrue(report['ok'])
        self.assertEqual(report['hardware']['gpus'],[])
        self.assertGreater(report['hardware']['home_disk']['total_gib'],0)

    def test_missing_required_tools_fail(self):
        with patch.object(doctor.shutil,'which',return_value=None):
            report=doctor.collect(['uv','codex'],self.home)
        self.assertFalse(report['ok']);self.assertEqual(report['missing_required'],['uv','codex'])

    def test_gpu_inventory_and_failed_query(self):
        with patch.object(doctor.shutil,'which',return_value='/fake/nvidia-smi'),patch.object(doctor,'command',return_value=(0,'0, NVIDIA RTX 3070, 555.42, 8192\n')):
            report=doctor.inventory(self.home)
        self.assertEqual(report['gpus'][0]['vram_mib'],'8192')
        self.assertEqual(report['gpus'][0]['driver'],'555.42')
        with patch.object(doctor.shutil,'which',return_value='/fake/nvidia-smi'),patch.object(doctor,'command',return_value=(1,'driver unavailable')):
            report=doctor.inventory(self.home)
        self.assertEqual(report['gpus'],[]);self.assertIn('query failed',report['gpu_status'])

    def test_broken_managed_shell_configuration_fails(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('config',ROOT/'scripts/configure.py')
        config=importlib.util.module_from_spec(spec);spec.loader.exec_module(config)
        config.configure(self.home)
        (self.home/'.config/jayson-dev/env.sh').write_text('if then\n')
        with patch.object(doctor.shutil,'which',return_value=None):report=doctor.collect([],self.home)
        self.assertFalse(report['ok'])
        self.assertTrue(any(not item['ok'] for item in report['configuration']))

if __name__=='__main__':unittest.main()
