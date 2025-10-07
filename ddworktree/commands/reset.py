"""
Command for resetting worktrees in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_git_status


def reset_worktrees(
    repo: DDWorktreeRepo,
    commitish: Optional[str] = None,
    hard: bool = False,
    soft: bool = False,
    keep_local: bool = False,
    verbose: bool = False
) -> int:
    """Reset both trees to same commit or HEAD safely."""
    current_dir = Path.cwd()

    try:
        # Check if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")

        # Get paired worktree
        paired_worktree = _get_paired_worktree(current_dir, repo, is_local)

        # Confirm before hard reset
        if hard:
            if not _confirm_hard_reset(current_dir, paired_worktree, verbose):
                print("Hard reset cancelled")
                return 0

        # Reset current worktree
        reset_result = _reset_worktree(
            current_dir, commitish, hard, soft, verbose
        )

        if reset_result != 0:
            return reset_result

        # Reset paired worktree if not keeping local changes
        if paired_worktree and paired_worktree.exists() and not keep_local:
            if verbose:
                print(f"Resetting paired worktree: {paired_worktree}")

            paired_result = _reset_worktree(
                paired_worktree, commitish, hard, soft, verbose
            )

            if paired_result != 0:
                return paired_result

        print(f"Reset completed in {worktree_type} worktree")
        if paired_worktree and not keep_local:
            print(f"Reset completed in paired worktree")

        return 0

    except Exception as e:
        print(f"Error resetting worktrees: {e}")
        return 1


def _is_local_worktree(worktree_path: Path, repo: DDWorktreeRepo) -> bool:
    """Check if this is a local worktree."""
    local_suffix = repo.get_local_suffix()
    return local_suffix in worktree_path.name


def _get_paired_worktree(
    current_path: Path,
    repo: DDWorktreeRepo,
    is_local: bool
) -> Optional[Path]:
    """Get the paired worktree path."""
    pairs = repo.get_pairs()
    current_name = current_path.name

    for pair_name, (main_path, local_path) in pairs.items():
        if is_local and current_path == Path(local_path):
            return Path(main_path)
        elif not is_local and current_path == Path(main_path):
            return Path(local_path)

    return None


def _confirm_hard_reset(
    current_path: Path,
    paired_path: Optional[Path],
    verbose: bool
) -> bool:
    """Confirm hard reset with user."""
    print("⚠️  WARNING: Hard reset will discard all uncommitted changes!")
    print(f"Current worktree: {current_path}")

    if paired_path and paired_path.exists():
        print(f"Paired worktree: {paired_path}")

    # Get status to show what will be lost
    try:
        current_status = get_git_status(current_path)
        if any(current_status.values()):
            print("Uncommitted changes in current worktree:")
            _print_status_summary(current_status)

        if paired_path and paired_path.exists():
            paired_status = get_git_status(paired_path)
            if any(paired_status.values()):
                print("Uncommitted changes in paired worktree:")
                _print_status_summary(paired_status)
    except Exception:
        pass  # Don't fail if we can't get status

    response = input("Are you sure you want to continue? (y/N): ").strip().lower()
    return response in ['y', 'yes']


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


def _reset_worktree(
    worktree_path: Path,
    commitish: Optional[str],
    hard: bool = False,
    soft: bool = False,
    verbose: bool = False
) -> int:
    """Reset a specific worktree."""
    args = ['git', 'reset']

    if hard:
        args.append('--hard')
    elif soft:
        args.append('--soft')

    if commitish:
        args.append(commitish)

    result = subprocess.run(
        args,
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error resetting {worktree_path}: {result.stderr}")
        return 1

    if verbose:
        reset_type = "hard" if hard else "soft" if soft else "mixed"
        target = commitish if commitish else "HEAD"
        print(f"Successfully {reset_type} reset {worktree_path} to {target}")

    return 0


def main(args: List[str]) -> int:
    """Main entry point for reset command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree reset',
        description='Reset both trees to same commit or HEAD safely'
    )
    parser.add_argument(
        'commitish',
        nargs='?',
        help='Commit to reset to (default: HEAD)'
    )
    parser.add_argument(
        '--hard',
        action='store_true',
        help='Hard reset (discard all changes)'
    )
    parser.add_argument(
        '--soft',
        action='store_true',
        help='Soft reset (keep changes staged)'
    )
    parser.add_argument(
        '--keep-local',
        action='store_true',
        help='Keep local changes in paired worktree'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed output'
    )

    parsed_args = parser.parse_args(args)

    # Validate mutually exclusive options
    if parsed_args.hard and parsed_args.soft:
        print("Error: --hard and --soft are mutually exclusive", file=sys.stderr)
        return 1

    try:
        repo = DDWorktreeRepo()
        return reset_worktrees(
            repo,
            parsed_args.commitish,
            parsed_args.hard,
            parsed_args.soft,
            parsed_args.keep_local,
            parsed_args.verbose
        )
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())