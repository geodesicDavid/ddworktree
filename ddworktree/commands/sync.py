"""
Command for synchronizing worktrees in ddworktree.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.diff import detect_drift, generate_diff_report, sync_files


def sync_worktrees(
    repo: DDWorktreeRepo,
    pair: Optional[str] = None,
    auto_commit: bool = False,
    dry_run: bool = False,
    verbose: bool = False
) -> int:
    """Resynchronize pair to remove drift."""
    current_dir = Path.cwd()

    try:
        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Detected {worktree_type} worktree")

        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")

        # Get the worktrees to sync
        main_worktree, local_worktree = _get_worktrees_for_sync(repo, current_dir, pair, is_local)

        if not main_worktree or not local_worktree:
            print("Error: Could not find paired worktrees to synchronize")
            return 1

        if verbose:
            print(f"Synchronizing worktrees:")
            print(f"  Main:  {main_worktree}")
            print(f"  Local: {local_worktree}")

        # Check if worktrees exist
        if not main_worktree.exists():
            print(f"Error: Main worktree does not exist: {main_worktree}")
            return 1

        if not local_worktree.exists():
            print(f"Error: Local worktree does not exist: {local_worktree}")
            return 1

        # Detect current drift
        drift = detect_drift(main_worktree, local_worktree)

        if not (drift.commit_drift or drift.added_files or drift.deleted_files or drift.modified_files):
            print("✅ No drift detected - worktrees are already in sync")
            return 0

        # Show drift summary
        print("\n📋 Drift Summary:")
        report = generate_diff_report(drift)
        print(report)

        if dry_run:
            print("\n🔍 Dry run complete - no changes made")
            return 0

        # Ask for confirmation unless auto-commit is enabled
        if not auto_commit:
            response = input("\nProceed with synchronization? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Synchronization cancelled")
                return 0

        # Perform synchronization
        sync_result = _perform_synchronization(
            main_worktree, local_worktree, drift, auto_commit, verbose
        )

        if sync_result != 0:
            return sync_result

        # Verify synchronization
        if verbose:
            print("\n🔍 Verifying synchronization...")
        new_drift = detect_drift(main_worktree, local_worktree)

        if new_drift.commit_drift or new_drift.added_files or new_drift.deleted_files or new_drift.modified_files:
            print("⚠️  Warning: Synchronization completed but drift still detected")
            if verbose:
                print("Remaining drift:")
                print(generate_diff_report(new_drift))
            return 1
        else:
            print("✅ Synchronization completed successfully")
            return 0

    except Exception as e:
        print(f"Error synchronizing worktrees: {e}")
        return 1


def _is_local_worktree(worktree_path: Path, repo: DDWorktreeRepo) -> bool:
    """Check if this is a local worktree."""
    local_suffix = repo.get_local_suffix()
    return local_suffix in worktree_path.name


def _get_worktrees_for_sync(
    repo: DDWorktreeRepo,
    current_path: Path,
    pair: Optional[str],
    is_local: bool
) -> tuple:
    """Get main and local worktree paths for synchronization."""
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


def _perform_synchronization(
    main_worktree: Path,
    local_worktree: Path,
    drift,
    auto_commit: bool,
    verbose: bool
) -> int:
    """Perform the actual synchronization."""
    import subprocess
    import shutil

    sync_actions = []

    # Handle added files (copy from local to main)
    if drift.added_files:
        if verbose:
            print(f"\n📁 Syncing {len(drift.added_files)} added files...")
        result = sync_files(local_worktree, main_worktree, drift.added_files, dry_run=False)
        sync_actions.extend(result)

        # Stage the files in main worktree
        for file_path in drift.added_files:
            subprocess.run(
                ['git', 'add', file_path],
                cwd=main_worktree,
                capture_output=True
            )

    # Handle deleted files (remove from main if they don't exist in local)
    if drift.deleted_files:
        if verbose:
            print(f"\n🗑️  Syncing {len(drift.deleted_files)} deleted files...")
        for file_path in drift.deleted_files:
            main_file = main_worktree / file_path
            if main_file.exists():
                main_file.unlink()
                subprocess.run(
                    ['git', 'rm', file_path],
                    cwd=main_worktree,
                    capture_output=True
                )
                sync_actions.append(f"Removed: {file_path}")

    # Handle modified files (copy newer version)
    if drift.modified_files:
        if verbose:
            print(f"\n✏️  Syncing {len(drift.modified_files)} modified files...")
        result = sync_files(local_worktree, main_worktree, drift.modified_files, dry_run=False)
        sync_actions.extend(result)

        # Stage the modified files in main worktree
        for file_path in drift.modified_files:
            subprocess.run(
                ['git', 'add', file_path],
                cwd=main_worktree,
                capture_output=True
            )

    # Handle commit drift
    if drift.commit_drift:
        if verbose:
            print(f"\n🔄 Commit drift detected:")
            print(f"  Main:  {drift.main_commit[:8] if drift.main_commit else 'unknown'}")
            print(f"  Local: {drift.local_commit[:8] if drift.local_commit else 'unknown'}")

        # Reset main to match local commit if needed
        if drift.main_commit and drift.local_commit and drift.main_commit != drift.local_commit:
            if verbose:
                print(f"Resetting main worktree to commit {drift.local_commit[:8]}")
            subprocess.run(
                ['git', 'reset', '--hard', drift.local_commit],
                cwd=main_worktree,
                capture_output=True
            )
            sync_actions.append(f"Reset main to {drift.local_commit[:8]}")

    # Auto-commit if requested and there are changes
    if auto_commit and sync_actions:
        if verbose:
            print("\n💾 Auto-committing synchronization changes...")

        # Check if there are staged changes
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=main_worktree,
            capture_output=True,
            text=True
        )

        if status_result.stdout.strip():
            commit_result = subprocess.run(
                ['git', 'commit', '-m', 'Automatic synchronization from ddworktree'],
                cwd=main_worktree,
                capture_output=True,
                text=True
            )

            if commit_result.returncode == 0:
                sync_actions.append("Auto-committed changes")
            else:
                print("Warning: Auto-commit failed")
        else:
            if verbose:
                print("No staged changes to commit")

    return 0


def main(args: List[str]) -> int:
    """Main entry point for sync command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree sync',
        description='Synchronize worktrees'
    )
    parser.add_argument(
        'pair',
        nargs='?',
        help='Specific pair to sync'
    )
    parser.add_argument(
        '--auto-commit',
        action='store_true',
        help='Auto-commit changes'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done'
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
        return sync_worktrees(
            repo,
            parsed_args.pair,
            parsed_args.auto_commit,
            parsed_args.dry_run,
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