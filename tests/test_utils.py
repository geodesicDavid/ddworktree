"""
Tests for ddworktree utilities.
"""

import tempfile
import unittest
from pathlib import Path

from ddworktree.utils.gitignore import (
    parse_gitignore,
    get_combined_gitignore_patterns,
    is_ignored_by_pattern,
    get_tracked_files,
    get_git_status
)


class TestGitIgnoreUtils(unittest.TestCase):
    """Test gitignore utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def test_parse_gitignore_no_file(self):
        """Test parsing non-existent gitignore file."""
        non_existent = self.temp_path / '.gitignore'
        patterns = parse_gitignore(non_existent)
        self.assertEqual(patterns, set())

    def test_parse_gitignore_empty_file(self):
        """Test parsing empty gitignore file."""
        gitignore_file = self.temp_path / '.gitignore'
        gitignore_file.write_text('')

        patterns = parse_gitignore(gitignore_file)
        self.assertEqual(patterns, set())

    def test_parse_gitignore_with_content(self):
        """Test parsing gitignore file with content."""
        content = """
# This is a comment
*.pyc
__pycache__/
node_modules/
.env.local
config/secrets.py

# Empty line below

*.log
"""
        gitignore_file = self.temp_path / '.gitignore'
        gitignore_file.write_text(content)

        patterns = parse_gitignore(gitignore_file)
        expected = {'*.pyc', '__pycache__/', 'node_modules/', '.env.local', 'config/secrets.py', '*.log'}
        self.assertEqual(patterns, expected)

    def test_get_combined_gitignore_patterns(self):
        """Test combining .gitignore and .gitignore-local patterns."""
        # Create .gitignore
        gitignore_file = self.temp_path / '.gitignore'
        gitignore_file.write_text('*.pyc\n__pycache__/')

        # Create .gitignore-local
        gitignore_local_file = self.temp_path / '.gitignore-local'
        gitignore_local_file.write_text('*.local\n.env')

        patterns = get_combined_gitignore_patterns(self.temp_path)
        expected = {'*.pyc', '__pycache__/', '*.local', '.env'}
        self.assertEqual(patterns, expected)

    def test_is_ignored_by_pattern_simple(self):
        """Test simple ignore pattern matching."""
        patterns = {'*.pyc', '__pycache__'}

        self.assertTrue(is_ignored_by_pattern(Path('test.pyc'), patterns))
        self.assertTrue(is_ignored_by_pattern(Path('module/__pycache__'), patterns))
        self.assertFalse(is_ignored_by_pattern(Path('test.py'), patterns))

    def test_is_ignored_by_pattern_directory(self):
        """Test directory ignore pattern matching."""
        patterns = {'node_modules/', 'build/'}

        self.assertTrue(is_ignored_by_pattern(Path('node_modules/file.js'), patterns))
        self.assertTrue(is_ignored_by_pattern(Path('build/output.txt'), patterns))
        self.assertFalse(is_ignored_by_pattern(Path('src/main.js'), patterns))

    def test_is_ignored_by_pattern_absolute(self):
        """Test absolute path ignore pattern matching."""
        patterns = {'/config/secrets.py', '/.env'}

        self.assertTrue(is_ignored_by_pattern(Path('/config/secrets.py'), patterns))
        self.assertTrue(is_ignored_by_pattern(Path('/.env'), patterns))
        # Test that different paths don't match
        self.assertFalse(is_ignored_by_pattern(Path('/other/secrets.py'), patterns))

    def test_get_tracked_files_with_ignored(self):
        """Test getting files including ignored ones."""
        # Create test files
        (self.temp_path / 'main.py').write_text('print("hello")')
        (self.temp_path / 'test.pyc').write_text('compiled')
        (self.temp_path / 'config' / 'secrets.py').mkdir(parents=True)
        (self.temp_path / 'config' / 'secrets.py' / 'key').write_text('secret')

        files = get_tracked_files(self.temp_path, include_ignored=True)
        file_names = [f.name for f in files]

        self.assertIn('main.py', file_names)
        self.assertIn('test.pyc', file_names)
        self.assertIn('key', file_names)

    def test_get_tracked_files_without_ignored(self):
        """Test getting files excluding ignored ones."""
        # Create test files
        (self.temp_path / 'main.py').write_text('print("hello")')
        (self.temp_path / 'test.pyc').write_text('compiled')

        # Create .gitignore
        gitignore_file = self.temp_path / '.gitignore'
        gitignore_file.write_text('*.pyc')

        files = get_tracked_files(self.temp_path, include_ignored=False)
        file_names = [f.name for f in files]

        self.assertIn('main.py', file_names)
        self.assertNotIn('test.pyc', file_names)


class TestDiffUtils(unittest.TestCase):
    """Test diff utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def test_worktree_diff_creation(self):
        """Test WorktreeDiff dataclass creation."""
        from ddworktree.utils.diff import WorktreeDiff

        diff = WorktreeDiff(
            added_files=['file1.txt', 'file2.txt'],
            deleted_files=['old.txt'],
            modified_files=['config.py'],
            commit_drift=True,
            main_commit='abc123',
            local_commit='def456'
        )

        self.assertEqual(diff.added_files, ['file1.txt', 'file2.txt'])
        self.assertEqual(diff.deleted_files, ['old.txt'])
        self.assertEqual(diff.modified_files, ['config.py'])
        self.assertTrue(diff.commit_drift)
        self.assertEqual(diff.main_commit, 'abc123')
        self.assertEqual(diff.local_commit, 'def456')

    def test_generate_diff_report_no_drift(self):
        """Test generating diff report with no drift."""
        from ddworktree.utils.diff import WorktreeDiff, generate_diff_report

        diff = WorktreeDiff(
            added_files=[],
            deleted_files=[],
            modified_files=[],
            commit_drift=False,
            main_commit='abc123',
            local_commit='abc123'
        )

        report = generate_diff_report(diff)
        self.assertIn('✅ No drift detected', report)

    def test_generate_diff_report_with_drift(self):
        """Test generating diff report with drift."""
        from ddworktree.utils.diff import WorktreeDiff, generate_diff_report

        diff = WorktreeDiff(
            added_files=['new.txt', 'config/local.json'],
            deleted_files=['old.txt'],
            modified_files=['main.py'],
            commit_drift=True,
            main_commit='abc123',
            local_commit='def456'
        )

        report = generate_diff_report(diff)
        self.assertIn('🔄 Commit drift detected', report)
        self.assertIn('➕ Files added in local:', report)
        self.assertIn('➖ Files deleted in local:', report)
        self.assertIn('✏️  Files modified:', report)
        self.assertIn('new.txt', report)
        self.assertIn('old.txt', report)
        self.assertIn('main.py', report)


if __name__ == '__main__':
    unittest.main()