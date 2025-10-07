"""
Command for cloning with paired worktrees in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

from ddworktree.core import DDWorktreeRepo, DDWorktreeError


def clone_with_worktrees(
    repo: DDWorktreeRepo,
    url: str,
    directory: Optional[str] = None,
    branch: Optional[str] = None,
    no_local: bool = False,
    verbose: bool = False
) -> int:
    """Clone repository and add paired local worktree."""
    try:
        if verbose:
            print(f"Cloning repository: {url}")

        # Determine target directory
        if directory:
            target_dir = Path(directory).resolve()
        else:
            # Extract repo name from URL
            repo_name = url.rstrip('/').split('/')[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            target_dir = Path.cwd() / repo_name

        if verbose:
            print(f"Target directory: {target_dir}")

        # Check if target directory exists
        if target_dir.exists():
            print(f"Error: Target directory already exists: {target_dir}")
            return 1

        # Create parent directory if needed
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        # Build clone command
        clone_args = ['git', 'clone']
        if branch:
            clone_args.extend(['--branch', branch])
        clone_args.extend([url, str(target_dir)])

        # Execute clone
        if verbose:
            print(f"Running: {' '.join(clone_args)}")

        result = subprocess.run(
            clone_args,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Error cloning repository: {result.stderr}")
            return 1

        if verbose:
            print("Clone successful")

        # Initialize ddworktree configuration in the cloned repo
        cloned_repo = DDWorktreeRepo(str(target_dir))

        # Create local worktree unless --no-local is specified
        if not no_local:
            local_suffix = cloned_repo.get_local_suffix()
            local_path = target_dir / (target_dir.name + local_suffix)

            if verbose:
                print(f"Creating local worktree: {local_path}")

            # Create local worktree from the same commit as main
            try:
                # Get current commit hash
                commit_result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=target_dir,
                    capture_output=True,
                    text=True
                )
                if commit_result.returncode == 0:
                    commit_hash = commit_result.stdout.strip()
                else:
                    commit_hash = None

                if commit_hash:
                    # Create worktree
                    cloned_repo.create_worktree(str(local_path), commit_hash)

                    # Create .gitignore-local
                    cloned_repo.create_local_gitignore(str(local_path))

                    # Add pair to configuration
                    pair_name = target_dir.name
                    cloned_repo.add_pair(pair_name, str(target_dir), str(local_path))

                    if verbose:
                        print(f"Created pair '{pair_name}':")
                        print(f"  Main:  {target_dir}")
                        print(f"  Local: {local_path}")
                else:
                    print("Warning: Could not get commit hash, skipping local worktree creation")

            except Exception as e:
                print(f"Error creating local worktree: {e}")

        print(f"✅ Successfully cloned repository to {target_dir}")
        if not no_local:
            print("Run 'ddworktree doctor' to verify setup")
        return 0

    except Exception as e:
        print(f"Error cloning with worktrees: {e}")
        return 1


def main(args: List[str]) -> int:
    """Main entry point for clone command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree clone',
        description='Clone repository and add paired worktree'
    )
    parser.add_argument(
        'url',
        help='Repository URL'
    )
    parser.add_argument(
        'directory',
        nargs='?',
        help='Target directory'
    )
    parser.add_argument(
        '--branch',
        help='Branch to checkout'
    )
    parser.add_argument(
        '--no-local',
        action='store_true',
        help='Do not create local worktree'
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
        return clone_with_worktrees(
            repo,
            parsed_args.url,
            parsed_args.directory,
            parsed_args.branch,
            parsed_args.no_local,
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