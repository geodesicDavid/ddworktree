"""
Command for committing changes in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_git_status


def commit_changes(
    repo: DDWorktreeRepo,
    message: str,
    amend: bool = False,
    split: bool = False,
    verbose: bool = False
) -> int:
    """Commit changes to both trees, respecting ignore scopes."""
    current_dir = Path.cwd()

    try:
        # Get current git status
        status = get_git_status(current_dir)

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Repository: {repo.repo_path}")

        # Check if there are staged changes
        if not any([status['modified'], status['added'], status['deleted']]):
            print("No staged changes to commit")
            return 0

        # Determine if this is a main or local worktree
        is_local = _is_local_worktree(current_dir, repo)
        worktree_type = "local" if is_local else "main"

        if verbose:
            print(f"Detected {worktree_type} worktree")

        # Commit in current worktree
        commit_result = _commit_in_worktree(
            current_dir, message, amend, verbose
        )

        if commit_result != 0:
            return commit_result

        # If not split, try to commit in paired worktree
        if not split:
            paired_worktree = _get_paired_worktree(current_dir, repo, is_local)
            if paired_worktree and paired_worktree.exists():
                if verbose:
                    print(f"Attempting to commit in paired worktree: {paired_worktree}")

                # Sync changes to paired worktree
                sync_result = _sync_and_commit_paired(
                    current_dir, paired_worktree, message, amend, verbose
                )

                if sync_result != 0:
                    return sync_result

        print(f"Committed changes in {worktree_type} worktree")
        return 0

    except Exception as e:
        print(f"Error committing changes: {e}")
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


def _commit_in_worktree(
    worktree_path: Path,
    message: str,
    amend: bool = False,
    verbose: bool = False
) -> int:
    """Commit changes in a specific worktree."""
    args = ['git', 'commit']
    if amend:
        args.append('--amend')
    args.extend(['-m', message])

    result = subprocess.run(
        args,
        cwd=worktree_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        if "nothing to commit" in result.stdout:
            if verbose:
                print("No changes to commit in this worktree")
            return 0
        else:
            print(f"Error committing in {worktree_path}: {result.stderr}")
            return 1

    if verbose:
        print(f"Successfully committed in {worktree_path}")

    return 0


def _sync_and_commit_paired(
    source_path: Path,
    target_path: Path,
    message: str,
    amend: bool = False,
    verbose: bool = False
) -> int:
    """Sync changes from source to target worktree and commit."""
    try:
        # Get status of both worktrees
        source_status = get_git_status(source_path)
        target_status = get_git_status(target_path)

        # Check if there are relevant changes to sync
        relevant_changes = _get_relevant_changes(source_status, target_path)

        if not relevant_changes:
            if verbose:
                print("No relevant changes to sync to paired worktree")
            return 0

        # Copy relevant files to target worktree
        import shutil
        for file_path in relevant_changes:
            source_file = source_path / file_path
            target_file = target_path / file_path

            if source_file.exists():
                # Create target directory if needed
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)

                # Stage the file in target worktree
                subprocess.run(
                    ['git', 'add', str(target_file)],
                    cwd=target_path,
                    capture_output=True
                )

        # Commit in target worktree
        return _commit_in_worktree(target_path, message, amend, verbose)

    except Exception as e:
        print(f"Error syncing to paired worktree: {e}")
        return 1


def _get_relevant_changes(status: Dict[str, Any], target_path: Path) -> List[str]:
    """Get list of files that should be synced to target worktree."""
    relevant_files = []

    # Add modified and added files
    relevant_files.extend(status['modified'])
    relevant_files.extend(status['added'])

    # Note: deleted files need special handling
    # For now, we'll skip them to avoid accidental data loss

    return relevant_files


def main(args: List[str]) -> int:
    """Main entry point for commit command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree commit',
        description='Commit changes to both trees, respecting ignore scopes'
    )
    parser.add_argument(
        '-m', '--message',
        required=True,
        help='Commit message'
    )
    parser.add_argument(
        '--amend',
        action='store_true',
        help='Amend previous commit'
    )
    parser.add_argument(
        '--split',
        action='store_true',
        help='Create separate commits in each worktree'
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
        return commit_changes(
            repo,
            parsed_args.message,
            parsed_args.amend,
            parsed_args.split,
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