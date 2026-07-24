from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import unittest

from observatory_site.build import build_site

FIX = Path(__file__).parent / "fixtures"

class BuildTests(unittest.TestCase):
    def _repo(self, root: Path):
        for name in ['data','reports','experiments']:
            src=FIX/name
            if src.exists(): shutil.copytree(src, root/name)
        (root/'docs').mkdir(exist_ok=True)
        (root/'docs'/'methodology.md').write_text('# Method\n\nObservation is not causation.\n',encoding='utf-8')

    def test_build_writes_expected_routes_without_touching_sources(self):
        with TemporaryDirectory() as td:
            root=Path(td)/'repo'; out=Path(td)/'public'; root.mkdir(); self._repo(root)
            before=(root/'data'/'latest'/'public-status.json').read_bytes()
            build_site(root,out,'/theseus-public-observatory/',datetime(2026,7,24,13,30,tzinfo=timezone.utc))
            for rel in ['index.html','observations/index.html','experiments/index.html','experiments/gw150914/index.html','method/index.html','about/index.html']:
                self.assertTrue((out/rel).is_file(), rel)
            self.assertEqual(before,(root/'data'/'latest'/'public-status.json').read_bytes())
            self.assertIn('Observation is not causation',(out/'method'/'index.html').read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()

class WorkflowTests(unittest.TestCase):
    def test_pages_workflow_has_build_deploy_split_and_main_only_deploy(self):
        repo = Path(__file__).resolve().parents[2]
        text = (repo/'.github'/'workflows'/'pages.yml').read_text(encoding='utf-8')
        self.assertIn('build:', text)
        self.assertIn('deploy:', text)
        self.assertIn('needs: build', text)
        self.assertIn("refs/heads/main", text)
        self.assertIn('actions/upload-pages-artifact', text)
        self.assertIn('actions/deploy-pages', text)
