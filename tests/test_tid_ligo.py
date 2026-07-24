import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'experiments' / 'tid_root' / 'ligo_pilot.py'
spec = importlib.util.spec_from_file_location('ligo_pilot', MODULE)
ligo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ligo)

class WindowContractTests(unittest.TestCase):
    def test_fixed_windows_are_predeclared_and_nonoverlapping(self):
        windows = ligo.fixed_windows(event_center_s=16.4, duration_s=32.0, width_s=4.0)
        self.assertEqual(windows['event'], (14.4, 18.4))
        self.assertEqual(windows['controls'], [(2.0, 6.0), (7.0, 11.0), (21.0, 25.0), (26.0, 30.0)])
        e0, e1 = windows['event']
        for c0, c1 in windows['controls']:
            self.assertTrue(c1 <= e0 or c0 >= e1)

    def test_manifest_does_not_encode_historical_tid_target_values(self):
        manifest = ligo.build_manifest(
            source_sha256={'H1':'a'*64,'L1':'b'*64},
            sample_rate_hz=16384,
            samples=524288,
        )
        text = str(manifest)
        self.assertNotIn('0.382', text)
        self.assertNotIn('0.618', text)
        self.assertEqual(manifest['epistemic_status'], 'MEASUREMENT_ONLY')
        self.assertEqual(manifest['pre_registered_windows']['event'], [14.4, 18.4])

if __name__ == '__main__':
    unittest.main()
