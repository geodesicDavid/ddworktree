"""
Command for fetching remote updates in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError


def fetch_updates(
    repo: DDWorktreeRepo,
    all_flag: bool = False,
    prune: bool = False,
    verbose: bool = False
) -> int:
    """Fetch remote updates for paired branches."""
    current_dir = Path.cwd()

    try:
        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")

        # Build fetch command
        fetch_args = ['git', 'fetch']
        if all_flag:
            fetch_args.append('--all')
        if prune:
            fetch_args.append('--prune')

        # Execute fetch from main repository
        if verbose:
            print(f"Fetching updates from main repository: {repo.repo_path}")

        result = subprocess.run(
            fetch_args,
            cwd=repo.repo_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Error fetching updates: {result.stderr}")
            return 1

        if verbose:
            print("Fetch output:")
            print(result.stdout)

        # Get paired worktree and verify its state
        paired_worktree = _get_paired_worktree(current_dir, repo, is_local)
        if paired_worktree and paired_worktree.exists():
            if verbose:
                print(f"Verifying branch state in paired worktree: {paired_worktree}")

            # Get current branch in paired worktree
            paired_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=paired_worktree,
                capture_output=True,
                text=True
            )

            if paired_result.returncode == 0:
                paired_branch = paired_result.stdout.strip()
                if paired_branch:
                    if verbose:
                        print(f"Paired worktree branch: {paired_branch}")

                    # Verify remote tracking for this branch
                    remote_result = subprocess.run(
                        ['git', 'rev-parse', '--abbrev-ref', f'{paired_branch}@{{upstream}}'],
                        cwd=paired_worktree,
                        capture_output=True,
                        text=True
                    )

                    if remote_result.returncode != 0:
                        print(f"Warning: Paired worktree branch '{paired_branch}' has no upstream tracking")
                    elif verbose:
                        remote_branch = remote_result.stdout.strip()
                        print(f"Remote tracking: {remote_branch}")

        print("Successfully fetched remote updates")
        return 0

    except Exception as e:
        print(f"Error fetching updates: {e}")
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


def main(args: List[str]) -> int:
    """Main entry point for fetch command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree fetch',
        description='Fetch remote updates for paired branches'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Fetch all remotes'
    )
    parser.add_argument(
        '--prune',
        action='store_true',
        help='Prune deleted branches'
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
        return fetch_updates(repo, parsed_args.all, parsed_args.prune, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())