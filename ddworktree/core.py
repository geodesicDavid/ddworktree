"""
Core ddworktree functionality - Git repository wrapper and worktree management.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import git
from git import Repo


class DDWorktreeError(Exception):
    """Base exception for ddworktree operations."""
    pass


class DDWorktreeRepo:
    """Wrapper around Git repository for ddworktree operations."""

    def __init__(self, repo_path: Optional[str] = None):
        """Initialize with repository path (defaults to current directory)."""
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        try:
            self.repo = Repo(self.repo_path)
        except git.exc.InvalidGitRepositoryError:
            raise DDWorktreeError(f"Not a Git repository: {self.repo_path}")

    @property
    def config_file(self) -> Path:
        """Path to .ddconfig file."""
        return self.repo_path / '.ddconfig'

    def load_config(self) -> Dict[str, Any]:
        """Load .ddconfig file."""
        if not self.config_file.exists():
            return {'pairs': {}, 'options': {}}

        # Try TOML first, then YAML
        try:
            import tomllib
            with open(self.config_file, 'rb') as f:
                config = tomllib.load(f)
                # Convert boolean values back to strings for consistency
                if 'options' in config:
                    for key, value in config['options'].items():
                        if isinstance(value, bool):
                            config['options'][key] = str(value).lower()
                return config
        except ImportError:
            try:
                import tomli
                with open(self.config_file, 'rb') as f:
                    config = tomli.load(f)
                    # Convert boolean values back to strings for consistency
                    if 'options' in config:
                        for key, value in config['options'].items():
                            if isinstance(value, bool):
                                config['options'][key] = str(value).lower()
                    return config
            except ImportError:
                # Fallback to basic parsing
                return self._parse_basic_config()

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to .ddconfig file."""
        try:
            import tomllib
            # Write basic TOML format
            with open(self.config_file, 'w') as f:
                f.write('# ddworktree configuration\n\n')

                if 'pairs' in config:
                    f.write('[pairs]\n')
                    for key, value in config['pairs'].items():
                        f.write(f'{key} = "{value}"\n')
                    f.write('\n')

                if 'options' in config:
                    f.write('[options]\n')
                    for key, value in config['options'].items():
                        if isinstance(value, bool):
                            f.write(f'{key} = {str(value).lower()}\n')
                        elif isinstance(value, str):
                            f.write(f'{key} = "{value}"\n')
                        else:
                            f.write(f'{key} = {value}\n')
        except ImportError:
            # Fallback to basic format
            self._save_basic_config(config)

    def _parse_basic_config(self) -> Dict[str, Any]:
        """Basic config file parser for when TOML is not available."""
        config = {'pairs': {}, 'options': {}}
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                current_section = None
                for line in f:
                    line = line.strip()
                    if line.startswith('[pairs]'):
                        current_section = 'pairs'
                    elif line.startswith('[options]'):
                        current_section = 'options'
                    elif '=' in line and current_section:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        # Keep boolean values as strings for consistency
                        config[current_section][key] = value
        return config

    def _save_basic_config(self, config: Dict[str, Any]) -> None:
        """Save config in basic format when TOML is not available."""
        with open(self.config_file, 'w') as f:
            f.write('# ddworktree configuration\n\n')

            if 'pairs' in config and config['pairs']:
                f.write('[pairs]\n')
                for key, value in config['pairs'].items():
                    f.write(f'{key} = "{value}"\n')
                f.write('\n')

            if 'options' in config and config['options']:
                f.write('[options]\n')
                for key, value in config['options'].items():
                    if isinstance(value, bool):
                        f.write(f'{key} = {str(value).lower()}\n')
                    elif isinstance(value, str):
                        f.write(f'{key} = "{value}"\n')
                    else:
                        f.write(f'{key} = {value}\n')

    def get_pairs(self) -> Dict[str, Tuple[str, str]]:
        """Get all configured worktree pairs."""
        config = self.load_config()
        pairs = {}
        for name, pair_str in config.get('pairs', {}).items():
            main, local = pair_str.split(',', 1)
            pairs[name] = (main.strip(), local.strip())
        return pairs

    def add_pair(self, name: str, main_path: str, local_path: str) -> None:
        """Add a new worktree pair configuration."""
        config = self.load_config()
        if 'pairs' not in config:
            config['pairs'] = {}
        config['pairs'][name] = f"{main_path}, {local_path}"
        self.save_config(config)

    def remove_pair(self, name: str) -> None:
        """Remove a worktree pair configuration."""
        config = self.load_config()
        if 'pairs' in config and name in config['pairs']:
            del config['pairs'][name]
            self.save_config(config)

    def get_option(self, key: str, default: Any = None) -> Any:
        """Get a configuration option value."""
        config = self.load_config()
        return config.get('options', {}).get(key, default)

    def set_option(self, key: str, value: Any) -> None:
        """Set a configuration option value."""
        config = self.load_config()
        if 'options' not in config:
            config['options'] = {}
        config['options'][key] = value
        self.save_config(config)

    def get_worktrees(self) -> List[dict]:
        """Get all worktrees for this repository."""
        try:
            return list(self.repo.worktrees)
        except AttributeError:
            # Handle different GitPython versions
            result = subprocess.run(
                ['git', 'worktree', 'list', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return []

            worktrees = []
            current_worktree = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('worktree '):
                    if current_worktree:
                        worktrees.append(current_worktree)
                    current_worktree = {'path': line[9:]}
                elif line.startswith('HEAD '):
                    current_worktree['head'] = line[5:]
                elif line.startswith('branch '):
                    current_worktree['branch'] = line[7:]

            if current_worktree:
                worktrees.append(current_worktree)

            return worktrees

    def is_valid_worktree(self, path: str) -> bool:
        """Check if a path is a valid worktree."""
        worktree_path = Path(path).resolve()
        try:
            # Check if path exists and has .git file pointing to main repo
            git_file = worktree_path / '.git'
            if not git_file.exists():
                return False

            with open(git_file, 'r') as f:
                content = f.read().strip()
                return 'gitdir:' in content and self.repo_path.name in content
        except (OSError, IOError):
            return False

    def create_worktree(self, path: str, commitish: Optional[str] = None) -> None:
        """Create a new worktree."""
        args = ['git', 'worktree', 'add', path]
        if commitish:
            args.append(commitish)

        result = subprocess.run(args, cwd=self.repo_path, capture_output=True, text=True)
        if result.returncode != 0:
            raise DDWorktreeError(f"Failed to create worktree: {result.stderr}")

    def remove_worktree(self, path: str, force: bool = False) -> None:
        """Remove a worktree."""
        args = ['git', 'worktree', 'remove']
        if force:
            args.append('--force')
        args.append(path)

        result = subprocess.run(args, cwd=self.repo_path, capture_output=True, text=True)
        if result.returncode != 0:
            raise DDWorktreeError(f"Failed to remove worktree: {result.stderr}")

    def get_local_suffix(self) -> str:
        """Get the local suffix from configuration."""
        return self.get_option('local_suffix', '-local')

    def create_local_gitignore(self, worktree_path: str) -> None:
        """Create .gitignore-local file in a worktree."""
        local_ignore_path = Path(worktree_path) / '.gitignore-local'
        if not local_ignore_path.exists():
            # Create basic .gitignore-local with common local files
            basic_ignores = [
                "# Local files that should not be committed globally",
                "*.local",
                "*.env.local",
                "*.secrets",
                "config/local/",
                "logs/",
                "tmp/",
                ".env",
                ".env.local",
                ".env.development.local",
                ".env.test.local",
                ".env.production.local"
            ]
            with open(local_ignore_path, 'w') as f:
                f.write('\n'.join(basic_ignores) + '\n')