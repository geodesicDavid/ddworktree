"""
Command for cherry-picking commits in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_git_status


def cherry_pick_commit(
    repo: DDWorktreeRepo,
    commit: str,
    verbose: bool = False
) -> int:
    """Apply commits to both trees, respecting ignore scope."""
    current_dir = Path.cwd()

    try:
        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")
            print(f"Cherry-picking commit: {commit}")

        # Get paired worktree
        paired_worktree = _get_paired_worktree(current_dir, repo, is_local)

        # Verify the commit exists
        if not _commit_exists(repo.repo_path, commit):
            print(f"Error: Commit '{commit}' not found")
            return 1

        # Get commit info for validation
        commit_info = _get_commit_info(repo.repo_path, commit)
        if verbose:
            print(f"Commit info: {commit_info}")

        # Check for uncommitted changes before cherry-pick
        current_status = get_git_status(current_dir)
        if any(current_status.values()):
            print("Warning: You have uncommitted changes in current worktree:")
            _print_status_summary(current_status)
            response = input("Continue with cherry-pick? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Cherry-pick cancelled")
                return 0

        # Cherry-pick in current worktree
        cp_result = _cherry_pick_in_worktree(
            current_dir, commit, verbose
        )

        if cp_result != 0:
            return cp_result

        # Cherry-pick in paired worktree if it exists
        if paired_worktree and paired_worktree.exists():
            if verbose:
                print(f"Cherry-picking in paired worktree: {paired_worktree}")

            # Check paired worktree status
            paired_status = get_git_status(paired_worktree)
            if any(paired_status.values()):
                print("Warning: Paired worktree has uncommitted changes:")
                _print_status_summary(paired_status)
                response = input("Continue with cherry-pick in paired worktree? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Cherry-pick in paired worktree cancelled")
                    return 0

            paired_result = _cherry_pick_in_worktree(
                paired_worktree, commit, verbose
            )

            if paired_result != 0:
                return paired_result

        print(f"Successfully cherry-picked commit '{commit}'")
        return 0

    except Exception as e:
        print(f"Error cherry-picking commit: {e}")
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


def _commit_exists(repo_path: Path, commit: str) -> bool:
    """Check if a commit exists."""
    result = subprocess.run(
        ['git', 'cat-file', '-e', f'{commit}^{commit}'],
        cwd=repo_path,
        capture_output=True
    )
    return result.returncode == 0


def _get_commit_info(repo_path: Path, commit: str) -> str:
    """Get commit information."""
    result = subprocess.run(
        ['git', 'log', '--oneline', '-n', '1', commit],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return f"Commit {commit}"


def _cherry_pick_in_worktree(
    worktree_path: Path,
    commit: str,
    verbose: bool = False
) -> int:
    """Cherry-pick a commit in a specific worktree."""
    # Check if commit already exists in this worktree
    exists_check = subprocess.run(
        ['git', 'merge-base', '--is-ancestor', commit, 'HEAD'],
        cwd=worktree_path,
        capture_output=True
    )

    if exists_check.returncode == 0:
        if verbose:
            print(f"Commit {commit} already exists in {worktree_path.name}")
        return 0

    # Perform the cherry-pick
    args = ['git', 'cherry-pick', commit]
    result = subprocess.run(
        args,
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error cherry-picking commit '{commit}' in {worktree_path}: {result.stderr}")

        # Check if it's a conflict
        if "CONFLICT" in result.stderr or "conflict" in result.stderr.lower():
            print("Cherry-pick conflict detected!")
            print("Please resolve conflicts manually:")
            print(f"  1. Work in: {worktree_path}")
            print("  2. Resolve conflicts in affected files")
            print("  3. Run 'git cherry-pick --continue'")
            print("  4. Or abort with 'git cherry-pick --abort'")
            return 1

        # Offer to abort
        print("Cherry-pick failed. Would you like to abort?")
        response = input("Abort cherry-pick? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            abort_result = subprocess.run(
                ['git', 'cherry-pick', '--abort'],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            if abort_result.returncode == 0:
                print("Cherry-pick aborted")
            else:
                print("Error aborting cherry-pick")
        return 1

    if verbose:
        print(f"Successfully cherry-picked commit '{commit}' in {worktree_path}")
        if result.stdout:
            print("Cherry-pick output:")
            print(result.stdout)

    return 0


def main(args: List[str]) -> int:
    """Main entry point for cherry-pick command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree cherry-pick',
        description='Apply commits to both trees'
    )
    parser.add_argument(
        'commit',
        help='Commit to cherry-pick'
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
        return cherry_pick_commit(repo, parsed_args.commit, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())