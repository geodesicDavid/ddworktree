"""
Command for rebasing worktrees in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_git_status


def rebase_worktrees(
    repo: DDWorktreeRepo,
    branch: str,
    verbose: bool = False
) -> int:
    """Rebase both paired trees on a branch."""
    current_dir = Path.cwd()

    try:
        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")
            print(f"Rebasing onto branch: {branch}")

        # Get paired worktree
        paired_worktree = _get_paired_worktree(current_dir, repo, is_local)

        # Check for uncommitted changes before rebase
        current_status = get_git_status(current_dir)
        if any(current_status.values()):
            print("Warning: You have uncommitted changes in current worktree:")
            _print_status_summary(current_status)
            response = input("Continue with rebase? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Rebase cancelled")
                return 0

        # Rebase current worktree
        rebase_result = _rebase_worktree(
            current_dir, branch, verbose
        )

        if rebase_result != 0:
            return rebase_result

        # Rebase paired worktree if it exists
        if paired_worktree and paired_worktree.exists():
            if verbose:
                print(f"Rebasing paired worktree: {paired_worktree}")

            # Check paired worktree status
            paired_status = get_git_status(paired_worktree)
            if any(paired_status.values()):
                print("Warning: Paired worktree has uncommitted changes:")
                _print_status_summary(paired_status)
                response = input("Continue with rebase in paired worktree? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Rebase in paired worktree cancelled")
                    return 0

            paired_result = _rebase_worktree(
                paired_worktree, branch, verbose
            )

            if paired_result != 0:
                return paired_result

        print(f"Successfully rebased onto branch '{branch}'")
        return 0

    except Exception as e:
        print(f"Error rebasing worktrees: {e}")
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


def _rebase_worktree(
    worktree_path: Path,
    branch: str,
    verbose: bool = False
) -> int:
    """Rebase a specific worktree onto a branch."""
    # Check if the target branch exists
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
            print(f"Error: Target branch '{branch}' not found")
            return 1

        if verbose:
            print(f"Using remote branch 'origin/{branch}' as rebase target")

    # Store current commit for potential rollback
    current_commit = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    if current_commit.returncode != 0:
        print(f"Error getting current commit in {worktree_path}")
        return 1

    current_commit_hash = current_commit.stdout.strip()
    if verbose:
        print(f"Current commit: {current_commit_hash[:8]}")

    # Perform the rebase
    args = ['git', 'rebase', branch]
    result = subprocess.run(
        args,
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error rebasing {worktree_path} onto '{branch}': {result.stderr}")

        # Check if it's a rebase conflict
        if "CONFLICT" in result.stderr or "merge failed" in result.stderr:
            print("Rebase conflict detected!")
            print("Please resolve conflicts manually:")
            print(f"  1. Work in: {worktree_path}")
            print(f"  2. Resolve conflicts in affected files")
            print("  3. Run 'git rebase --continue'")
            print(f"  4. Or abort with 'git rebase --abort' (rollback to {current_commit_hash[:8]})")
            return 1

        # Offer to abort and rollback
        print("Rebase failed. Would you like to abort and rollback?")
        response = input("Abort rebase? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            abort_result = subprocess.run(
                ['git', 'rebase', '--abort'],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            if abort_result.returncode == 0:
                print(f"Rebase aborted, rolled back to {current_commit_hash[:8]}")
            else:
                print("Error aborting rebase")
        return 1

    if verbose:
        print(f"Successfully rebased {worktree_path} onto '{branch}'")
        if result.stdout:
            print("Rebase output:")
            print(result.stdout)

    return 0


def main(args: List[str]) -> int:
    """Main entry point for rebase command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree rebase',
        description='Rebase worktrees onto a branch'
    )
    parser.add_argument(
        'branch',
        help='Branch to rebase onto'
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
        return rebase_worktrees(repo, parsed_args.branch, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())