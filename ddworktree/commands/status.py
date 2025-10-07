"""
Command for showing combined git status across both worktrees.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_git_status


def show_combined_status(
    repo: DDWorktreeRepo,
    short: bool = False,
    verbose: bool = False
) -> int:
    """Show combined git status across both worktrees."""
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

        # Get status for current worktree
        current_status = get_git_status(current_dir)

        if verbose:
            print(f"\n📁 Status for {worktree_type} worktree ({current_dir.name}):")
        else:
            print(f"\n📁 {worktree_type.upper()} worktree ({current_dir.name}):")

        _print_worktree_status(current_status, current_dir.name, short, verbose)

        # Get status for paired worktree if it exists
        if paired_worktree and paired_worktree.exists():
            paired_type = "main" if is_local else "local"
            paired_status = get_git_status(paired_worktree)

            if verbose:
                print(f"\n📁 Status for {paired_type} worktree ({paired_worktree.name}):")
            else:
                print(f"\n📁 {paired_type.upper()} worktree ({paired_worktree.name}):")

            _print_worktree_status(paired_status, paired_worktree.name, short, verbose)

            # Show drift summary if both worktrees exist
            if not short:
                _show_drift_summary(current_dir, paired_worktree, repo, verbose)
        else:
            if verbose:
                print(f"\n⚠️  No paired worktree found")

        # Show repository summary
        if verbose:
            _show_repository_summary(repo, current_dir, paired_worktree)

        return 0

    except Exception as e:
        print(f"Error showing status: {e}")
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


def _print_worktree_status(status: dict, worktree_name: str, short: bool, verbose: bool) -> None:
    """Print status for a single worktree."""
    if short:
        # Short format - just show summary
        total_changes = (
            len(status['modified']) +
            len(status['added']) +
            len(status['deleted']) +
            len(status['untracked'])
        )

        if total_changes == 0:
            print(f"  ✅ Clean")
        else:
            changes = []
            if status['modified']:
                changes.append(f"M:{len(status['modified'])}")
            if status['added']:
                changes.append(f"A:{len(status['added'])}")
            if status['deleted']:
                changes.append(f"D:{len(status['deleted'])}")
            if status['untracked']:
                changes.append(f"U:{len(status['untracked'])}")
            print(f"  ⚠️  {' '.join(changes)}")
    else:
        # Verbose format - show detailed status
        if any(status.values()):
            if status['modified']:
                print(f"  📝 Modified files ({len(status['modified'])}):")
                for file in status['modified']:
                    print(f"    M {file}")

            if status['added']:
                print(f"  ➕ Added files ({len(status['added'])}):")
                for file in status['added']:
                    print(f"    A {file}")

            if status['deleted']:
                print(f"  ➖ Deleted files ({len(status['deleted'])}):")
                for file in status['deleted']:
                    print(f"    D {file}")

            if status['untracked']:
                print(f"  ❓ Untracked files ({len(status['untracked'])}):")
                for file in status['untracked']:
                    print(f"    ? {file}")
        else:
            print("  ✅ Working tree clean")


def _show_drift_summary(main_dir: Path, local_dir: Path, repo: DDWorktreeRepo, verbose: bool) -> None:
    """Show drift summary between worktrees."""
    try:
        from ddworktree.utils.diff import detect_drift

        drift = detect_drift(main_dir, local_dir)

        if drift.commit_drift or drift.added_files or drift.deleted_files or drift.modified_files:
            print(f"\n🔄 Drift Summary:")
            if drift.commit_drift:
                main_commit = drift.main_commit[:8] if drift.main_commit else 'unknown'
                local_commit = drift.local_commit[:8] if drift.local_commit else 'unknown'
                print(f"  🔄 Commit drift: main={main_commit}, local={local_commit}")

            total_drift = len(drift.added_files) + len(drift.deleted_files) + len(drift.modified_files)
            if total_drift > 0:
                print(f"  📊 File drift: {total_drift} files")
                if verbose:
                    if drift.added_files:
                        print(f"    ➕ Added ({len(drift.added_files)}): {', '.join(drift.added_files[:3])}{'...' if len(drift.added_files) > 3 else ''}")
                    if drift.deleted_files:
                        print(f"    ➖ Deleted ({len(drift.deleted_files)}): {', '.join(drift.deleted_files[:3])}{'...' if len(drift.deleted_files) > 3 else ''}")
                    if drift.modified_files:
                        print(f"    ✏️  Modified ({len(drift.modified_files)}): {', '.join(drift.modified_files[:3])}{'...' if len(drift.modified_files) > 3 else ''}")
        else:
            print(f"\n✅ No drift detected")

    except Exception:
        if verbose:
            print(f"\n⚠️  Could not check drift status")


def _show_repository_summary(repo: DDWorktreeRepo, current_dir: Path, paired_worktree: Path) -> None:
    """Show repository-wide summary."""
    print(f"\n📊 Repository Summary:")
    print(f"  Root: {repo.repo_path}")

    # Show configured pairs
    pairs = repo.get_pairs()
    if pairs:
        print(f"  Configured pairs ({len(pairs)}):")
        for pair_name, (main_path, local_path) in pairs.items():
            main_exists = "✅" if Path(main_path).exists() else "❌"
            local_exists = "✅" if Path(local_path).exists() else "❌"
            print(f"    {pair_name}: {main_exists} {local_exists}")
    else:
        print("  No configured pairs")

    # Show current branch info
    try:
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=current_dir,
            capture_output=True,
            text=True
        )
        if branch_result.returncode == 0:
            current_branch = branch_result.stdout.strip()
            print(f"  Current branch: {current_branch}")
    except Exception:
        pass

    # Show remote info
    try:
        remote_result = subprocess.run(
            ['git', 'remote', '-v'],
            cwd=repo.repo_path,
            capture_output=True,
            text=True
        )
        if remote_result.returncode == 0:
            remotes = remote_result.stdout.strip().split('\n')
            if remotes and remotes[0]:
                print(f"  Remote: {remotes[0].split()[1]}")
    except Exception:
        pass


def main(args: List[str]) -> int:
    """Main entry point for status command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree status',
        description='Show combined status across both worktrees'
    )
    parser.add_argument(
        '--short',
        action='store_true',
        help='Short format'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose format'
    )

    parsed_args = parser.parse_args(args)

    # Validate mutually exclusive options
    if parsed_args.short and parsed_args.verbose:
        print("Error: --short and --verbose are mutually exclusive", file=sys.stderr)
        return 1

    try:
        repo = DDWorktreeRepo()
        return show_combined_status(repo, parsed_args.short, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())