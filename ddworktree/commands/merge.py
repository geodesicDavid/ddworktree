"""
Command for merging branches in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_git_status


def merge_branch(
    repo: DDWorktreeRepo,
    branch: str,
    verbose: bool = False
) -> int:
    """Merge another branch into both trees."""
    current_dir = Path.cwd()

    try:
        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")
            print(f"Merging branch: {branch}")

        # Get paired worktree
        paired_worktree = _get_paired_worktree(current_dir, repo, is_local)

        # Check for uncommitted changes before merge
        current_status = get_git_status(current_dir)
        if any(current_status.values()):
            print("Warning: You have uncommitted changes in current worktree:")
            _print_status_summary(current_status)
            response = input("Continue with merge? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Merge cancelled")
                return 0

        # Merge in current worktree
        merge_result = _merge_in_worktree(
            current_dir, branch, verbose
        )

        if merge_result != 0:
            return merge_result

        # Merge in paired worktree if it exists
        if paired_worktree and paired_worktree.exists():
            if verbose:
                print(f"Merging in paired worktree: {paired_worktree}")

            # Check paired worktree status
            paired_status = get_git_status(paired_worktree)
            if any(paired_status.values()):
                print("Warning: Paired worktree has uncommitted changes:")
                _print_status_summary(paired_status)
                response = input("Continue with merge in paired worktree? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Merge in paired worktree cancelled")
                    return 0

            paired_result = _merge_in_worktree(
                paired_worktree, branch, verbose
            )

            if paired_result != 0:
                return paired_result

        print(f"Successfully merged branch '{branch}'")
        return 0

    except Exception as e:
        print(f"Error merging branch: {e}")
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


def _merge_in_worktree(
    worktree_path: Path,
    branch: str,
    verbose: bool = False
) -> int:
    """Merge a branch in a specific worktree."""
    # First, check if the branch exists
    branch_check = subprocess.run(
        ['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}'],
        cwd=worktree_path,
        capture_output=True
    )

    if branch_check.returncode != 0:
        # Check if it's a remote branch
        remote_check = subprocess.run(
            ['git', 'show-ref', '--verify', '--quiet', f'refs/remotes/origin/{branch}'],
            cwd=worktree_path,
            capture_output=True
        )

        if remote_check.returncode != 0:
            print(f"Error: Branch '{branch}' not found in {worktree_path}")
            return 1

        if verbose:
            print(f"Using remote branch 'origin/{branch}'")

    # Perform the merge
    args = ['git', 'merge', branch]
    result = subprocess.run(
        args,
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error merging branch '{branch}' in {worktree_path}: {result.stderr}")

        # Check if it's a merge conflict
        if "CONFLICT" in result.stderr or "Merge conflict" in result.stderr:
            print("Merge conflict detected!")
            print("Please resolve conflicts manually and then commit.")
            print(f"Work in: {worktree_path}")
            return 1

        return 1

    if verbose:
        print(f"Successfully merged branch '{branch}' in {worktree_path}")
        if result.stdout:
            print("Merge output:")
            print(result.stdout)

    return 0


def main(args: List[str]) -> int:
    """Main entry point for merge command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree merge',
        description='Merge branch into both trees'
    )
    parser.add_argument(
        'branch',
        help='Branch to merge'
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
        return merge_branch(repo, parsed_args.branch, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())