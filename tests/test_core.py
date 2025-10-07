"""
Tests for ddworktree core functionality.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import git
from git import Repo

from ddworktree.core import DDWorktreeRepo, DDWorktreeError


class TestDDWorktreeRepo(unittest.TestCase):
    """Test DDWorktreeRepo class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create a real Git repository for testing
        git.Repo.init(self.temp_path)
        self.mock_repo = Mock(spec=git.Repo)
        self.mock_repo.path = str(self.temp_path)

    def test_init_with_valid_repo(self):
        """Test initialization with valid repository."""
        repo = DDWorktreeRepo(str(self.temp_path))
        self.assertEqual(repo.repo_path, self.temp_path)
        self.assertIsNotNone(repo.repo)

    def test_init_with_invalid_repo(self):
        """Test initialization with invalid repository."""
        non_git_dir = self.temp_path / 'non_git'
        non_git_dir.mkdir()
        with self.assertRaises(DDWorktreeError):
            DDWorktreeRepo(str(non_git_dir))

    def test_config_file_path(self):
        """Test config file path property."""
        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            expected_path = self.temp_path / '.ddconfig'
            self.assertEqual(repo.config_file, expected_path)

    def test_load_config_no_file(self):
        """Test loading config when no file exists."""
        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            config = repo.load_config()
            self.assertEqual(config, {'pairs': {}, 'options': {}})

    def test_load_config_with_file(self):
        """Test loading config with existing file."""
        # Create a test config file
        config_content = """
[pairs]
dev = "dev, dev-local"
test = "test, test-local"

[options]
auto_sync = true
push_local = false
local_suffix = "-local"
"""
        config_file = self.temp_path / '.ddconfig'
        config_file.write_text(config_content)

        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            config = repo.load_config()

            expected_pairs = {
                'dev': 'dev, dev-local',
                'test': 'test, test-local'
            }
            expected_options = {
                'auto_sync': 'true',
                'push_local': 'false',
                'local_suffix': '-local'
            }

            self.assertEqual(config['pairs'], expected_pairs)
            self.assertEqual(config['options'], expected_options)

    def test_get_pairs(self):
        """Test getting worktree pairs."""
        config_content = """
[pairs]
dev = "dev, dev-local"
test = "test, test-local"
"""
        config_file = self.temp_path / '.ddconfig'
        config_file.write_text(config_content)

        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            pairs = repo.get_pairs()

            expected = {
                'dev': ('dev', 'dev-local'),
                'test': ('test', 'test-local')
            }

            self.assertEqual(pairs, expected)

    def test_add_pair(self):
        """Test adding a worktree pair."""
        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            repo.add_pair('feature1', 'feature1', 'feature1-local')

            config = repo.load_config()
            self.assertEqual(config['pairs']['feature1'], 'feature1, feature1-local')

    def test_remove_pair(self):
        """Test removing a worktree pair."""
        # Create config with a pair
        config_content = """
[pairs]
dev = "dev, dev-local"
test = "test, test-local"
"""
        config_file = self.temp_path / '.ddconfig'
        config_file.write_text(config_content)

        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            repo.remove_pair('dev')

            config = repo.load_config()
            self.assertNotIn('dev', config['pairs'])
            self.assertIn('test', config['pairs'])

    def test_get_option(self):
        """Test getting configuration options."""
        config_content = """
[options]
auto_sync = true
push_local = false
local_suffix = "-local"
"""
        config_file = self.temp_path / '.ddconfig'
        config_file.write_text(config_content)

        repo = DDWorktreeRepo(str(self.temp_path))

        self.assertEqual(repo.get_option('auto_sync'), 'true')
        self.assertEqual(repo.get_option('push_local'), 'false')
        self.assertEqual(repo.get_option('local_suffix'), '-local')
        self.assertIsNone(repo.get_option('nonexistent'))
        self.assertEqual(repo.get_option('nonexistent', 'default'), 'default')

    def test_set_option(self):
        """Test setting configuration options."""
        repo = DDWorktreeRepo(str(self.temp_path))
        repo.set_option('auto_sync', True)
        repo.set_option('local_suffix', '-custom')

        config = repo.load_config()
        self.assertEqual(config['options']['auto_sync'], 'true')
        self.assertEqual(config['options']['local_suffix'], '-custom')

    def test_get_local_suffix_default(self):
        """Test getting default local suffix."""
        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            self.assertEqual(repo.get_local_suffix(), '-local')

    def test_get_local_suffix_custom(self):
        """Test getting custom local suffix."""
        config_content = """
[options]
local_suffix = "-custom"
"""
        config_file = self.temp_path / '.ddconfig'
        config_file.write_text(config_content)

        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            self.assertEqual(repo.get_local_suffix(), '-custom')

    @patch('subprocess.run')
    def test_create_worktree_success(self, mock_run):
        """Test successful worktree creation."""
        mock_run.return_value.returncode = 0

        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            repo.create_worktree('/path/to/worktree', 'main')

            mock_run.assert_called_once_with(
                ['git', 'worktree', 'add', '/path/to/worktree', 'main'],
                cwd=self.temp_path,
                capture_output=True,
                text=True
            )

    @patch('subprocess.run')
    def test_create_worktree_failure(self, mock_run):
        """Test failed worktree creation."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = 'Error: worktree already exists'

        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))

            with self.assertRaises(DDWorktreeError) as context:
                repo.create_worktree('/path/to/worktree', 'main')

            self.assertIn('Failed to create worktree', str(context.exception))

    @patch('subprocess.run')
    def test_remove_worktree(self, mock_run):
        """Test worktree removal."""
        mock_run.return_value.returncode = 0

        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            repo.remove_worktree('/path/to/worktree', force=True)

            mock_run.assert_called_once_with(
                ['git', 'worktree', 'remove', '--force', '/path/to/worktree'],
                cwd=self.temp_path,
                capture_output=True,
                text=True
            )

    def test_create_local_gitignore(self):
        """Test creating .gitignore-local file."""
        worktree_dir = self.temp_path / 'worktree'
        worktree_dir.mkdir()

        with patch('git.Repo', return_value=self.mock_repo):
            repo = DDWorktreeRepo(str(self.temp_path))
            repo.create_local_gitignore(str(worktree_dir))

            gitignore_local = worktree_dir / '.gitignore-local'
            self.assertTrue(gitignore_local.exists())

            content = gitignore_local.read_text()
            self.assertIn('# Local files that should not be committed globally', content)
            self.assertIn('*.local', content)
            self.assertIn('.env', content)


class TestDDWorktreeError(unittest.TestCase):
    """Test DDWorktreeError exception."""

    def test_exception_creation(self):
        """Test creating DDWorktreeError."""
        error = DDWorktreeError("Test error message")
        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)


if __name__ == '__main__':
    unittest.main()