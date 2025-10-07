"""
Utilities for parsing and comparing .gitignore files.
"""

import os
from pathlib import Path
from typing import Set, List, Optional


def parse_gitignore(gitignore_path: Path) -> Set[str]:
    """Parse a .gitignore file and return set of patterns."""
    patterns = set()

    if not gitignore_path.exists():
        return patterns

    with open(gitignore_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            patterns.add(line)

    return patterns


def get_combined_gitignore_patterns(directory: Path) -> Set[str]:
    """Get combined patterns from .gitignore and .gitignore-local."""
    patterns = set()

    # Standard .gitignore
    gitignore_path = directory / '.gitignore'
    patterns.update(parse_gitignore(gitignore_path))

    # Local .gitignore-local
    gitignore_local_path = directory / '.gitignore-local'
    patterns.update(parse_gitignore(gitignore_local_path))

    return patterns


def is_ignored_by_pattern(file_path: Path, patterns: Set[str]) -> bool:
    """Check if a file matches any ignore pattern."""
    relative_path = file_path.name

    for pattern in patterns:
        if pattern.endswith('/'):
            # Directory pattern
            if file_path.parent.name == pattern.rstrip('/'):
                return True
        elif pattern.startswith('*.'):
            # Extension pattern
            if relative_path.endswith(pattern[1:]):
                return True
        elif pattern.startswith('/'):
            # Absolute path pattern
            if str(file_path).endswith(pattern[1:]):
                return True
        else:
            # Simple pattern
            if pattern in relative_path:
                return True

    return False


def get_tracked_files(directory: Path, include_ignored: bool = False) -> List[Path]:
    """Get list of tracked files, optionally including ignored files."""
    tracked_files = []

    if include_ignored:
        # Include all files
        for root, dirs, files in os.walk(directory):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')

            for file in files:
                file_path = Path(root) / file
                tracked_files.append(file_path)
    else:
        # Only include non-ignored files
        patterns = get_combined_gitignore_patterns(directory)

        for root, dirs, files in os.walk(directory):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')

            for file in files:
                file_path = Path(root) / file
                if not is_ignored_by_pattern(file_path, patterns):
                    tracked_files.append(file_path)

    return tracked_files


def get_git_status(directory: Path) -> dict:
    """Get git status for a directory."""
    import subprocess

    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=directory,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {'error': result.stderr}

    status = {
        'modified': [],
        'added': [],
        'deleted': [],
        'untracked': [],
        'renamed': [],
        'copied': []
    }

    for line in result.stdout.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Parse porcelain output
        index_status = line[0] if len(line) > 0 else ' '
        working_status = line[1] if len(line) > 1 else ' '
        file_path = line[3:]

        if index_status == 'M' or working_status == 'M':
            status['modified'].append(file_path)
        elif index_status == 'A':
            status['added'].append(file_path)
        elif index_status == 'D':
            status['deleted'].append(file_path)
        elif index_status == 'R':
            status['renamed'].append(file_path)
        elif index_status == 'C':
            status['copied'].append(file_path)
        elif index_status == '?' and working_status == '?':
            status['untracked'].append(file_path)

    return status