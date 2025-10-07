"""
Command for manually linking worktrees in ddworktree.
"""

import argparse
import sys
from pathlib import Path
from typing import List

from ddworktree.core import DDWorktreeRepo, DDWorktreeError


def pair_worktrees(
    repo: DDWorktreeRepo,
    treeA: str,
    treeB: str,
    force: bool = False,
    verbose: bool = False
) -> int:
    """Manually link two existing worktrees."""
    try:
        if verbose:
            print(f"Pairing worktrees:")
            print(f"  Tree A: {treeA}")
            print(f"  Tree B: {treeB}")

        # Convert to absolute paths
        pathA = Path(treeA).resolve()
        pathB = Path(treeB).resolve()

        # Validate both trees exist
        if not pathA.exists():
            print(f"Error: Worktree A does not exist: {pathA}")
            return 1

        if not pathB.exists():
            print(f"Error: Worktree B does not exist: {pathB}")
            return 1

        # Validate both are valid Git worktrees
        if not _is_valid_worktree(pathA):
            print(f"Error: Path A is not a valid Git worktree: {pathA}")
            return 1

        if not _is_valid_worktree(pathB):
            print(f"Error: Path B is not a valid Git worktree: {pathB}")
            return 1

        # Check if paths are already paired
        existing_pairs = repo.get_pairs()
        pair_name = None

        for name, (main, local) in existing_pairs.items():
            if (Path(main) == pathA and Path(local) == pathB) or \
               (Path(main) == pathB and Path(local) == pathA):
                pair_name = name
                break

        if pair_name and not force:
            print(f"Worktrees are already paired as '{pair_name}'")
            print("Use --force to override")
            return 1

        # Determine which is main and which is local
        local_suffix = repo.get_local_suffix()
        if local_suffix in pathB.name:
            main_path, local_path = str(pathA), str(pathB)
        elif local_suffix in pathA.name:
            main_path, local_path = str(pathB), str(pathA)
        else:
            # Neither has local suffix, ask user
            print("Neither worktree has the local suffix. Please specify:")
            print(f"1. {pathA.name} as main, {pathB.name} as local")
            print(f"2. {pathB.name} as main, {pathA.name} as local")

            while True:
                choice = input("Enter choice (1 or 2): ").strip()
                if choice == '1':
                    main_path, local_path = str(pathA), str(pathB)
                    break
                elif choice == '2':
                    main_path, local_path = str(pathB), str(pathA)
                    break
                else:
                    print("Please enter 1 or 2")

        # Generate pair name
        if not pair_name:
            pair_name = _generate_pair_name(main_path, local_path, existing_pairs)

        if verbose:
            print(f"Creating pair '{pair_name}':")
            print(f"  Main:  {main_path}")
            print(f"  Local: {local_path}")

        # Add the pair configuration
        repo.add_pair(pair_name, main_path, local_path)

        print(f"✅ Successfully paired worktrees as '{pair_name}'")
        return 0

    except Exception as e:
        print(f"Error pairing worktrees: {e}")
        return 1


def _is_valid_worktree(path: Path) -> bool:
    """Check if a path is a valid Git worktree."""
    try:
        # Check if it has a .git file (worktree) or .git directory (regular repo)
        git_file = path / '.git'
        git_dir = path / '.git'

        if git_file.exists():
            # It's a worktree - check if the gitdir points to a valid repo
            with open(git_file, 'r') as f:
                content = f.read().strip()
                if content.startswith('gitdir: '):
                    git_dir = Path(content[8:])
                    return (git_dir / 'HEAD').exists()
        elif git_dir.exists():
            # It's a regular repo - check if it has HEAD
            return (git_dir / 'HEAD').exists()

        return False

    except Exception:
        return False


def _generate_pair_name(main_path: str, local_path: str, existing_pairs: dict) -> str:
    """Generate a unique pair name."""
    # Extract directory names
    main_name = Path(main_path).name
    local_name = Path(local_path).name

    # Remove local suffix from local name
    local_suffix = '-local'  # Default suffix
    if local_name.endswith(local_suffix):
        base_name = local_name[:-len(local_suffix)]
    else:
        base_name = local_name

    # Try using the base name
    if base_name not in existing_pairs:
        return base_name

    # If already exists, add a number
    counter = 2
    while f"{base_name}{counter}" in existing_pairs:
        counter += 1

    return f"{base_name}{counter}"


def main(args: List[str]) -> int:
    """Main entry point for pair command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree pair',
        description='Manually link two existing worktrees'
    )
    parser.add_argument(
        'treeA',
        help='First worktree'
    )
    parser.add_argument(
        'treeB',
        help='Second worktree'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force pairing (override existing)'
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
        return pair_worktrees(repo, parsed_args.treeA, parsed_args.treeB, parsed_args.force, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())