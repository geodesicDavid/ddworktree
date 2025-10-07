"""
Command for pulling updates in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_git_status


def pull_updates(
    repo: DDWorktreeRepo,
    remote: Optional[str] = None,
    branch: Optional[str] = None,
    verbose: bool = False
) -> int:
    """Pull updates and sync both trees."""
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

        # Check for uncommitted changes before pull
        current_status = get_git_status(current_dir)
        if any(current_status.values()):
            print("Warning: You have uncommitted changes:")
            _print_status_summary(current_status)
            response = input("Continue with pull? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Pull cancelled")
                return 0

        # Pull in current worktree
        pull_result = _pull_in_worktree(
            current_dir, remote, branch, verbose
        )

        if pull_result != 0:
            return pull_result

        # Pull in paired worktree if it exists
        if paired_worktree and paired_worktree.exists():
            if verbose:
                print(f"Pulling in paired worktree: {paired_worktree}")

            # Check paired worktree status
            paired_status = get_git_status(paired_worktree)
            if any(paired_status.values()):
                print("Warning: Paired worktree has uncommitted changes:")
                _print_status_summary(paired_status)
                response = input("Continue with pull in paired worktree? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Pull in paired worktree cancelled")
                    return 0

            paired_result = _pull_in_worktree(
                paired_worktree, remote, branch, verbose
            )

            if paired_result != 0:
                return paired_result

        print("Successfully pulled updates")
        return 0

    except Exception as e:
        print(f"Error pulling updates: {e}")
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


def _print_status_summary(status: dict) -> None:
    """Print a summary of git status."""
    if status['modified']:
        print(f"  Modified: {len(status['modified'])} files")
    if status['added']:
        print(f"  Added: {len(status['added'])} files")
    if status['deleted']:
        print(f"  Deleted: {len(status['deleted'])} files")
    if status['untracked']:
        print(f"  Untracked: {len(status['untracked'])} files")


def _pull_in_worktree(
    worktree_path: Path,
    remote: Optional[str],
    branch: Optional[str],
    verbose: bool = False
) -> int:
    """Pull updates in a specific worktree."""
    args = ['git', 'pull']

    if remote:
        args.append(remote)
    if branch:
        args.append(branch)

    result = subprocess.run(
        args,
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error pulling in {worktree_path}: {result.stderr}")
        return 1

    if verbose:
        print(f"Successfully pulled updates in {worktree_path}")
        if result.stdout:
            print("Pull output:")
            print(result.stdout)

    return 0


def main(args: List[str]) -> int:
    """Main entry point for pull command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree pull',
        description='Pull updates and sync both trees'
    )
    parser.add_argument(
        'remote',
        nargs='?',
        help='Remote to pull from'
    )
    parser.add_argument(
        'branch',
        nargs='?',
        help='Branch to pull'
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
        return pull_updates(repo, parsed_args.remote, parsed_args.branch, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())