"""
Command for staging files for commit in ddworktree.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.gitignore import get_combined_gitignore_patterns, get_git_status


def add_files(repo: DDWorktreeRepo, files: List[str], verbose: bool = False) -> int:
    """Stage files for commit respecting ignore rules."""
    if not files:
        files = ['.']  # Default to current directory

    # Get current directory
    current_dir = Path.cwd()

    try:
        # Get git status to see what files are available
        status = get_git_status(current_dir)

        if verbose:
            print(f"Working in: {current_dir}")
            print(f"Repository: {repo.repo_path}")

        staged_files = []
        skipped_files = []

        for file_pattern in files:
            if file_pattern == '.':
                # Add all files in current directory
                if verbose:
                    print("Adding all files in current directory...")

                # Get tracked files including untracked ones
                import os
                for root, dirs, files_list in os.walk(current_dir):
                    if '.git' in dirs:
                        dirs.remove('.git')

                    for file in files_list:
                        file_path = Path(root) / file
                        relative_path = file_path.relative_to(current_dir)

                        # Check if file should be ignored
                        patterns = get_combined_gitignore_patterns(current_dir)
                        if not _is_ignored(file_path, patterns):
                            staged_files.append(str(relative_path))
                        else:
                            skipped_files.append(str(relative_path))
            else:
                # Add specific file or pattern
                file_path = Path(file_pattern)
                if file_path.exists():
                    relative_path = file_path.relative_to(current_dir)
                    patterns = get_combined_gitignore_patterns(current_dir)
                    if not _is_ignored(file_path, patterns):
                        staged_files.append(str(relative_path))
                    else:
                        skipped_files.append(str(relative_path))
                else:
                    print(f"Warning: File not found: {file_pattern}")

        # Stage files using git
        if staged_files:
            import subprocess
            result = subprocess.run(
                ['git', 'add'] + staged_files,
                cwd=current_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"Error staging files: {result.stderr}")
                return 1

            if verbose:
                print(f"Staged {len(staged_files)} files:")
                for file in staged_files:
                    print(f"  {file}")
            else:
                print(f"Staged {len(staged_files)} files")

        if skipped_files and verbose:
            print(f"Skipped {len(skipped_files)} ignored files:")
            for file in skipped_files:
                print(f"  {file}")

        return 0

    except Exception as e:
        print(f"Error adding files: {e}")
        return 1


def _is_ignored(file_path: Path, patterns: set) -> bool:
    """Check if a file should be ignored."""
    file_name = file_path.name
    relative_path = str(file_path)

    for pattern in patterns:
        if pattern.endswith('/'):
            # Directory pattern
            if file_path.parent.name == pattern.rstrip('/'):
                return True
        elif pattern.startswith('*.'):
            # Extension pattern
            if file_name.endswith(pattern[1:]):
                return True
        elif pattern.startswith('/'):
            # Absolute path pattern
            if relative_path.startswith(pattern[1:]):
                return True
        else:
            # Simple pattern
            if pattern in file_name or pattern in relative_path:
                return True

    return False


def main(args: List[str]) -> int:
    """Main entry point for add command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree add',
        description='Stage files for commit respecting ignore rules'
    )
    parser.add_argument(
        'files',
        nargs='*',
        default=['.'],
        help='Files to stage (default: all files in current directory)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed output'
    )

    # Filter out ddworktree global args that we don't want to parse here
    filtered_args = []
    skip_next = False
    for i, arg in enumerate(args):
        if arg in ['--verbose', '-v']:
            continue  # Skip verbose as it's handled by parent
        elif arg.startswith('--') and i < len(args) - 1 and not args[i + 1].startswith('-'):
            skip_next = True
        elif skip_next:
            skip_next = False
            continue
        else:
            filtered_args.append(arg)

    parsed_args = parser.parse_args(filtered_args)

    try:
        repo = DDWorktreeRepo()
        return add_files(repo, parsed_args.files, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())