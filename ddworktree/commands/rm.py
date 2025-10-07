"""
Command for removing files in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_combined_gitignore_patterns, get_git_status


def remove_files(repo: DDWorktreeRepo, files: List[str], verbose: bool = False) -> int:
    """Remove tracked files across trees, respecting ignore rules."""
    current_dir = Path.cwd()

    try:
        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")

        # Get paired worktree
        paired_worktree = _get_paired_worktree(current_dir, repo, is_local)

        # Process each file
        removed_files = []
        skipped_files = []
        error_files = []

        for file_pattern in files:
            file_path = Path(file_pattern)

            if not file_path.exists():
                error_files.append(f"{file_pattern} (not found)")
                continue

            # Check if file should be ignored
            patterns = get_combined_gitignore_patterns(current_dir)
            if _is_ignored(file_path, patterns):
                skipped_files.append(f"{file_pattern} (ignored)")
                continue

            # Remove from current worktree
            if _remove_file(current_dir, file_path, verbose):
                removed_files.append(str(file_pattern))

                # Remove from paired worktree if it exists
                if paired_worktree and paired_worktree.exists():
                    paired_file_path = paired_worktree / file_path.relative_to(current_dir)
                    if paired_file_path.exists():
                        if _remove_file(paired_worktree, paired_file_path, verbose):
                            removed_files.append(f"{file_pattern} (paired)")
            else:
                error_files.append(f"{file_pattern} (failed)")

        # Report results
        if removed_files:
            print(f"Removed {len(removed_files)} files:")
            for file in removed_files:
                print(f"  {file}")

        if skipped_files:
            print(f"Skipped {len(skipped_files)} files:")
            for file in skipped_files:
                print(f"  {file}")

        if error_files:
            print(f"Errors with {len(error_files)} files:")
            for file in error_files:
                print(f"  {file}")
            return 1

        return 0

    except Exception as e:
        print(f"Error removing files: {e}")
        return 1


def _is_local_worktree(worktree_path: Path, repo: DDWorktreeRepo) -> bool:
    """Check if this is a local worktree."""
    local_suffix = repo.get_local_suffix()
    return local_suffix in worktree_path.name


def _get_paired_worktree(
    current_path: Path,
    repo: DDWorktreeRepo,
    is_local: bool
) -> Path:
    """Get the paired worktree path."""
    pairs = repo.get_pairs()
    current_name = current_path.name

    for pair_name, (main_path, local_path) in pairs.items():
        if is_local and current_path == Path(local_path):
            return Path(main_path)
        elif not is_local and current_path == Path(main_path):
            return Path(local_path)

    return None


def _is_ignored(file_path: Path, patterns: set) -> bool:
    """Check if a file should be ignored."""
    file_name = file_path.name
    relative_path = str(file_path)

    for pattern in patterns:
        if pattern.endswith('/'):
            # Directory pattern
            if file_path.parent.name == pattern.rstrip('/'):
                return True
        elif pattern.startswith('*.'):
            # Extension pattern
            if file_name.endswith(pattern[1:]):
                return True
        elif pattern.startswith('/'):
            # Absolute path pattern
            if relative_path.startswith(pattern[1:]):
                return True
        else:
            # Simple pattern
            if pattern in file_name or pattern in relative_path:
                return True

    return False


def _remove_file(worktree_path: Path, file_path: Path, verbose: bool = False) -> bool:
    """Remove a file from a worktree."""
    try:
        relative_path = file_path.relative_to(worktree_path)

        # Use git rm to properly remove from version control
        result = subprocess.run(
            ['git', 'rm', str(relative_path)],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            if verbose:
                print(f"Removed {relative_path} from {worktree_path.name}")
            return True
        else:
            # If git rm fails, try regular file removal
            try:
                file_path.unlink()
                if verbose:
                    print(f"Removed {relative_path} from {worktree_path.name} (not tracked)")
                return True
            except OSError:
                return False

    except Exception:
        return False


def main(args: List[str]) -> int:
    """Main entry point for rm command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree rm',
        description='Remove tracked files across trees'
    )
    parser.add_argument(
        'files',
        nargs='+',
        help='Files to remove'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed output'
    )

    parsed_args = parser.parse_args(args)

    try:
        repo = DDWorktreeRepo()
        return remove_files(repo, parsed_args.files, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())