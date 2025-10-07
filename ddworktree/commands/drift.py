"""
Command for detecting drift between worktrees in ddworktree.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.diff import detect_drift, generate_diff_report


def detect_drift_command(
    repo: DDWorktreeRepo,
    pair: Optional[str] = None,
    verbose: bool = False
) -> int:
    """Detect unaligned commits or file differences between pair."""
    current_dir = Path.cwd()

    try:
        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")

        # Get the worktrees to compare
        main_worktree, local_worktree = _get_worktrees_for_comparison(repo, current_dir, pair, is_local)

        if not main_worktree or not local_worktree:
            print("Error: Could not find paired worktrees to compare")
            return 1

        if verbose:
            print(f"Comparing worktrees:")
            print(f"  Main:  {main_worktree}")
            print(f"  Local: {local_worktree}")

        # Check if worktrees exist
        if not main_worktree.exists():
            print(f"Error: Main worktree does not exist: {main_worktree}")
            return 1

        if not local_worktree.exists():
            print(f"Error: Local worktree does not exist: {local_worktree}")
            return 1

        # Detect drift
        drift = detect_drift(main_worktree, local_worktree)

        # Generate and display report
        report = generate_diff_report(drift)
        print(report)

        # Return exit code based on drift detection
        if drift.commit_drift or drift.added_files or drift.deleted_files or drift.modified_files:
            if verbose:
                print("\n⚠️  Drift detected between worktrees")
            return 1  # Exit with error code for CI use
        else:
            if verbose:
                print("\n✅ No drift detected - worktrees are in sync")
            return 0

    except Exception as e:
        print(f"Error detecting drift: {e}")
        return 1


def _is_local_worktree(worktree_path: Path, repo: DDWorktreeRepo) -> bool:
    """Check if this is a local worktree."""
    local_suffix = repo.get_local_suffix()
    return local_suffix in worktree_path.name


def _get_worktrees_for_comparison(
    repo: DDWorktreeRepo,
    current_path: Path,
    pair: Optional[str],
    is_local: bool
) -> tuple:
    """Get main and local worktree paths for comparison."""
    pairs = repo.get_pairs()

    if pair:
        # Use specified pair
        if pair in pairs:
            main_path, local_path = pairs[pair]
            return Path(main_path), Path(local_path)
        else:
            print(f"Error: Pair '{pair}' not found")
            return None, None
    else:
        # Auto-detect pair based on current worktree
        current_name = current_path.name

        for pair_name, (main_path, local_path) in pairs.items():
            if is_local and current_path == Path(local_path):
                return Path(main_path), Path(local_path)
            elif not is_local and current_path == Path(main_path):
                return Path(main_path), Path(local_path)

        # If not found in pairs, try to infer from current path
        local_suffix = repo.get_local_suffix()
        if is_local:
            # Current is local, infer main
            main_inferred = current_path.parent / current_path.name.replace(local_suffix, '')
            if main_inferred.exists():
                return main_inferred, current_path
        else:
            # Current is main, infer local
            local_inferred = current_path.parent / (current_path.name + local_suffix)
            if local_inferred.exists():
                return current_path, local_inferred

        print("Error: Could not find paired worktree")
        print("Available pairs:")
        for pair_name, (main_path, local_path) in pairs.items():
            print(f"  {pair_name}: {main_path} <-> {local_path}")

        return None, None


def main(args: List[str]) -> int:
    """Main entry point for drift command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree drift',
        description='Detect drift between worktrees'
    )
    parser.add_argument(
        'pair',
        nargs='?',
        help='Specific pair to check'
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
        return detect_drift_command(repo, parsed_args.pair, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())