import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)
        self.plans = self.cwd / '.plans'
        self.plans.mkdir()
        self.path = self.plans / 'alpha-beta-gamma.md'
        self.old = '# Example\n' + 'old content ' * 10
        self.new = '# Example\n' + 'new content ' * 10

    def run_hook(self, name, content=None, path=None, deny_symlink=False):
        event = {'tool_name': 'Write', 'tool_input': {
            'file_path': str(path if path is not None else self.path),
            'content': self.old if content is None else content}}
        script = str(ROOT / name)
        if deny_symlink:
            code = "import runpy,sys; from unittest.mock import patch; " + \
                   "p=patch('os.symlink',side_effect=OSError('simulated unavailable')); " + \
                   "p.start(); runpy.run_path(sys.argv[1],run_name='__main__')"
            command = [sys.executable, '-c', code, script]
        else:
            command = [sys.executable, script]
        result = subprocess.run(command, input=json.dumps(event), text=True,
                                encoding='utf-8', cwd=self.cwd, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_symlink_repeated_write(self):
        self.path.write_text(self.old, encoding='utf-8')
        self.run_hook('plan-rename.py')
        self.assertTrue(self.path.is_symlink())
        target = self.path.resolve()
        self.path.write_text(self.new, encoding='utf-8')
        self.run_hook('plan-rename.py', self.new)
        self.assertEqual(self.path.resolve(), target)
        self.assertEqual(target.read_text(encoding='utf-8'), self.new)
        self.assertEqual(len(list(self.plans.glob('*-v*.md'))), 1)

    def test_non_plan_and_missing_heading_unchanged(self):
        outside = self.cwd / 'alpha-beta-gamma.md'
        outside.write_text(self.old, encoding='utf-8')
        self.run_hook('plan-rename.py', path=outside)
        self.assertFalse(outside.is_symlink())
        self.path.write_text('No heading', encoding='utf-8')
        self.run_hook('plan-rename.py', 'No heading')
        self.assertFalse(self.path.is_symlink())
        self.assertEqual(len(list(self.plans.glob('*-v*.md'))), 0)

    def test_hardlink_fallback_is_idempotent(self):
        self.path.write_text(self.old, encoding='utf-8')
        self.run_hook('plan-rename.py', deny_symlink=True)
        target, = self.plans.glob('*-v*.md')
        self.assertFalse(self.path.is_symlink())
        self.assertTrue(self.path.samefile(target))
        self.path.write_text(self.new, encoding='utf-8')
        self.run_hook('plan-rename.py', self.new, deny_symlink=True)
        self.assertEqual(list(self.plans.glob('*-v*.md')), [target])
        self.assertTrue(self.path.samefile(target))
        self.assertEqual(target.read_text(encoding='utf-8'), self.new)

    def test_unrelated_hardlink_does_not_suppress_rename(self):
        self.path.write_text(self.old, encoding='utf-8')
        os.link(self.path, self.plans / 'unrelated.md')
        self.run_hook('plan-rename.py', deny_symlink=True)
        self.assertEqual(len(list(self.plans.glob('*-v*.md'))), 1)

    def test_replaced_hardlink_is_processed_as_new_file(self):
        self.path.write_text(self.old, encoding='utf-8')
        self.run_hook('plan-rename.py', deny_symlink=True)
        original, = self.plans.glob('*-v*.md')
        self.path.unlink()
        self.path.write_text(self.new, encoding='utf-8')
        self.run_hook('plan-rename.py', self.new, deny_symlink=True)
        self.assertEqual(len(list(self.plans.glob('*-v*.md'))), 2)
        self.assertEqual(original.read_text(encoding='utf-8'), self.old)


if __name__ == '__main__':
    unittest.main()
