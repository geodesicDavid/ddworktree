"""
Command for showing differences between worktrees in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.diff import detect_drift, generate_diff_report


def show_worktree_diff(
    repo: DDWorktreeRepo,
    name_only: bool = False,
    patch: bool = False,
    paths: List[str] = None,
    verbose: bool = False
) -> int:
    """Show diff between paired worktrees."""
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

        if not paired_worktree or not paired_worktree.exists():
            print("Error: No paired worktree found")
            return 1

        if verbose:
            print(f"Comparing with paired worktree: {paired_worktree}")

        # Detect drift
        drift = detect_drift(current_dir, paired_worktree)

        if not (drift.commit_drift or drift.added_files or drift.deleted_files or drift.modified_files):
            print("✅ No differences found between worktrees")
            return 0

        # Filter paths if specified
        if paths:
            drift = _filter_drift_by_paths(drift, paths)

            if not (drift.commit_drift or drift.added_files or drift.deleted_files or drift.modified_files):
                print("✅ No differences found for specified paths")
                return 0

        # Show drift header
        print(f"\n🔄 Differences between worktrees:")
        print(f"  {worktree_type.capitalize()}: {current_dir.name}")
        print(f"  {'Main' if is_local else 'Local'}: {paired_worktree.name}")

        # Show commit drift if present
        if drift.commit_drift:
            print(f"\n🔄 Commit drift:")
            main_commit = drift.main_commit[:8] if drift.main_commit else 'unknown'
            local_commit = drift.local_commit[:8] if drift.local_commit else 'unknown'
            print(f"  Main:  {main_commit}")
            print(f"  Local: {local_commit}")

        # Show file differences
        if name_only:
            _show_name_only_diff(drift)
        elif patch:
            _show_patch_diff(current_dir, paired_worktree, drift, verbose)
        else:
            _show_summary_diff(drift)

        return 0

    except Exception as e:
        print(f"Error showing diff: {e}")
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


def _filter_drift_by_paths(drift, paths: List[str]):
    """Filter drift results to only include specified paths."""
    from dataclasses import dataclass

    @dataclass
    class WorktreeDiff:
        added_files: List[str]
        deleted_files: List[str]
        modified_files: List[str]
        commit_drift: bool
        main_commit: str
        local_commit: str

    filtered = WorktreeDiff(
        added_files=[f for f in drift.added_files if any(p in f for p in paths)],
        deleted_files=[f for f in drift.deleted_files if any(p in f for p in paths)],
        modified_files=[f for f in drift.modified_files if any(p in f for p in paths)],
        commit_drift=drift.commit_drift,
        main_commit=drift.main_commit,
        local_commit=drift.local_commit
    )

    return filtered


def _show_name_only_diff(drift) -> None:
    """Show only file names that differ."""
    print(f"\n📁 Files that differ:")

    all_files = []
    all_files.extend([f"A {f}" for f in drift.added_files])
    all_files.extend([f"D {f}" for f in drift.deleted_files])
    all_files.extend([f"M {f}" for f in drift.modified_files])

    for file_line in sorted(all_files):
        print(f"  {file_line}")


def _show_summary_diff(drift) -> None:
    """Show a summary of differences."""
    print(f"\n📊 Summary of differences:")
    print(f"  Added files: {len(drift.added_files)}")
    print(f"  Deleted files: {len(drift.deleted_files)}")
    print(f"  Modified files: {len(drift.modified_files)}")

    if drift.added_files:
        print(f"\n➕ Added files:")
        for file in sorted(drift.added_files):
            print(f"  {file}")

    if drift.deleted_files:
        print(f"\n➖ Deleted files:")
        for file in sorted(drift.deleted_files):
            print(f"  {file}")

    if drift.modified_files:
        print(f"\n✏️  Modified files:")
        for file in sorted(drift.modified_files):
            print(f"  {file}")


def _show_patch_diff(worktree1: Path, worktree2: Path, drift, verbose: bool) -> None:
    """Show patch-style diff between worktrees."""
    import tempfile
    import os

    print(f"\n🔍 Detailed differences:")

    # Show diff for each type of change
    for file_path in drift.added_files:
        file2 = worktree2 / file_path
        if file2.exists():
            print(f"\n➕ Added: {file_path}")
            result = subprocess.run(
                ['git', 'diff', '--no-index', '/dev/null', str(file2)],
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(result.stdout)

    for file_path in drift.deleted_files:
        file1 = worktree1 / file_path
        if file1.exists():
            print(f"\n➖ Deleted: {file_path}")
            result = subprocess.run(
                ['git', 'diff', '--no-index', str(file1), '/dev/null'],
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(result.stdout)

    for file_path in drift.modified_files:
        file1 = worktree1 / file_path
        file2 = worktree2 / file_path
        if file1.exists() and file2.exists():
            print(f"\n✏️  Modified: {file_path}")
            result = subprocess.run(
                ['git', 'diff', '--no-index', str(file1), str(file2)],
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(result.stdout)


def main(args: List[str]) -> int:
    """Main entry point for diff command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree diff',
        description='Show differences between worktrees'
    )
    parser.add_argument(
        '--name-only',
        action='store_true',
        help='Show only file names'
    )
    parser.add_argument(
        '--patch',
        action='store_true',
        help='Show patch'
    )
    parser.add_argument(
        'paths',
        nargs='*',
        help='Paths to diff'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed output'
    )

    parsed_args = parser.parse_args(args)

    # Validate mutually exclusive options
    if parsed_args.name_only and parsed_args.patch:
        print("Error: --name-only and --patch are mutually exclusive", file=sys.stderr)
        return 1

    try:
        repo = DDWorktreeRepo()
        return show_worktree_diff(
            repo,
            parsed_args.name_only,
            parsed_args.patch,
            parsed_args.paths,
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