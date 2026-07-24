import importlib.util
from pathlib import Path
import unittest
import numpy as np

MODULE = Path(__file__).resolve().parents[1] / 'experiments' / 'tid_root' / 'run_ligo_analysis.py'
spec = importlib.util.spec_from_file_location('run_ligo_analysis', MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FeatureContractTests(unittest.TestCase):
    def test_feature_row_is_finite_and_target_free(self):
        rng = np.random.default_rng(7)
        x = rng.normal(size=4096)
        row = mod.compute_features(x, sample_rate_hz=1024)
        for key in ['dfa_h','mfdfa_delta_alpha','psd_slope','sample_entropy']:
            self.assertIn(key, row)
            self.assertTrue(np.isfinite(row[key]), key)
        self.assertNotIn('tid_class', row)
        self.assertNotIn('target_gamma', row)

    def test_window_slice_is_exact(self):
        x = np.arange(3200)
        y = mod.slice_window(x, sample_rate_hz=100, window=(2.0,6.0))
        self.assertEqual(len(y), 400)
        self.assertEqual(y[0], 200)
        self.assertEqual(y[-1], 599)

if __name__ == '__main__':
    unittest.main()
