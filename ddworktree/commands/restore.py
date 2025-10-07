"""
Command for restoring worktrees in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

from ddworktree.core import DDWorktreeRepo, DDWorktreeError


def restore_worktree(
    repo: DDWorktreeRepo,
    tree: str,
    from_pair: Optional[str] = None,
    verbose: bool = False
) -> int:
    """Rebuild a missing or broken paired worktree."""
    try:
        if verbose:
            print(f"Restoring worktree: {tree}")

        # Determine which worktree to restore
        target_path = Path(tree).resolve()
        is_local = _is_local_worktree_name(target_path.name, repo)

        if verbose:
            worktree_type = "local" if is_local else "main"
            print(f"Target is a {worktree_type} worktree")

        # Find the source worktree
        source_path = _find_source_worktree(repo, target_path, from_pair, is_local, verbose)

        if not source_path:
            print("Error: Could not find source worktree for restoration")
            return 1

        if verbose:
            print(f"Source worktree: {source_path}")

        # Validate source worktree
        if not _is_valid_worktree(source_path):
            print(f"Error: Source worktree is not valid: {source_path}")
            return 1

        # Check if target already exists
        if target_path.exists():
            if verbose:
                print("Target worktree already exists")
            response = input("Overwrite existing worktree? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Restore cancelled")
                return 0

            # Remove existing worktree
            try:
                import shutil
                shutil.rmtree(target_path)
                if verbose:
                    print(f"Removed existing worktree: {target_path}")
            except Exception as e:
                print(f"Error removing existing worktree: {e}")
                return 1

        # Get current commit from source worktree
        commit_hash = _get_current_commit(source_path)
        if not commit_hash:
            print("Error: Could not get current commit from source worktree")
            return 1

        if verbose:
            print(f"Restoring from commit: {commit_hash[:8]}")

        # Create the worktree
        create_result = repo.create_worktree(str(target_path), commit_hash)
        if create_result != 0:
            print("Error creating worktree")
            return 1

        # Copy .gitignore-local if restoring local worktree
        if is_local:
            repo.create_local_gitignore(str(target_path))
            if verbose:
                print("Created .gitignore-local in restored worktree")

        # Update configuration if needed
        _update_configuration(repo, target_path, source_path, verbose)

        print(f"✅ Successfully restored worktree: {target_path}")
        return 0

    except Exception as e:
        print(f"Error restoring worktree: {e}")
        return 1


def _is_local_worktree_name(name: str, repo: DDWorktreeRepo) -> bool:
    """Check if a worktree name indicates it's a local worktree."""
    local_suffix = repo.get_local_suffix()
    return local_suffix in name


def _find_source_worktree(
    repo: DDWorktreeRepo,
    target_path: Path,
    from_pair: Optional[str],
    is_local: bool,
    verbose: bool
) -> Optional[Path]:
    """Find the source worktree for restoration."""
    pairs = repo.get_pairs()

    if from_pair:
        # Use specified pair
        if from_pair in pairs:
            main_path, local_path = pairs[from_pair]
            if is_local:
                return Path(main_path)
            else:
                return Path(local_path)
        else:
            print(f"Error: Pair '{from_pair}' not found")
            print("Available pairs:")
            for name, (main, local) in pairs.items():
                print(f"  {name}: {main} <-> {local}")
            return None
    else:
        # Auto-detect based on configuration
        target_name = target_path.name

        for pair_name, (main_path, local_path) in pairs.items():
            if is_local and target_path == Path(local_path):
                return Path(main_path)
            elif not is_local and target_path == Path(main_path):
                return Path(local_path)

        # Try to infer from naming convention
        local_suffix = repo.get_local_suffix()
        if is_local:
            # Target is local, look for main
            inferred_main = target_path.parent / target_path.name.replace(local_suffix, '')
            if inferred_main.exists() and _is_valid_worktree(inferred_main):
                return inferred_main
        else:
            # Target is main, look for local
            inferred_local = target_path.parent / (target_path.name + local_suffix)
            if inferred_local.exists() and _is_valid_worktree(inferred_local):
                return inferred_local

        # If no configured pair found, ask user
        print("No source worktree found in configuration.")
        print("Available worktrees:")

        available_worktrees = []
        # Check all configured worktrees
        for pair_name, (main_path, local_path) in pairs.items():
            main_exists = Path(main_path).exists()
            local_exists = Path(local_path).exists()

            if main_exists and _is_valid_worktree(Path(main_path)):
                available_worktrees.append((Path(main_path), f"{pair_name} (main)"))
            if local_exists and _is_valid_worktree(Path(local_path)):
                available_worktrees.append((Path(local_path), f"{pair_name} (local)"))

        # Also check main repository
        if _is_valid_worktree(repo.repo_path):
            available_worktrees.append((repo.repo_path, "Main repository"))

        if not available_worktrees:
            print("No valid worktrees found for restoration")
            return None

        for i, (path, desc) in enumerate(available_worktrees, 1):
            print(f"  {i}. {desc} ({path})")

        while True:
            try:
                choice = input("Select source worktree (number): ").strip()
                index = int(choice) - 1
                if 0 <= index < len(available_worktrees):
                    return available_worktrees[index][0]
                else:
                    print("Invalid selection")
            except (ValueError, KeyboardInterrupt):
                print("Invalid selection")
                return None


def _is_valid_worktree(path: Path) -> bool:
    """Check if a path is a valid Git worktree."""
    try:
        git_file = path / '.git'
        git_dir = path / '.git'

        if git_file.exists():
            with open(git_file, 'r') as f:
                content = f.read().strip()
                if content.startswith('gitdir: '):
                    git_dir = Path(content[8:])
                    return (git_dir / 'HEAD').exists()
        elif git_dir.exists():
            return (git_dir / 'HEAD').exists()

        return False

    except Exception:
        return False


def _get_current_commit(worktree_path: Path) -> Optional[str]:
    """Get the current commit hash from a worktree."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def _update_configuration(
    repo: DDWorktreeRepo,
    target_path: Path,
    source_path: Path,
    verbose: bool
) -> None:
    """Update configuration if the restored worktree needs to be paired."""
    # Check if the worktree should be paired
    pairs = repo.get_pairs()
    local_suffix = repo.get_local_suffix()

    # Determine if this should be a paired worktree
    target_is_local = local_suffix in target_path.name
    source_is_local = local_suffix in source_path.name

    # If one is local and one is main, they should be paired
    if target_is_local != source_is_local:
        # Find or create a pair name
        pair_name = None
        for name, (main, local) in pairs.items():
            if (Path(main) == source_path and Path(local) == target_path) or \
               (Path(main) == target_path and Path(local) == source_path):
                pair_name = name
                break

        if not pair_name:
            # Generate a pair name
            base_name = target_path.name.replace(local_suffix, '') if target_is_local else target_path.name
            counter = 1
            pair_name = base_name
            while pair_name in pairs:
                pair_name = f"{base_name}{counter}"
                counter += 1

        # Add or update the pair
        if target_is_local:
            repo.add_pair(pair_name, str(source_path), str(target_path))
        else:
            repo.add_pair(pair_name, str(target_path), str(source_path))

        if verbose:
            print(f"Updated configuration with pair '{pair_name}'")


def main(args: List[str]) -> int:
    """Main entry point for restore command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree restore',
        description='Restore a missing or broken worktree'
    )
    parser.add_argument(
        'tree',
        help='Worktree to restore'
    )
    parser.add_argument(
        '--from',
        dest='from_pair',
        help='Pair to restore from'
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
        return restore_worktree(repo, parsed_args.tree, parsed_args.from_pair, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())