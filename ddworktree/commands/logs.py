"""
Command for showing commit logs in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

from ddworktree.core import DDWorktreeRepo, DDWorktreeError


def show_logs(
    repo: DDWorktreeRepo,
    graph: bool = False,
    since: Optional[str] = None,
    until: Optional[str] = None,
    verbose: bool = False
) -> int:
    """Show commit logs across paired trees."""
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

        # Build log command
        log_args = ['git', 'log']
        if graph:
            log_args.append('--graph')
        if since:
            log_args.extend(['--since', since])
        if until:
            log_args.extend(['--until', until])

        # Add pretty format for better readability
        log_args.extend(['--pretty=format:%h %ad | %s%d %an', '--date=short'])

        # Show logs for current worktree
        print(f"\n📁 Commit logs for {worktree_type} worktree ({current_dir.name}):")
        print("-" * 80)

        result = subprocess.run(
            log_args,
            cwd=current_dir,
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            print(result.stdout)
        else:
            print("  No commits found")

        # Show logs for paired worktree if it exists
        if paired_worktree and paired_worktree.exists():
            paired_type = "main" if is_local else "local"
            print(f"\n📁 Commit logs for {paired_type} worktree ({paired_worktree.name}):")
            print("-" * 80)

            paired_result = subprocess.run(
                log_args,
                cwd=paired_worktree,
                capture_output=True,
                text=True
            )

            if paired_result.returncode == 0 and paired_result.stdout.strip():
                print(paired_result.stdout)
            else:
                print("  No commits found")

            # Show commit comparison if both worktrees have commits
            if result.returncode == 0 and paired_result.returncode == 0:
                if result.stdout.strip() and paired_result.stdout.strip():
                    _show_commit_comparison(current_dir, paired_worktree, verbose)

        # Show repository summary if verbose
        if verbose:
            _show_repository_summary(repo, current_dir, paired_worktree)

        return 0

    except Exception as e:
        print(f"Error showing logs: {e}")
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


def _show_commit_comparison(worktree1: Path, worktree2: Path, verbose: bool) -> None:
    """Show a comparison of commits between worktrees."""
    try:
        # Get commit hashes for both worktrees
        result1 = subprocess.run(
            ['git', 'rev-list', '--all'],
            cwd=worktree1,
            capture_output=True,
            text=True
        )
        result2 = subprocess.run(
            ['git', 'rev-list', '--all'],
            cwd=worktree2,
            capture_output=True,
            text=True
        )

        if result1.returncode == 0 and result2.returncode == 0:
            commits1 = set(result1.stdout.strip().split('\n')) if result1.stdout.strip() else set()
            commits2 = set(result2.stdout.strip().split('\n')) if result2.stdout.strip() else set()

            common_commits = commits1 & commits2
            unique_to_1 = commits1 - commits2
            unique_to_2 = commits2 - commits1

            if unique_to_1 or unique_to_2:
                print(f"\n🔄 Commit Comparison:")
                if unique_to_1:
                    print(f"  Commits only in {worktree1.name}: {len(unique_to_1)}")
                if unique_to_2:
                    print(f"  Commits only in {worktree2.name}: {len(unique_to_2)}")
                if common_commits:
                    print(f"  Common commits: {len(common_commits)}")
            elif verbose:
                print(f"\n✅ Both worktrees have identical commit histories")

    except Exception:
        if verbose:
            print("\n⚠️  Could not compare commit histories")


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

    # Show commit counts
    try:
        for worktree_name, worktree_path in [("Current", current_dir), ("Paired", paired_worktree)]:
            if worktree_path and worktree_path.exists():
                count_result = subprocess.run(
                    ['git', 'rev-list', '--count', '--all'],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True
                )
                if count_result.returncode == 0:
                    count = count_result.stdout.strip()
                    print(f"  {worktree_name} commits: {count}")
    except Exception:
        pass


def main(args: List[str]) -> int:
    """Main entry point for logs command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree logs',
        description='Show commit logs across paired trees'
    )
    parser.add_argument(
        '--graph',
        action='store_true',
        help='Show graph'
    )
    parser.add_argument(
        '--since',
        help='Show commits since date'
    )
    parser.add_argument(
        '--until',
        help='Show commits until date'
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
        return show_logs(repo, parsed_args.graph, parsed_args.since, parsed_args.until, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())