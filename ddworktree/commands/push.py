"""
Command for pushing commits in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError


def push_commits(
    repo: DDWorktreeRepo,
    include_local: bool = False,
    verbose: bool = False
) -> int:
    """Push commits from main tree (optionally local)."""
    current_dir = Path.cwd()

    try:
        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")

        # Check configuration for push_local
        push_local_config = repo.get_option('push_local', 'false')
        push_local = push_local_config == 'true' or include_local

        # Get paired worktree
        paired_worktree = _get_paired_worktree(current_dir, repo, is_local)

        # Push from main worktree
        if not is_local:
            if verbose:
                print("Pushing from main worktree")

            push_result = _push_from_worktree(current_dir, verbose)
            if push_result != 0:
                return push_result

        # Push from local worktree if configured
        if push_local and paired_worktree and paired_worktree.exists():
            if verbose:
                print("Pushing from local worktree")

            local_push_result = _push_from_worktree(paired_worktree, verbose)
            if local_push_result != 0:
                return local_push_result

        print("Successfully pushed commits")
        return 0

    except Exception as e:
        print(f"Error pushing commits: {e}")
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


def _push_from_worktree(worktree_path: Path, verbose: bool = False) -> int:
    """Push commits from a specific worktree."""
    # Get current branch
    branch_result = subprocess.run(
        ['git', 'branch', '--show-current'],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    if branch_result.returncode != 0:
        print(f"Error getting current branch in {worktree_path}")
        return 1

    current_branch = branch_result.stdout.strip()
    if not current_branch:
        print(f"No current branch in {worktree_path}")
        return 1

    if verbose:
        print(f"Pushing branch '{current_branch}' from {worktree_path.name}")

    # Check if branch has upstream tracking
    remote_result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', f'{current_branch}@{{upstream}}'],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    if remote_result.returncode != 0:
        print(f"Branch '{current_branch}' has no upstream tracking branch")
        print("Setting upstream tracking...")

        # Try to set upstream tracking
        upstream_result = subprocess.run(
            ['git', 'push', '-u', 'origin', current_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )

        if upstream_result.returncode != 0:
            print(f"Error setting upstream for branch '{current_branch}': {upstream_result.stderr}")
            return 1

        if verbose:
            print(f"Set upstream tracking for branch '{current_branch}'")
    else:
        # Normal push
        push_result = subprocess.run(
            ['git', 'push'],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )

        if push_result.returncode != 0:
            print(f"Error pushing from {worktree_path}: {push_result.stderr}")
            return 1

        if verbose and push_result.stdout:
            print(f"Push output from {worktree_path.name}:")
            print(push_result.stdout)

    return 0


def main(args: List[str]) -> int:
    """Main entry point for push command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree push',
        description='Push commits from main tree (optionally local)'
    )
    parser.add_argument(
        '--include-local',
        action='store_true',
        help='Include local commits in push'
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
        return push_commits(repo, parsed_args.include_local, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())