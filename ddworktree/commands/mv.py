"""
Command for moving/renaming files in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_combined_gitignore_patterns


def move_files(
    repo: DDWorktreeRepo,
    source: str,
    destination: str,
    verbose: bool = False
) -> int:
    """Move/rename files across paired trees."""
    current_dir = Path.cwd()

    try:
        source_path = Path(source)
        destination_path = Path(destination)

        # Validate source exists
        if not source_path.exists():
            print(f"Error: Source path does not exist: {source}")
            return 1

        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")

        # Get paired worktree
        paired_worktree = _get_paired_worktree(current_dir, repo, is_local)

        # Move in current worktree
        move_result = _move_in_worktree(
            current_dir, source_path, destination_path, verbose
        )

        if move_result != 0:
            return move_result

        # Move in paired worktree if it exists
        if paired_worktree and paired_worktree.exists():
            if verbose:
                print(f"Moving in paired worktree: {paired_worktree}")

            # Calculate corresponding paths in paired worktree
            relative_source = source_path.relative_to(current_dir)
            relative_dest = destination_path.relative_to(current_dir)

            paired_source = paired_worktree / relative_source
            paired_dest = paired_worktree / relative_dest

            # Only move if source exists in paired worktree
            if paired_source.exists():
                paired_result = _move_in_worktree(
                    paired_worktree, paired_source, paired_dest, verbose
                )

                if paired_result != 0:
                    return paired_result

        print(f"Successfully moved {source} to {destination}")
        return 0

    except Exception as e:
        print(f"Error moving files: {e}")
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


def _move_in_worktree(
    worktree_path: Path,
    source_path: Path,
    destination_path: Path,
    verbose: bool = False
) -> int:
    """Move a file within a specific worktree."""
    try:
        relative_source = source_path.relative_to(worktree_path)
        relative_dest = destination_path.relative_to(worktree_path)

        # Create destination directory if it doesn't exist
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        # Use git mv for tracked files
        result = subprocess.run(
            ['git', 'mv', str(relative_source), str(relative_dest)],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            if verbose:
                print(f"Moved {relative_source} to {relative_dest} in {worktree_path.name}")
            return 0
        else:
            # If git mv fails (file not tracked), try regular move
            try:
                source_path.rename(destination_path)
                if verbose:
                    print(f"Moved {relative_source} to {relative_dest} in {worktree_path.name} (untracked)")
                return 0
            except OSError as e:
                print(f"Error moving {source_path} to {destination_path}: {e}")
                return 1

    except Exception as e:
        print(f"Error in move operation: {e}")
        return 1


def main(args: List[str]) -> int:
    """Main entry point for mv command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree mv',
        description='Move/rename files across paired trees'
    )
    parser.add_argument(
        'source',
        help='Source file or directory'
    )
    parser.add_argument(
        'destination',
        help='Destination file or directory'
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
        return move_files(repo, parsed_args.source, parsed_args.destination, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())